# 🔬 얼굴 분석 시스템 통합 가이드 (Jetson Orin 최적화)

---

## 📋 개요

**목표**: 기존 YOLO ROI 사람 감지 시스템에 얼굴 분석 기능 추가

**분석 항목**:
1. 얼굴 표정 (Facial Expression) - 감정, 고통, 찡그림
2. 눈 상태 (Eye State) - 뜨기/감기
3. 입 상태 (Mouth State) - 열기/닫기/말하기
4. 인공호흡기 검출 (Ventilator Detection)

**플랫폼**: Jetson Orin (GPU 가속)

---

## 🎯 추천 아키텍처 (Jetson Orin 최적화)

### **2단계 파이프라인**

```
┌─────────────────────────────────────────────────────────┐
│  Stage 1: 사람 검출 (YOLO)                               │
│  ─────────────────────────────────────────────────────  │
│  입력: 카메라 프레임 (1280x720)                          │
│  출력: 사람 BBox + ROI 필터링                            │
│  성능: 30-60 FPS (현재 시스템)                          │
└─────────────────────────────────────────────────────────┘
              ↓ (사람 BBox 전달)
┌─────────────────────────────────────────────────────────┐
│  Stage 2: 얼굴 분석 (MediaPipe Face Mesh)               │
│  ─────────────────────────────────────────────────────  │
│  입력: 사람 BBox 크롭 이미지                             │
│  처리:                                                   │
│    1. Face Detection (얼굴 검출)                        │
│    2. Face Landmarks (468개 특징점)                     │
│    3. Feature Analysis:                                 │
│       - EAR (Eye Aspect Ratio) → 눈 개폐              │
│       - MAR (Mouth Aspect Ratio) → 입 상태            │
│       - Facial Expression → 표정 분류                  │
│       - Mask/Ventilator Detection → 마스크/호흡기     │
│  성능: 15-30 FPS (얼굴당)                               │
└─────────────────────────────────────────────────────────┘
```

---

## 💡 왜 MediaPipe Face Mesh인가?

### ✅ 장점
1. **경량**: CPU에서도 30+ FPS
2. **정확**: 468개 3D 랜드마크
3. **무료**: 오픈소스 (Apache 2.0)
4. **GPU 가속**: TensorFlow Lite GPU 지원
5. **검증됨**: Google 프로덕션 사용

### ❌ 대안들의 단점
- **dlib**: CPU만 지원, 느림 (5-10 FPS)
- **OpenCV DNN**: 제한적 랜드마크 (68개)
- **커스텀 CNN**: 학습 데이터 부족, 개발 시간 ↑

---

## 🔧 구현 방법

### 1️⃣ **패키지 설치**

```bash
# MediaPipe 설치
pip install mediapipe-gpu opencv-python numpy

# 얼굴 표정 분석용 (선택)
pip install fer  # Facial Expression Recognition
```

### 2️⃣ **FaceAnalyzer 클래스 설계**

