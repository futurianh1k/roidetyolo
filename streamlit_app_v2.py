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
import pandas as pd
import time
import uuid
import os
import requests
from datetime import datetime
from pathlib import Path

# API endpoint persistence (SQLite)
from api_endpoint_db import ApiEndpointDB

# API 전송 유틸리티 (통합 + 재시도 + 비동기)
from api_utils import send_api_event_async, send_to_multiple_endpoints

# 로컬 모듈
from video_source_manager import (
    VideoSourceManager,
    SourceConfig,
    SourceType,
    create_source_config,
)
from detection_engine import DetectionEngine
from roi_utils import (
    create_quadrant_rois,
    create_left_right_rois,
    create_fullscreen_roi,
    create_top_bottom_rois,
)
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
            # API 설정
            "api_endpoints": [],
            # 기본값은 운영에서 바로 쓸 수 있게 지정하되,
            # 환경변수(EMERGENCY_API_URL/EMERGENCY_WATCH_ID)가 있으면 그것을 우선한다.
            "api_base_url": os.getenv(
                "EMERGENCY_API_URL",
                "https://lukus.store/emergency/api/emergency/quick",
            ),
            "watch_id": os.getenv("EMERGENCY_WATCH_ID", "watch_1764653561585_7956"),
            "sender_id": os.getenv("EMERGENCY_SENDER_ID", "streamlit-app"),
            "image_base_url": os.getenv("IMAGE_BASE_URL", ""),
            "fcm_project_id": os.getenv("FCM_PROJECT_ID", "emergency-alert-system"),
            "api_send_on_absence": True,  # 부재 감지 시 API 전송 (기본: 활성화)
            "api_send_on_detection": True,  # 사람 검출 시 API 전송 (기본: 활성화)
            # 부재 판단 설정
            "absence_threshold": 10,  # 연속 미검출 횟수 기준
        }

    # DB (API 엔드포인트/설정 영구 저장)
    if "api_db" not in st.session_state:
        db_path = os.getenv(
            "STREAMLIT_API_DB_PATH",
            os.path.join(os.path.dirname(__file__), "streamlit_api.db"),
        )
        st.session_state.api_db = ApiEndpointDB(db_path=db_path)
        st.session_state.api_db.init()

    # 마지막 검출 결과 (상태 패널 표시용)
    if "last_detection_result" not in st.session_state:
        st.session_state.last_detection_result = None

    # API 테스트 상태
    if "test_api_response" not in st.session_state:
        st.session_state.test_api_response = None

    # 브라우저 상태
    if "browser_selected_date" not in st.session_state:
        st.session_state.browser_selected_date = None

    if "browser_selected_source" not in st.session_state:
        st.session_state.browser_selected_source = None

    if "browser_selected_session" not in st.session_state:
        st.session_state.browser_selected_session = None

    if "browser_selected_frame" not in st.session_state:
        st.session_state.browser_selected_frame = None

    # ROI 상태 추적 (부재 감지용)
    if "prev_roi_states" not in st.session_state:
        st.session_state.prev_roi_states = {}

    # ROI별 연속 미검출 카운터 (부재 판단용)
    if "absence_counters" not in st.session_state:
        st.session_state.absence_counters = {}  # {roi_id: count}

    # ROI별 부재 API 전송 여부 (중복 전송 방지)
    if "absence_api_sent" not in st.session_state:
        st.session_state.absence_api_sent = {}  # {roi_id: bool}

    # ROI별 연속 검출 카운터 (10회마다 재전송용)
    if "detection_counters" not in st.session_state:
        st.session_state.detection_counters = {}  # {roi_id: count}

    # API 전송 이력 (최근 100개 유지)
    if "api_history" not in st.session_state:
        st.session_state.api_history = (
            []
        )  # [{timestamp, note, event_type, roi_id, status_code, success}]


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

    # 저장 세션 관리
    if st.session_state.result_storage:
        if source_type == "none":
            # 소스 없음 선택 시 세션 종료
            st.session_state.result_storage.end_session()
        else:
            # 새 소스 선택 시 새 세션 시작
            source_name = str(source) if source else source_type
            st.session_state.result_storage.start_session(source_type, source_name)

    return True


def update_roi_regions(roi_regions):
    """ROI 영역 업데이트"""

    st.session_state.roi_regions = roi_regions

    if st.session_state.detection_engine:
        st.session_state.detection_engine.set_roi_regions(roi_regions)


def save_detection_result(result) -> str:
    """
    검출 결과 저장

    Returns:
        저장된 파일 경로 또는 None
    """
    if not st.session_state.save_detections:
        return None

    if st.session_state.result_storage is None:
        return None

    if result is None or result.annotated_frame is None:
        return None

    # 검출이 있을 때만 저장 (선택적)
    # if len(result.detections) == 0:
    #     return None

    saved_path = st.session_state.result_storage.save_detection(
        annotated_frame=result.annotated_frame,
        detections=result.detections,
        face_results=result.face_results,
    )

    return saved_path


