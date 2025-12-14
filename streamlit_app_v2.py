"""
YOLO ROI Person Detector - Streamlit App v2

리팩토링된 구조:
- DetectionEngine: 앱 시작 시 자동 초기화, 계속 실행
- VideoSourceManager: 동적 소스 변경 지원
- ROI: 런타임 변경 가능
- ResultStorage: 검출 결과 저장 및 브라우징

참고자료:
- Streamlit: https://docs.streamlit.io/
- Ultralytics YOLO: https://docs.ultralytics.com/
"""

import streamlit as st
import cv2
import numpy as np
import time
from datetime import datetime
from pathlib import Path

# 로컬 모듈
from video_source_manager import (
    VideoSourceManager,
    SourceConfig,
    SourceType,
    create_source_config,
)
from detection_engine import DetectionEngine
from roi_utils import create_quadrant_rois, create_left_right_rois
from camera_utils import detect_available_cameras, format_camera_list_for_ui
from result_storage import ResultStorage, get_storage

# 페이지 설정
st.set_page_config(
    page_title="YOLO ROI Detector v2",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 세션 상태 초기화 및 엔진 관리
# ============================================================


def init_session_state():
    """세션 상태 초기화"""

    # 엔진 관련
    if "source_manager" not in st.session_state:
        st.session_state.source_manager = None

    if "detection_engine" not in st.session_state:
        st.session_state.detection_engine = None

    if "engines_initialized" not in st.session_state:
        st.session_state.engines_initialized = False

    # 결과 저장소
    if "result_storage" not in st.session_state:
        st.session_state.result_storage = None

    if "save_detections" not in st.session_state:
        st.session_state.save_detections = True  # 기본값: 저장 활성화

    # ROI 관련
    if "roi_regions" not in st.session_state:
        st.session_state.roi_regions = []

    # 소스 설정
    if "current_source_type" not in st.session_state:
        st.session_state.current_source_type = "none"

    if "current_source" not in st.session_state:
        st.session_state.current_source = None

    # 카메라 목록
    if "available_cameras" not in st.session_state:
        st.session_state.available_cameras = []

    # 설정
    if "config" not in st.session_state:
        st.session_state.config = {
            "yolo_model": "yolov8n.pt",
            "confidence_threshold": 0.5,
            "detection_interval": 1.0,
            "enable_face_analysis": True,
            "storage_base_path": "./detection_results",
            "storage_max_mb": 100,
        }

    # 브라우저 상태
    if "browser_selected_date" not in st.session_state:
        st.session_state.browser_selected_date = None

    if "browser_selected_source" not in st.session_state:
        st.session_state.browser_selected_source = None

    if "browser_selected_session" not in st.session_state:
        st.session_state.browser_selected_session = None

    if "browser_selected_frame" not in st.session_state:
        st.session_state.browser_selected_frame = None


def initialize_engines():
    """엔진 초기화 (앱 시작 시 1회)"""

    if st.session_state.engines_initialized:
        return True

    try:
        # VideoSourceManager 생성 및 시작
        if st.session_state.source_manager is None:
            st.session_state.source_manager = VideoSourceManager(frame_queue_size=5)
            st.session_state.source_manager.start()
            print("[App] ✅ VideoSourceManager 시작됨")

        # DetectionEngine 생성 및 시작
        if st.session_state.detection_engine is None:
            config = st.session_state.config
            st.session_state.detection_engine = DetectionEngine(
                source_manager=st.session_state.source_manager,
                yolo_model=config["yolo_model"],
                confidence_threshold=config["confidence_threshold"],
                detection_interval=config["detection_interval"],
                enable_face_analysis=config["enable_face_analysis"],
            )
            st.session_state.detection_engine.start()
            print("[App] ✅ DetectionEngine 시작됨")

        # ResultStorage 생성
        if st.session_state.result_storage is None:
            config = st.session_state.config
            st.session_state.result_storage = ResultStorage(
                base_path=config["storage_base_path"],
                max_size_mb=config["storage_max_mb"],
            )
            print("[App] ✅ ResultStorage 초기화됨")

        st.session_state.engines_initialized = True
        return True

    except Exception as e:
        st.error(f"엔진 초기화 실패: {e}")
        import traceback

        traceback.print_exc()
        return False


def change_source(source_type: str, source, **options):
    """비디오 소스 변경"""

    if st.session_state.source_manager is None:
        return False

    config = create_source_config(source_type, source, **options)
    st.session_state.source_manager.change_source(config)

    st.session_state.current_source_type = source_type
    st.session_state.current_source = source

    # 새 저장 세션 시작
    if st.session_state.result_storage and source_type != "none":
        source_name = str(source) if source else source_type
        st.session_state.result_storage.start_session(source_type, source_name)

    return True


def update_roi_regions(roi_regions):
    """ROI 영역 업데이트"""

    st.session_state.roi_regions = roi_regions

    if st.session_state.detection_engine:
        st.session_state.detection_engine.set_roi_regions(roi_regions)


def save_detection_result(result):
    """검출 결과 저장"""
    if not st.session_state.save_detections:
        return

    if st.session_state.result_storage is None:
        return

    if result is None or result.annotated_frame is None:
        return

    # 검출이 있을 때만 저장 (선택적)
    # if len(result.detections) == 0:
    #     return

    st.session_state.result_storage.save_detection(
        annotated_frame=result.annotated_frame,
        detections=result.detections,
        face_results=result.face_results,
    )


# ============================================================
# 초기화
# ============================================================

init_session_state()


# ============================================================
# 사이드바 - 설정
# ============================================================

st.sidebar.title("⚙️ 설정")

# 엔진 상태 표시
if st.session_state.engines_initialized:
    st.sidebar.success("✅ 엔진 실행 중")
else:
    st.sidebar.warning("⏳ 엔진 초기화 필요")
    if st.sidebar.button("🚀 엔진 시작"):
        with st.spinner("엔진 초기화 중..."):
            if initialize_engines():
                st.success("엔진이 시작되었습니다!")
                st.rerun()

st.sidebar.divider()

# ============================================================
# 비디오 소스 선택
# ============================================================

st.sidebar.subheader("📹 비디오 소스")

# 카메라 검색 버튼
if st.sidebar.button("🔍 카메라 검색"):
    with st.spinner("카메라 검색 중..."):
        st.session_state.available_cameras = detect_available_cameras(max_cameras=5)
    st.rerun()

# 소스 타입 선택
source_type = st.sidebar.radio(
    "소스 타입",
    ["없음", "USB 웹캠", "HTTP 스트림", "HTTP POST 수신", "RTSP 스트림", "비디오 파일"],
    key="source_type_radio",
)

# 소스별 설정
source_config = None

if source_type == "없음":
    source_config = ("none", None)
    st.sidebar.info("소스를 선택하세요")

elif source_type == "USB 웹캠":
    if st.session_state.available_cameras:
        camera_options = format_camera_list_for_ui(st.session_state.available_cameras)
        selected_idx = st.sidebar.selectbox(
            "카메라 선택",
            range(len(camera_options)),
            format_func=lambda x: camera_options[x],
        )
        camera_id = st.session_state.available_cameras[selected_idx]["index"]
        source_config = ("usb", camera_id)
    else:
        camera_id = st.sidebar.number_input(
            "카메라 인덱스", min_value=0, max_value=10, value=0
        )
        source_config = ("usb", camera_id)

elif source_type == "HTTP 스트림":
    url = st.sidebar.text_input(
        "HTTP Stream URL",
        value="http://10.10.11.83:81/stream",
        help="MJPEG 스트림 URL (예: http://IP:81/stream)",
    )
    source_config = ("http", url)
    st.sidebar.caption("💡 CoreS3 장비: http://장비IP:81/stream")

elif source_type == "HTTP POST 수신":
    port = st.sidebar.number_input(
        "수신 포트", min_value=1024, max_value=65535, value=8502
    )
    source_config = ("http_post", f":{port}", {"port": port})
    st.sidebar.info(f"📷 장비가 http://서버IP:{port}/upload/image 로 전송")

elif source_type == "RTSP 스트림":
    url = st.sidebar.text_input(
        "RTSP URL",
        value="rtsp://192.168.1.100:554/stream",
        help="RTSP 스트림 URL",
    )
    source_config = ("rtsp", url)

elif source_type == "비디오 파일":
    file_path = st.sidebar.text_input(
        "파일 경로",
        value="video.mp4",
        help="비디오 파일 경로",
    )
    source_config = ("file", file_path)

# 소스 적용 버튼
if st.sidebar.button("▶️ 소스 적용", disabled=not st.session_state.engines_initialized):
    if source_config:
        if len(source_config) == 3:
            success = change_source(
                source_config[0], source_config[1], **source_config[2]
            )
        else:
            success = change_source(source_config[0], source_config[1])

        if success:
            st.sidebar.success("✅ 소스 변경됨")
        else:
            st.sidebar.error("❌ 소스 변경 실패")

# 현재 소스 상태
if st.session_state.source_manager:
    stats = st.session_state.source_manager.get_stats()
    if stats["source_connected"]:
        st.sidebar.success(f"📡 연결됨: {stats['source_type']}")
        st.sidebar.caption(f"해상도: {stats['frame_width']}x{stats['frame_height']}")
    else:
        st.sidebar.warning("📡 연결 안됨")

st.sidebar.divider()

# ============================================================
# ROI 설정
# ============================================================

st.sidebar.subheader("🎯 ROI 설정")

col1, col2 = st.sidebar.columns(2)

with col1:
    if st.button("⬅️➡️ 좌/우"):
        rois = create_left_right_rois(normalized=True)
        update_roi_regions(rois)
        st.success("좌/우 ROI 생성됨")

with col2:
    if st.button("🔲 4사분면"):
        rois = create_quadrant_rois(normalized=True)
        update_roi_regions(rois)
        st.success("4사분면 ROI 생성됨")

if st.sidebar.button("🗑️ ROI 초기화"):
    update_roi_regions([])
    st.sidebar.success("ROI 초기화됨")

# ROI 목록 표시
if st.session_state.roi_regions:
    st.sidebar.caption(f"ROI: {len(st.session_state.roi_regions)}개")
    for roi in st.session_state.roi_regions:
        st.sidebar.text(f"  • {roi.get('id', 'unknown')}")

st.sidebar.divider()

# ============================================================
# 검출 설정
# ============================================================

st.sidebar.subheader("🔧 검출 설정")

# 신뢰도 임계값
confidence = st.sidebar.slider(
    "신뢰도 임계값",
    min_value=0.1,
    max_value=1.0,
    value=st.session_state.config["confidence_threshold"],
    step=0.05,
)
st.session_state.config["confidence_threshold"] = confidence

# 검출 간격
interval = st.sidebar.slider(
    "검출 간격 (초)",
    min_value=0.1,
    max_value=5.0,
    value=st.session_state.config["detection_interval"],
    step=0.1,
)
st.session_state.config["detection_interval"] = interval

# 얼굴 분석
face_analysis = st.sidebar.checkbox(
    "얼굴 분석 활성화",
    value=st.session_state.config["enable_face_analysis"],
)
st.session_state.config["enable_face_analysis"] = face_analysis

st.sidebar.divider()

# ============================================================
# 저장 설정
# ============================================================

st.sidebar.subheader("💾 저장 설정")

# 저장 활성화
st.session_state.save_detections = st.sidebar.checkbox(
    "검출 결과 저장",
    value=st.session_state.save_detections,
    help="검출된 이미지를 자동으로 저장합니다",
)

# 저장소 정보
if st.session_state.result_storage:
    storage_info = st.session_state.result_storage.get_storage_info()
    usage_percent = storage_info["usage_percent"]

    # 진행 바 색상
    if usage_percent > 90:
        st.sidebar.error(
            f"💾 {storage_info['used_mb']:.1f} / {storage_info['max_mb']} MB ({usage_percent:.0f}%)"
        )
    elif usage_percent > 70:
        st.sidebar.warning(
            f"💾 {storage_info['used_mb']:.1f} / {storage_info['max_mb']} MB ({usage_percent:.0f}%)"
        )
    else:
        st.sidebar.info(
            f"💾 {storage_info['used_mb']:.1f} / {storage_info['max_mb']} MB ({usage_percent:.0f}%)"
        )

    st.sidebar.progress(min(usage_percent / 100, 1.0))


# ============================================================
# 메인 영역 - 탭
# ============================================================

st.title("🎯 YOLO ROI Person Detector v2")

# 엔진 초기화되지 않았으면 안내
if not st.session_state.engines_initialized:
    st.info("👈 사이드바에서 '엔진 시작' 버튼을 눌러 시작하세요")
    st.stop()

# 탭 생성
tab_realtime, tab_browser = st.tabs(["📹 실시간 검출", "📁 결과 브라우저"])


# ============================================================
# 탭 1: 실시간 검출
# ============================================================

with tab_realtime:
    # 레이아웃
    col_video, col_status = st.columns([3, 1])

    with col_video:
        st.subheader("📹 실시간 영상")

        # 영상 플레이스홀더
        video_placeholder = st.empty()

        # 소스 연결 상태에 따른 표시
        if (
            st.session_state.source_manager
            and st.session_state.source_manager.is_connected()
        ):
            # 프레임 표시 루프
            if st.session_state.detection_engine:
                # 검출 결과 가져오기
                result = st.session_state.detection_engine.get_result(timeout=0.1)

                if result is not None:
                    # 검출 결과 저장
                    save_detection_result(result)

                    if result.annotated_frame is not None:
                        # BGR → RGB 변환
                        frame_rgb = cv2.cvtColor(
                            result.annotated_frame, cv2.COLOR_BGR2RGB
                        )
                        video_placeholder.image(
                            frame_rgb, channels="RGB", use_container_width=True
                        )
                else:
                    # 시각화 프레임만 가져오기
                    frame = st.session_state.detection_engine.get_annotated_frame(
                        timeout=0.1
                    )
                    if frame is not None:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        video_placeholder.image(
                            frame_rgb, channels="RGB", use_container_width=True
                        )
                    else:
                        video_placeholder.info("⏳ 프레임 대기 중...")
        else:
            video_placeholder.warning("📡 비디오 소스를 연결하세요")

    with col_status:
        st.subheader("📊 상태")

        # 엔진 통계
        if st.session_state.detection_engine:
            engine_stats = st.session_state.detection_engine.get_stats()

            st.metric("FPS", f"{engine_stats['current_fps']:.1f}")
            st.metric("처리 프레임", engine_stats["frames_processed"])
            st.metric("검출 수", engine_stats["detections_count"])
            st.metric("추론 시간", f"{engine_stats['inference_time_ms']:.1f}ms")

        st.divider()

        # ROI 상태
        st.caption("ROI 상태")
        if st.session_state.detection_engine:
            roi_states = st.session_state.detection_engine.get_roi_states()

            for roi_id, state in roi_states.items():
                if state["person_detected"]:
                    st.success(f"✅ {roi_id}: 사람 감지")
                else:
                    st.error(f"❌ {roi_id}: 비어있음")

        st.divider()

        # 저장 상태
        if st.session_state.result_storage and st.session_state.save_detections:
            storage_info = st.session_state.result_storage.get_storage_info()
            if storage_info["current_session"]:
                st.caption("💾 현재 세션")
                session_path = Path(storage_info["current_session"])
                st.text(
                    f"{session_path.parent.parent.name}/{session_path.parent.name}/{session_path.name}"
                )


# ============================================================
# 탭 2: 결과 브라우저
# ============================================================

with tab_browser:
    st.subheader("📁 저장된 검출 결과 브라우저")

    if st.session_state.result_storage is None:
        st.warning("저장소가 초기화되지 않았습니다")
    else:
        storage = st.session_state.result_storage

        # 저장소 정보
        storage_info = storage.get_storage_info()
        st.caption(f"📂 저장 경로: {storage_info['base_path']}")
        st.caption(
            f"💾 사용량: {storage_info['used_mb']:.1f} / {storage_info['max_mb']} MB"
        )

        st.divider()

        # 3단 레이아웃: 날짜/소스/세션 선택 | 이미지 그리드 | 상세 정보
        col_nav, col_grid, col_detail = st.columns([1, 2, 1])

        with col_nav:
            st.markdown("#### 📅 탐색")

            # 날짜 선택
            dates = storage.list_dates()
            if not dates:
                st.info("저장된 결과가 없습니다")
            else:
                # 날짜 포맷팅
                date_options = []
                for d in dates:
                    try:
                        formatted = datetime.strptime(d, "%Y%m%d").strftime("%Y-%m-%d")
                        date_options.append((d, formatted))
                    except:
                        date_options.append((d, d))

                selected_date_idx = st.selectbox(
                    "📅 날짜",
                    range(len(date_options)),
                    format_func=lambda x: date_options[x][1],
                    key="browser_date_select",
                )
                selected_date = (
                    date_options[selected_date_idx][0] if date_options else None
                )

                if selected_date:
                    # 소스 선택
                    sources = storage.list_sources_by_date(selected_date)
                    if sources:
                        selected_source = st.selectbox(
                            "📂 소스", sources, key="browser_source_select"
                        )

                        if selected_source:
                            # 세션 선택
                            sessions = storage.list_sessions_by_date_source(
                                selected_date, selected_source
                            )
                            if sessions:
                                session_options = []
                                for s in sessions:
                                    start_time = s.get("start_time", "")
                                    if start_time:
                                        try:
                                            dt = datetime.fromisoformat(start_time)
                                            time_str = dt.strftime("%H:%M:%S")
                                        except:
                                            time_str = s["session_id"]
                                    else:
                                        time_str = s["session_id"]

                                    label = f"{time_str} ({s['total_frames']}장, {s['size_mb']}MB)"
                                    session_options.append((s, label))

                                selected_session_idx = st.selectbox(
                                    "🕐 세션",
                                    range(len(session_options)),
                                    format_func=lambda x: session_options[x][1],
                                    key="browser_session_select",
                                )
                                selected_session = (
                                    session_options[selected_session_idx][0]
                                    if session_options
                                    else None
                                )

                                # 세션 삭제 버튼
                                if selected_session:
                                    if st.button("🗑️ 세션 삭제", key="delete_session"):
                                        if storage.delete_session(
                                            selected_session["path"]
                                        ):
                                            st.success("세션이 삭제되었습니다")
                                            st.rerun()
                                        else:
                                            st.error("삭제 실패")

        with col_grid:
            st.markdown("#### 🖼️ 이미지")

            # 세션이 선택되었으면 이미지 표시
            if "selected_session" in dir() and selected_session:
                frames = storage.list_frames(selected_session["path"])

                if not frames:
                    st.info("이미지가 없습니다")
                else:
                    # 이미지 그리드 (3열)
                    cols_per_row = 3

                    for i in range(0, len(frames), cols_per_row):
                        cols = st.columns(cols_per_row)
                        for j, col in enumerate(cols):
                            idx = i + j
                            if idx < len(frames):
                                frame_info = frames[idx]

                                with col:
                                    # 썸네일 이미지
                                    img = storage.load_frame_image(frame_info["path"])
                                    if img is not None:
                                        # 썸네일 크기로 리사이즈
                                        h, w = img.shape[:2]
                                        thumb_size = 150
                                        scale = thumb_size / max(h, w)
                                        thumb = cv2.resize(
                                            img, (int(w * scale), int(h * scale))
                                        )
                                        thumb_rgb = cv2.cvtColor(
                                            thumb, cv2.COLOR_BGR2RGB
                                        )

                                        # 이미지 클릭 버튼
                                        if st.button(
                                            f"#{idx+1}",
                                            key=f"frame_{idx}",
                                            help=f"검출: {frame_info.get('detections_count', 0)}명",
                                        ):
                                            st.session_state.browser_selected_frame = (
                                                frame_info
                                            )

                                        st.image(thumb_rgb, use_container_width=True)

                                        # 시간 표시
                                        captured_at = frame_info.get("captured_at", "")
                                        if captured_at:
                                            try:
                                                dt = datetime.fromisoformat(captured_at)
                                                st.caption(dt.strftime("%H:%M:%S"))
                                            except:
                                                pass
            else:
                st.info("👈 왼쪽에서 세션을 선택하세요")

        with col_detail:
            st.markdown("#### 📋 상세 정보")

            # 선택된 프레임 정보 표시
            selected_frame = st.session_state.browser_selected_frame

            if selected_frame:
                # 큰 이미지 표시
                img = storage.load_frame_image(selected_frame["path"])
                if img is not None:
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    st.image(img_rgb, use_container_width=True)

                # 메타데이터
                st.markdown("**캡처 시간**")
                captured_at = selected_frame.get("captured_at", "")
                if captured_at:
                    try:
                        dt = datetime.fromisoformat(captured_at)
                        st.text(dt.strftime("%Y-%m-%d %H:%M:%S"))
                    except:
                        st.text(captured_at)

                st.markdown("**검출 결과**")
                detections = selected_frame.get("detections", [])
                st.text(f"검출 인원: {len(detections)}명")

                for i, det in enumerate(detections):
                    conf = det.get("confidence", 0)
                    st.text(f"  #{i+1}: {det.get('class', 'person')} ({conf:.0%})")

                # 얼굴 분석 결과
                face_results = selected_frame.get("face_results", [])
                if face_results:
                    st.markdown("**표정 분석**")
                    for i, face in enumerate(face_results):
                        expr = face.get("expression", "unknown")
                        conf = face.get("expression_confidence", 0)
                        st.text(f"  #{i+1}: {expr} ({conf:.0%})")
            else:
                st.info("이미지를 선택하세요")


# ============================================================
# 자동 새로고침 (실시간 탭일 때만)
# ============================================================

# 실시간 탭이 활성화된 경우에만 새로고침
# (브라우저 탭에서는 새로고침하지 않음)
if st.session_state.source_manager and st.session_state.source_manager.is_connected():
    time.sleep(0.5)
    st.rerun()