```python
import mediapipe as mp
import cv2
import numpy as np
from collections import deque

class FaceAnalyzer:
    """
    MediaPipe 기반 실시간 얼굴 분석기
    - 눈 개폐 (EAR)
    - 입 상태 (MAR)
    - 표정 분석
    - 마스크/호흡기 검출
    """
    
    def __init__(self):
        # MediaPipe Face Mesh 초기화
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=5,           # 최대 5명
            refine_landmarks=True,      # 눈/입술 정제
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # 랜드마크 인덱스 (468개 중 주요 점)
        self.LEFT_EYE = [362, 385, 387, 263, 373, 380]
        self.RIGHT_EYE = [33, 160, 158, 133, 153, 144]
        self.MOUTH_OUTER = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308]
        self.MOUTH_INNER = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415]
        
        # 임계값
        self.EAR_THRESHOLD = 0.21      # 눈 감음 기준
        self.MAR_SPEAK_THRESHOLD = 0.3  # 말하기 기준
        self.MAR_OPEN_THRESHOLD = 0.5   # 입 크게 열림
        
        # 안정화를 위한 버퍼
        self.ear_buffer = deque(maxlen=5)
        self.mar_buffer = deque(maxlen=5)
    
    def calculate_ear(self, landmarks, eye_indices):
        """Eye Aspect Ratio 계산"""
        points = np.array([
            [landmarks[i].x, landmarks[i].y]
            for i in eye_indices
        ])
        
        # 수직 거리
        A = np.linalg.norm(points[1] - points[5])
        B = np.linalg.norm(points[2] - points[4])
        
        # 수평 거리
        C = np.linalg.norm(points[0] - points[3])
        
        ear = (A + B) / (2.0 * C)
        return ear
    
    def calculate_mar(self, landmarks, mouth_indices):
        """Mouth Aspect Ratio 계산"""
        points = np.array([
            [landmarks[i].x, landmarks[i].y]
            for i in mouth_indices
        ])
        
        # 수직 거리
        A = np.linalg.norm(points[1] - points[7])
        B = np.linalg.norm(points[2] - points[6])
        C = np.linalg.norm(points[3] - points[5])
        
        # 수평 거리
        D = np.linalg.norm(points[0] - points[4])
        
        mar = (A + B + C) / (3.0 * D)
        return mar
    
    def detect_ventilator(self, frame, face_bbox):
        """
        인공호흡기 검출
        - 얼굴 아래 영역에서 마스크/튜브 검출
        - 색상 기반 + 형태 분석
        """
        x1, y1, x2, y2 = face_bbox
        h, w = frame.shape[:2]
        
        # 얼굴 아래 영역 크롭
        mouth_region_y1 = int(y1 + (y2 - y1) * 0.6)
        mouth_region_y2 = min(int(y2 + (y2 - y1) * 0.3), h)
        mouth_region = frame[mouth_region_y1:mouth_region_y2, x1:x2]
        
        if mouth_region.size == 0:
            return False, 0.0
        
        # HSV 변환
        hsv = cv2.cvtColor(mouth_region, cv2.COLOR_BGR2HSV)
        
        # 흰색/청록색 마스크 검출 (의료용 마스크 색상)
        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 30, 255])
        mask_white = cv2.inRange(hsv, lower_white, upper_white)
        
        lower_blue = np.array([90, 50, 50])
        upper_blue = np.array([130, 255, 255])
        mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
        
        mask_combined = cv2.bitwise_or(mask_white, mask_blue)
        
        # 마스크 영역 비율
        mask_ratio = np.count_nonzero(mask_combined) / mask_combined.size
        
        has_ventilator = mask_ratio > 0.3  # 30% 이상이면 호흡기 착용
        
        return has_ventilator, mask_ratio
    
    def analyze_expression(self, landmarks):
        """
        얼굴 표정 분석 (간단한 규칙 기반)
        - 더 정확한 분석은 FER 모델 사용
        """
        # 눈썹 높이 (찡그림 검출)
        left_eyebrow = landmarks[70].y
        right_eyebrow = landmarks[300].y
        eyebrow_avg = (left_eyebrow + right_eyebrow) / 2
        
        # 입꼬리 (웃음 검출)
        left_mouth = landmarks[61].y
        right_mouth = landmarks[291].y
        mouth_corners_avg = (left_mouth + right_mouth) / 2
        
        # 간단한 규칙
        if eyebrow_avg < 0.35:  # 눈썹이 올라감
            return "surprised"
        elif mouth_corners_avg > 0.6:  # 입꼬리가 내려감
            return "sad"
        else:
            return "neutral"
    
    def analyze_face(self, frame, person_bbox):
        """
        얼굴 분석 메인 함수
        
        Args:
            frame: 전체 프레임
            person_bbox: 사람 BBox (x1, y1, x2, y2)
        
        Returns:
            dict: 분석 결과
        """
        x1, y1, x2, y2 = map(int, person_bbox)
        
        # 사람 영역 크롭
        person_crop = frame[y1:y2, x1:x2]
        
        if person_crop.size == 0:
            return None
        
        # RGB 변환 (MediaPipe 요구사항)
        rgb_crop = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)
        
        # MediaPipe 처리
        results = self.face_mesh.process(rgb_crop)
        
        if not results.multi_face_landmarks:
            return None
        
        # 첫 번째 얼굴 분석
        face_landmarks = results.multi_face_landmarks[0]
        
        # EAR 계산 (눈 상태)
        left_ear = self.calculate_ear(
            face_landmarks.landmark,
            self.LEFT_EYE
        )
        right_ear = self.calculate_ear(
            face_landmarks.landmark,
            self.RIGHT_EYE
        )
        avg_ear = (left_ear + right_ear) / 2
        self.ear_buffer.append(avg_ear)
        ear_smoothed = np.mean(self.ear_buffer)
        
        # MAR 계산 (입 상태)
        mar = self.calculate_mar(
            face_landmarks.landmark,
            self.MOUTH_OUTER
        )
        self.mar_buffer.append(mar)
        mar_smoothed = np.mean(self.mar_buffer)
        
        # 눈 상태 판단
        eyes_open = ear_smoothed > self.EAR_THRESHOLD
        
        # 입 상태 판단
        if mar_smoothed > self.MAR_OPEN_THRESHOLD:
            mouth_state = "wide_open"
        elif mar_smoothed > self.MAR_SPEAK_THRESHOLD:
            mouth_state = "speaking"
        else:
            mouth_state = "closed"
        
        # 표정 분석
        expression = self.analyze_expression(face_landmarks.landmark)
        
        # 호흡기 검출
        has_ventilator, ventilator_conf = self.detect_ventilator(
            person_crop,
            (0, 0, x2-x1, y2-y1)  # 크롭 내 상대 좌표
        )
        
        return {
            'face_detected': True,
            'eyes_open': eyes_open,
            'ear': ear_smoothed,
            'mouth_state': mouth_state,
            'mar': mar_smoothed,
            'expression': expression,
            'has_ventilator': has_ventilator,
            'ventilator_confidence': ventilator_conf,
            'landmarks': face_landmarks
        }
```