def generate_note_message(
    event_type: str,
    roi_id: str,
    detections: list = None,
    face_results: dict = None,
) -> str:
    """
    검출 결과에 따른 Note 메시지 생성

    Args:
        event_type: 이벤트 타입 (absence, detection 등)
        roi_id: ROI ID
        detections: 검출된 객체 리스트
        face_results: 얼굴 분석 결과 딕셔너리 {bbox_tuple: result}

    Returns:
        str: Note 메시지

    메시지 규칙:
        1. 사람 미검출: "사람이 검출되지 않습니다"
        2. 사람 검출, 얼굴 미검출: "사람이 검출 되었습니다"
        3. 사람 검출, 얼굴 검출, 표정 분류됨: "감정 상태: {표정}"
    """
    # 검출이 없는 경우 (absence 이벤트)
    if event_type == "absence" or not detections or len(detections) == 0:
        return "사람이 검출되지 않습니다"

    # 사람이 검출된 경우
    person_count = len(detections)

    # 얼굴 분석 결과가 없는 경우
    if not face_results:
        if person_count == 1:
            return "사람이 검출 되었습니다"
        else:
            return f"사람 {person_count}명이 검출 되었습니다"

    # 얼굴 분석 결과가 있는 경우 - 표정 추출
    # face_results 형태 호환:
    # - DetectionEngine: Dict[tuple, Dict[str, Any]] (result["expression"] = {expression, confidence})
    # - Storage/Browser: List[{"expression": "...", "expression_confidence": 0.0~1.0}, ...]
    expressions = []
    if isinstance(face_results, dict):
        for _bbox_tuple, result in face_results.items():
            expr_info = (result or {}).get("expression", {}) or {}
            if isinstance(expr_info, dict):
                expression = expr_info.get("expression", "")
                confidence = float(expr_info.get("confidence", 0) or 0)
                if expression and confidence > 0.3:  # 신뢰도 30% 이상
                    # 영어 표정을 한글로 변환
                    expression_kr = {
                        "happy": "행복",
                        "sad": "슬픔",
                        "angry": "분노",
                        "surprise": "놀람",
                        "fear": "두려움",
                        "disgust": "혐오",
                        "neutral": "무표정",
                    }.get(str(expression).lower(), expression)
                    expressions.append(f"{expression_kr}({confidence*100:.0f}%)")
    elif isinstance(face_results, list):
        for face in face_results:
            expression = (face or {}).get("expression", "")
            confidence = float((face or {}).get("expression_confidence", 0) or 0)
            if expression and confidence > 0.3:
                expression_kr = {
                    "happy": "행복",
                    "sad": "슬픔",
                    "angry": "분노",
                    "surprise": "놀람",
                    "fear": "두려움",
                    "disgust": "혐오",
                    "neutral": "무표정",
                }.get(str(expression).lower(), expression)
                expressions.append(f"{expression_kr}({confidence*100:.0f}%)")

    if expressions:
        if len(expressions) == 1:
            return f"감정 상태: {expressions[0]}"
        else:
            return f"감정 상태: {', '.join(expressions)}"
    else:
        # 얼굴은 검출되었지만 표정 분류가 안된 경우
        return "사람이 검출 되었습니다 (표정 분석 불가)"


def send_api_alert(
    event_type: str,
    roi_id: str,
    image_path: str = None,
    force: bool = False,
    detections: list = None,
    face_results: dict = None,
) -> dict:
    """
    API 알림 전송 (리팩토링: api_utils 사용)

    Args:
        event_type: 이벤트 타입 (absence, detection, manual_test 등)
        roi_id: ROI ID
        image_path: 저장된 이미지 파일 경로 (선택)
        force: True면 설정 무시하고 강제 전송
        detections: 검출된 객체 리스트 (Note 메시지 생성용)
        face_results: 얼굴 분석 결과 (Note 메시지 생성용)

    Returns:
        dict: 전송 결과 {"success": bool, "results": list}
    """
    config = st.session_state.config

    # 이벤트 타입에 따른 전송 여부 확인 (force=True면 무시)
    if not force:
        if event_type == "absence" and not config.get("api_send_on_absence", False):
            return {
                "success": False,
                "results": [],
                "reason": "api_send_on_absence disabled",
            }
        if event_type == "detection" and not config.get("api_send_on_detection", False):
            return {
                "success": False,
                "results": [],
                "reason": "api_send_on_detection disabled",
            }

    watch_id = config.get("watch_id", "")
    sender_id = config.get("sender_id", "streamlit-app")
    api_base_url = config.get("api_base_url", "")

    # API 엔드포인트 목록 구성
    api_endpoints = []

    # 기본 API URL (base_url + watch_id)
    if api_base_url and watch_id:
        primary_url = f"{api_base_url.rstrip('/')}/{watch_id}"
        api_endpoints.append(
            {
                "name": "Primary API",
                "url": primary_url,
                "type": "multipart",
                "enabled": True,
            }
        )

    # 추가 등록된 엔드포인트
    extra_endpoints = config.get("api_endpoints", [])
    enabled_extras = [ep for ep in extra_endpoints if ep.get("enabled", True)]
    api_endpoints.extend(enabled_extras)

    if not api_endpoints:
        return {
            "success": False,
            "results": [],
            "reason": "no API configured (set api_base_url + watch_id)",
        }

    # 이벤트 ID 생성
    event_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()

    # 이미지 URL 생성
    image_url = None
    image_base_url = config.get("image_base_url", os.getenv("IMAGE_BASE_URL", ""))
    if image_base_url:
        image_filename = f"emergency_{event_id.split('-')[0]}.jpeg"
        image_url = f"{image_base_url}/{image_filename}"

    # FCM Message ID 생성
    fcm_project = config.get("fcm_project_id", "emergency-alert-system")
    fcm_message_id = f"projects/{fcm_project}/messages/{int(time.time() * 1000)}"

    # Note 메시지 생성
    note_message = generate_note_message(
        event_type=event_type,
        roi_id=roi_id,
        detections=detections,
        face_results=face_results,
    )

    # 이벤트 데이터 구성
    event_data = {
        "eventId": event_id,
        "fcmMessageId": fcm_message_id,
        "imageUrl": image_url,
        "status": "SENT",
        "createdAt": timestamp,
        "watchId": watch_id,
        "senderId": sender_id,
        "eventType": event_type,
        "roiId": roi_id,
        "note": note_message,
    }

    # 🚀 새로운 통합 API 전송 함수 사용 (비동기 + 재시도)
    api_results = send_to_multiple_endpoints(
        endpoints=api_endpoints,
        event_data=event_data,
        image_path=image_path,
        timeout=10,  # 5초 → 10초로 증가
        retry_count=3,  # 재시도 3회
        async_mode=True,  # 비동기 전송 (빠름)
    )

    # 결과 변환 (기존 형식 호환)
    results = []
    for api_result in api_results:
        endpoint_name = api_result["endpoint_name"]
        result = api_result["result"]

        formatted_result = {
            "endpoint": endpoint_name,
            "url": next((ep["url"] for ep in api_endpoints if ep["name"] == endpoint_name), ""),
            "success": result.get("success", False),
            "status_code": result.get("status_code"),
            "response_text": result.get("response_text", ""),
            "error": result.get("error"),
        }
        results.append(formatted_result)

        # API 전송 이력 저장
        history_entry = {
            "timestamp": timestamp,
            "event_type": event_type,
            "roi_id": roi_id or "",
            "note": note_message,
            "endpoint_name": endpoint_name,
            "status_code": result.get("status_code"),
            "success": result.get("success", False),
            "error": result.get("error"),
        }

        # 세션 상태에 이력 추가 (최근 100개 유지)
        if "api_history" in st.session_state:
            st.session_state.api_history.insert(0, history_entry)
            st.session_state.api_history = st.session_state.api_history[:100]

    # 전체 결과 반환
    success_count = sum(1 for r in results if r["success"])
    return {
        "success": success_count > 0,
        "results": results,
        "total": len(results),
        "success_count": success_count,
        "note": note_message,
    }


