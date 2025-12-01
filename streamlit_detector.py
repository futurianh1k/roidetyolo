"""
Streamlit 백엔드 검출 엔진
실시간 YOLO 검출 및 API 이벤트 전송
"""

import cv2
import numpy as np
import time
import json
import uuid
import requests
from datetime import datetime
from ultralytics import YOLO
import threading


class StreamlitDetector:
    def __init__(self, config, roi_regions, event_callback=None, stats_callback=None):
        """
        Streamlit용 검출기 초기화
        
        Args:
            config: 설정 딕셔너리
            roi_regions: ROI 영역 리스트
            event_callback: 이벤트 발생 시 콜백 함수
            stats_callback: 상태 업데이트 시 콜백 함수
        """
        self.config = config
        self.roi_regions = roi_regions
        self.event_callback = event_callback
        self.stats_callback = stats_callback
        
        # YOLO 모델 로드
        model_name = config.get('yolo_model', 'yolov8n.pt')
        print(f"[Detector] YOLO 모델 로딩: {model_name}")
        self.model = YOLO(model_name)
        
        # 카메라 초기화
        self.camera_source = config.get('camera_source', 0)
        self.cap = None
        
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
        self.count_interval = config.get('count_interval_seconds', 1)
        self.confidence_threshold = config.get('confidence_threshold', 0.5)
        self.person_class_id = 0  # COCO dataset person class
        
        # 실행 제어
        self.running = False
        self.thread = None
        
        print("[Detector] 초기화 완료")
    
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
    
    def send_event_to_api(self, roi_id, object_type, status):
        """API 엔드포인트로 이벤트 전송"""
        try:
            event_data = {
                "eventId": str(uuid.uuid4()),
                "roiId": roi_id,
                "objectType": object_type,
                "status": status,
                "createdAt": datetime.now().isoformat(),
                "watchId": self.config.get('watch_id', 'watch_streamlit')
            }
            
            print(f"[API] 이벤트 전송: {roi_id}, {object_type}, {status}")
            
            # 이벤트 콜백
            if self.event_callback:
                self.event_callback({
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'roi_id': roi_id,
                    'status': status,
                    'data': event_data
                })
            
            # API 호출
            api_endpoint = self.config.get('api_endpoint')
            if api_endpoint:
                response = requests.post(
                    api_endpoint,
                    json=event_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=5
                )
                
                if response.status_code in [200, 201]:
                    print(f"[API] 전송 성공: {response.status_code}")
                else:
                    print(f"[API] 전송 실패: {response.status_code}")
        
        except Exception as e:
            print(f"[API] 오류: {e}")
    
    def update_roi_state(self, roi_id, person_detected):
        """ROI 상태 업데이트"""
        state = self.roi_states[roi_id]
        current_time = time.time()
        
        # 1초마다 카운트
        if current_time - state['last_count_time'] >= self.count_interval:
            if person_detected:
                state['detection_count'] += 1
            state['last_count_time'] = current_time
        
        # 사람 검출됨
        if person_detected:
            if not state['person_detected']:
                state['person_detected'] = True
                state['detection_start_time'] = current_time
                state['absence_start_time'] = None
                state['detection_count'] = 1
                print(f"[{roi_id}] 사람 검출 시작")
            
            detection_duration = current_time - state['detection_start_time']
            
            if (detection_duration >= self.presence_threshold and
                state['last_status_sent'] != 'present'):
                print(f"[{roi_id}] 사람 존재 확인 ({detection_duration:.1f}초)")
                self.send_event_to_api(roi_id, 'human', 1)
                state['last_status_sent'] = 'present'
        
        # 사람 검출 안됨
        else:
            if state['person_detected']:
                state['person_detected'] = False
                state['absence_start_time'] = current_time
                state['detection_start_time'] = None
                print(f"[{roi_id}] 사람 검출 종료")
            
            if state['absence_start_time'] is not None:
                absence_duration = current_time - state['absence_start_time']
                
                if (absence_duration >= self.absence_threshold and
                    state['last_status_sent'] != 'absent'):
                    print(f"[{roi_id}] 사람 부재 확인 ({absence_duration:.1f}초)")
                    self.send_event_to_api(roi_id, 'human', 0)
                    state['last_status_sent'] = 'absent'
                    state['detection_count'] = 0
        
        # 상태 콜백
        if self.stats_callback:
            self.stats_callback(roi_id, {
                'status': state['last_status_sent'] or 'None',
                'count': state['detection_count'],
                'last_update': datetime.now().strftime('%H:%M:%S')
            })
    
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
        
        return frame_copy
    
    def process_frame(self):
        """단일 프레임 처리"""
        ret, frame = self.cap.read()
        if not ret:
            return None, []
        
        # YOLO 추론
        results = self.model(frame, verbose=False)
        
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
                        bbox = box.xyxy[0].cpu().numpy()
                        
                        detections.append({
                            'bbox': bbox,
                            'confidence': conf
                        })
                        
                        if self.is_person_in_polygon_roi(bbox, roi):
                            person_in_roi = True
            
            # ROI 상태 업데이트
            self.update_roi_state(roi_id, person_in_roi)
        
        # 시각화
        annotated_frame = self.draw_rois_and_detections(frame, detections)
        
        return annotated_frame, detections
    
    def run(self):
        """검출 루프 실행"""
        print("[Detector] 검출 시작")
        
        self.cap = cv2.VideoCapture(self.camera_source)
        
        if not self.cap.isOpened():
            print("[Detector] 카메라를 열 수 없습니다")
            return
        
        frame_count = 0
        
        while self.running:
            frame, detections = self.process_frame()
            
            if frame is None:
                print("[Detector] 프레임 읽기 실패")
                break
            
            frame_count += 1
            
            # FPS 제한 (약 30 FPS)
            time.sleep(0.033)
        
        self.cap.release()
        print(f"[Detector] 검출 종료 (총 {frame_count} 프레임)")
    
    def start(self):
        """백그라운드에서 검출 시작"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            print("[Detector] 백그라운드 시작")
    
    def stop(self):
        """검출 중지"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        print("[Detector] 중지됨")
    
    def get_current_frame(self):
        """현재 프레임 가져오기 (스트리밍용)"""
        if self.cap and self.cap.isOpened():
            frame, _ = self.process_frame()
            return frame
        return None