---

## 🔗 기존 시스템 통합

### 3️⃣ **RealtimeDetector 수정**

```python
# realtime_detector.py 수정

from face_analyzer import FaceAnalyzer

class RealtimeDetector:
    def __init__(self, config, roi_regions):
        # ... 기존 코드 ...
        
        # 얼굴 분석기 추가
        self.face_analyzer = FaceAnalyzer()
        self.enable_face_analysis = config.get('enable_face_analysis', False)
    
    def process_frame(self):
        """프레임 처리 (얼굴 분석 추가)"""
        ret, frame = self.cap.read()
        if not ret:
            return None
        
        current_time = time.time()
        detections = []
        face_analysis_results = {}
        
        # YOLO 추론 (설정된 간격마다)
        if current_time - self.last_detection_time >= self.detection_interval:
            
            # YOLO로 사람 검출
            results = self.model(frame, verbose=False)
            
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
                        
                        # 얼굴 분석 (옵션)
                        if self.enable_face_analysis:
                            face_result = self.face_analyzer.analyze_face(
                                frame, bbox
                            )
                            
                            if face_result:
                                face_analysis_results[tuple(bbox)] = face_result
            
            # ROI 체크 및 상태 업데이트
            for roi in self.roi_regions:
                roi_id = roi['id']
                person_in_roi = False
                
                for detection in detections:
                    if self.is_person_in_polygon_roi(detection['bbox'], roi):
                        person_in_roi = True
                        break
                
                self.update_roi_state(roi_id, person_in_roi)
            
            self.last_detections = detections
            self.last_face_results = face_analysis_results
            self.last_detection_time = current_time
        
        # 프레임에 시각화
        annotated_frame = self.draw_detections_with_faces(
            frame,
            self.last_detections,
            self.last_face_results
        )
        
        return annotated_frame
    
    def draw_detections_with_faces(self, frame, detections, face_results):
        """BBox + 얼굴 분석 결과 시각화"""
        frame_copy = frame.copy()
        
        for detection in detections:
            bbox = detection['bbox']
            x1, y1, x2, y2 = map(int, bbox)
            
            # 사람 BBox 그리기
            cv2.rectangle(frame_copy, (x1, y1), (x2, y2), (255, 0, 0), 2)
            
            # 얼굴 분석 결과 표시
            face_result = face_results.get(tuple(bbox))
            
            if face_result and face_result['face_detected']:
                # 텍스트 준비
                info_lines = [
                    f"Eyes: {'Open' if face_result['eyes_open'] else 'Closed'}",
                    f"Mouth: {face_result['mouth_state']}",
                    f"Expr: {face_result['expression']}",
                ]
                
                if face_result['has_ventilator']:
                    info_lines.append(f"Ventilator: Yes ({face_result['ventilator_confidence']:.2f})")
                
                # 텍스트 배경
                text_y = y1 - 10
                for i, line in enumerate(info_lines):
                    text_y_pos = text_y - (len(info_lines) - i) * 20
                    cv2.putText(
                        frame_copy, line,
                        (x1, text_y_pos),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (0, 255, 0), 2
                    )
        
        return frame_copy
```

---

## 📊 성능 최적화 전략

### **Jetson Orin 최적화**