# ============================================================
# 초기화
# ============================================================

init_session_state()


def _ensure_api_defaults_and_load_from_db():
    """
    - 기존 세션이 이미 config를 갖고 있더라도, 값이 비어있으면 기본값으로 채움
    - DB에 저장된 base_url/watch_id 및 엔드포인트 목록을 로드하여 config에 반영
    """
    config = st.session_state.config
    api_db: ApiEndpointDB = st.session_state.api_db

    # 1) DB에 값이 있으면 우선 적용
    db_base_url = api_db.get_kv("api_base_url")
    db_watch_id = api_db.get_kv("watch_id")
    db_sender_id = api_db.get_kv("sender_id")
    db_send_on_absence = api_db.get_kv("api_send_on_absence")
    db_send_on_detection = api_db.get_kv("api_send_on_detection")

    if db_base_url is not None:
        config["api_base_url"] = db_base_url
    if db_watch_id is not None:
        config["watch_id"] = db_watch_id
    if db_sender_id is not None:
        config["sender_id"] = db_sender_id
    if db_send_on_absence is not None:
        config["api_send_on_absence"] = db_send_on_absence == "1"
    if db_send_on_detection is not None:
        config["api_send_on_detection"] = db_send_on_detection == "1"

    # 2) 그래도 비어있다면(초기 실행/이전 세션), 기본값 주입
    if not config.get("api_base_url"):
        config["api_base_url"] = "https://lukus.store/emergency/api/emergency/quick"
    if not config.get("watch_id"):
        config["watch_id"] = "watch_1764653561585_7956"

    # 3) 엔드포인트 로드 (DB가 우선)
    endpoints = api_db.list_endpoints()
    config["api_endpoints"] = [
        {
            "id": e["id"],
            "name": e["name"],
            "url": e["url"],
            "enabled": bool(e["enabled"]),
            "method": e.get("method", "POST"),
            "type": e.get("type", "multipart"),
        }
        for e in endpoints
    ]


_ensure_api_defaults_and_load_from_db()


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

# 소스 적용/중단 버튼
col_apply, col_stop = st.sidebar.columns(2)

with col_apply:
    if st.button(
        "▶️ 적용",
        disabled=not st.session_state.engines_initialized or source_config is None,
        key="apply_source_btn",
    ):
        if source_config:
            if len(source_config) == 3:
                success = change_source(
                    source_config[0], source_config[1], **source_config[2]
                )
            else:
                success = change_source(source_config[0], source_config[1])

            if success:
                st.success("✅")
            else:
                st.error("❌")

with col_stop:
    # 소스가 연결되어 있을 때만 중단 버튼 활성화
    is_connected = (
        st.session_state.source_manager
        and st.session_state.source_manager.get_stats()["source_connected"]
    )
    if st.button("⏹️ 중단", disabled=not is_connected, key="stop_source_btn"):
        change_source("none", None)
        st.success("⏹️")
        st.rerun()

# 현재 소스 상태
if st.session_state.source_manager:
    stats = st.session_state.source_manager.get_stats()
    if stats["source_connected"]:
        st.sidebar.success(f"📡 연결됨: {stats['source_type']}")
        st.sidebar.caption(f"해상도: {stats['frame_width']}x{stats['frame_height']}")
    elif st.session_state.current_source_type != "none":
        st.sidebar.warning("📡 연결 시도 중...")
    else:
        st.sidebar.info("📡 대기 중")

st.sidebar.divider()

# ============================================================
# ROI 설정
# ============================================================

st.sidebar.subheader("🎯 ROI 설정")

# ROI 프리셋 버튼들 (2행 3열)
roi_col1, roi_col2, roi_col3 = st.sidebar.columns(3)

with roi_col1:
    if st.button("📺 전체", help="전체 화면"):
        rois = create_fullscreen_roi(normalized=True)
        update_roi_regions(rois)
        st.success("전체 ROI")

with roi_col2:
    if st.button("⬅️➡️ 좌우", help="좌/우 2분할"):
        rois = create_left_right_rois(normalized=True)
        update_roi_regions(rois)
        st.success("좌/우 ROI")

with roi_col3:
    if st.button("⬆️⬇️ 상하", help="상/하 2분할"):
        rois = create_top_bottom_rois(normalized=True)
        update_roi_regions(rois)
        st.success("상/하 ROI")

roi_col4, roi_col5, roi_col6 = st.sidebar.columns(3)

with roi_col4:
    if st.button("🔲 4분면", help="4사분면"):
        rois = create_quadrant_rois(normalized=True)
        update_roi_regions(rois)
        st.success("4사분면 ROI")

with roi_col5:
    pass  # 빈 공간

with roi_col6:
    if st.button("🗑️ 초기화", help="ROI 초기화"):
        update_roi_regions([])
        st.success("초기화됨")

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

# 검출 간격 (10초~60초 선택 가능)
interval_options = [0.5, 1.0, 2.0, 5.0, 10.0, 15.0, 20.0, 30.0, 45.0, 60.0]
interval_labels = {
    0.5: "0.5초",
    1.0: "1초",
    2.0: "2초",
    5.0: "5초",
    10.0: "10초",
    15.0: "15초",
    20.0: "20초",
    30.0: "30초",
    45.0: "45초",
    60.0: "1분",
}

# 현재 값에 가장 가까운 옵션 찾기
current_interval = st.session_state.config["detection_interval"]
closest_idx = min(
    range(len(interval_options)),
    key=lambda i: abs(interval_options[i] - current_interval),
)

interval_idx = st.sidebar.select_slider(
    "검출 간격",
    options=range(len(interval_options)),
    value=closest_idx,
    format_func=lambda i: interval_labels[interval_options[i]],
)
st.session_state.config["detection_interval"] = interval_options[interval_idx]

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

st.sidebar.divider()

# ============================================================
# API 설정
# ============================================================

st.sidebar.subheader("🌐 API 설정")

