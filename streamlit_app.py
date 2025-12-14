"""
Streamlit 기반 YOLO ROI 사람 검출 시스템
- 웹 브라우저 기반 UI
- ROI 영역 편집 기능
- 실시간 검출 및 모니터링
"""

import streamlit as st
import cv2
import numpy as np
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
import requests
from ultralytics import YOLO
import threading
from collections import deque
from PIL import Image
import io

# 이미지 좌표 클릭 라이브러리 (선택적)
try:
    from streamlit_image_coordinates import streamlit_image_coordinates

    IMAGE_COORDINATES_AVAILABLE = True
except ImportError:
    IMAGE_COORDINATES_AVAILABLE = False
    print("[Streamlit] ⚠️  streamlit-image-coordinates 없음 - 수동 좌표 입력 사용")

# 유틸리티 함수 임포트
from camera_utils import (
    detect_available_cameras,
    format_camera_list_for_ui,
    get_camera_frame,
)
from roi_utils import (
    create_quadrant_rois,
    create_left_right_rois,
    validate_roi,
    get_roi_center,
    denormalize_roi,
    denormalize_rois,
)
from realtime_detector import RealtimeDetector

# 페이지 설정
st.set_page_config(
    page_title="YOLO ROI Person Detector",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 세션 상태 초기화
if "config" not in st.session_state:
    st.session_state.config = None
if "roi_regions" not in st.session_state:
    st.session_state.roi_regions = []
if "current_points" not in st.session_state:
    st.session_state.current_points = []
if "editing_mode" not in st.session_state:
    st.session_state.editing_mode = False
if "detection_running" not in st.session_state:
    st.session_state.detection_running = False
if "event_log" not in st.session_state:
    st.session_state.event_log = deque(maxlen=50)
if "detection_stats" not in st.session_state:
    st.session_state.detection_stats = {}
if "selected_roi_idx" not in st.session_state:
    st.session_state.selected_roi_idx = None
if "api_endpoints" not in st.session_state:
    st.session_state.api_endpoints = []
if "test_api_response" not in st.session_state:
    st.session_state.test_api_response = None
if "available_cameras" not in st.session_state:
    st.session_state.available_cameras = []
if "camera_detected" not in st.session_state:
    st.session_state.camera_detected = False
if "detector" not in st.session_state:
    st.session_state.detector = None
if "custom_roi_mode" not in st.session_state:
    st.session_state.custom_roi_mode = False
if "custom_roi_image" not in st.session_state:
    st.session_state.custom_roi_image = None
if "face_analysis_stats" not in st.session_state:
    st.session_state.face_analysis_stats = {
        "total_faces_detected": 0,
        "expressions": {
            "neutral": 0,
            "happy": 0,
            "sad": 0,
            "surprised": 0,
            "pain": 0,
            "angry": 0,
        },
        "eyes_open_count": 0,
        "eyes_closed_count": 0,
        "mouth_closed_count": 0,
        "mouth_speaking_count": 0,
        "mouth_wide_open_count": 0,
        "mask_detected_count": 0,
        "last_expression": None,
        "last_update": None,
    }


def load_config():
    """config.json 파일 로드"""
    config_path = Path("config.json")
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

            # ROI 데이터 정규화 (rectangle → polygon 변환)
            if "roi_regions" in config:
                config["roi_regions"] = [
                    normalize_roi_format(roi) for roi in config["roi_regions"]
                ]

            return config
    else:
        # 기본 설정
        return {
            "yolo_model": "yolov8n.pt",
            "camera_source": 0,
            "frame_width": 1280,
            "frame_height": 720,
            "confidence_threshold": 0.5,
            "detection_interval_seconds": 1.0,
            "presence_threshold_seconds": 5,
            "absence_threshold_seconds": 3,
            "count_interval_seconds": 1,
            "enable_face_analysis": False,
            "face_analysis_roi_only": True,
            "api_endpoints": [
                {
                    "name": "Emergency Alert API (JSON)",
                    "url": "http://10.10.11.23:10008/api/emergency/quick",
                    "enabled": True,
                    "method": "POST",
                    "type": "json",
                },
                {
                    "name": "Emergency Alert API (Multipart)",
                    "url": "http://10.10.11.23:10008/api/emergency/quick/{watchId}",
                    "enabled": True,
                    "method": "POST",
                    "type": "multipart",
                },
            ],
            "watch_id": "watch_1760663070591_8022",
            "include_image_url": True,
            "image_base_url": "http://10.10.11.79:8080/api/images",
            "fcm_project_id": "emergency-alert-system-f27e6",
            "roi_regions": [],
        }


def save_config(config):
    """config.json 파일 저장"""
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def normalize_roi_format(roi):
    """
    ROI 데이터를 polygon 형식으로 정규화
    - rectangle 형식 (x, y, width, height) → polygon 형식 (points)
    - 이미 polygon 형식이면 그대로 반환
    - 정규화된 좌표(points_normalized)가 있으면 그대로 유지
    """
    # 정규화된 좌표가 있으면 그대로 반환
    if roi.get("normalized", False) and "points_normalized" in roi:
        return roi

    if "points" in roi:
        # 이미 polygon 형식
        return roi

    # rectangle 형식 → polygon 변환
    if "x" in roi and "y" in roi and "width" in roi and "height" in roi:
        x, y, w, h = roi["x"], roi["y"], roi["width"], roi["height"]
        roi["points"] = [
            [x, y],  # 좌상단
            [x + w, y],  # 우상단
            [x + w, y + h],  # 우하단
            [x, y + h],  # 좌하단
        ]
        roi["type"] = "polygon"

    return roi


def draw_polygon_on_frame(frame, points, color=(0, 255, 0), thickness=2):
    """프레임에 다각형 그리기"""
    if len(points) < 2:
        return frame

    frame_copy = frame.copy()
    points_array = np.array(points, dtype=np.int32)

    # 점이 3개 이상이면 다각형 그리기
    if len(points) >= 3:
        # 반투명 채우기
        overlay = frame_copy.copy()
        cv2.fillPoly(overlay, [points_array], color)
        cv2.addWeighted(overlay, 0.3, frame_copy, 0.7, 0, frame_copy)

        # 테두리
        cv2.polylines(frame_copy, [points_array], True, color, thickness)
    else:
        # 2개 이하의 점이면 선만 그리기
        cv2.polylines(frame_copy, [points_array], False, color, thickness)

    # 꼭지점 표시
    for i, point in enumerate(points):
        cv2.circle(frame_copy, tuple(point), 5, color, -1)
        cv2.putText(
            frame_copy,
            str(i + 1),
            (point[0] + 10, point[1] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2,
        )

    return frame_copy


def draw_all_rois(frame, roi_regions, selected_idx=None):
    """모든 ROI 영역 그리기 (정규화된 좌표 자동 변환)"""
    frame_copy = frame.copy()
    frame_height, frame_width = frame.shape[:2]

    for i, roi in enumerate(roi_regions):
        # 선택된 ROI는 다른 색상
        color = (255, 255, 0) if i == selected_idx else (0, 255, 0)

        # 정규화된 좌표라면 현재 프레임 크기로 변환
        if roi.get("normalized", False) and "points_normalized" in roi:
            roi = denormalize_roi(roi, frame_width, frame_height)

        if roi.get("type") == "polygon" and "points" in roi:
            points = roi["points"]
            points_array = np.array(points, dtype=np.int32)

            # 반투명 채우기
            overlay = frame_copy.copy()
            cv2.fillPoly(overlay, [points_array], color)
            cv2.addWeighted(overlay, 0.2, frame_copy, 0.8, 0, frame_copy)

            # 테두리
            cv2.polylines(frame_copy, [points_array], True, color, 2)

            # ROI ID 표시 (중심점에)
            M = cv2.moments(points_array)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                cv2.putText(
                    frame_copy,
                    roi["id"],
                    (cx - 30, cy),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (255, 255, 255),
                    3,
                )
                cv2.putText(
                    frame_copy,
                    roi["id"],
                    (cx - 30, cy),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    color,
                    2,
                )

    return frame_copy


def is_point_in_polygon(point, polygon_points):
    """점이 다각형 내부에 있는지 확인"""
    points_array = np.array(polygon_points, dtype=np.int32)
    result = cv2.pointPolygonTest(points_array, tuple(point), False)
    return result >= 0


# 사이드바 - 설정 패널
st.sidebar.title("⚙️ 설정")

# Config 로드
if st.session_state.config is None:
    st.session_state.config = load_config()
    st.session_state.roi_regions = st.session_state.config.get("roi_regions", [])

config = st.session_state.config

# 모델 설정
st.sidebar.subheader("🤖 YOLO 모델")
model_options = ["yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt"]
config["yolo_model"] = st.sidebar.selectbox(
    "모델 선택",
    model_options,
    index=model_options.index(config.get("yolo_model", "yolov8n.pt")),
)

# 카메라 설정
st.sidebar.subheader("📹 카메라")

# 카메라 자동 검색 버튼
if st.sidebar.button("🔍 카메라 자동 검색"):
    with st.spinner("카메라 검색 중..."):
        st.session_state.available_cameras = detect_available_cameras(max_cameras=5)
        st.session_state.camera_detected = True

    if st.session_state.available_cameras:
        st.sidebar.success(
            f"✅ {len(st.session_state.available_cameras)}개의 카메라 발견!"
        )
    else:
        st.sidebar.warning("⚠️ 카메라를 찾을 수 없습니다")

# 카메라 소스 타입 선택
camera_type = st.sidebar.radio(
    "소스 타입",
    ["USB 웹캠", "RTSP 스트림", "HTTP 스트림", "비디오 파일", "기타"],
    help="다양한 카메라 입력 소스를 지원합니다",
)

if camera_type == "USB 웹캠":
    config["camera_source_type"] = "usb"

    if st.session_state.available_cameras:
        # 검색된 카메라 목록에서 선택
        camera_options = format_camera_list_for_ui(st.session_state.available_cameras)
        selected_camera_idx = st.sidebar.selectbox(
            "카메라 선택",
            range(len(camera_options)),
            format_func=lambda x: camera_options[x],
        )
        config["camera_source"] = st.session_state.available_cameras[
            selected_camera_idx
        ]["index"]

        # 카메라 정보 표시
        cam = st.session_state.available_cameras[selected_camera_idx]
        st.sidebar.info(
            f"**해상도**: {cam['resolution'][0]}x{cam['resolution'][1]}\n\n"
            f"**FPS**: {cam['fps']:.0f}"
        )
    else:
        # 카메라 번호 직접 입력
        config["camera_source"] = st.sidebar.number_input(
            "웹캠 번호",
            0,
            10,
            (
                int(config.get("camera_source", 0))
                if isinstance(config.get("camera_source"), int)
                else 0
            ),
        )
        st.sidebar.info(
            "💡 '카메라 자동 검색' 버튼을 클릭하면 사용 가능한 카메라를 자동으로 찾습니다."
        )

elif camera_type == "RTSP 스트림":
    config["camera_source_type"] = "rtsp"
    config["camera_source"] = st.sidebar.text_input(
        "RTSP URL",
        (
            config.get(
                "camera_source", "rtsp://admin:password@192.168.1.100:554/stream1"
            )
            if isinstance(config.get("camera_source"), str)
            and config.get("camera_source", "").startswith("rtsp://")
            else "rtsp://admin:password@192.168.1.100:554/stream1"
        ),
        help="예: rtsp://username:password@ip:port/stream",
    )
    st.sidebar.caption("💡 예제:")
    st.sidebar.code("rtsp://admin:1234@192.168.1.100:554/stream1", language="text")
    st.sidebar.info(
        "⚠️ RTSP는 네트워크 지연이 있을 수 있습니다. detection_interval을 조정하세요."
    )

elif camera_type == "HTTP 스트림":
    config["camera_source_type"] = "http"
    config["camera_source"] = st.sidebar.text_input(
        "HTTP Stream URL",
        (
            config.get("camera_source", "http://192.168.1.100:8080/video")
            if isinstance(config.get("camera_source"), str)
            and config.get("camera_source", "").startswith("http")
            else "http://192.168.1.100:8080/video"
        ),
        help="HTTP MJPEG 스트림 URL",
    )
    st.sidebar.caption("💡 예제:")
    st.sidebar.code("http://192.168.1.100:8080/video", language="text")

elif camera_type == "비디오 파일":
    config["camera_source_type"] = "file"
    config["camera_source"] = st.sidebar.text_input(
        "비디오 파일 경로",
        (
            config.get("camera_source", "video.mp4")
            if isinstance(config.get("camera_source"), str)
            and not config.get("camera_source", "").startswith(("rtsp://", "http://"))
            else "video.mp4"
        ),
        help="로컬 비디오 파일 경로 (.mp4, .avi, .mkv 등)",
    )
    st.sidebar.caption("💡 지원 형식: MP4, AVI, MKV, MOV 등")

else:  # 기타
    config["camera_source_type"] = st.sidebar.selectbox(
        "고급 소스 타입",
        ["image_sequence", "gstreamer"],
        help="이미지 시퀀스 또는 GStreamer 파이프라인",
    )

    if config["camera_source_type"] == "image_sequence":
        config["camera_source"] = st.sidebar.text_input(
            "이미지 시퀀스 패턴",
            config.get("camera_source", "/path/to/images/frame_%04d.jpg"),
            help="예: /path/to/images/frame_%04d.jpg",
        )
        st.sidebar.caption("💡 %04d는 숫자 형식 (0001, 0002, ...)")
    else:  # gstreamer
        config["camera_source"] = st.sidebar.text_area(
            "GStreamer 파이프라인",
            config.get("camera_source", "videotestsrc ! videoconvert ! appsink"),
            help="커스텀 GStreamer 파이프라인",
        )
        st.sidebar.caption("💡 GStreamer가 설치되어 있어야 합니다")

# 검출 임계값
st.sidebar.subheader("🎯 검출 설정")
config["detection_interval_seconds"] = st.sidebar.select_slider(
    "🔄 YOLO 검출 간격 (초)",
    options=[0.5, 1.0, 2.0, 3.0, 5.0],
    value=float(config.get("detection_interval_seconds", 1.0)),
    help="YOLO 추론을 실행하는 간격입니다. 간격을 늘리면 CPU/GPU 사용량이 줄어듭니다.",
)
st.sidebar.caption(f"💡 {config['detection_interval_seconds']}초마다 사람 검출")

config["confidence_threshold"] = st.sidebar.slider(
    "신뢰도 임계값", 0.0, 1.0, float(config.get("confidence_threshold", 0.5)), 0.05
)
config["presence_threshold_seconds"] = st.sidebar.number_input(
    "존재 확인 시간 (초)", 1, 60, int(config.get("presence_threshold_seconds", 5))
)
config["absence_threshold_seconds"] = st.sidebar.number_input(
    "부재 확인 시간 (초)", 1, 60, int(config.get("absence_threshold_seconds", 3))
)

# 얼굴 분석 설정
st.sidebar.subheader("😊 얼굴 분석")
config["enable_face_analysis"] = st.sidebar.checkbox(
    "얼굴 분석 활성화",
    config.get("enable_face_analysis", False),
    help="MediaPipe Face Mesh를 사용한 실시간 얼굴 분석 (눈/입 상태, 표정, 호흡기)",
)

if config["enable_face_analysis"]:
    config["face_analysis_roi_only"] = st.sidebar.checkbox(
        "ROI 내부만 분석",
        config.get("face_analysis_roi_only", True),
        help="체크하면 ROI 영역 내 사람만 얼굴 분석을 수행합니다.",
    )

    st.sidebar.info(
        "📊 분석 항목:\n- 👁️ 눈 개폐 (EAR)\n- 👄 입 상태 (MAR)\n- 😊 표정 분석\n- 😷 호흡기 검출"
    )
else:
    config["face_analysis_roi_only"] = config.get("face_analysis_roi_only", True)

st.sidebar.markdown("---")

# API 설정
st.sidebar.subheader("🌐 API 설정")

# Watch ID (필수)
config["watch_id"] = st.sidebar.text_input(
    "Watch ID (필수)",
    config.get("watch_id", "watch_1764653561585_7956"),
    help="워치 ID - API 호출 시 필수",
)

# Sender ID (필수)
config["sender_id"] = st.sidebar.text_input(
    "Sender ID (필수)",
    config.get("sender_id", "test-user"),
    help="발신자 ID - API 호출 시 필수",
)

# 이미지 전송 설정 (선택)
config["include_image"] = st.sidebar.checkbox(
    "이미지 전송 활성화 (선택)",
    config.get("include_image", False),
    help="검출된 프레임을 이미지 파일로 전송",
)

# Note (선택)
config["note"] = st.sidebar.text_input(
    "기본 메시지 (선택)",
    config.get("note", config.get("default_note", "")),
    help="응급상황 메시지 - 선택사항",
)

# Method (선택)
config["method"] = st.sidebar.text_input(
    "검출 방법 (선택)",
    config.get("method", "realtime_detection"),
    help="검출 방법 식별자 - 선택사항",
)

st.sidebar.markdown("---")

# API 엔드포인트 관리
with st.sidebar.expander("🔗 API 엔드포인트 관리", expanded=False):
    # 저장된 API 엔드포인트 목록
    if "api_endpoints" not in config:
        config["api_endpoints"] = []

    st.markdown("**등록된 API 엔드포인트**")

    for i, endpoint in enumerate(config["api_endpoints"]):
        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            st.text(endpoint.get("name", f"API {i+1}"))
            st.caption(endpoint.get("url", ""))

        with col2:
            enabled = st.checkbox(
                "활성",
                endpoint.get("enabled", True),
                key=f"enabled_{i}",
                label_visibility="collapsed",
            )
            config["api_endpoints"][i]["enabled"] = enabled

        with col3:
            if st.button("🗑️", key=f"delete_api_{i}"):
                config["api_endpoints"].pop(i)
                st.rerun()

        st.markdown("---")

    # 새 API 추가
    st.markdown("**새 API 추가**")
    new_api_name = st.text_input("API 이름", "Emergency Alert API", key="new_api_name")

    st.caption("📝 API URL 형식: http://host:port/api/emergency/quick/{watchId}")
    new_api_base_url = st.text_input(
        "API Base URL",
        "http://10.10.11.23:10008/api/emergency/quick",
        key="new_api_url",
        help="watchId는 자동으로 추가됩니다",
    )

    if st.button("➕ API 추가"):
        new_endpoint = {
            "name": new_api_name,
            "url": new_api_base_url,
            "enabled": True,
            "method": "POST",
        }
        config["api_endpoints"].append(new_endpoint)
        st.success(f"✅ {new_api_name} 추가됨!")
        st.rerun()

# 설정 저장 버튼
if st.sidebar.button("💾 설정 저장", type="primary"):
    config["roi_regions"] = st.session_state.roi_regions
    save_config(config)
    st.sidebar.success("✅ 설정이 저장되었습니다!")

# 메인 영역
st.title("👤 YOLO ROI 사람 검출 시스템")

# 탭 생성
tab1, tab2, tab3, tab4 = st.tabs(
    ["📐 ROI 편집", "🎥 실시간 검출", "📊 통계 & 로그", "🔗 API 테스트"]
)

# 탭 1: ROI 편집
with tab1:
    st.header("ROI 영역 편집")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🎨 ROI 그리기")

        # 카메라 프레임 가져오기
        cap = cv2.VideoCapture(config["camera_source"])
        ret, frame = cap.read()
        cap.release()

        if ret:
            # 현재 편집 중인 polygon 표시
            if len(st.session_state.current_points) > 0:
                frame = draw_polygon_on_frame(
                    frame, st.session_state.current_points, (0, 0, 255), 2
                )

            # 저장된 ROI들 표시
            frame = draw_all_rois(
                frame, st.session_state.roi_regions, st.session_state.selected_roi_idx
            )

            # BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # 커스텀 ROI 모드 체크
            if st.session_state.custom_roi_mode and IMAGE_COORDINATES_AVAILABLE:
                # 클릭 가능한 이미지 표시
                st.info(
                    "🖱️ **커스텀 ROI 모드**: 이미지를 클릭하여 다각형 점을 추가하세요!"
                )

                value = streamlit_image_coordinates(frame_rgb, key="image_click")

                # 클릭 이벤트 처리
                if value is not None and value.get("x") is not None:
                    clicked_x = int(value["x"])
                    clicked_y = int(value["y"])

                    # 클릭한 점 추가
                    st.session_state.current_points.append([clicked_x, clicked_y])
                    st.success(f"✅ 점 추가됨: ({clicked_x}, {clicked_y})")
                    st.rerun()
            else:
                # 일반 이미지 표시 (PIL Image로 변환하여 미디어 오류 방지)
                pil_image_roi = Image.fromarray(frame_rgb)
                st.image(pil_image_roi, use_column_width=True)

                if st.session_state.custom_roi_mode and not IMAGE_COORDINATES_AVAILABLE:
                    st.warning(
                        "⚠️ 마우스 클릭 기능을 사용하려면 `pip install streamlit-image-coordinates`를 실행하세요."
                    )

            # 좌표 입력 UI
            st.markdown("---")
            st.markdown("**점 추가 (좌표 입력)**")

            col_x, col_y, col_btn = st.columns([1, 1, 1])
            with col_x:
                point_x = st.number_input("X 좌표", 0, frame.shape[1], 0, key="point_x")
            with col_y:
                point_y = st.number_input("Y 좌표", 0, frame.shape[0], 0, key="point_y")
            with col_btn:
                st.write("")  # 정렬용
                st.write("")
                if st.button("➕ 점 추가"):
                    st.session_state.current_points.append([int(point_x), int(point_y)])
                    st.rerun()

        else:
            st.error("❌ 카메라를 열 수 없습니다. 카메라 설정을 확인해주세요.")

    with col2:
        st.subheader("🛠️ 편집 도구")

        # ROI 자동 생성 옵션
        st.markdown("**📐 자동 ROI 생성**")

        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            # 좌/우 2분할 ROI 자동 생성 버튼
            if st.button("⬅️➡️ 좌/우 2분할"):
                # 정규화된 좌표 사용 - 해상도 독립적
                lr_rois = create_left_right_rois(normalized=True)

                # 기존 ROI 초기화
                st.session_state.roi_regions = []

                # 좌/우 ROI 추가
                st.session_state.roi_regions.extend(lr_rois)
                st.success(f"✅ 좌/우 2분할 ROI 생성! (해상도 자동 적응)")
                st.rerun()

        with col_btn2:
            # 4사분면 ROI 자동 생성 버튼
            if st.button("🎯 4사분면"):
                # 정규화된 좌표 사용 - 해상도 독립적
                quadrant_rois = create_quadrant_rois(normalized=True)

                # 기존 ROI 초기화
                st.session_state.roi_regions = []

                # 4사분면 ROI 추가
                st.session_state.roi_regions.extend(quadrant_rois)
                st.success(f"✅ 4사분면 ROI 생성! (해상도 자동 적응)")
                st.rerun()

        st.markdown("---")

        # 커스텀 ROI 설정 버튼
        st.markdown("**✏️ 커스텀 ROI 설정**")

        if not st.session_state.custom_roi_mode:
            if st.button("🖱️ 마우스로 ROI 그리기", type="primary"):
                st.session_state.custom_roi_mode = True
                st.session_state.custom_roi_image = frame_rgb.copy() if ret else None
                st.rerun()
        else:
            st.success("✅ 커스텀 ROI 모드 활성화!")

            if IMAGE_COORDINATES_AVAILABLE:
                st.info(
                    "🖱️ **사용 방법**:\n1. 왼쪽 이미지를 클릭하여 점 추가\n2. 최소 3개 점 추가\n3. ROI ID 입력 후 저장"
                )
            else:
                st.warning("📝 수동 좌표 입력 모드")

            if st.button("❌ 커스텀 ROI 모드 종료", type="secondary"):
                st.session_state.custom_roi_mode = False
                st.session_state.custom_roi_image = None
                st.rerun()

        st.markdown("---")

        # 현재 그리는 중인 polygon 정보
        if len(st.session_state.current_points) > 0:
            st.info(f"📍 현재 점 개수: {len(st.session_state.current_points)}")

            # 점 목록 표시
            for i, point in enumerate(st.session_state.current_points):
                col_info, col_del = st.columns([3, 1])
                with col_info:
                    st.text(f"점 {i+1}: ({point[0]}, {point[1]})")
                with col_del:
                    if st.button("🗑️", key=f"del_point_{i}"):
                        st.session_state.current_points.pop(i)
                        st.rerun()

            st.markdown("---")

            # Polygon 완성 및 저장
            if len(st.session_state.current_points) >= 3:
                roi_id = st.text_input(
                    "ROI ID", f"ROI{len(st.session_state.roi_regions) + 1}"
                )
                roi_desc = st.text_input("설명", "새 ROI 영역")

                if st.button("✅ Polygon 저장", type="primary"):
                    new_roi = {
                        "id": roi_id,
                        "type": "polygon",
                        "points": st.session_state.current_points.copy(),
                        "description": roi_desc,
                    }
                    st.session_state.roi_regions.append(new_roi)
                    st.session_state.current_points = []
                    st.success(f"✅ {roi_id} 저장 완료!")
                    st.rerun()
            else:
                st.warning("⚠️ Polygon을 완성하려면 최소 3개의 점이 필요합니다.")

            # 초기화 버튼
            if st.button("🔄 현재 Polygon 초기화"):
                st.session_state.current_points = []
                st.rerun()

        else:
            st.info("💡 좌표를 입력하여 Polygon의 점을 추가하세요.")

        st.markdown("---")

        # 저장된 ROI 목록
        st.subheader("📋 저장된 ROI")

        if len(st.session_state.roi_regions) > 0:
            for i, roi in enumerate(st.session_state.roi_regions):
                # ROI 정규화 (안전성 체크)
                roi = normalize_roi_format(roi)
                st.session_state.roi_regions[i] = roi

                # 정규화된 좌표 또는 픽셀 좌표에서 점 개수 확인
                points_key = (
                    "points_normalized" if roi.get("normalized", False) else "points"
                )
                num_points = len(roi.get(points_key, []))

                with st.expander(
                    f"{roi['id']} ({num_points}개 점, {'정규화' if roi.get('normalized') else '픽셀'})"
                ):
                    st.text(f"타입: {roi.get('type', 'polygon')}")
                    st.text(f"설명: {roi.get('description', 'N/A')}")
                    if roi.get("normalized"):
                        st.text("📐 해상도 자동 적응")

                    col_select, col_delete = st.columns(2)
                    with col_select:
                        if st.button("🎯 선택", key=f"select_{i}"):
                            st.session_state.selected_roi_idx = i
                            st.rerun()
                    with col_delete:
                        if st.button("🗑️ 삭제", key=f"delete_{i}"):
                            st.session_state.roi_regions.pop(i)
                            if st.session_state.selected_roi_idx == i:
                                st.session_state.selected_roi_idx = None
                            st.rerun()

            # 모든 ROI 초기화
            if st.button("🧹 모든 ROI 초기화", type="secondary"):
                st.session_state.roi_regions = []
                st.session_state.selected_roi_idx = None
                st.rerun()
        else:
            st.info("저장된 ROI가 없습니다.")

# 탭 2: 실시간 검출
with tab2:
    st.header("실시간 검출")

    col1, col2 = st.columns([3, 1])

    with col1:
        # 검출 시작/중지 버튼
        if not st.session_state.detection_running:
            if st.button("▶️ 검출 시작", type="primary"):
                if len(st.session_state.roi_regions) == 0:
                    st.error("❌ ROI 영역을 먼저 설정해주세요!")
                else:
                    st.session_state.detection_running = True
                    st.rerun()
        else:
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("⏸️ 검출 중지", type="secondary"):
                    st.session_state.detection_running = False
                    st.rerun()
            with col_btn2:
                # 수동 테스트 API 전송 버튼
                if st.button(
                    "🧪 테스트 API 전송",
                    type="primary",
                    help="현재 프레임으로 테스트 API 전송 (원본 이미지, ROI 제외)",
                ):
                    if st.session_state.detector is not None:
                        # 첫 번째 ROI 선택
                        if len(st.session_state.roi_regions) > 0:
                            test_roi_id = st.session_state.roi_regions[0]["id"]
                            # 원본 프레임 가져오기 (ROI 그리기 전)
                            current_frame = st.session_state.detector.get_latest_frame(
                                original=True
                            )

                            # API 전송
                            try:
                                st.session_state.detector.send_realtime_api(
                                    roi_id=test_roi_id,
                                    event_type="absent",
                                    reason="Manual test API call",
                                    frame=current_frame,
                                )
                                st.success(
                                    f"✅ 테스트 API 전송 완료! (ROI: {test_roi_id}, 원본 이미지)"
                                )
                            except Exception as e:
                                st.error(f"❌ API 전송 실패: {e}")
                        else:
                            st.warning("⚠️ ROI 영역이 없습니다.")
                    else:
                        st.warning("⚠️ 검출기가 초기화되지 않았습니다.")

        # 검출 화면 표시 영역
        if st.session_state.detection_running:
            # 검출기 초기화 (처음 시작할 때만)
            if st.session_state.detector is None:
                st.info("🔄 검출기 초기화 중...")
                try:
                    st.session_state.detector = RealtimeDetector(
                        config, st.session_state.roi_regions
                    )
                    st.session_state.detector.start()
                    time.sleep(0.5)  # 검출기 시작 대기
                except Exception as e:
                    st.error(f"❌ 검출기 초기화 실패: {e}")
                    st.session_state.detection_running = False
                    st.rerun()

            st.success("🎥 실시간 검출 실행 중 (백그라운드 스레드)")

            # 비디오 플레이스홀더
            video_placeholder = st.empty()
            fps_placeholder = st.empty()

            # 실시간 프레임 업데이트 루프
            while st.session_state.detection_running:
                # 최신 프레임 가져오기
                frame = st.session_state.detector.get_latest_frame()

                if frame is not None:
                    # BGR -> RGB 변환
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    # PIL Image로 변환 (미디어 파일 오류 방지)
                    pil_image = Image.fromarray(frame_rgb)
                    video_placeholder.image(pil_image, use_column_width=True)

                    # FPS 정보
                    fps_placeholder.caption(f"FPS: {st.session_state.detector.fps:.1f}")

                # 최신 통계 업데이트
                stats_updates = st.session_state.detector.get_latest_stats()
                for stat in stats_updates:
                    roi_id = stat["roi_id"]
                    st.session_state.detection_stats[roi_id] = {
                        "status": stat["status"],
                        "count": stat["count"],
                        "last_update": datetime.now(),
                    }

                # 최신 이벤트 로그 추가
                events = st.session_state.detector.get_latest_events()
                for event in events:
                    st.session_state.event_log.append(event)

                # 얼굴 분석 통계 업데이트
                if (
                    hasattr(st.session_state.detector, "last_face_results")
                    and st.session_state.detector.last_face_results
                ):
                    for (
                        bbox,
                        face_result,
                    ) in st.session_state.detector.last_face_results.items():
                        if face_result and face_result.get("face_detected"):
                            # 총 얼굴 검출 수
                            st.session_state.face_analysis_stats[
                                "total_faces_detected"
                            ] += 1

                            # 눈 상태
                            if face_result.get("eyes_open"):
                                st.session_state.face_analysis_stats[
                                    "eyes_open_count"
                                ] += 1
                            else:
                                st.session_state.face_analysis_stats[
                                    "eyes_closed_count"
                                ] += 1

                            # 입 상태
                            mouth_state = face_result.get("mouth_state", "closed")
                            if mouth_state == "closed":
                                st.session_state.face_analysis_stats[
                                    "mouth_closed_count"
                                ] += 1
                            elif mouth_state == "speaking":
                                st.session_state.face_analysis_stats[
                                    "mouth_speaking_count"
                                ] += 1
                            elif mouth_state == "wide_open":
                                st.session_state.face_analysis_stats[
                                    "mouth_wide_open_count"
                                ] += 1

                            # 표정
                            expr_info = face_result.get("expression", {})
                            if isinstance(expr_info, dict):
                                expression = expr_info.get("expression", "neutral")
                                if (
                                    expression
                                    in st.session_state.face_analysis_stats[
                                        "expressions"
                                    ]
                                ):
                                    st.session_state.face_analysis_stats["expressions"][
                                        expression
                                    ] += 1
                                st.session_state.face_analysis_stats[
                                    "last_expression"
                                ] = expression

                            # 마스크/호흡기
                            if face_result.get("has_mask_or_ventilator"):
                                st.session_state.face_analysis_stats[
                                    "mask_detected_count"
                                ] += 1

                            # 업데이트 시간
                            st.session_state.face_analysis_stats["last_update"] = (
                                datetime.now()
                            )

                # UI 업데이트 주기 (0.033초 = 약 30fps)
                time.sleep(0.033)

                # Streamlit 자동 새로고침 방지 (프레임만 업데이트)
        else:
            # 검출 중지 시 검출기 정리
            if st.session_state.detector is not None:
                st.session_state.detector.stop()
                st.session_state.detector = None

            st.info("▶️ '검출 시작' 버튼을 눌러 검출을 시작하세요.")

    with col2:
        st.subheader("📊 실시간 상태")

        # ROI별 상태 표시
        for roi in st.session_state.roi_regions:
            roi_id = roi["id"]

            # 세션 상태에서 ROI 상태 가져오기
            if roi_id not in st.session_state.detection_stats:
                st.session_state.detection_stats[roi_id] = {
                    "status": "None",
                    "count": 0,
                    "last_update": None,
                }

            stats = st.session_state.detection_stats[roi_id]

            with st.container():
                st.markdown(f"**{roi_id}**")

                # 상태 표시
                status_color = {"present": "🟢", "absent": "🔴", "None": "⚪"}
                st.text(f"{status_color.get(stats['status'], '⚪')} {stats['status']}")
                st.text(f"카운트: {stats['count']}")

                if stats["last_update"]:
                    st.text(f"업데이트: {stats['last_update']}")

                st.markdown("---")

# 탭 3: 통계 & 로그
with tab3:
    st.header("통계 및 이벤트 로그")

    # 얼굴 분석 통계 (활성화 시에만 표시)
    if (
        config.get("enable_face_analysis", False)
        and st.session_state.face_analysis_stats["total_faces_detected"] > 0
    ):
        st.subheader("😊 얼굴 분석 통계")

        face_stats = st.session_state.face_analysis_stats

        # 통계 카드 3열
        col_face1, col_face2, col_face3 = st.columns(3)

        with col_face1:
            st.metric("🎭 총 검출 얼굴", face_stats["total_faces_detected"])

            # 표정 분포
            st.markdown("**표정 분포**")
            total_expr = sum(face_stats["expressions"].values())
            if total_expr > 0:
                for expr, count in face_stats["expressions"].items():
                    if count > 0:
                        percentage = (count / total_expr) * 100
                        emoji_map = {
                            "neutral": "😐",
                            "happy": "😊",
                            "sad": "😢",
                            "surprised": "😲",
                            "pain": "😖",
                            "angry": "😠",
                        }
                        st.text(
                            f"{emoji_map.get(expr, '😐')} {expr.capitalize()}: {count} ({percentage:.1f}%)"
                        )

            if face_stats["last_expression"]:
                st.info(f"최근 표정: {face_stats['last_expression']}")

        with col_face2:
            # 눈 상태
            st.markdown("**👁️ 눈 상태**")
            st.metric("눈 뜸", face_stats["eyes_open_count"])
            st.metric("눈 감음", face_stats["eyes_closed_count"])

            total_eyes = face_stats["eyes_open_count"] + face_stats["eyes_closed_count"]
            if total_eyes > 0:
                open_rate = (face_stats["eyes_open_count"] / total_eyes) * 100
                st.progress(open_rate / 100, text=f"개안율: {open_rate:.1f}%")

        with col_face3:
            # 입 상태
            st.markdown("**👄 입 상태**")
            st.metric("닫힘", face_stats["mouth_closed_count"])
            st.metric("말하기", face_stats["mouth_speaking_count"])
            st.metric("크게 열림", face_stats["mouth_wide_open_count"])

            # 마스크/호흡기
            st.markdown("**😷 마스크/호흡기**")
            st.metric("착용 검출", face_stats["mask_detected_count"])

        # 통계 초기화 버튼
        if st.button("🔄 얼굴 분석 통계 초기화"):
            st.session_state.face_analysis_stats = {
                "total_faces_detected": 0,
                "expressions": {
                    "neutral": 0,
                    "happy": 0,
                    "sad": 0,
                    "surprised": 0,
                    "pain": 0,
                    "angry": 0,
                },
                "eyes_open_count": 0,
                "eyes_closed_count": 0,
                "mouth_closed_count": 0,
                "mouth_speaking_count": 0,
                "mouth_wide_open_count": 0,
                "mask_detected_count": 0,
                "last_expression": None,
                "last_update": None,
            }
            st.rerun()

        st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 YOLO 검출 통계")

        # 통계 카드
        for roi in st.session_state.roi_regions:
            roi_id = roi["id"]

            if roi_id in st.session_state.detection_stats:
                stats = st.session_state.detection_stats[roi_id]

                st.metric(
                    label=roi_id, value=stats["status"], delta=f"{stats['count']} 검출"
                )

    with col2:
        st.subheader("📝 이벤트 로그")

        # 로그 표시
        if len(st.session_state.event_log) > 0:
            for event in reversed(list(st.session_state.event_log)):
                timestamp = event.get("timestamp", "N/A")
                roi_id = event.get("roi_id", "N/A")
                status = event.get("status", "N/A")

                status_emoji = "🟢" if status == 1 else "🔴"
                st.text(f"{status_emoji} [{timestamp}] {roi_id}: {status}")
        else:
            st.info("아직 이벤트가 없습니다.")

        # 로그 초기화 버튼
        if st.button("🧹 로그 초기화"):
            st.session_state.event_log.clear()
            st.rerun()

# 탭 4: API 테스트
with tab4:
    st.header("API 엔드포인트 테스트")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🔗 API 설정")

        # API 선택
        if len(config.get("api_endpoints", [])) > 0:
            api_options = [
                f"{ep['name']} ({ep['url']})" for ep in config["api_endpoints"]
            ]
            selected_api_idx = st.selectbox(
                "테스트할 API 선택",
                range(len(api_options)),
                format_func=lambda x: api_options[x],
            )

            selected_api = config["api_endpoints"][selected_api_idx]

            st.info(f"**URL**: {selected_api['url']}")
            st.info(f"**Method**: {selected_api['method']}")

            # 테스트 이벤트 데이터 생성
            st.markdown("---")
            st.subheader("📤 테스트 데이터")

            # API 타입 선택
            api_type = st.radio(
                "API 타입",
                ["JSON (application/json)", "Multipart (multipart/form-data)"],
                key="api_type",
            )

            # 공통 필드
            test_watch_id = st.text_input(
                "1. watchId (필수)", config.get("watch_id", "watch_1764653561585_7956")
            )
            test_sender_id = st.text_input("2. senderId (필수)", "test-user")
            test_note = st.text_input("3. note (선택)", "응급상황 메시지")

            # 이미지 업로드 (Multipart만)
            uploaded_file = None
            if api_type.startswith("Multipart"):
                uploaded_file = st.file_uploader(
                    "4. image (선택)", type=["jpg", "jpeg", "png"]
                )

            # 테스트 버튼
            if st.button("🚀 API 테스트 실행", type="primary"):
                try:
                    # API 호출
                    with st.spinner("API 호출 중..."):
                        if api_type.startswith("JSON"):
                            # JSON 방식 (기존)
                            event_id = str(uuid.uuid4())
                            timestamp = datetime.now().isoformat()

                            # 이미지 URL 생성 (테스트용)
                            image_url = None
                            if config.get("include_image_url", False):
                                image_base = config.get(
                                    "image_base_url",
                                    "http://10.10.11.79:8080/api/images",
                                )
                                image_filename = (
                                    f"emergency_{event_id.split('-')[0]}.jpeg"
                                )
                                image_url = f"{image_base}/{image_filename}"

                            # FCM Message ID 생성
                            fcm_project = config.get(
                                "fcm_project_id", "emergency-alert-system-f27e6"
                            )
                            fcm_message_id = f"projects/{fcm_project}/messages/{int(time.time() * 1000)}"

                            event_data = {
                                "eventId": event_id,
                                "fcmMessageId": fcm_message_id,
                                "imageUrl": image_url,
                                "status": "SENT",
                                "createdAt": timestamp,
                                "watchId": test_watch_id,
                                "senderId": test_sender_id,
                                "note": test_note if test_note else "(empty)",
                            }

                            response = requests.request(
                                method=selected_api["method"],
                                url=selected_api["url"],
                                json=event_data,
                                headers={"Content-Type": "application/json"},
                                timeout=10,
                            )

                            request_data = event_data

                        else:
                            # Multipart 방식 (새로 추가)
                            # URL에 watchId 추가
                            api_url = selected_api["url"]
                            if "{watchId}" in api_url:
                                # 플레이스홀더가 있으면 교체
                                api_url = api_url.replace("{watchId}", test_watch_id)
                            elif test_watch_id in api_url:
                                # 이미 watchId가 URL에 포함되어 있으면 그대로 사용
                                pass
                            else:
                                # watchId가 URL에 없으면 path parameter로 추가
                                if not api_url.endswith("/"):
                                    api_url += "/"
                                api_url += test_watch_id

                            # Form data 생성
                            form_data = {
                                "senderId": test_sender_id,
                            }

                            # note가 비어있지 않으면 추가
                            if test_note:
                                form_data["note"] = test_note

                            # 파일 첨부
                            files = {}
                            if uploaded_file is not None:
                                files["image"] = (
                                    uploaded_file.name,
                                    uploaded_file.getvalue(),
                                    uploaded_file.type,
                                )

                            response = requests.request(
                                method=selected_api["method"],
                                url=api_url,
                                data=form_data,
                                files=files if files else None,
                                timeout=10,
                            )

                            request_data = {
                                "url": api_url,
                                "method": selected_api["method"],
                                "senderId": test_sender_id,
                                "note": test_note if test_note else "(empty)",
                                "image": (
                                    uploaded_file.name if uploaded_file else "(no file)"
                                ),
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

        else:
            st.warning(
                "⚠️ 등록된 API 엔드포인트가 없습니다. 사이드바에서 API를 추가해주세요."
            )

    with col2:
        st.subheader("📋 테스트 결과")

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
                    st.success(f"**상태 코드**: {status_code} ✅")
                else:
                    st.error(f"**상태 코드**: {status_code} ❌")

                # 요청 데이터
                with st.expander("📤 요청 데이터", expanded=True):
                    st.json(result.get("request_data", {}))

                # 응답 데이터
                with st.expander("📥 응답 데이터", expanded=True):
                    response_text = result.get("response_text", "")
                    try:
                        # JSON 파싱 시도
                        response_json = json.loads(response_text)
                        st.json(response_json)
                    except:
                        # JSON이 아니면 텍스트로 표시
                        st.text(response_text)
        else:
            st.info("아직 테스트를 실행하지 않았습니다.")

    # 사용 예시
    st.markdown("---")
    st.subheader("💡 API 이벤트 형식")

    with st.expander("📘 JSON API 예시 (application/json)"):
        example_json_event = {
            "eventId": "fc4d54d0-717c-4fe8-95be-fdf8f188a401",
            "fcmMessageId": "projects/emergency-alert-system-f27e6/messages/1234567890",
            "imageUrl": "http://10.10.11.79:8080/api/images/emergency_2cd5e9eb.jpeg",
            "status": "SENT",
            "createdAt": "2025-10-17T10:30:00",
            "watchId": "watch_1760663070591_8022",
        }
        st.json(example_json_event)

        st.markdown(
            """
        **JSON 필드 설명**:
        - `eventId`: 이벤트 고유 ID (UUID)
        - `fcmMessageId`: Firebase Cloud Messaging ID
        - `imageUrl`: 이벤트 관련 이미지 URL (선택적)
        - `status`: 이벤트 상태 (SENT, PENDING, FAILED)
        - `createdAt`: 이벤트 생성 시간 (ISO 8601)
        - `watchId`: Watch 고유 식별자
        """
        )

    with st.expander("📗 Multipart API 예시 (multipart/form-data)"):
        st.markdown(
            """
        **URL**: `POST /api/emergency/quick/{watchId}`
        
        **Path Parameters**:
        - `watchId` (필수): 워치 ID (예: watch_1764653561585_7956)
        
        **Form Data**:
        - `senderId` (필수, string): 발신자 ID (예: test-user)
        - `note` (선택, string): 응급상황 메시지 (예: 응급실 호출 - 환자 상태 악화)
        - `image` (선택, binary): 이미지 파일 (JPG, PNG, JPEG 형식)
        
        **예시**:
        ```bash
        curl -X POST "http://10.10.11.23:10008/api/emergency/quick/watch_1764653561585_7956" \\
          -F "senderId=test-user" \\
          -F "note=응급상황 메시지" \\
          -F "image=@detection_frame.jpg"
        ```
        """
        )

# 푸터
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p>YOLO ROI Person Detection System | Streamlit Version</p>
        <p>GitHub: <a href='https://github.com/futurianh1k/roidetyolo'>futurianh1k/roidetyolo</a></p>
    </div>
    """,
    unsafe_allow_html=True,
)