#### 1️⃣ **GPU 메모리 관리**
```python
# TensorFlow Lite GPU Delegate 사용
import tensorflow as tf

# GPU 메모리 증가 허용
gpus = tf.config.experimental.list_physical_devices('GPU')
if gpus:
    tf.config.experimental.set_memory_growth(gpus[0], True)
```

#### 2️⃣ **병렬 처리**
```python
# YOLO와 Face Analysis를 번갈아 실행
frame_count = 0

if frame_count % 2 == 0:
    # YOLO 추론
    yolo_results = model(frame)
else:
    # 얼굴 분석 (이전 YOLO 결과 사용)
    if previous_detections:
        for bbox in previous_detections:
            face_result = face_analyzer.analyze_face(frame, bbox)

frame_count += 1
```

#### 3️⃣ **해상도 조정**
```python
# 얼굴 분석은 낮은 해상도로
person_crop_resized = cv2.resize(person_crop, (320, 320))
face_result = face_analyzer.analyze_face(person_crop_resized, ...)
```

#### 4️⃣ **선택적 분석**
```python
# ROI 내부 사람만 얼굴 분석
if person_in_roi:
    face_result = face_analyzer.analyze_face(frame, bbox)
```

---

## ⚙️ 설정 파일 (config.json)

```json
{
  "yolo_model": "yolov8n.pt",
  "camera_source": 0,
  "frame_width": 1280,
  "frame_height": 720,
  "confidence_threshold": 0.5,
  "detection_interval_seconds": 1.0,
  
  "enable_face_analysis": true,
  "face_analysis_interval": 2.0,
  "face_analysis_roi_only": true,
  
  "ear_threshold": 0.21,
  "mar_speak_threshold": 0.3,
  "mar_open_threshold": 0.5,
  "ventilator_detection_threshold": 0.3
}
```

---

## 📈 예상 성능 (Jetson Orin Nano)

| 모드 | YOLO FPS | Face Analysis FPS | 총 FPS |
|------|----------|-------------------|--------|
| YOLO만 | 30-40 | - | 30-40 |
| 모두 활성화 (번갈아) | 30 | 15 | 25-30 |
| ROI만 분석 | 35 | 10-15 | 30-35 |

---

## 🚀 빠른 시작

### 설치
```bash
cd /home/user/yolo_roi_detector

# MediaPipe 설치
pip install mediapipe-gpu

# 새 파일 생성
# - face_analyzer.py (위 FaceAnalyzer 클래스)
# - realtime_detector.py 수정
```

### 실행
```bash
# config.json 수정
# "enable_face_analysis": true 설정

# Streamlit 실행
streamlit run streamlit_app.py
```

---

## 🎯 추가 개선 아이디어

### 1️⃣ **표정 분석 정확도 향상**
```bash
# FER (Facial Expression Recognition) 사용
pip install fer

from fer import FER
detector = FER(mtcnn=False)  # MediaPipe 랜드마크 사용
emotions = detector.detect_emotions(face_crop)
```

### 2️⃣ **Gaze Tracking (시선 추적)**
```python
# MediaPipe 아이리스 랜드마크 활용
# 좌우 시선 방향 검출
```

### 3️⃣ **Head Pose Estimation (머리 방향)**
```python
# 3D 랜드마크로 얼굴 회전 각도 계산
# Pitch, Yaw, Roll
```

### 4️⃣ **Drowsiness Detection (졸음 감지)**
```python
# EAR이 낮은 상태가 3초 이상 지속
# + 하품 검출 (MAR 높음)
```

---

## 📚 참고 자료

- **MediaPipe**: https://google.github.io/mediapipe/
- **Face Mesh Guide**: https://google.github.io/mediapipe/solutions/face_mesh
- **EAR Paper**: Real-Time Eye Blink Detection using Facial Landmarks
- **MAR Paper**: Driver Yawning Detection Based on Mouth Aspect Ratio

---

## ✅ 요약

**최적 구성 (Jetson Orin)**:
1. ✅ YOLO (사람 검출) - 기존 유지
2. ✅ MediaPipe Face Mesh (얼굴 분석) - 추가
3. ✅ EAR/MAR 알고리즘 (눈/입 상태)
4. ✅ 색상 기반 호흡기 검출
5. ✅ 선택적 처리 (ROI 내부만)

**예상 성능**: 25-35 FPS (전체 파이프라인)

**개발 시간**: 2-3일 (통합 및 테스트 포함)