config = st.session_state.config
api_db: ApiEndpointDB = st.session_state.api_db

# API Base URL
config["api_base_url"] = st.sidebar.text_input(
    "API Base URL",
    config.get("api_base_url", ""),
    help="API 기본 URL (예: http://server:8080/api/emergency)",
)
api_db.set_kv("api_base_url", config.get("api_base_url", ""))

# Watch ID
config["watch_id"] = st.sidebar.text_input(
    "Watch ID",
    config.get("watch_id", ""),
    help="워치 ID - API URL에 자동 추가됨",
)
api_db.set_kv("watch_id", config.get("watch_id", ""))

# 최종 API URL 표시
if config["api_base_url"] and config["watch_id"]:
    final_api_url = f"{config['api_base_url'].rstrip('/')}/{config['watch_id']}"
    st.sidebar.caption(f"📡 API URL: `{final_api_url}`")

# Sender ID
config["sender_id"] = st.sidebar.text_input(
    "Sender ID",
    config.get("sender_id", "streamlit-app"),
    help="발신자 ID",
)
api_db.set_kv("sender_id", config.get("sender_id", ""))

# 검출 판단 기준 슬라이더
st.sidebar.markdown("---")
st.sidebar.markdown("**🔍 검출 판단 설정**")

config["detection_threshold"] = st.sidebar.slider(
    "검출 판단 기준 (연속 검출 횟수)",
    min_value=1,
    max_value=100,
    value=config.get("detection_threshold", 10),
    help="사람이 연속으로 N회 검출되면 재전송",
)
st.sidebar.caption(
    f"💡 사람이 {config['detection_threshold']}회 연속 검출되면 검출 API 재전송"
)

# 부재 판단 기준 슬라이더
st.sidebar.markdown("---")
st.sidebar.markdown("**🔍 부재 판단 설정**")

config["absence_threshold"] = st.sidebar.slider(
    "부재 판단 기준 (연속 미검출 횟수)",
    min_value=1,
    max_value=100,
    value=config.get("absence_threshold", 10),
    help="사람이 연속으로 N회 검출되지 않으면 재전송",
)
st.sidebar.caption(
    f"💡 사람이 {config['absence_threshold']}회 연속 미검출되면 부재 API 재전송"
)

st.sidebar.markdown("---")

# 사람 검출 시 API 전송 (기본: 활성화)
config["api_send_on_detection"] = st.sidebar.checkbox(
    "✅ 사람 검출 시 API 전송",
    value=config.get("api_send_on_detection", True),
    help="ROI 영역에서 사람이 나타나면 API 전송",
)
api_db.set_kv("api_send_on_detection", "1" if config["api_send_on_detection"] else "0")

# 부재 감지 시 API 전송 (기본: 활성화)
config["api_send_on_absence"] = st.sidebar.checkbox(
    "✅ 부재 감지 시 API 전송",
    value=config.get("api_send_on_absence", True),
    help="ROI 영역에서 사람이 사라지면 API 전송",
)
api_db.set_kv("api_send_on_absence", "1" if config["api_send_on_absence"] else "0")

# 고급 설정
with st.sidebar.expander("🔧 고급 API 설정", expanded=False):
    config["image_base_url"] = st.text_input(
        "Image Base URL",
        config.get("image_base_url", ""),
        help="이미지 URL 생성용 기본 URL (예: http://server:8080/api/images)",
    )

    config["fcm_project_id"] = st.text_input(
        "FCM Project ID",
        config.get("fcm_project_id", "emergency-alert-system"),
        help="Firebase Cloud Messaging 프로젝트 ID",
    )

# API 엔드포인트 관리
with st.sidebar.expander("🔗 API 엔드포인트 관리", expanded=False):
    if "api_endpoints" not in config:
        config["api_endpoints"] = []

    api_endpoints = config["api_endpoints"]
    api_db: ApiEndpointDB = st.session_state.api_db

    if api_endpoints:
        st.markdown("**📋 등록된 API**")

        # 전체 활성/비활성 버튼
        col_all_on, col_all_off = st.columns(2)
        with col_all_on:
            if st.button("✅ 전체 활성", key="api_all_on"):
                for ep in api_endpoints:
                    ep["enabled"] = True
                    if ep.get("id"):
                        api_db.update_endpoint(int(ep["id"]), enabled=True)
                st.rerun()
        with col_all_off:
            if st.button("⬜ 전체 비활성", key="api_all_off"):
                for ep in api_endpoints:
                    ep["enabled"] = False
                    if ep.get("id"):
                        api_db.update_endpoint(int(ep["id"]), enabled=False)
                st.rerun()

        st.markdown("---")

        # API 목록 (체크박스로 선택)
        for i, endpoint in enumerate(api_endpoints):
            enabled = st.checkbox(
                f"**{endpoint.get('name', f'API {i+1}')}**",
                value=endpoint.get("enabled", True),
                key=f"api_enabled_{i}",
                help=endpoint.get("url", ""),
            )
            config["api_endpoints"][i]["enabled"] = enabled
            if endpoint.get("id"):
                api_db.update_endpoint(int(endpoint["id"]), enabled=enabled)

            col_info, col_del = st.columns([4, 1])
            with col_info:
                st.caption(
                    f"🔗 {endpoint.get('url', '')[:35]}... ({endpoint.get('type', 'json')})"
                )
            with col_del:
                if st.button("🗑️", key=f"delete_api_{i}", help="삭제"):
                    if endpoint.get("id"):
                        api_db.delete_endpoint(int(endpoint["id"]))
                    config["api_endpoints"].pop(i)
                    st.rerun()

        # 활성화된 API 수 표시
        enabled_count = sum(1 for ep in api_endpoints if ep.get("enabled", True))
        st.info(f"✅ {enabled_count}/{len(api_endpoints)}개 API 활성화됨")

    else:
        st.info("등록된 API가 없습니다")

    st.markdown("---")

    # 새 API 추가
    st.markdown("**➕ 새 API 추가**")
    new_api_name = st.text_input("이름", "Emergency API", key="new_api_name")
    new_api_url = st.text_input(
        "URL",
        "http://localhost:8000/api/emergency",
        key="new_api_url",
    )
    new_api_type = st.selectbox(
        "타입",
        ["multipart", "json"],  # multipart를 기본값으로 (첫 번째)
        index=0,  # multipart 선택
        key="new_api_type",
        help="multipart: 이미지 포함 전송 (권장), json: JSON 데이터만 전송",
    )

    if st.button("➕ API 추가", key="add_api_btn"):
        new_id = api_db.insert_endpoint(
            name=new_api_name,
            url=new_api_url,
            method="POST",
            endpoint_type=new_api_type,
            enabled=True,
        )
        config["api_endpoints"].append(
            {
                "id": new_id,
                "name": new_api_name,
                "url": new_api_url,
                "enabled": True,
                "method": "POST",
                "type": new_api_type,
            }
        )
        st.success(f"✅ {new_api_name} 추가됨!")
        st.rerun()


