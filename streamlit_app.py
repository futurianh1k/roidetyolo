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

# 페이지 설정
st.set_page_config(
    page_title="YOLO ROI Person Detector",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 세션 상태 초기화
if 'config' not in st.session_state:
    st.session_state.config = None
if 'roi_regions' not in st.session_state:
    st.session_state.roi_regions = []
if 'current_points' not in st.session_state:
    st.session_state.current_points = []
if 'editing_mode' not in st.session_state:
    st.session_state.editing_mode = False
if 'detection_running' not in st.session_state:
    st.session_state.detection_running = False
if 'event_log' not in st.session_state:
    st.session_state.event_log = deque(maxlen=50)
if 'detection_stats' not in st.session_state:
    st.session_state.detection_stats = {}
if 'selected_roi_idx' not in st.session_state:
    st.session_state.selected_roi_idx = None


def load_config():
    """config.json 파일 로드"""
    config_path = Path('config.json')
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # 기본 설정
        return {
            "yolo_model": "yolov8n.pt",
            "camera_source": 0,
            "frame_width": 1280,
            "frame_height": 720,
            "confidence_threshold": 0.5,
            "presence_threshold_seconds": 5,
            "absence_threshold_seconds": 3,
            "count_interval_seconds": 1,
            "api_endpoint": "http://10.10.11.23:10008/api/emergency",
            "watch_id": "watch_streamlit",
            "include_image_url": False,
            "roi_regions": []
        }


def save_config(config):
    """config.json 파일 저장"""
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


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
        cv2.putText(frame_copy, str(i+1), (point[0] + 10, point[1] - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    return frame_copy


def draw_all_rois(frame, roi_regions, selected_idx=None):
    """모든 ROI 영역 그리기"""
    frame_copy = frame.copy()
    
    for i, roi in enumerate(roi_regions):
        # 선택된 ROI는 다른 색상
        color = (255, 255, 0) if i == selected_idx else (0, 255, 0)
        
        if roi.get('type') == 'polygon' and 'points' in roi:
            points = roi['points']
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
                cv2.putText(frame_copy, roi['id'], (cx - 30, cy),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 3)
                cv2.putText(frame_copy, roi['id'], (cx - 30, cy),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    
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
    st.session_state.roi_regions = st.session_state.config.get('roi_regions', [])

config = st.session_state.config

# 모델 설정
st.sidebar.subheader("🤖 YOLO 모델")
model_options = ['yolov8n.pt', 'yolov8s.pt', 'yolov8m.pt', 'yolov8l.pt']
config['yolo_model'] = st.sidebar.selectbox(
    "모델 선택",
    model_options,
    index=model_options.index(config.get('yolo_model', 'yolov8n.pt'))
)

# 카메라 설정
st.sidebar.subheader("📹 카메라")
camera_type = st.sidebar.radio("소스 타입", ["웹캠", "비디오 파일"])
if camera_type == "웹캠":
    config['camera_source'] = st.sidebar.number_input("웹캠 번호", 0, 10, 0)
else:
    config['camera_source'] = st.sidebar.text_input("비디오 파일 경로", "video.mp4")

# 검출 임계값
st.sidebar.subheader("🎯 검출 설정")
config['confidence_threshold'] = st.sidebar.slider(
    "신뢰도 임계값",
    0.0, 1.0, 
    float(config.get('confidence_threshold', 0.5)),
    0.05
)
config['presence_threshold_seconds'] = st.sidebar.number_input(
    "존재 확인 시간 (초)",
    1, 60,
    int(config.get('presence_threshold_seconds', 5))
)
config['absence_threshold_seconds'] = st.sidebar.number_input(
    "부재 확인 시간 (초)",
    1, 60,
    int(config.get('absence_threshold_seconds', 3))
)

# API 설정
st.sidebar.subheader("🌐 API 설정")
config['api_endpoint'] = st.sidebar.text_input(
    "API 엔드포인트",
    config.get('api_endpoint', 'http://10.10.11.23:10008/api/emergency')
)
config['watch_id'] = st.sidebar.text_input(
    "Watch ID",
    config.get('watch_id', 'watch_streamlit')
)

# 설정 저장 버튼
if st.sidebar.button("💾 설정 저장", type="primary"):
    config['roi_regions'] = st.session_state.roi_regions
    save_config(config)
    st.sidebar.success("✅ 설정이 저장되었습니다!")

# 메인 영역
st.title("👤 YOLO ROI 사람 검출 시스템")

# 탭 생성
tab1, tab2, tab3 = st.tabs(["📐 ROI 편집", "🎥 실시간 검출", "📊 통계 & 로그"])

# 탭 1: ROI 편집
with tab1:
    st.header("ROI 영역 편집")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🎨 ROI 그리기")
        
        # 카메라 프레임 가져오기
        cap = cv2.VideoCapture(config['camera_source'])
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            # 현재 편집 중인 polygon 표시
            if len(st.session_state.current_points) > 0:
                frame = draw_polygon_on_frame(
                    frame,
                    st.session_state.current_points,
                    (0, 0, 255),
                    2
                )
            
            # 저장된 ROI들 표시
            frame = draw_all_rois(
                frame,
                st.session_state.roi_regions,
                st.session_state.selected_roi_idx
            )
            
            # BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 이미지 표시 (클릭 가능하도록)
            st.image(frame_rgb, use_container_width=True)
            
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
                roi_id = st.text_input("ROI ID", f"ROI{len(st.session_state.roi_regions) + 1}")
                roi_desc = st.text_input("설명", "새 ROI 영역")
                
                if st.button("✅ Polygon 저장", type="primary"):
                    new_roi = {
                        'id': roi_id,
                        'type': 'polygon',
                        'points': st.session_state.current_points.copy(),
                        'description': roi_desc
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
                with st.expander(f"{roi['id']} ({len(roi['points'])}개 점)"):
                    st.text(f"타입: {roi['type']}")
                    st.text(f"설명: {roi.get('description', 'N/A')}")
                    
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
            if st.button("⏸️ 검출 중지", type="secondary"):
                st.session_state.detection_running = False
                st.rerun()
        
        # 검출 화면 표시 영역
        if st.session_state.detection_running:
            st.info("🎥 검출 실행 중... (실제 구현 시 실시간 스트리밍)")
            
            # 실시간 검출은 별도 스레드나 프로세스로 구현 필요
            # 여기서는 placeholder로 표시
            video_placeholder = st.empty()
            
            # 샘플 프레임 표시 (실제로는 실시간 스트림)
            cap = cv2.VideoCapture(config['camera_source'])
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                frame = draw_all_rois(frame, st.session_state.roi_regions)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                video_placeholder.image(frame_rgb, use_container_width=True)
        else:
            st.info("▶️ '검출 시작' 버튼을 눌러 검출을 시작하세요.")
    
    with col2:
        st.subheader("📊 실시간 상태")
        
        # ROI별 상태 표시
        for roi in st.session_state.roi_regions:
            roi_id = roi['id']
            
            # 세션 상태에서 ROI 상태 가져오기
            if roi_id not in st.session_state.detection_stats:
                st.session_state.detection_stats[roi_id] = {
                    'status': 'None',
                    'count': 0,
                    'last_update': None
                }
            
            stats = st.session_state.detection_stats[roi_id]
            
            with st.container():
                st.markdown(f"**{roi_id}**")
                
                # 상태 표시
                status_color = {
                    'present': '🟢',
                    'absent': '🔴',
                    'None': '⚪'
                }
                st.text(f"{status_color.get(stats['status'], '⚪')} {stats['status']}")
                st.text(f"카운트: {stats['count']}")
                
                if stats['last_update']:
                    st.text(f"업데이트: {stats['last_update']}")
                
                st.markdown("---")

# 탭 3: 통계 & 로그
with tab3:
    st.header("통계 및 이벤트 로그")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 검출 통계")
        
        # 통계 카드
        for roi in st.session_state.roi_regions:
            roi_id = roi['id']
            
            if roi_id in st.session_state.detection_stats:
                stats = st.session_state.detection_stats[roi_id]
                
                st.metric(
                    label=roi_id,
                    value=stats['status'],
                    delta=f"{stats['count']} 검출"
                )
    
    with col2:
        st.subheader("📝 이벤트 로그")
        
        # 로그 표시
        if len(st.session_state.event_log) > 0:
            for event in reversed(list(st.session_state.event_log)):
                timestamp = event.get('timestamp', 'N/A')
                roi_id = event.get('roi_id', 'N/A')
                status = event.get('status', 'N/A')
                
                status_emoji = '🟢' if status == 1 else '🔴'
                st.text(f"{status_emoji} [{timestamp}] {roi_id}: {status}")
        else:
            st.info("아직 이벤트가 없습니다.")
        
        # 로그 초기화 버튼
        if st.button("🧹 로그 초기화"):
            st.session_state.event_log.clear()
            st.rerun()

# 푸터
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p>YOLO ROI Person Detection System | Streamlit Version</p>
        <p>GitHub: <a href='https://github.com/futurianh1k/roidetyolo'>futurianh1k/roidetyolo</a></p>
    </div>
    """,
    unsafe_allow_html=True
)
