"""
얼굴 분석 모듈 (MediaPipe 기반)
- 눈 개폐 검출 (EAR - Eye Aspect Ratio)
- 입 상태 검출 (MAR - Mouth Aspect Ratio)
- 표정 분석
- 인공호흡기/마스크 검출
"""

import cv2
import numpy as np
from collections import deque

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print("⚠️ MediaPipe not installed. Run: pip install mediapipe")


class FaceAnalyzer:
    """
    MediaPipe 기반 실시간 얼굴 분석기
    """
    
    def __init__(self, config=None):
        """
        Args:
            config: 설정 딕셔너리
        """
        if not MEDIAPIPE_AVAILABLE:
            raise ImportError("MediaPipe is required. Install: pip install mediapipe")
        
        self.config = config or {}
        
        # MediaPipe Face Mesh 초기화
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=3,                # 최대 3명
            refine_landmarks=True,          # 눈/입술 정제
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # MediaPipe Drawing (시각화용)
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # 랜드마크 인덱스 (468개 중 주요 점)
        # 왼쪽 눈 (6개 점)
        self.LEFT_EYE = [362, 385, 387, 263, 373, 380]
        # 오른쪽 눈 (6개 점)
        self.RIGHT_EYE = [33, 160, 158, 133, 153, 144]
        # 입 외곽 (12개 점)
        self.MOUTH_OUTER = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308]
        # 입 내부 (8개 점)
        self.MOUTH_INNER = [78, 95, 88, 178, 87, 14, 317, 402]
        # 눈썹 (표정 분석용)
        self.LEFT_EYEBROW = [70, 63, 105, 66, 107]
        self.RIGHT_EYEBROW = [336, 296, 334, 293, 300]
        
        # 임계값 (config에서 가져오거나 기본값)
        self.EAR_THRESHOLD = self.config.get('ear_threshold', 0.21)
        self.MAR_SPEAK_THRESHOLD = self.config.get('mar_speak_threshold', 0.3)
        self.MAR_OPEN_THRESHOLD = self.config.get('mar_open_threshold', 0.5)
        self.VENTILATOR_THRESHOLD = self.config.get('ventilator_detection_threshold', 0.3)
        
        # 안정화를 위한 버퍼 (5 프레임 평균)
        self.ear_buffer = deque(maxlen=5)
        self.mar_buffer = deque(maxlen=5)
        
        print("[FaceAnalyzer] 초기화 완료")
        print(f"  - EAR Threshold: {self.EAR_THRESHOLD}")
        print(f"  - MAR Speak Threshold: {self.MAR_SPEAK_THRESHOLD}")
        print(f"  - MAR Open Threshold: {self.MAR_OPEN_THRESHOLD}")
    
    def calculate_ear(self, landmarks, eye_indices):
        """
        Eye Aspect Ratio 계산
        
        EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
        
        Args:
            landmarks: MediaPipe 랜드마크
            eye_indices: 눈 랜드마크 인덱스 리스트
        
        Returns:
            float: EAR 값 (0.2 이하면 눈 감음)
        """
        # 랜드마크 좌표 추출
        points = np.array([
            [landmarks[i].x, landmarks[i].y]
            for i in eye_indices
        ])
        
        # 수직 거리 (2개)
        A = np.linalg.norm(points[1] - points[5])
        B = np.linalg.norm(points[2] - points[4])
        
        # 수평 거리
        C = np.linalg.norm(points[0] - points[3])
        
        # EAR 계산
        ear = (A + B) / (2.0 * C + 1e-6)  # 0으로 나누기 방지
        
        return ear
    
    def calculate_mar(self, landmarks, mouth_indices):
        """
        Mouth Aspect Ratio 계산
        
        MAR = (||p2-p8|| + ||p3-p7|| + ||p4-p6||) / (3 * ||p1-p5||)
        
        Args:
            landmarks: MediaPipe 랜드마크
            mouth_indices: 입 랜드마크 인덱스 리스트
        
        Returns:
            float: MAR 값 (높을수록 입이 크게 열림)
        """
        # 랜드마크 좌표 추출
        points = np.array([
            [landmarks[i].x, landmarks[i].y]
            for i in mouth_indices
        ])
        
        # 수직 거리 (3개)
        A = np.linalg.norm(points[1] - points[7])
        B = np.linalg.norm(points[2] - points[6])
        C = np.linalg.norm(points[3] - points[5])
        
        # 수평 거리
        D = np.linalg.norm(points[0] - points[4])
        
        # MAR 계산
        mar = (A + B + C) / (3.0 * D + 1e-6)
        
        return mar
    
    def detect_mask_or_ventilator(self, frame, face_bbox):
        """
        마스크/인공호흡기 검출
        
        방법: 얼굴 하단 영역에서 흰색/청록색 마스크 검출
        
        Args:
            frame: 원본 프레임
            face_bbox: 얼굴 BBox (x1, y1, x2, y2)
        
        Returns:
            tuple: (검출 여부, 신뢰도)
        """
        x1, y1, x2, y2 = map(int, face_bbox)
        h, w = frame.shape[:2]
        
        # 얼굴 아래 영역 크롭 (입 주변 + 턱 아래)
        mouth_region_y1 = int(y1 + (y2 - y1) * 0.5)  # 얼굴 중간부터
        mouth_region_y2 = min(int(y2 + (y2 - y1) * 0.2), h)  # 얼굴 아래 20%까지
        mouth_region_x1 = max(int(x1 - (x2 - x1) * 0.1), 0)  # 좌우 10% 확장
        mouth_region_x2 = min(int(x2 + (x2 - x1) * 0.1), w)
        
        mouth_region = frame[mouth_region_y1:mouth_region_y2, mouth_region_x1:mouth_region_x2]
        
        if mouth_region.size == 0:
            return False, 0.0
        
        # HSV 변환
        hsv = cv2.cvtColor(mouth_region, cv2.COLOR_BGR2HSV)
        
        # 흰색 마스크 검출 (의료용 마스크)
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 50, 255])
        mask_white = cv2.inRange(hsv, lower_white, upper_white)
        
        # 청록색/파란색 마스크 검출
        lower_blue = np.array([80, 40, 40])
        upper_blue = np.array([130, 255, 255])
        mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
        
        # 녹색 마스크 (산소 마스크)
        lower_green = np.array([40, 40, 40])
        upper_green = np.array([80, 255, 255])
        mask_green = cv2.inRange(hsv, lower_green, upper_green)
        
        # 마스크 결합
        mask_combined = cv2.bitwise_or(mask_white, mask_blue)
        mask_combined = cv2.bitwise_or(mask_combined, mask_green)
        
        # 마스크 영역 비율
        mask_ratio = np.count_nonzero(mask_combined) / (mask_combined.size + 1e-6)
        
        # 임계값 이상이면 마스크/호흡기 착용
        has_device = mask_ratio > self.VENTILATOR_THRESHOLD
        
        return has_device, float(mask_ratio)
    
    def analyze_expression(self, landmarks):
        """
        얼굴 표정 분석 (개선된 규칙 기반)
        
        Args:
            landmarks: MediaPipe 랜드마크
        
        Returns:
            dict: 표정 정보 {'expression': str, 'confidence': float, 'metrics': dict}
        """
        # 눈썹 평균 높이 (정규화)
        left_eyebrow_y = np.mean([landmarks[i].y for i in self.LEFT_EYEBROW])
        right_eyebrow_y = np.mean([landmarks[i].y for i in self.RIGHT_EYEBROW])
        eyebrow_avg = (left_eyebrow_y + right_eyebrow_y) / 2
        
        # 눈 중앙점
        left_eye_center_y = np.mean([landmarks[i].y for i in self.LEFT_EYE])
        right_eye_center_y = np.mean([landmarks[i].y for i in self.RIGHT_EYE])
        eye_avg = (left_eye_center_y + right_eye_center_y) / 2
        
        # 눈썹-눈 거리 (표정 강도 측정)
        eyebrow_eye_dist = eye_avg - eyebrow_avg
        
        # 입꼏리 좌표
        left_mouth_corner = landmarks[61]  # 왼쪽 입꼬리
        right_mouth_corner = landmarks[291]  # 오른쪽 입꼬리
        
        # 입 중앙 상단/하단
        mouth_top = landmarks[13].y  # 윗입술 중앙
        mouth_bottom = landmarks[14].y  # 아랫입술 중앙
        
        # 입꼬리 평균 높이
        mouth_corners_avg = (left_mouth_corner.y + right_mouth_corner.y) / 2
        
        # 입 벌림 정도 (MAR과 유사)
        mouth_opening = mouth_bottom - mouth_top
        
        # 입꼬리 상승/하강 (웃음/슬픔 판단)
        mouth_corner_curl = mouth_top - mouth_corners_avg
        
        # 디버깅 메트릭
        metrics = {
            'eyebrow_avg': float(eyebrow_avg),
            'eyebrow_eye_dist': float(eyebrow_eye_dist),
            'mouth_corners_avg': float(mouth_corners_avg),
            'mouth_corner_curl': float(mouth_corner_curl),
            'mouth_opening': float(mouth_opening)
        }
        
        # 표정 분류 (개선된 규칙)
        expression = "neutral"
        confidence = 0.5
        
        # 놀람: 눈썹 많이 올라감 + 입 벌림
        if eyebrow_eye_dist > 0.04 and mouth_opening > 0.03:
            expression = "surprised"
            confidence = min(0.9, eyebrow_eye_dist * 15 + mouth_opening * 15)
        
        # 웃음: 입꼬리 올라감
        elif mouth_corner_curl > 0.015:
            expression = "happy"
            confidence = min(0.9, mouth_corner_curl * 40)
        
        # 슬픔: 입꼬리 내려감
        elif mouth_corner_curl < -0.015:
            expression = "sad"
            confidence = min(0.9, abs(mouth_corner_curl) * 40)
        
        # 고통/찡그림: 눈썹 좁아짐 + 입 약간 벌림
        elif eyebrow_eye_dist < 0.025 and mouth_opening > 0.02:
            expression = "pain"
            confidence = min(0.9, (0.03 - eyebrow_eye_dist) * 20)
        
        # 화남: 눈썹 좁아짐 + 입 다물음
        elif eyebrow_eye_dist < 0.025 and mouth_opening < 0.015:
            expression = "angry"
            confidence = min(0.9, (0.03 - eyebrow_eye_dist) * 20)
        
        return {
            'expression': expression,
            'confidence': confidence,
            'metrics': metrics
        }
    
    def analyze_face(self, frame, person_bbox=None):
        """
        얼굴 분석 메인 함수
        
        Args:
            frame: 전체 프레임 또는 사람 크롭
            person_bbox: 사람 BBox (x1, y1, x2, y2) - None이면 전체 프레임 분석
        
        Returns:
            dict or None: 분석 결과
        """
        # 사람 영역 크롭 (person_bbox 제공 시)
        if person_bbox is not None:
            x1, y1, x2, y2 = map(int, person_bbox)
            
            # 경계 확인
            h, w = frame.shape[:2]
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(w, x2)
            y2 = min(h, y2)
            
            person_crop = frame[y1:y2, x1:x2]
            
            if person_crop.size == 0:
                return None
        else:
            person_crop = frame
            x1, y1, x2, y2 = 0, 0, frame.shape[1], frame.shape[0]
        
        # RGB 변환 (MediaPipe 요구사항)
        rgb_crop = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)
        
        # MediaPipe 처리
        results = self.face_mesh.process(rgb_crop)
        
        if not results.multi_face_landmarks:
            return None
        
        # 첫 번째 얼굴만 분석 (추후 다중 얼굴 지원 가능)
        face_landmarks = results.multi_face_landmarks[0]
        
        # EAR 계산 (눈 상태)
        left_ear = self.calculate_ear(face_landmarks.landmark, self.LEFT_EYE)
        right_ear = self.calculate_ear(face_landmarks.landmark, self.RIGHT_EYE)
        avg_ear = (left_ear + right_ear) / 2
        
        # 버퍼에 추가 (안정화)
        self.ear_buffer.append(avg_ear)
        ear_smoothed = np.mean(self.ear_buffer)
        
        # MAR 계산 (입 상태)
        mar = self.calculate_mar(face_landmarks.landmark, self.MOUTH_OUTER)
        
        # 버퍼에 추가 (안정화)
        self.mar_buffer.append(mar)
        mar_smoothed = np.mean(self.mar_buffer)
        
        # 눈 상태 판단
        eyes_open = ear_smoothed > self.EAR_THRESHOLD
        
        # 입 상태 판단
        if mar_smoothed > self.MAR_OPEN_THRESHOLD:
            mouth_state = "wide_open"  # 크게 열림 (하품, 고통)
        elif mar_smoothed > self.MAR_SPEAK_THRESHOLD:
            mouth_state = "speaking"   # 말하기
        else:
            mouth_state = "closed"     # 닫힘
        
        # 표정 분석
        expression = self.analyze_expression(face_landmarks.landmark)
        
        # 얼굴 BBox 계산 (랜드마크 기준)
        landmark_points = np.array([
            [lm.x * person_crop.shape[1], lm.y * person_crop.shape[0]]
            for lm in face_landmarks.landmark
        ])
        face_x1 = int(np.min(landmark_points[:, 0]))
        face_y1 = int(np.min(landmark_points[:, 1]))
        face_x2 = int(np.max(landmark_points[:, 0]))
        face_y2 = int(np.max(landmark_points[:, 1]))
        
        # 절대 좌표로 변환
        face_bbox_abs = (
            x1 + face_x1,
            y1 + face_y1,
            x1 + face_x2,
            y1 + face_y2
        )
        
        # 마스크/호흡기 검출
        has_device, device_conf = self.detect_mask_or_ventilator(
            frame, face_bbox_abs
        )
        
        return {
            'face_detected': True,
            'face_bbox': face_bbox_abs,
            'eyes_open': eyes_open,
            'ear': float(ear_smoothed),
            'mouth_state': mouth_state,
            'mar': float(mar_smoothed),
            'expression': expression,
            'has_mask_or_ventilator': has_device,
            'device_confidence': float(device_conf),
            'landmarks': face_landmarks,
            'num_faces': len(results.multi_face_landmarks)
        }
    
    def draw_face_analysis(self, frame, face_result):
        """
        얼굴 분석 결과를 프레임에 그리기
        
        Args:
            frame: 원본 프레임
            face_result: analyze_face() 결과
        
        Returns:
            frame: 결과가 그려진 프레임
        """
        if not face_result or not face_result['face_detected']:
            return frame
        
        x1, y1, x2, y2 = map(int, face_result['face_bbox'])
        
        # 얼굴 BBox (녹색)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # 정보 텍스트
        info_lines = [
            f"Eyes: {'Open' if face_result['eyes_open'] else 'Closed'} (EAR: {face_result['ear']:.2f})",
            f"Mouth: {face_result['mouth_state']} (MAR: {face_result['mar']:.2f})",
            f"Expression: {face_result['expression']}",
        ]
        
        if face_result['has_mask_or_ventilator']:
            info_lines.append(
                f"Mask/Vent: Yes ({face_result['device_confidence']:.2f})"
            )
        
        # 텍스트 배경 (반투명)
        text_y = y1 - 10
        for i, line in enumerate(info_lines):
            text_y_pos = text_y - (len(info_lines) - i) * 25
            
            # 텍스트 크기 측정
            (text_w, text_h), _ = cv2.getTextSize(
                line, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2
            )
            
            # 배경 사각형
            cv2.rectangle(
                frame,
                (x1, text_y_pos - text_h - 2),
                (x1 + text_w, text_y_pos + 2),
                (0, 0, 0), -1
            )
            
            # 텍스트
            cv2.putText(
                frame, line,
                (x1, text_y_pos),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5, (0, 255, 0), 2
            )
        
        return frame
    
    def __del__(self):
        """소멸자 - MediaPipe 자원 해제"""
        if hasattr(self, 'face_mesh'):
            self.face_mesh.close()