# ============================================================
# 메인 영역 - 탭
# ============================================================

st.title("🎯 YOLO ROI Person Detector v2")

# 엔진 초기화되지 않았으면 안내
if not st.session_state.engines_initialized:
    st.info("👈 사이드바에서 '엔진 시작' 버튼을 눌러 시작하세요")
    st.stop()

# 탭 생성
tab_realtime, tab_browser, tab_api = st.tabs(
    ["📹 실시간 검출", "📁 결과 브라우저", "🔗 API 테스트"]
)


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
                    # 상태 패널에서 참조할 수 있도록 마지막 결과 저장
                    st.session_state.last_detection_result = {
                        "timestamp": result.timestamp,
                        "detections": result.detections,
                        "face_results": result.face_results,
                        "note_preview": generate_note_message(
                            event_type="detection",
                            roi_id="",
                            detections=result.detections,
                            face_results=result.face_results,
                        ),
                    }

                    # 검출 결과 저장 및 경로 받기
                    saved_image_path = save_detection_result(result)

                    # ROI 상태 변화 감지 및 API 전송
                    if result.roi_states:
                        detection_threshold = config.get("detection_threshold", 10)
                        absence_threshold = config.get("absence_threshold", 10)

                        for roi_id, state in result.roi_states.items():
                            prev_state = st.session_state.prev_roi_states.get(
                                roi_id, {}
                            )
                            prev_detected = prev_state.get("person_detected", False)
                            curr_detected = state.get("person_detected", False)

                            # 카운터 초기화
                            if roi_id not in st.session_state.absence_counters:
                                st.session_state.absence_counters[roi_id] = 0
                            if roi_id not in st.session_state.detection_counters:
                                st.session_state.detection_counters[roi_id] = 0

                            # 사람이 검출된 경우
                            if curr_detected:
                                # 부재 카운터 리셋
                                st.session_state.absence_counters[roi_id] = 0

                                # 검출 카운터 증가
                                st.session_state.detection_counters[roi_id] += 1
                                detection_count = st.session_state.detection_counters[roi_id]

                                # 첫 검출(카운터=1) 또는 N회 도달 시 API 전송
                                if detection_count == 1 or detection_count >= detection_threshold:
                                    if config.get("api_send_on_detection", True):
                                        send_api_alert(
                                            event_type="detection",
                                            roi_id=roi_id,
                                            image_path=saved_image_path,
                                            detections=result.detections,
                                            face_results=result.face_results,
                                        )

                                        # N회 도달 시 카운터 리셋 (다음에 다시 1부터 시작)
                                        if detection_count >= detection_threshold:
                                            st.session_state.detection_counters[roi_id] = 0
                                            print(
                                                f"[Detection] ROI {roi_id}: {detection_threshold}회 연속 검출 → API 재전송"
                                            )
                                        else:
                                            print(f"[Detection] ROI {roi_id}: 첫 검출 → API 전송")

                            else:
                                # 사람이 검출되지 않은 경우
                                # 검출 카운터 리셋
                                st.session_state.detection_counters[roi_id] = 0

                                # 부재 카운터 증가
                                st.session_state.absence_counters[roi_id] += 1
                                absence_count = st.session_state.absence_counters[roi_id]

                                # 첫 미검출(카운터=1) 또는 N회 도달 시 API 전송
                                if absence_count == 1 or absence_count >= absence_threshold:
                                    if config.get("api_send_on_absence", True):
                                        send_api_alert(
                                            event_type="absence",
                                            roi_id=roi_id,
                                            image_path=saved_image_path,
                                            detections=None,  # 부재 시 검출 없음
                                            face_results=None,
                                        )

                                        # N회 도달 시 카운터 리셋 (다음에 다시 1부터 시작)
                                        if absence_count >= absence_threshold:
                                            st.session_state.absence_counters[roi_id] = 0
                                            print(
                                                f"[Absence] ROI {roi_id}: {absence_threshold}회 연속 미검출 → API 재전송"
                                            )
                                        else:
                                            print(f"[Absence] ROI {roi_id}: 첫 미검출 → API 전송")

                        # 상태 업데이트
                        st.session_state.prev_roi_states = result.roi_states.copy()

                    if result.annotated_frame is not None:
                        try:
                            # 프레임 복사 후 BGR → RGB 변환 (캐시 안전성)
                            frame_copy = result.annotated_frame.copy()
                            frame_rgb = cv2.cvtColor(frame_copy, cv2.COLOR_BGR2RGB)
                            video_placeholder.image(
                                frame_rgb, channels="RGB", width="stretch"
                            )
                        except Exception:
                            pass  # 이미지 캐시 오류 무시
                else:
                    # 시각화 프레임만 가져오기
                    frame = st.session_state.detection_engine.get_annotated_frame(
                        timeout=0.1
                    )
                    if frame is not None:
                        try:
                            frame_copy = frame.copy()
                            frame_rgb = cv2.cvtColor(frame_copy, cv2.COLOR_BGR2RGB)
                            video_placeholder.image(
                                frame_rgb, channels="RGB", width="stretch"
                            )
                        except Exception:
                            pass  # 이미지 캐시 오류 무시
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
        detection_threshold = config.get("detection_threshold", 10)
        absence_threshold = config.get("absence_threshold", 10)

        if st.session_state.detection_engine:
            roi_states = st.session_state.detection_engine.get_roi_states()

            for roi_id, state in roi_states.items():
                absence_count = st.session_state.absence_counters.get(roi_id, 0)
                detection_count = st.session_state.detection_counters.get(roi_id, 0)

                if state["person_detected"]:
                    # 검출 상태 표시 (카운터 포함)
                    progress = detection_count / detection_threshold
                    st.success(f"✅ {roi_id}: 사람 감지 ({detection_count}/{detection_threshold})")
                    if detection_count > 0:
                        st.progress(min(progress, 1.0))
                else:
                    # 미검출 상태 표시 (카운터 포함)
                    progress = absence_count / absence_threshold
                    if absence_count > 0:
                        st.warning(
                            f"⏳ {roi_id}: 미검출 ({absence_count}/{absence_threshold})"
                        )
                        st.progress(min(progress, 1.0))
                    else:
                        st.info(f"ℹ️ {roi_id}: 대기 중")

        st.divider()

        # 얼굴/표정 (마지막 검출 결과 기준)
        st.caption("🙂 얼굴/표정")
        last = st.session_state.get("last_detection_result")
        if not last:
            st.info("최근 검출 결과 없음")
        else:
            detections = last.get("detections") or []
            face_results = last.get("face_results") or {}

            # 사람 수
            person_count = 0
            for d in detections:
                try:
                    if d.get("class_name") == "person":
                        person_count += 1
                except Exception:
                    pass
            st.text(f"사람: {person_count}명")

            # Note 미리보기(= API로 보낼 메시지 규칙과 동일)
            st.text(f"Note: {last.get('note_preview', '')}")

            # 표정 요약
            expr_msg = generate_note_message(
                event_type="detection",
                roi_id="",
                detections=detections,
                face_results=face_results,
            )
            if expr_msg.startswith("감정 상태:"):
                st.success(expr_msg)
            else:
                st.info(expr_msg)

        # 저장 상태
        if st.session_state.result_storage and st.session_state.save_detections:
            storage_info = st.session_state.result_storage.get_storage_info()
            if storage_info["current_session"]:
                st.caption("💾 현재 세션")
                session_path = Path(storage_info["current_session"])
                st.text(
                    f"{session_path.parent.parent.name}/{session_path.parent.name}/{session_path.name}"
                )

        st.divider()

        # 테스트 API 전송 버튼
        st.caption("🔗 API 테스트")

        config = st.session_state.config
        api_endpoints = config.get("api_endpoints", [])
        primary_ready = bool(config.get("api_base_url") and config.get("watch_id"))
        enabled_extras = sum(1 for ep in api_endpoints if ep.get("enabled", True))
        enabled_count = enabled_extras + (1 if primary_ready else 0)

        if enabled_count == 0:
            st.warning("활성화된 API 없음")
        else:
            st.text(f"활성 API: {enabled_count}개")

            # 저장된 최신 이미지 경로 가져오기
            latest_image_path = None
            if st.session_state.result_storage:
                storage_info = st.session_state.result_storage.get_storage_info()
                if storage_info["current_session"]:
                    session_path = Path(storage_info["current_session"])
                    # 최신 이미지 찾기
                    images = sorted(session_path.glob("frame_*.jpg"))
                    if images:
                        latest_image_path = str(images[-1])

            col_btn1, col_btn2 = st.columns(2)

            with col_btn1:
                if st.button(
                    "🧪 테스트 전송", help="저장된 최신 이미지로 테스트 API 전송"
                ):
                    # ROI가 있으면 첫 번째 ROI 사용
                    roi_id = "test_roi"
                    if st.session_state.detection_engine:
                        roi_states = st.session_state.detection_engine.get_roi_states()
                        if roi_states:
                            roi_id = list(roi_states.keys())[0]

                    result = send_api_alert(
                        event_type="manual_test",
                        roi_id=roi_id,
                        image_path=latest_image_path,
                        force=True,
                    )

                    if result["success"]:
                        st.success(
                            f"✅ {result['success_count']}/{result['total']} 성공"
                        )
                    else:
                        if result.get("reason"):
                            st.error(f"❌ {result['reason']}")
                        else:
                            st.error(f"❌ 전송 실패")

            with col_btn2:
                if latest_image_path:
                    st.caption(f"📷 {Path(latest_image_path).name}")
                else:
                    st.caption("📷 저장된 이미지 없음")


