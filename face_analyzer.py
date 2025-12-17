"""
얼굴 분석 모듈 (MediaPipe 기반)
- 눈 개폐 검출 (EAR - Eye Aspect Ratio)
- 입 상태 검출 (MAR - Mouth Aspect Ratio)
- 표정 분석
- 인공호흡기/마스크 검출
- 머리 움직임 감지 (도리도리, 급격한 움직임)

참고자료:
- MediaPipe Face Mesh: https://google.github.io/mediapipe/solutions/face_mesh.html
- Head Pose Estimation: solvePnP 기반 3D 회전 추정
- 머리 움직임 분석 알고리즘: 각속도/각가속도 기반 이상 움직임 감지
"""

import cv2
import math
import time
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
            max_num_faces=3,  # 최대 3명
            refine_landmarks=True,  # 눈/입술 정제
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
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
        self.EAR_THRESHOLD = self.config.get("ear_threshold", 0.21)
        self.MAR_SPEAK_THRESHOLD = self.config.get("mar_speak_threshold", 0.3)
        self.MAR_OPEN_THRESHOLD = self.config.get("mar_open_threshold", 0.5)
        self.VENTILATOR_THRESHOLD = self.config.get(
            "ventilator_detection_threshold", 0.3
        )

        # 안정화를 위한 버퍼 (5 프레임 평균)
        self.ear_buffer = deque(maxlen=5)
        self.mar_buffer = deque(maxlen=5)

        # ===== 머리 움직임 감지 설정 =====
        # Head pose estimation용 랜드마크 인덱스
        # 코, 턱, 좌/우 눈꼬리, 좌/우 입꼬리 (6개 점)
        self.HEAD_POSE_LANDMARKS = [
            1,
            33,
            263,
            61,
            291,
            199,
        ]  # nose, left eye, right eye, left mouth, right mouth, chin

        # 머리 움직임 감지 임계값 (튜닝 가능)
        self.YAW_AMPLITUDE_DEG = self.config.get(
            "yaw_amplitude_deg", 15.0
        )  # 도리도리 최소 진폭
        self.HEAD_MOTION_WINDOW_SEC = self.config.get(
            "head_motion_window_sec", 2.0
        )  # 분석 창 길이(초)
        self.VELOCITY_SPIKE_DEG_PER_S = self.config.get(
            "velocity_spike_deg_per_s", 120.0
        )  # 급격한 움직임 각속도 임계
        self.ACCEL_SPIKE_DEG_PER_S2 = self.config.get(
            "accel_spike_deg_per_s2", 1000.0
        )  # 가속도 스파이크 임계
        self.HEAD_MOTION_FPS = self.config.get("head_motion_fps", 15.0)  # 처리 FPS 추정

        # 머리 움직임 시계열 버퍼 (yaw, pitch, roll + 타임스탬프)
        maxlen_head = int(self.HEAD_MOTION_WINDOW_SEC * self.HEAD_MOTION_FPS) + 10
        self.yaw_buffer = deque(maxlen=maxlen_head)
        self.pitch_buffer = deque(maxlen=maxlen_head)
        self.roll_buffer = deque(maxlen=maxlen_head)
        self.head_time_buffer = deque(maxlen=maxlen_head)

        # 베이스라인 학습용 (처음 N프레임)
        self.baseline_frames = 30
        self.baseline_yaw = None
        self.baseline_pitch = None
        self.baseline_roll = None
        self.frame_count = 0

        # 3D 모델 포인트 (일반적인 얼굴 비율 기반)
        # 참고: https://github.com/google/mediapipe/issues/1879
        self.model_points_3d = np.array(
            [
                (0.0, 0.0, 0.0),  # Nose tip (index 1)
                (-225.0, 170.0, -135.0),  # Left eye left corner (index 33)
                (225.0, 170.0, -135.0),  # Right eye right corner (index 263)
                (-150.0, -150.0, -125.0),  # Left mouth corner (index 61)
                (150.0, -150.0, -125.0),  # Right mouth corner (index 291)
                (0.0, -330.0, -65.0),  # Chin (index 199)
            ],
            dtype=np.float64,
        )

        print("[FaceAnalyzer] 초기화 완료")
        print(f"  - EAR Threshold: {self.EAR_THRESHOLD}")
        print(f"  - MAR Speak Threshold: {self.MAR_SPEAK_THRESHOLD}")
        print(f"  - MAR Open Threshold: {self.MAR_OPEN_THRESHOLD}")
        print(f"  - Head Motion Detection: Enabled")
        print(f"    - Yaw Amplitude: {self.YAW_AMPLITUDE_DEG}°")
        print(f"    - Velocity Spike: {self.VELOCITY_SPIKE_DEG_PER_S}°/s")

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
        points = np.array([[landmarks[i].x, landmarks[i].y] for i in eye_indices])

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
        points = np.array([[landmarks[i].x, landmarks[i].y] for i in mouth_indices])

        # 수직 거리 (3개)
        A = np.linalg.norm(points[1] - points[7])
        B = np.linalg.norm(points[2] - points[6])
        C = np.linalg.norm(points[3] - points[5])

        # 수평 거리
        D = np.linalg.norm(points[0] - points[4])

        # MAR 계산
        mar = (A + B + C) / (3.0 * D + 1e-6)

        return mar

    def estimate_head_pose(self, landmarks, img_w, img_h):
        """
        Head Pose 추정 (solvePnP 기반)

        3D 모델 포인트와 2D 이미지 포인트를 이용해 머리의 회전(yaw, pitch, roll)을 계산

        Args:
            landmarks: MediaPipe 랜드마크
            img_w: 이미지 너비
            img_h: 이미지 높이

        Returns:
            tuple: (yaw, pitch, roll) in degrees, or None if failed
        """
        # 2D 이미지 포인트 추출
        image_points = np.array(
            [
                (landmarks[1].x * img_w, landmarks[1].y * img_h),  # Nose tip
                (landmarks[33].x * img_w, landmarks[33].y * img_h),  # Left eye corner
                (
                    landmarks[263].x * img_w,
                    landmarks[263].y * img_h,
                ),  # Right eye corner
                (landmarks[61].x * img_w, landmarks[61].y * img_h),  # Left mouth corner
                (
                    landmarks[291].x * img_w,
                    landmarks[291].y * img_h,
                ),  # Right mouth corner
                (landmarks[199].x * img_w, landmarks[199].y * img_h),  # Chin
            ],
            dtype=np.float64,
        )

        # 카메라 매트릭스 (근사값)
        focal_length = img_w
        center = (img_w / 2, img_h / 2)
        camera_matrix = np.array(
            [[focal_length, 0, center[0]], [0, focal_length, center[1]], [0, 0, 1]],
            dtype=np.float64,
        )

        # 렌즈 왜곡 계수 (0으로 가정)
        dist_coeffs = np.zeros((4, 1))

        try:
            # solvePnP로 회전/이동 벡터 계산
            success, rotation_vector, translation_vector = cv2.solvePnP(
                self.model_points_3d,
                image_points,
                camera_matrix,
                dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE,
            )

            if not success:
                return None

            # 회전 벡터 → 회전 행렬 → 오일러 각
            rotation_matrix, _ = cv2.Rodrigues(rotation_vector)

            # 오일러 각 계산 (XYZ 순서)
            sy = math.sqrt(rotation_matrix[0, 0] ** 2 + rotation_matrix[1, 0] ** 2)
            singular = sy < 1e-6

            if not singular:
                x = math.atan2(rotation_matrix[2, 1], rotation_matrix[2, 2])
                y = math.atan2(-rotation_matrix[2, 0], sy)
                z = math.atan2(rotation_matrix[1, 0], rotation_matrix[0, 0])
            else:
                x = math.atan2(-rotation_matrix[1, 2], rotation_matrix[1, 1])
                y = math.atan2(-rotation_matrix[2, 0], sy)
                z = 0

            # 라디안 → 도
            pitch = math.degrees(x)  # 상하 (고개 끄덕임)
            yaw = math.degrees(y)  # 좌우 (고개 돌림)
            roll = math.degrees(z)  # 기울기 (고개 기울임)

            return yaw, pitch, roll

        except Exception as e:
            # solvePnP 실패 시
            return None

    def estimate_head_pose_simple(self, landmarks, img_w, img_h):
        """
        간단한 Head Pose 추정 (랜드마크 기반)

        solvePnP 없이 눈 중심-코 벡터로 yaw 근사 계산

        Args:
            landmarks: MediaPipe 랜드마크
            img_w: 이미지 너비
            img_h: 이미지 높이

        Returns:
            tuple: (yaw, pitch, roll) in degrees
        """
        # 눈 중심 계산
        left_eye_center = np.array(
            [
                np.mean([landmarks[i].x for i in self.LEFT_EYE]) * img_w,
                np.mean([landmarks[i].y for i in self.LEFT_EYE]) * img_h,
                np.mean([landmarks[i].z for i in self.LEFT_EYE]) * img_w,
            ]
        )
        right_eye_center = np.array(
            [
                np.mean([landmarks[i].x for i in self.RIGHT_EYE]) * img_w,
                np.mean([landmarks[i].y for i in self.RIGHT_EYE]) * img_h,
                np.mean([landmarks[i].z for i in self.RIGHT_EYE]) * img_w,
            ]
        )
        eyes_mid = (left_eye_center + right_eye_center) / 2.0

        # 코 위치
        nose_pt = np.array(
            [landmarks[1].x * img_w, landmarks[1].y * img_h, landmarks[1].z * img_w]
        )

        # 눈 중심 → 코 벡터
        vec = nose_pt - eyes_mid

        # Yaw 근사: x 성분 기반
        yaw = math.degrees(math.atan2(vec[0], vec[2] + 1e-6))

        # Pitch 근사: y 성분 기반
        pitch = math.degrees(math.atan2(vec[1], vec[2] + 1e-6))

        # Roll 근사: 눈 사이 기울기
        eye_diff = right_eye_center - left_eye_center
        roll = math.degrees(math.atan2(eye_diff[1], eye_diff[0] + 1e-6))

        return yaw, pitch, roll

    def analyze_head_motion(self):
        """
        머리 움직임 시계열 분석

        Returns:
            dict: {
                'head_shake': bool,      # 도리도리 감지
                'sharp_movement': bool,  # 급격한 움직임 감지
                'yaw_amplitude': float,  # yaw 진폭(도)
                'max_velocity': float,   # 최대 각속도(°/s)
                'max_acceleration': float,  # 최대 각가속도(°/s²)
            }
        """
        result = {
            "head_shake": False,
            "sharp_movement": False,
            "yaw_amplitude": 0.0,
            "max_velocity": 0.0,
            "max_acceleration": 0.0,
        }

        if len(self.yaw_buffer) < 5:
            return result

        yaws = np.array(self.yaw_buffer)
        times = np.array(self.head_time_buffer)

        # 베이스라인 보정
        if self.baseline_yaw is not None:
            yaws = yaws - self.baseline_yaw

        # 진폭 (peak-to-peak)
        amplitude = np.ptp(yaws)
        result["yaw_amplitude"] = float(amplitude)

        # 피크 수 계산 (부호 변화 횟수)
        dy = np.diff(yaws)
        if len(dy) >= 2:
            sign_changes = np.sum((dy[:-1] * dy[1:]) < 0)
        else:
            sign_changes = 0

        # 도리도리 판정: 진폭 >= 임계값 AND 피크 >= 2
        result["head_shake"] = amplitude >= self.YAW_AMPLITUDE_DEG and sign_changes >= 2

        # 각속도 계산
        dt = np.diff(times)
        dt = np.where(dt < 1e-6, 1e-6, dt)  # 0 나누기 방지
        ang_vel = np.abs(np.diff(yaws) / dt)  # °/s

        if len(ang_vel) > 0:
            max_vel = np.max(ang_vel)
            result["max_velocity"] = float(max_vel)

            # 각가속도 계산
            if len(ang_vel) > 1:
                ang_acc = np.abs(np.diff(ang_vel) / dt[1:])
                max_acc = np.max(ang_acc) if len(ang_acc) > 0 else 0.0
                result["max_acceleration"] = float(max_acc)
            else:
                max_acc = 0.0

            # 급격한 움직임 판정
            result["sharp_movement"] = (
                max_vel >= self.VELOCITY_SPIKE_DEG_PER_S
                or max_acc >= self.ACCEL_SPIKE_DEG_PER_S2
            )

        return result

    def analyze_grimace(self, landmarks):
        """
        찡그림(고통 표정) 검출

        눈썹 사이 거리 감소, 눈 주변 변화 등으로 고통 신호 판별

        Args:
            landmarks: MediaPipe 랜드마크

        Returns:
            dict: {
                'is_grimacing': bool,
                'eyebrow_distance': float,
                'grimace_confidence': float
            }
        """
        # 눈썹 내측 랜드마크 (눈썹 사이)
        left_inner_eyebrow = landmarks[107]  # 왼쪽 눈썹 안쪽
        right_inner_eyebrow = landmarks[336]  # 오른쪽 눈썹 안쪽

        # 눈썹 사이 거리
        eyebrow_dist = math.sqrt(
            (right_inner_eyebrow.x - left_inner_eyebrow.x) ** 2
            + (right_inner_eyebrow.y - left_inner_eyebrow.y) ** 2
        )

        # 눈썹 높이 (눈 대비)
        left_eyebrow_y = np.mean([landmarks[i].y for i in self.LEFT_EYEBROW])
        right_eyebrow_y = np.mean([landmarks[i].y for i in self.RIGHT_EYEBROW])
        left_eye_y = np.mean([landmarks[i].y for i in self.LEFT_EYE])
        right_eye_y = np.mean([landmarks[i].y for i in self.RIGHT_EYE])

        eyebrow_lowered = (left_eye_y - left_eyebrow_y) < 0.025 or (
            right_eye_y - right_eyebrow_y
        ) < 0.025

        # 찡그림 판정
        is_grimacing = eyebrow_dist < 0.08 and eyebrow_lowered

        # 신뢰도 계산
        if is_grimacing:
            confidence = min(0.9, (0.1 - eyebrow_dist) * 10)
        else:
            confidence = 0.0

        return {
            "is_grimacing": is_grimacing,
            "eyebrow_distance": float(eyebrow_dist),
            "grimace_confidence": float(confidence),
        }

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

        mouth_region = frame[
            mouth_region_y1:mouth_region_y2, mouth_region_x1:mouth_region_x2
        ]

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
            "eyebrow_avg": float(eyebrow_avg),
            "eyebrow_eye_dist": float(eyebrow_eye_dist),
            "mouth_corners_avg": float(mouth_corners_avg),
            "mouth_corner_curl": float(mouth_corner_curl),
            "mouth_opening": float(mouth_opening),
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

        # LUKUS - pain, sad, angry 를 pain 으로 단순화 시켜서 보고한다
        if expression == "angry" or expression == "sad" or expression == "pain":
            expression = "pain"

        return {"expression": expression, "confidence": confidence, "metrics": metrics}

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
            mouth_state = "speaking"  # 말하기
        else:
            mouth_state = "closed"  # 닫힘

        # 표정 분석
        expression = self.analyze_expression(face_landmarks.landmark)

        # 얼굴 BBox 계산 (랜드마크 기준)
        landmark_points = np.array(
            [
                [lm.x * person_crop.shape[1], lm.y * person_crop.shape[0]]
                for lm in face_landmarks.landmark
            ]
        )
        face_x1 = int(np.min(landmark_points[:, 0]))
        face_y1 = int(np.min(landmark_points[:, 1]))
        face_x2 = int(np.max(landmark_points[:, 0]))
        face_y2 = int(np.max(landmark_points[:, 1]))

        # 절대 좌표로 변환
        face_bbox_abs = (x1 + face_x1, y1 + face_y1, x1 + face_x2, y1 + face_y2)

        # 마스크/호흡기 검출
        has_device, device_conf = self.detect_mask_or_ventilator(frame, face_bbox_abs)

        # ===== 머리 움직임 분석 =====
        img_h, img_w = person_crop.shape[:2]

        # Head pose 추정 (solvePnP 우선, 실패 시 간단한 방식 사용)
        head_pose = self.estimate_head_pose(face_landmarks.landmark, img_w, img_h)
        if head_pose is None:
            head_pose = self.estimate_head_pose_simple(
                face_landmarks.landmark, img_w, img_h
            )

        yaw, pitch, roll = head_pose
        current_time = time.time()

        # 베이스라인 학습 (첫 N 프레임)
        self.frame_count += 1
        if self.frame_count <= self.baseline_frames:
            self.yaw_buffer.append(yaw)
            self.pitch_buffer.append(pitch)
            self.roll_buffer.append(roll)
            self.head_time_buffer.append(current_time)

            if self.frame_count == self.baseline_frames:
                self.baseline_yaw = np.mean(self.yaw_buffer)
                self.baseline_pitch = np.mean(self.pitch_buffer)
                self.baseline_roll = np.mean(self.roll_buffer)
        else:
            # 버퍼에 추가
            self.yaw_buffer.append(yaw)
            self.pitch_buffer.append(pitch)
            self.roll_buffer.append(roll)
            self.head_time_buffer.append(current_time)

        # 머리 움직임 분석
        head_motion = self.analyze_head_motion()

        # 찡그림 분석
        grimace = self.analyze_grimace(face_landmarks.landmark)

        # 이상 움직임 종합 판단
        abnormal_motion = head_motion["head_shake"] or head_motion["sharp_movement"]
        pain_indicators = grimace["is_grimacing"] or expression["expression"] == "pain"

        return {
            "face_detected": True,
            "face_bbox": face_bbox_abs,
            "eyes_open": eyes_open,
            "ear": float(ear_smoothed),
            "mouth_state": mouth_state,
            "mar": float(mar_smoothed),
            "expression": expression,
            "has_mask_or_ventilator": has_device,
            "device_confidence": float(device_conf),
            "landmarks": face_landmarks,
            "num_faces": len(results.multi_face_landmarks),
            # 머리 움직임 관련 결과
            "head_pose": {
                "yaw": float(yaw),
                "pitch": float(pitch),
                "roll": float(roll),
            },
            "head_motion": head_motion,
            "grimace": grimace,
            "abnormal_motion": abnormal_motion,
            "pain_indicators": pain_indicators,
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
        if not face_result or not face_result["face_detected"]:
            return frame

        x1, y1, x2, y2 = map(int, face_result["face_bbox"])

        # 얼굴 BBox (녹색)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # 정보 텍스트
        info_lines = [
            f"Eyes: {'Open' if face_result['eyes_open'] else 'Closed'} (EAR: {face_result['ear']:.2f})",
            f"Mouth: {face_result['mouth_state']} (MAR: {face_result['mar']:.2f})",
            f"Expression: {face_result['expression']}",
        ]

        if face_result["has_mask_or_ventilator"]:
            info_lines.append(
                f"Mask/Vent: Yes ({face_result['device_confidence']:.2f})"
            )

        # 머리 움직임 정보 표시
        if "head_pose" in face_result:
            pose = face_result["head_pose"]
            info_lines.append(
                f"Head: Y={pose['yaw']:.1f} P={pose['pitch']:.1f} R={pose['roll']:.1f}"
            )

        if "head_motion" in face_result:
            motion = face_result["head_motion"]
            if motion["head_shake"]:
                info_lines.append("⚠️ HEAD SHAKE (도리도리)")
            if motion["sharp_movement"]:
                info_lines.append("⚠️ SHARP MOVEMENT (급격)")

        if face_result.get("pain_indicators"):
            info_lines.append("🔴 PAIN INDICATORS")

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
                (0, 0, 0),
                -1,
            )

            # 텍스트
            cv2.putText(
                frame,
                line,
                (x1, text_y_pos),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2,
            )

        return frame

    def __del__(self):
        """소멸자 - MediaPipe 자원 해제"""
        if hasattr(self, "face_mesh"):
            self.face_mesh.close()
