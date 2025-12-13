"""
실시간 YOLO 검출 엔진 (백그라운드 스레드)
Streamlit UI와 독립적으로 실행되는 검출 시스템
얼굴 분석 기능 통합 (MediaPipe Face Mesh)
"""

import cv2
import numpy as np
import time
import threading
import queue
from datetime import datetime
from ultralytics import YOLO
import platform
import requests
import json

# 카메라 소스 관리자 임포트
try:
    from camera_utils import CameraSourceManager, CameraSourceType
    CAMERA_UTILS_AVAILABLE = True
    print("[RealtimeDetector] ✅ CameraSourceManager 로드 완료")
except ImportError:
    CAMERA_UTILS_AVAILABLE = False
    print("[RealtimeDetector] ⚠️  CameraSourceManager 없음 - 기본 카메라만 지원")

# 얼굴 분석기 임포트 (선택적)
try:
    from face_analyzer import FaceAnalyzer
    FACE_ANALYZER_AVAILABLE = True
    print("[RealtimeDetector] ✅ FaceAnalyzer 모듈 로드 완료")
except ImportError:
    FACE_ANALYZER_AVAILABLE = False
    print("[RealtimeDetector] ⚠️  FaceAnalyzer 모듈 없음 - 얼굴 분석 비활성화")


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
        self.camera_source_type = config.get('camera_source_type', None)  # 자동 감지 가능
        self.cap = None
        
        # 카메라 소스 정보 출력
        if CAMERA_UTILS_AVAILABLE:
            source_info = CameraSourceManager.get_source_info(self.camera_source)
            print(f"[RealtimeDetector] 카메라 소스: {source_info['description']}")
            print(f"[RealtimeDetector] 소스 타입: {source_info['source_type']}")
        
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
        
        # 얼굴 분석 설정
        self.enable_face_analysis = config.get('enable_face_analysis', False)
        self.face_analysis_roi_only = config.get('face_analysis_roi_only', True)
        self.face_analyzer = None
        self.last_face_results = {}  # 마지막 얼굴 분석 결과 저장
        
        if self.enable_face_analysis and FACE_ANALYZER_AVAILABLE:
            try:
                self.face_analyzer = FaceAnalyzer()
                print("[RealtimeDetector] ✅ FaceAnalyzer 초기화 완료")
            except Exception as e:
                print(f"[RealtimeDetector] ⚠️  FaceAnalyzer 초기화 실패: {e}")
                self.enable_face_analysis = False
        elif self.enable_face_analysis and not FACE_ANALYZER_AVAILABLE:
            print("[RealtimeDetector] ⚠️  FaceAnalyzer 모듈 없음 - 얼굴 분석 비활성화")
            self.enable_face_analysis = False
        
        # 스레드 제어
        self.running = False
        self.thread = None
        
        # 프레임 및 상태 큐 (Streamlit과 통신)
        self.frame_queue = queue.Queue(maxsize=2)  # 최대 2개 프레임만 버퍼링
        self.original_frame_queue = queue.Queue(maxsize=2)  # 원본 프레임 큐 (ROI/라벨 없음)
        self.stats_queue = queue.Queue(maxsize=10)
        self.event_queue = queue.Queue(maxsize=50)
        
        # FPS 측정
        self.fps = 0
        self.frame_count = 0
        self.fps_start_time = time.time()
        
        # API 설정
        self.api_endpoint = config.get('api_endpoint', '')
        self.api_enabled = bool(self.api_endpoint)
        
        # 실시간 API 전송 상태 추적
        self.last_sad_api_time = {}  # ROI별 마지막 SAD API 전송 시간
        self.sad_api_cooldown = 10  # SAD API 재전송 대기 시간 (초)
        
        print("[RealtimeDetector] 초기화 완료")
        if self.api_enabled:
            print(f"[RealtimeDetector] API 엔드포인트: {self.api_endpoint}")
    
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
    
    def send_realtime_api(self, roi_id, event_type, reason, frame=None):
        """실시간 API 전송 (SAD 표정, 부재 상태) - 현재 스냅샷 이미지 포함"""
        if not self.api_enabled:
            return
        
        try:
            import uuid
            import base64
            from io import BytesIO
            
            # UUID 생성
            event_id = str(uuid.uuid4())
            
            # FCM Message ID 생성
            fcm_project = self.config.get('fcm_project_id', 'emergency-alert-system-f27e6')
            fcm_message_id = f"projects/{fcm_project}/messages/{int(time.time() * 1000)}"
            
            # API 페이로드 생성 (요청한 형식)
            payload = {
                'eventId': event_id,
                'fcmMessageId': fcm_message_id,
                'imageUrl': None,
                'status': 'SENT',
                'createdAt': datetime.now().isoformat(),
                'watchId': self.config.get('watch_id', 'unknown'),
                'senderId': self.config.get('sender_id', 'test-user'),
                'note': self.config.get('note', '응급상황 메시지')
            }
            
            print(f"[RealtimeDetector] 🚨 실시간 API 전송: {roi_id} - {reason}")
            
            # 이미지가 있으면 multipart/form-data로 전송
            if frame is not None:
                # 프레임을 JPEG로 인코딩
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                image_bytes = BytesIO(buffer.tobytes())
                
                # Multipart form data 생성
                files = {
                    'image': ('snapshot.jpg', image_bytes, 'image/jpeg')
                }
                
                # Form data (JSON 데이터를 form field로)
                form_data = {
                    'eventId': payload['eventId'],
                    'fcmMessageId': payload['fcmMessageId'],
                    'status': payload['status'],
                    'createdAt': payload['createdAt'],
                    'watchId': payload['watchId'],
                    'senderId': payload['senderId'],
                    'note': payload['note']
                }
                
                # API 전송 (multipart/form-data)
                response = requests.post(
                    self.api_endpoint,
                    data=form_data,
                    files=files,
                    timeout=10
                )
            else:
                # 이미지 없으면 JSON으로 전송
                response = requests.post(
                    self.api_endpoint,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
            
            if response.status_code in [200, 201]:
                print(f"[RealtimeDetector] ✅ API 전송 성공: {response.status_code}")
                print(f"[RealtimeDetector] 📤 전송된 데이터: {payload}")
            else:
                print(f"[RealtimeDetector] ⚠️ API 응답 오류: {response.status_code}")
                print(f"[RealtimeDetector] 응답 내용: {response.text}")
                
        except requests.exceptions.Timeout:
            print(f"[RealtimeDetector] ⏱️ API 타임아웃")
        except requests.exceptions.ConnectionError:
            print(f"[RealtimeDetector] ❌ API 연결 실패")
        except Exception as e:
            print(f"[RealtimeDetector] ❌ API 전송 오류: {e}")
            import traceback
            traceback.print_exc()
    
    def update_roi_state(self, roi_id, person_in_roi, frame=None):
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
                        
                        # 🚨 실시간 API 전송 (부재 상태) - 현재 프레임 포함
                        self.send_realtime_api(
                            roi_id=roi_id,
                            event_type='absent',
                            reason='Person absence detected',
                            frame=frame
                        )
                        
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
        """프레임에 ROI와 검출 결과 그리기 (얼굴 분석 결과 포함)"""
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
        
        # 검출된 사람 바운딩 박스 + 얼굴 분석 결과
        for detection in detections:
            x1, y1, x2, y2 = map(int, detection['bbox'])
            conf = detection['confidence']
            
            # 사람 BBox
            cv2.rectangle(frame_copy, (x1, y1), (x2, y2), (255, 0, 0), 2)
            
            # 얼굴 분석 결과 표시
            face_result = self.last_face_results.get(tuple(detection['bbox']))
            
            if face_result and face_result.get('face_detected'):
                # 표정 정보 추출 (딕셔너리 처리)
                expr_info = face_result.get('expression', {})
                if isinstance(expr_info, dict):
                    expr_text = f"{expr_info.get('expression', 'unknown')} ({expr_info.get('confidence', 0):.2f})"
                else:
                    expr_text = str(expr_info)
                
                # 텍스트 준비
                info_lines = [
                    f"Person {conf:.2f}",
                    f"Eyes: {'Open' if face_result['eyes_open'] else 'Closed'}",
                    f"Mouth: {face_result['mouth_state']}",
                    f"Expr: {expr_text}",
                ]
                
                if face_result.get('has_mask_or_ventilator'):
                    info_lines.append(f"Mask/Ventilator: Yes ({face_result['device_confidence']:.2f})")
                
                # 텍스트 배경 및 표시
                text_y = y1 - 10
                for i, line in enumerate(info_lines):
                    text_y_pos = text_y - (len(info_lines) - i - 1) * 20
                    
                    # 배경 사각형
                    (text_width, text_height), _ = cv2.getTextSize(
                        line, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2
                    )
                    cv2.rectangle(
                        frame_copy, 
                        (x1, text_y_pos - text_height - 2), 
                        (x1 + text_width + 5, text_y_pos + 2),
                        (0, 0, 0), -1
                    )
                    
                    # 텍스트
                    cv2.putText(
                        frame_copy, line, (x1, text_y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2
                    )
            else:
                # 얼굴 분석 없을 때는 기본 표시
                cv2.putText(frame_copy, f'Person {conf:.2f}', (x1, y1 - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        
        # FPS 및 검출 간격 표시
        cv2.putText(frame_copy, f'Display FPS: {self.fps:.1f}', (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame_copy, f'YOLO: Every {self.detection_interval}s', (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        # 얼굴 분석 활성화 표시
        if self.enable_face_analysis:
            mode_text = "Face: ON (ROI Only)" if self.face_analysis_roi_only else "Face: ON (All)"
            cv2.putText(frame_copy, mode_text, (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
        
        return frame_copy
    
    def process_frame(self, frame=None):
        """단일 프레임 처리 (YOLO 추론은 설정된 간격마다만 수행)"""
        # 프레임이 제공되지 않으면 카메라에서 읽기
        if frame is None:
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
            
            # 얼굴 분석 (옵션)
            face_analysis_results = {}
            if self.enable_face_analysis and self.face_analyzer:
                print(f"[RealtimeDetector] 얼굴 분석 실행 ({len(detections)}명 검출)")
                
                for detection in detections:
                    bbox = detection['bbox']
                    
                    # ROI 내부 사람만 분석 옵션
                    if self.face_analysis_roi_only:
                        person_in_any_roi = False
                        for roi in self.roi_regions:
                            if self.is_person_in_polygon_roi(bbox, roi):
                                person_in_any_roi = True
                                break
                        
                        if not person_in_any_roi:
                            continue  # ROI 밖이면 건너뛰기
                    
                    # 얼굴 분석 수행
                    try:
                        face_result = self.face_analyzer.analyze_face(frame, bbox)
                        if face_result:
                            face_analysis_results[tuple(bbox)] = face_result
                            
                            # 표정 정보 추출 (딕셔너리 처리)
                            expr_info = face_result.get('expression', {})
                            if isinstance(expr_info, dict):
                                expression = expr_info.get('expression', 'unknown')
                                confidence = expr_info.get('confidence', 0)
                                expr_text = f"{expression} ({confidence:.2f})"
                            else:
                                expression = 'unknown'
                                expr_text = str(expr_info)
                            
                            print(f"[RealtimeDetector] ✅ 얼굴 분석 완료: Eyes={'Open' if face_result['eyes_open'] else 'Closed'}, Mouth={face_result['mouth_state']}, Expression={expr_text}")
                            
                            # 🚨 SAD 표정 감지 시 실시간 API 전송
                            if expression == 'sad' and confidence > 0.6:
                                # 어느 ROI에 속하는지 확인
                                person_roi = None
                                for roi in self.roi_regions:
                                    if self.is_person_in_polygon_roi(bbox, roi):
                                        person_roi = roi['id']
                                        break
                                
                                if person_roi:
                                    # Cooldown 체크 (같은 ROI에서 10초 내 중복 전송 방지)
                                    last_sad_time = self.last_sad_api_time.get(person_roi, 0)
                                    if current_time - last_sad_time >= self.sad_api_cooldown:
                                        self.send_realtime_api(
                                            roi_id=person_roi,
                                            event_type='sad_expression',
                                            reason=f'SAD expression detected (confidence: {confidence:.2f})',
                                            frame=frame
                                        )
                                        self.last_sad_api_time[person_roi] = current_time
                    except Exception as e:
                        print(f"[RealtimeDetector] ⚠️  얼굴 분석 실패: {e}")
            
            # 얼굴 분석 결과 저장
            self.last_face_results = face_analysis_results
            
            # ROI 상태 업데이트 (현재 프레임 전달)
            self.update_roi_state(roi_id, person_in_roi, frame=frame)
            
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
        
        # 카메라 열기 (CameraSourceManager 사용)
        if CAMERA_UTILS_AVAILABLE:
            print(f"[RealtimeDetector] CameraSourceManager로 카메라 열기")
            
            # 추가 옵션 설정
            camera_options = {}
            if self.is_linux and isinstance(self.camera_source, int):
                camera_options['backend'] = cv2.CAP_V4L2
            
            self.cap = CameraSourceManager.open_camera(
                self.camera_source, 
                self.camera_source_type,
                **camera_options
            )
        else:
            # 기본 방식 (하위 호환성)
            print(f"[RealtimeDetector] 기본 방식으로 카메라 열기")
            if self.is_linux and isinstance(self.camera_source, int):
                self.cap = cv2.VideoCapture(self.camera_source, cv2.CAP_V4L2)
                print(f"[RealtimeDetector] Linux: V4L2 백엔드로 카메라 {self.camera_source} 열기")
            else:
                self.cap = cv2.VideoCapture(self.camera_source)
        
        if not self.cap or not self.cap.isOpened():
            print(f"[RealtimeDetector] ❌ 카메라를 열 수 없습니다: {self.camera_source}")
            return
        
        print("[RealtimeDetector] ✅ 카메라 열림 성공")
        
        while self.running:
            # 원본 프레임 읽기
            ret, original_frame = self.cap.read()
            if not ret or original_frame is None:
                print("[RealtimeDetector] 프레임 읽기 실패")
                break
            
            # 프레임 처리 (검출 및 시각화)
            annotated_frame = self.process_frame(original_frame)
            
            if annotated_frame is None:
                continue
            
            # 시각화된 프레임 큐에 전송 (UI 표시용)
            try:
                self.frame_queue.put_nowait(annotated_frame)
            except queue.Full:
                # 큐가 가득 차면 오래된 프레임 제거 후 새 프레임 추가
                try:
                    self.frame_queue.get_nowait()
                    self.frame_queue.put_nowait(annotated_frame)
                except:
                    pass
            
            # 원본 프레임 큐에 전송 (테스트 API 전송용 - 순수 카메라 이미지)
            try:
                self.original_frame_queue.put_nowait(original_frame.copy())
            except queue.Full:
                # 큐가 가득 차면 오래된 프레임 제거 후 새 프레임 추가
                try:
                    self.original_frame_queue.get_nowait()
                    self.original_frame_queue.put_nowait(original_frame.copy())
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
    
    def get_latest_frame(self, original=False):
        """
        최신 프레임 가져오기 (논블로킹)
        
        Args:
            original: True면 원본 프레임 (ROI/라벨 없음), False면 시각화된 프레임
        """
        try:
            if original:
                return self.original_frame_queue.get_nowait()
            else:
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