# ============================================================
# 탭 2: 결과 브라우저
# ============================================================

with tab_browser:
    # 상단: API 전송 이력 표시
    st.subheader("📡 API 전송 이력")

    api_history = st.session_state.get("api_history", [])

    if not api_history:
        st.info("📭 아직 API 전송 이력이 없습니다")
    else:
        # 이력 개수 및 클리어 버튼
        col_hist_info, col_hist_clear = st.columns([3, 1])
        with col_hist_info:
            st.caption(f"📊 최근 {len(api_history)}건의 전송 이력")
        with col_hist_clear:
            if st.button("🗑️ 이력 삭제", key="clear_api_history"):
                st.session_state.api_history = []
                st.rerun()

        # 테이블 형태로 표시
        # 데이터 준비
        history_data = []
        for h in api_history[:20]:  # 최근 20건만 표시
            # 시간 포맷팅
            try:
                dt = datetime.fromisoformat(h.get("timestamp", ""))
                time_str = dt.strftime("%H:%M:%S")
            except:
                time_str = "N/A"

            # 상태 아이콘
            if h.get("success"):
                status_icon = "✅"
            elif h.get("error") == "Timeout":
                status_icon = "⏱️"
            elif h.get("error") == "Connection Error":
                status_icon = "🔌"
            else:
                status_icon = "❌"

            status_code = h.get("status_code")
            status_text = (
                f"{status_icon} {status_code}"
                if status_code
                else f"{status_icon} {h.get('error', 'Error')}"
            )

            history_data.append(
                {
                    "시간": time_str,
                    "이벤트": h.get("event_type", ""),
                    "ROI": h.get("roi_id", ""),
                    "메시지 (Note)": h.get("note", "")[:50]
                    + ("..." if len(h.get("note", "")) > 50 else ""),
                    "응답": status_text,
                }
            )

        # DataFrame으로 표시
        if history_data:
            df = pd.DataFrame(history_data)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "시간": st.column_config.TextColumn("시간", width="small"),
                    "이벤트": st.column_config.TextColumn("이벤트", width="small"),
                    "ROI": st.column_config.TextColumn("ROI", width="small"),
                    "메시지 (Note)": st.column_config.TextColumn(
                        "메시지 (Note)", width="large"
                    ),
                    "응답": st.column_config.TextColumn("응답", width="small"),
                },
            )

        # 더 많은 이력이 있으면 안내
        if len(api_history) > 20:
            st.caption(f"💡 최근 20건만 표시됨 (전체 {len(api_history)}건)")

    st.divider()

    # 하단: 저장된 검출 결과 브라우저
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

        # 세션 관리 섹션
        with st.expander("🗑️ 세션 관리 (일괄 삭제)", expanded=False):
            all_sessions = storage.list_sessions()

            if not all_sessions:
                st.info("저장된 세션이 없습니다")
            else:
                st.markdown(f"**총 {len(all_sessions)}개 세션**")

                # 세션 선택을 위한 상태 초기화
                if "sessions_to_delete" not in st.session_state:
                    st.session_state.sessions_to_delete = set()

                # 전체 선택/해제
                col_select_all, col_delete_all = st.columns(2)
                with col_select_all:
                    if st.button("☑️ 전체 선택"):
                        st.session_state.sessions_to_delete = {
                            s["path"] for s in all_sessions
                        }
                        st.rerun()
                with col_delete_all:
                    if st.button("⬜ 전체 해제"):
                        st.session_state.sessions_to_delete = set()
                        st.rerun()

                st.markdown("---")

                # 세션 목록 (체크박스)
                for session in all_sessions:
                    session_path = session["path"]
                    start_time = session.get("start_time", "")
                    source_type = session.get("source_type", "unknown")

                    # 시간 포맷팅
                    if start_time:
                        try:
                            dt = datetime.fromisoformat(start_time)
                            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                        except:
                            time_str = session["session_id"]
                    else:
                        time_str = session["session_id"]

                    label = f"📂 {source_type} | {time_str} | {session['total_frames']}장 | {session['size_mb']}MB"

                    is_selected = session_path in st.session_state.sessions_to_delete
                    if st.checkbox(
                        label,
                        value=is_selected,
                        key=f"session_check_{session_path}",
                    ):
                        st.session_state.sessions_to_delete.add(session_path)
                    else:
                        st.session_state.sessions_to_delete.discard(session_path)

                st.markdown("---")

                # 선택된 세션 삭제
                selected_count = len(st.session_state.sessions_to_delete)
                if selected_count > 0:
                    st.warning(f"⚠️ {selected_count}개 세션이 선택됨")

                    if st.button(
                        f"🗑️ 선택된 {selected_count}개 세션 삭제",
                        type="primary",
                    ):
                        deleted_count = 0
                        failed_sessions = []

                        for session_path in list(st.session_state.sessions_to_delete):
                            success, message = storage.delete_session(session_path)
                            if success:
                                deleted_count += 1
                            else:
                                failed_sessions.append((session_path, message))

                        st.session_state.sessions_to_delete = set()

                        if deleted_count > 0:
                            st.success(f"✅ {deleted_count}개 세션 삭제 완료!")

                        if failed_sessions:
                            for path, msg in failed_sessions:
                                st.error(f"❌ 삭제 실패: {Path(path).name} - {msg}")

                        st.rerun()

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
                                        success, message = storage.delete_session(
                                            selected_session["path"]
                                        )
                                        if success:
                                            st.success(f"✅ 세션 삭제됨: {message}")
                                            st.rerun()
                                        else:
                                            st.error(f"❌ 삭제 실패: {message}")

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

                                        st.image(thumb_rgb, width="stretch")

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
                    st.image(img_rgb, width="stretch")

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
# 탭 3: API 테스트
# ============================================================

