"""
실시간 YOLO 검출 엔진 (백그라운드 스레드)
Streamlit UI와 독립적으로 실행되는 검출 시스템
"""

import cv2
import numpy as np
import time
import threading
import queue
from datetime import datetime
from ultralytics import YOLO
import platform


class RealtimeDetector:
    """
    백그라운드 스레드에서 실행되는 실시간 YOLO 검출기
    큐를 사용하여 Streamlit UI와 통신
    """
    
    def __init__(self, config, roi_regions):
        """
        Args:
            config: 설정 딕셔너리
            roi_regions: ROI 영역 리스트
        """
        self.config = config
        self.roi_regions = roi_regions
        
        # YOLO 모델 로드
        model_path = config.get('yolo_model', 'yolov8n.pt')
        print(f"[RealtimeDetector] YOLO 모델 로딩: {model_path}")
        self.model = YOLO(model_path)
        
        # 카메라 초기화
        self.camera_source = config.get('camera_source', 0)
        self.cap = None
        
        # Linux 환경 감지
        self.is_linux = platform.system() == 'Linux'
        
        # ROI별 상태 추적
        self.roi_states = {}
        for roi in roi_regions:
            roi_id = roi['id']
            self.roi_states[roi_id] = {
                'person_detected': False,
                'detection_start_time': None,
                'absence_start_time': None,
                'last_status_sent': None,
                'detection_count': 0,
                'last_count_time': time.time()
            }
        
        # 설정값
        self.presence_threshold = config.get('presence_threshold_seconds', 5)
        self.absence_threshold = config.get('absence_threshold_seconds', 3)
        self.confidence_threshold = config.get('confidence_threshold', 0.5)
        self.person_class_id = 0  # COCO dataset person class
        
        # 검출 간격 설정 (초 단위)
        self.detection_interval = config.get('detection_interval_seconds', 1.0)  # 기본 1초
        self.last_detection_time = 0
        self.last_detections = []  # 마지막 검출 결과 저장
        
        # 스레드 제어
        self.running = False
        self.thread = None
        
        # 프레임 및 상태 큐 (Streamlit과 통신)
        self.frame_queue = queue.Queue(maxsize=2)  # 최대 2개 프레임만 버퍼링
        self.stats_queue = queue.Queue(maxsize=10)
        self.event_queue = queue.Queue(maxsize=50)
        
        # FPS 측정
        self.fps = 0
        self.frame_count = 0
        self.fps_start_time = time.time()
        
        print("[RealtimeDetector] 초기화 완료")
    
    def is_person_in_polygon_roi(self, bbox, roi):
        """사람이 ROI 내에 있는지 확인"""
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        center_point = (int(center_x), int(center_y))
        
        if roi.get('type') == 'polygon' and 'points' in roi:
            points = np.array(roi['points'], dtype=np.int32)
            result = cv2.pointPolygonTest(points, center_point, False)
            return result >= 0
        
        return False
    
    def update_roi_state(self, roi_id, person_in_roi):
        """ROI 상태 업데이트 및 API 이벤트 전송 판단"""
        state = self.roi_states[roi_id]
        current_time = time.time()
        
        if person_in_roi:
            # 사람 검출됨
            if not state['person_detected']:
                # 처음 검출된 경우
                state['person_detected'] = True
                state['detection_start_time'] = current_time
                state['absence_start_time'] = None
            else:
                # 계속 검출 중
                detection_duration = current_time - state['detection_start_time']
                
                # Presence threshold 초과 시 이벤트 전송
                if detection_duration >= self.presence_threshold:
                    if state['last_status_sent'] != 'present':
                        state['last_status_sent'] = 'present'
                        state['detection_count'] += 1
                        
                        # 이벤트 큐에 전송
                        self.event_queue.put({
                            'timestamp': datetime.now().strftime('%H:%M:%S'),
                            'roi_id': roi_id,
                            'status': 'present',
                            'count': state['detection_count']
                        })
        else:
            # 사람 미검출
            if state['person_detected']:
                # 이전에 검출되었다가 사라진 경우
                state['person_detected'] = False
                state['absence_start_time'] = current_time
                state['detection_start_time'] = None
            elif state['absence_start_time'] is not None:
                # 계속 미검출 중
                absence_duration = current_time - state['absence_start_time']
                
                # Absence threshold 초과 시 이벤트 전송
                if absence_duration >= self.absence_threshold:
                    if state['last_status_sent'] == 'present':
                        state['last_status_sent'] = 'absent'
                        
                        # 이벤트 큐에 전송
                        self.event_queue.put({
                            'timestamp': datetime.now().strftime('%H:%M:%S'),
                            'roi_id': roi_id,
                            'status': 'absent',
                            'count': state['detection_count']
                        })
        
        # 상태 큐 업데이트
        try:
            self.stats_queue.put_nowait({
                'roi_id': roi_id,
                'status': state['last_status_sent'] or 'None',
                'count': state['detection_count'],
                'person_detected': state['person_detected']
            })
        except queue.Full:
            pass  # 큐가 가득 차면 무시
    
    def draw_rois_and_detections(self, frame, detections):
        """프레임에 ROI와 검출 결과 그리기"""
        frame_copy = frame.copy()
        
        # ROI 그리기
        for roi in self.roi_regions:
            roi_id = roi['id']
            state = self.roi_states[roi_id]
            
            # 상태에 따른 색상
            color = (0, 255, 0) if state['person_detected'] else (0, 0, 255)
            
            if roi.get('type') == 'polygon' and 'points' in roi:
                points = np.array(roi['points'], dtype=np.int32)
                
                # 반투명 채우기
                overlay = frame_copy.copy()
                cv2.fillPoly(overlay, [points], color)
                cv2.addWeighted(overlay, 0.2, frame_copy, 0.8, 0, frame_copy)
                
                # 테두리
                cv2.polylines(frame_copy, [points], True, color, 2)
                
                # ROI ID
                M = cv2.moments(points)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    
                    cv2.putText(frame_copy, roi_id, (cx - 30, cy - 20),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 3)
                    cv2.putText(frame_copy, roi_id, (cx - 30, cy - 20),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    
                    # 상태 표시
                    status_text = f"{state['last_status_sent'] or 'None'}"
                    cv2.putText(frame_copy, status_text, (cx - 30, cy + 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                    
                    # 카운트
                    count_text = f"Count: {state['detection_count']}"
                    cv2.putText(frame_copy, count_text, (cx - 30, cy + 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 2)
        
        # 검출된 사람 바운딩 박스
        for detection in detections:
            x1, y1, x2, y2 = map(int, detection['bbox'])
            conf = detection['confidence']
            
            cv2.rectangle(frame_copy, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(frame_copy, f'Person {conf:.2f}', (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        
        # FPS 및 검출 간격 표시
        cv2.putText(frame_copy, f'Display FPS: {self.fps:.1f}', (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame_copy, f'YOLO: Every {self.detection_interval}s', (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        return frame_copy
    
    def process_frame(self):
        """단일 프레임 처리 (YOLO 추론은 설정된 간격마다만 수행)"""
        ret, frame = self.cap.read()
        if not ret:
            return None
        
        current_time = time.time()
        detections = []
        
        # YOLO 추론을 설정된 간격(기본 1초)마다만 수행
        if current_time - self.last_detection_time >= self.detection_interval:
            print(f"[RealtimeDetector] YOLO 추론 실행 (간격: {self.detection_interval}초)")
            
            # YOLO 추론 (NumPy 호환성 개선)
            try:
                # NumPy 배열을 명시적으로 contiguous하게 변환
                frame_input = np.ascontiguousarray(frame)
                results = self.model(frame_input, verbose=False)
            except RuntimeError as e:
                print(f"[RealtimeDetector] ⚠️  YOLO 추론 실패: {e}")
                # 프레임을 복사하여 재시도
                frame_input = frame.copy()
                results = self.model(frame_input, verbose=False)
            
            # 검출된 사람들
            detections = []
            
            # 각 ROI 확인
            for roi in self.roi_regions:
                roi_id = roi['id']
                person_in_roi = False
                
                for result in results:
                    boxes = result.boxes
                    for box in boxes:
                        cls = int(box.cls[0])
                        conf = float(box.conf[0])
                        
                        if cls == self.person_class_id and conf >= self.confidence_threshold:
                            # NumPy 변환 안전성 개선
                            try:
                                bbox = box.xyxy[0].cpu().numpy()
                            except:
                                bbox = np.array(box.xyxy[0].cpu())
                            
                            detections.append({
                                'bbox': bbox,
                                'confidence': conf
                            })
                            
                            if self.is_person_in_polygon_roi(bbox, roi):
                                person_in_roi = True
                
                # ROI 상태 업데이트
                self.update_roi_state(roi_id, person_in_roi)
            
            # 검출 결과 저장 (다음 프레임들에서 재사용)
            self.last_detections = detections
            self.last_detection_time = current_time
        else:
            # 이전 검출 결과 재사용 (YOLO 추론 생략)
            detections = self.last_detections
        
        # 시각화 (매 프레임마다 수행 - 부드러운 영상)
        annotated_frame = self.draw_rois_and_detections(frame, detections)
        
        # FPS 계산 (화면 FPS)
        self.frame_count += 1
        elapsed_time = time.time() - self.fps_start_time
        if elapsed_time > 1.0:
            self.fps = self.frame_count / elapsed_time
            self.frame_count = 0
            self.fps_start_time = time.time()
        
        return annotated_frame
    
    def run(self):
        """백그라운드 검출 루프"""
        print("[RealtimeDetector] 검출 시작")
        
        # 카메라 열기
        if self.is_linux:
            self.cap = cv2.VideoCapture(self.camera_source, cv2.CAP_V4L2)
            print(f"[RealtimeDetector] Linux: V4L2 백엔드로 카메라 {self.camera_source} 열기")
        else:
            self.cap = cv2.VideoCapture(self.camera_source)
        
        if not self.cap.isOpened():
            print(f"[RealtimeDetector] ❌ 카메라를 열 수 없습니다: {self.camera_source}")
            return
        
        print("[RealtimeDetector] ✅ 카메라 열림 성공")
        
        while self.running:
            frame = self.process_frame()
            
            if frame is None:
                print("[RealtimeDetector] 프레임 읽기 실패")
                break
            
            # 프레임 큐에 전송 (큐가 가득 차면 오래된 프레임 제거)
            try:
                self.frame_queue.put_nowait(frame)
            except queue.Full:
                # 큐가 가득 차면 오래된 프레임 제거 후 새 프레임 추가
                try:
                    self.frame_queue.get_nowait()
                    self.frame_queue.put_nowait(frame)
                except:
                    pass
        
        self.cap.release()
        print("[RealtimeDetector] 검출 종료")
    
    def start(self):
        """백그라운드 스레드 시작"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            print("[RealtimeDetector] 백그라운드 스레드 시작됨")
    
    def stop(self):
        """검출 중지"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        print("[RealtimeDetector] 중지됨")
    
    def get_latest_frame(self):
        """최신 프레임 가져오기 (논블로킹)"""
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None
    
    def get_latest_stats(self):
        """최신 통계 가져오기 (논블로킹)"""
        stats = []
        try:
            while True:
                stats.append(self.stats_queue.get_nowait())
        except queue.Empty:
            pass
        return stats
    
    def get_latest_events(self):
        """최신 이벤트 가져오기 (논블로킹)"""
        events = []
        try:
            while True:
                events.append(self.event_queue.get_nowait())
        except queue.Empty:
            pass
        return events
