"""
YOLO 기반 ROI 영역 사람 검출 및 이벤트 전송 시스템
- 여러 ROI 영역 설정 가능
- 각 ROI에서 사람 검출 시간 추적
- 조건에 따라 API 엔드포인트로 이벤트 전송
"""

import cv2
import numpy as np
import requests
import json
import time
import uuid
from datetime import datetime
from collections import defaultdict
from ultralytics import YOLO


class ROIPersonDetector:
    def __init__(self, config_path='config.json'):
        """
        ROI 사람 검출기 초기화
        
        Args:
            config_path: 설정 파일 경로
        """
        # 설정 파일 로드
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        # YOLO 모델 초기화 (최신 YOLOv8 또는 YOLOv11)
        model_name = self.config.get('yolo_model', 'yolov8n.pt')
        print(f"YOLO 모델 로딩 중: {model_name}")
        self.model = YOLO(model_name)
        
        # 카메라 초기화
        camera_source = self.config.get('camera_source', 0)
        self.cap = cv2.VideoCapture(camera_source)
        
        # 카메라 해상도 설정
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.get('frame_width', 640))
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.get('frame_height', 480))
        
        # ROI 영역 설정
        self.roi_regions = self.config.get('roi_regions', [])
        
        # API 엔드포인트 설정
        self.api_endpoint = self.config.get('api_endpoint', os.getenv('API_ENDPOINT', 'http://localhost:8080/api/emergency'))
        
        # 각 ROI별 상태 추적
        self.roi_states = {}
        for roi in self.roi_regions:
            roi_id = roi['id']
            self.roi_states[roi_id] = {
                'person_detected': False,
                'detection_start_time': None,
                'absence_start_time': None,
                'last_status_sent': None,  # 'present', 'absent', None
                'detection_count': 0,
                'last_count_time': time.time()
            }
        
        # 검출 임계값 설정
        self.presence_threshold = self.config.get('presence_threshold_seconds', 5)  # 5초
        self.absence_threshold = self.config.get('absence_threshold_seconds', 3)  # 3초
        self.count_interval = self.config.get('count_interval_seconds', 1)  # 1초
        
        # YOLO 사람 클래스 ID (COCO dataset에서 person = 0)
        self.person_class_id = 0
        
        # 신뢰도 임계값
        self.confidence_threshold = self.config.get('confidence_threshold', 0.5)
        
        print("ROI 사람 검출기 초기화 완료")
        print(f"ROI 영역 수: {len(self.roi_regions)}")
        print(f"존재 감지 임계값: {self.presence_threshold}초")
        print(f"부재 감지 임계값: {self.absence_threshold}초")
    
    def is_person_in_roi(self, bbox, roi):
        """
        사람 바운딩 박스가 ROI 영역 내에 있는지 확인
        
        Args:
            bbox: [x1, y1, x2, y2] 형식의 바운딩 박스
            roi: ROI 영역 정보 {'x': x, 'y': y, 'width': w, 'height': h}
        
        Returns:
            bool: ROI 내에 있으면 True
        """
        x1, y1, x2, y2 = bbox
        roi_x = roi['x']
        roi_y = roi['y']
        roi_w = roi['width']
        roi_h = roi['height']
        
        # 바운딩 박스 중심점 계산
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        
        # 중심점이 ROI 내에 있는지 확인
        if (roi_x <= center_x <= roi_x + roi_w and 
            roi_y <= center_y <= roi_y + roi_h):
            return True
        
        return False
    
    def send_event_to_api(self, roi_id, object_type, status):
        """
        API 엔드포인트로 이벤트 전송
        
        Args:
            roi_id: ROI 영역 ID
            object_type: 객체 타입 (예: 'human')
            status: 상태 (1: 검출됨, 0: 검출 안됨)
        """
        try:
            # 이벤트 데이터 구성
            event_data = {
                "eventId": str(uuid.uuid4()),
                "roiId": roi_id,
                "objectType": object_type,
                "status": status,
                "createdAt": datetime.now().isoformat(),
                "watchId": self.config.get('watch_id', f'watch_{int(time.time())}')
            }
            
            # 이미지 URL이 필요한 경우 (선택적)
            if self.config.get('include_image_url', False):
                event_data['imageUrl'] = f"http://example.com/images/roi_{roi_id}_{int(time.time())}.jpeg"
            
            print(f"\n📤 이벤트 전송: {roi_id}, {object_type}, {status}")
            print(f"   데이터: {json.dumps(event_data, indent=2, ensure_ascii=False)}")
            
            # API 호출
            response = requests.post(
                self.api_endpoint,
                json=event_data,
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            
            if response.status_code == 200 or response.status_code == 201:
                print(f"✅ 이벤트 전송 성공: {response.status_code}")
            else:
                print(f"⚠️  이벤트 전송 실패: {response.status_code} - {response.text}")
        
        except requests.exceptions.RequestException as e:
            print(f"❌ API 호출 오류: {e}")
        except Exception as e:
            print(f"❌ 예외 발생: {e}")
    
    def update_roi_state(self, roi_id, person_detected):
        """
        ROI 영역의 상태 업데이트 및 이벤트 전송 결정
        
        Args:
            roi_id: ROI 영역 ID
            person_detected: 사람 검출 여부
        """
        state = self.roi_states[roi_id]
        current_time = time.time()
        
        # 1초마다 카운트 업데이트
        if current_time - state['last_count_time'] >= self.count_interval:
            if person_detected:
                state['detection_count'] += 1
            state['last_count_time'] = current_time
        
        # 사람이 검출된 경우
        if person_detected:
            # 처음 검출되는 경우
            if not state['person_detected']:
                state['person_detected'] = True
                state['detection_start_time'] = current_time
                state['absence_start_time'] = None
                state['detection_count'] = 1
                print(f"🔍 [{roi_id}] 사람 검출 시작")
            
            # 검출 시간 체크
            detection_duration = current_time - state['detection_start_time']
            
            # presence_threshold초 이상 검출되면 'present' 이벤트 전송
            if (detection_duration >= self.presence_threshold and 
                state['last_status_sent'] != 'present'):
                print(f"👤 [{roi_id}] 사람 존재 확인 ({detection_duration:.1f}초)")
                self.send_event_to_api(roi_id, 'human', 1)
                state['last_status_sent'] = 'present'
        
        # 사람이 검출되지 않은 경우
        else:
            # 이전에 검출되었다가 사라진 경우
            if state['person_detected']:
                state['person_detected'] = False
                state['absence_start_time'] = current_time
                state['detection_start_time'] = None
                print(f"🚶 [{roi_id}] 사람 검출 종료")
            
            # 부재 시간 체크
            if state['absence_start_time'] is not None:
                absence_duration = current_time - state['absence_start_time']
                
                # absence_threshold초 이상 부재 시 'absent' 이벤트 전송
                if (absence_duration >= self.absence_threshold and 
                    state['last_status_sent'] != 'absent'):
                    print(f"🚫 [{roi_id}] 사람 부재 확인 ({absence_duration:.1f}초)")
                    self.send_event_to_api(roi_id, 'human', 0)
                    state['last_status_sent'] = 'absent'
                    state['detection_count'] = 0
    
    def draw_roi_and_info(self, frame):
        """
        프레임에 ROI 영역과 정보 표시
        
        Args:
            frame: 비디오 프레임
        
        Returns:
            annotated_frame: ROI와 정보가 표시된 프레임
        """
        annotated_frame = frame.copy()
        
        for roi in self.roi_regions:
            roi_id = roi['id']
            x, y, w, h = roi['x'], roi['y'], roi['width'], roi['height']
            state = self.roi_states[roi_id]
            
            # ROI 박스 색상 결정 (사람 검출 여부에 따라)
            color = (0, 255, 0) if state['person_detected'] else (0, 0, 255)
            
            # ROI 영역 그리기
            cv2.rectangle(annotated_frame, (x, y), (x + w, y + h), color, 2)
            
            # ROI ID 표시
            cv2.putText(annotated_frame, roi_id, (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # 상태 정보 표시
            status_text = f"Status: {state['last_status_sent'] or 'None'}"
            cv2.putText(annotated_frame, status_text, (x, y + h + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            # 검출 카운트 표시
            count_text = f"Count: {state['detection_count']}"
            cv2.putText(annotated_frame, count_text, (x, y + h + 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        return annotated_frame
    
    def run(self):
        """
        메인 검출 루프 실행
        """
        print("\n🚀 ROI 사람 검출 시작...")
        print("종료하려면 'q' 키를 누르세요.\n")
        
        frame_count = 0
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("⚠️  프레임 읽기 실패")
                break
            
            frame_count += 1
            
            # YOLO 추론 실행
            results = self.model(frame, verbose=False)
            
            # 각 ROI에 대해 사람 검출 확인
            for roi in self.roi_regions:
                roi_id = roi['id']
                person_in_roi = False
                
                # 검출된 객체 확인
                for result in results:
                    boxes = result.boxes
                    for box in boxes:
                        # 클래스 ID와 신뢰도 확인
                        cls = int(box.cls[0])
                        conf = float(box.conf[0])
                        
                        # 사람(class 0)이고 신뢰도가 임계값 이상인 경우
                        if cls == self.person_class_id and conf >= self.confidence_threshold:
                            bbox = box.xyxy[0].cpu().numpy()
                            
                            # ROI 내에 있는지 확인
                            if self.is_person_in_roi(bbox, roi):
                                person_in_roi = True
                                
                                # 시각화를 위해 바운딩 박스 그리기
                                x1, y1, x2, y2 = map(int, bbox)
                                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                                cv2.putText(frame, f'Person {conf:.2f}', (x1, y1 - 10),
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                
                # ROI 상태 업데이트
                self.update_roi_state(roi_id, person_in_roi)
            
            # ROI와 정보 표시
            annotated_frame = self.draw_roi_and_info(frame)
            
            # 프레임 표시
            cv2.imshow('ROI Person Detection', annotated_frame)
            
            # 'q' 키로 종료
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n🛑 사용자에 의해 중지됨")
                break
        
        # 정리
        self.cap.release()
        cv2.destroyAllWindows()
        print("\n✅ 프로그램 종료")


def main():
    """메인 함수"""
    try:
        detector = ROIPersonDetector('config.json')
        detector.run()
    except FileNotFoundError:
        print("❌ config.json 파일을 찾을 수 없습니다.")
        print("   설정 파일을 먼저 생성해주세요.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