with tab_api:
    st.subheader("🔗 API 엔드포인트 테스트")

    col_api_form, col_api_result = st.columns([1, 1])

    with col_api_form:
        st.markdown("#### 📤 테스트 요청")

        config = st.session_state.config
        api_endpoints = config.get("api_endpoints", [])

        # API 목록 구성 (Primary API 포함)
        available_apis = []

        # 1. Primary API (base_url + watch_id) - 기본 타입: multipart (이미지 첨부 지원)
        api_base_url = config.get("api_base_url", "")
        watch_id = config.get("watch_id", "")
        if api_base_url:
            primary_url = (
                f"{api_base_url.rstrip('/')}/{watch_id}" if watch_id else api_base_url
            )
            available_apis.append(
                {
                    "name": "✅ Primary API (Base URL + Watch ID)",
                    "url": primary_url,
                    "type": "multipart",  # 기본 타입: multipart (이미지 첨부 지원)
                    "enabled": True,
                    "is_primary": True,
                }
            )

        # 2. 활성화된 추가 API들
        enabled_endpoints = [ep for ep in api_endpoints if ep.get("enabled", True)]
        available_apis.extend(enabled_endpoints)

        if not available_apis:
            st.warning(
                "⚠️ 사용 가능한 API가 없습니다.\n\n"
                "• **Primary API**: 사이드바에서 'API Base URL'과 'Watch ID'를 설정하세요\n"
                "• **추가 API**: 사이드바 'API 엔드포인트 관리'에서 API를 추가하세요"
            )
        else:
            # API 선택
            api_options = [
                f"{ep.get('name', 'Unknown')} ({ep.get('type', 'json')})"
                for ep in available_apis
            ]
            selected_api_idx = st.selectbox(
                "테스트할 API",
                range(len(api_options)),
                format_func=lambda x: api_options[x],
            )
            selected_api = available_apis[selected_api_idx]

            st.info(f"**URL**: {selected_api['url']}")
            st.info(f"**Type**: {selected_api.get('type', 'json')}")

            st.markdown("---")

            # 테스트 데이터
            test_watch_id = st.text_input(
                "Watch ID",
                config.get("watch_id", "watch_1764653561585_7956"),
                key="test_watch_id",
            )
            test_sender_id = st.text_input(
                "Sender ID",
                config.get("sender_id", "streamlit-app"),
                key="test_sender_id",
            )
            test_note = st.text_area(
                "Note (메시지)",
                "테스트 알림 메시지입니다.",
                key="test_note",
            )

            # 이미지 첨부 옵션
            st.markdown("**📷 이미지 첨부**")

            image_source = st.radio(
                "이미지 소스",
                ["없음", "최근 검출 이미지", "직접 업로드"],
                horizontal=True,
                key="test_image_source",
            )

            test_image_data = None
            test_image_name = None

            if image_source == "최근 검출 이미지":
                # 저장소에서 최근 이미지 가져오기
                if st.session_state.result_storage:
                    latest_path = (
                        st.session_state.result_storage.get_latest_image_path()
                    )
                    if latest_path and os.path.exists(latest_path):
                        st.success(f"✅ 최근 이미지: {os.path.basename(latest_path)}")
                        # 이미지 미리보기
                        try:
                            preview_img = cv2.imread(latest_path)
                            if preview_img is not None:
                                preview_rgb = cv2.cvtColor(
                                    preview_img, cv2.COLOR_BGR2RGB
                                )
                                st.image(
                                    preview_rgb, width=200, caption="첨부할 이미지"
                                )
                                with open(latest_path, "rb") as f:
                                    test_image_data = f.read()
                                test_image_name = os.path.basename(latest_path)
                        except Exception as e:
                            st.warning(f"이미지 로드 실패: {e}")
                    else:
                        st.warning("⚠️ 저장된 검출 이미지가 없습니다")
                else:
                    st.warning("⚠️ 저장소가 초기화되지 않았습니다")

            elif image_source == "직접 업로드":
                uploaded_file = st.file_uploader(
                    "이미지 파일",
                    type=["jpg", "jpeg", "png"],
                    key="test_image_upload",
                )
                if uploaded_file:
                    test_image_data = uploaded_file.getvalue()
                    test_image_name = uploaded_file.name
                    st.image(test_image_data, width=200, caption="업로드된 이미지")

            # 테스트 실행
            if st.button("🚀 API 테스트 실행", type="primary"):
                try:
                    with st.spinner("API 호출 중..."):
                        api_url = selected_api["url"]

                        # watchId 치환
                        if "{watchId}" in api_url:
                            api_url = api_url.replace("{watchId}", test_watch_id)

                        if selected_api.get("type") == "json":
                            # JSON 방식 (이미지 없이 전송)
                            event_data = {
                                "eventId": str(uuid.uuid4()),
                                "watchId": test_watch_id,
                                "senderId": test_sender_id,
                                "note": test_note,
                                "createdAt": datetime.now().isoformat(),
                                "status": "TEST",
                                "eventType": "test",
                                "hasImage": test_image_data is not None,
                            }

                            response = requests.post(
                                api_url,
                                json=event_data,
                                headers={"Content-Type": "application/json"},
                                timeout=10,
                            )
                            request_data = event_data

                        else:
                            # Multipart 방식 (이미지 포함 전송)
                            form_data = {
                                "senderId": test_sender_id,
                                "note": test_note,
                                "watchId": test_watch_id,
                                "eventType": "test",
                            }

                            files = None
                            if test_image_data:
                                files = {
                                    "image": (
                                        test_image_name or "test_image.jpg",
                                        test_image_data,
                                        "image/jpeg",
                                    )
                                }

                            response = requests.post(
                                api_url,
                                data=form_data,
                                files=files,
                                timeout=10,
                            )
                            request_data = {
                                "url": api_url,
                                "senderId": test_sender_id,
                                "note": test_note,
                                "watchId": test_watch_id,
                                "image": test_image_name or "(없음)",
                            }

                    # 결과 저장
                    st.session_state.test_api_response = {
                        "status_code": response.status_code,
                        "response_text": response.text,
                        "request_data": request_data,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }

                    if response.status_code in [200, 201]:
                        st.success(
                            f"✅ API 호출 성공! (Status: {response.status_code})"
                        )
                    else:
                        st.error(f"⚠️ API 호출 실패 (Status: {response.status_code})")

                except requests.exceptions.Timeout:
                    st.error("❌ 타임아웃: API 응답이 없습니다.")
                    st.session_state.test_api_response = {
                        "error": "Timeout",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                except requests.exceptions.ConnectionError:
                    st.error("❌ 연결 오류: API 서버에 연결할 수 없습니다.")
                    st.session_state.test_api_response = {
                        "error": "Connection Error",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                except Exception as e:
                    st.error(f"❌ 오류 발생: {str(e)}")
                    st.session_state.test_api_response = {
                        "error": str(e),
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }

    with col_api_result:
        st.markdown("#### 📋 테스트 결과")

        if st.session_state.test_api_response:
            result = st.session_state.test_api_response

            st.markdown(f"**테스트 시간**: {result.get('timestamp', 'N/A')}")
            st.markdown("---")

            if "error" in result:
                st.error(f"**오류**: {result['error']}")
            else:
                # 상태 코드
                status_code = result.get("status_code", 0)
                if status_code in [200, 201]:
                    st.success(f"**Status Code**: {status_code}")
                else:
                    st.error(f"**Status Code**: {status_code}")

                # 요청 데이터
                st.markdown("**요청 데이터**")
                st.json(result.get("request_data", {}))

                # 응답
                st.markdown("**응답**")
                response_text = result.get("response_text", "")
                try:
                    import json

                    response_json = json.loads(response_text)
                    st.json(response_json)
                except:
                    st.code(
                        response_text[:500]
                        if len(response_text) > 500
                        else response_text
                    )

            # 결과 초기화 버튼
            if st.button("🗑️ 결과 초기화"):
                st.session_state.test_api_response = None
                st.rerun()
        else:
            st.info("API 테스트를 실행하면 결과가 여기에 표시됩니다.")

    # API 형식 예시
    st.markdown("---")
    with st.expander("💡 API 형식 예시"):
        st.markdown(
            """
        **JSON 방식** (`application/json`):
        ```json
        {
            "eventId": "uuid",
            "watchId": "watch_001",
            "senderId": "streamlit-app",
            "note": "알림 메시지",
            "createdAt": "2024-12-14T15:30:00",
            "status": "SENT"
        }
        ```

        **Multipart 방식** (`multipart/form-data`):
        ```
        POST /api/emergency/quick/{watchId}
        Content-Type: multipart/form-data

        senderId: test-user
        note: 응급상황 메시지
        image: (파일)
        ```
        """
        )


# ============================================================
# 자동 새로고침 (실시간 탭일 때만)
# ============================================================

# 실시간 탭이 활성화된 경우에만 새로고침
# (브라우저 탭에서는 새로고침하지 않음)
if st.session_state.source_manager and st.session_state.source_manager.is_connected():
    time.sleep(0.5)
    st.rerun()
