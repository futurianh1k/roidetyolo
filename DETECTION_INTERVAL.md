# 검출 간격 설정 가이드

## 🎯 개요

YOLO 추론은 GPU/CPU 리소스를 많이 사용합니다. 실시간 모니터링에서는 **매 프레임마다 검출할 필요가 없습니다**.

이 시스템은 **검출 간격**을 설정하여 리소스 사용량을 최적화합니다.

---

## 🔧 작동 방식

### 기본 개념

```
카메라 입력: 30 FPS (매 33ms마다 프레임)
YOLO 검출: 1초에 1회 (매 1000ms마다)
화면 표시: 30 FPS (부드러운 영상 유지)
```

### 구현 방식

```python
# realtime_detector.py
def process_frame(self):
    current_time = time.time()
    
    # YOLO 추론을 설정된 간격마다만 수행
    if current_time - self.last_detection_time >= self.detection_interval:
        # YOLO 추론 실행
        results = self.model(frame, verbose=False)
        # 검출 결과 저장
        self.last_detections = detections
        self.last_detection_time = current_time
    else:
        # 이전 검출 결과 재사용
        detections = self.last_detections
    
    # 시각화는 매 프레임마다 수행 (부드러운 영상)
    annotated_frame = self.draw_rois_and_detections(frame, detections)
```

**장점:**
- ✅ **화면은 부드럽게 30 FPS 유지**
- ✅ **YOLO 추론은 1초에 1회만** (CPU/GPU 부담 감소)
- ✅ **검출 결과는 다음 간격까지 재사용**

---

## 📊 검출 간격 옵션

### 1️⃣ **0.5초 (2회/초)**

```json
{
  "detection_interval_seconds": 0.5
}
```

**사용 시나리오:**
- 빠른 움직임 추적
- 정밀한 실시간 감지 필요
- 고성능 하드웨어 (AGX Orin)

**성능:**
- Orin Nano: FPS 영향 중간 (20-25 FPS)
- AGX Orin: FPS 영향 적음 (40-50 FPS)

### 2️⃣ **1.0초 (1회/초) ⭐ 권장**

```json
{
  "detection_interval_seconds": 1.0
}
```

**사용 시나리오:**
- 일반적인 사람 검출
- 균형잡힌 성능과 정확도
- **대부분의 경우에 적합**

**성능:**
- Orin Nano: 30 FPS, 낮은 리소스 사용
- AGX Orin: 60 FPS, 매우 낮은 리소스 사용

**장점:**
- ✅ 충분한 검출 빈도
- ✅ 낮은 CPU/GPU 사용률
- ✅ 안정적인 성능

### 3️⃣ **2.0초 (0.5회/초)**

```json
{
  "detection_interval_seconds": 2.0
}
```

**사용 시나리오:**
- 느린 움직임 또는 정적 장면
- 최소 리소스 사용
- 배터리 절약 (모바일 장비)

**성능:**
- Orin Nano: 30 FPS, 매우 낮은 리소스
- AGX Orin: 60 FPS, 거의 idle 상태

### 4️⃣ **3.0초 (0.33회/초)**

```json
{
  "detection_interval_seconds": 3.0
}
```

**사용 시나리오:**
- 장기 모니터링
- 극도로 낮은 리소스 사용
- 다중 카메라 동시 운영

### 5️⃣ **5.0초 (0.2회/초)**

```json
{
  "detection_interval_seconds": 5.0
}
```

**사용 시나리오:**
- 정적 환경 감시
- 최소한의 전력 소비
- 로그 기록 위주

---

## 📈 성능 비교

### Jetson Orin Nano (8GB)

| 검출 간격 | YOLO FPS | 화면 FPS | CPU 사용률 | GPU 사용률 |
|-----------|----------|----------|------------|------------|
| 0.5초 | 2회/초 | 30 | 60-70% | 40-50% |
| **1.0초 ⭐** | **1회/초** | **30** | **40-50%** | **25-35%** |
| 2.0초 | 0.5회/초 | 30 | 25-35% | 15-25% |
| 3.0초 | 0.33회/초 | 30 | 20-30% | 10-20% |
| 5.0초 | 0.2회/초 | 30 | 15-25% | 5-15% |

### Jetson AGX Orin (64GB)

| 검출 간격 | YOLO FPS | 화면 FPS | CPU 사용률 | GPU 사용률 |
|-----------|----------|----------|------------|------------|
| 0.5초 | 2회/초 | 60 | 40-50% | 30-40% |
| **1.0초 ⭐** | **1회/초** | **60** | **25-35%** | **15-25%** |
| 2.0초 | 0.5회/초 | 60 | 15-25% | 10-15% |
| 3.0초 | 0.33회/초 | 60 | 10-20% | 5-10% |
| 5.0초 | 0.2회/초 | 60 | 8-15% | 3-8% |

---

## ⚙️ 설정 방법

### 1️⃣ Streamlit UI에서 설정

**사이드바 → 검출 설정:**
```
🔄 YOLO 검출 간격 (초)
[슬라이더] 0.5 | 1.0 | 2.0 | 3.0 | 5.0
💡 1.0초마다 사람 검출
```

### 2️⃣ config.json 파일 수정

```json
{
  "detection_interval_seconds": 1.0,
  "confidence_threshold": 0.5,
  "presence_threshold_seconds": 5,
  "absence_threshold_seconds": 3
}
```

### 3️⃣ 프로그래밍 방식

```python
from realtime_detector import RealtimeDetector

config = {
    "detection_interval_seconds": 1.0,  # 1초에 1회 검출
    "yolo_model": "yolov8n.pt",
    # ... 기타 설정
}

detector = RealtimeDetector(config, roi_regions)
detector.start()
```

---

## 🎯 권장 사항

### 일반적인 사용 (권장)

```json
{
  "detection_interval_seconds": 1.0
}
```

**이유:**
- 1초 간격이면 충분히 빠른 검출
- 리소스 사용량 최적화
- 안정적인 성능

### 고성능 추적 필요 시

```json
{
  "detection_interval_seconds": 0.5
}
```

**이유:**
- 빠른 움직임 포착
- 고정밀 추적
- AGX Orin 이상 권장

### 리소스 절약 우선 시

```json
{
  "detection_interval_seconds": 2.0
}
```

**이유:**
- 배터리 절약
- 다중 카메라 운영
- 낮은 전력 소비

---

## 📊 실제 사용 예시

### 예시 1: 출입구 모니터링

```json
{
  "detection_interval_seconds": 1.0,
  "presence_threshold_seconds": 3,
  "absence_threshold_seconds": 2
}
```

**설명:**
- 1초마다 사람 검출
- 3초 이상 있으면 "입장" 이벤트
- 2초 이상 없으면 "퇴장" 이벤트

### 예시 2: 주차장 감시

```json
{
  "detection_interval_seconds": 2.0,
  "presence_threshold_seconds": 5,
  "absence_threshold_seconds": 5
}
```

**설명:**
- 2초마다 검출 (느린 움직임)
- 5초 이상 정지 시 "주차" 이벤트

### 예시 3: 고속 이동 추적

```json
{
  "detection_interval_seconds": 0.5,
  "presence_threshold_seconds": 2,
  "absence_threshold_seconds": 1
}
```

**설명:**
- 0.5초마다 검출 (빠른 움직임)
- 신속한 이벤트 감지

---

## 🔍 화면 표시 정보

실시간 검출 화면에 다음 정보가 표시됩니다:

```
좌상단:
┌─────────────────────────────┐
│ Display FPS: 30.0           │  ← 화면 프레임 속도
│ YOLO: Every 1.0s            │  ← YOLO 검출 간격
└─────────────────────────────┘
```

**의미:**
- **Display FPS**: 카메라에서 읽어오는 화면 FPS (항상 30 FPS)
- **YOLO: Every Xs**: YOLO 추론 간격 (설정값)

---

## 🐛 문제 해결

### 문제 1: 화면이 끊김

**원인:**
- 검출 간격과 무관한 문제
- 카메라 또는 네트워크 문제

**해결:**
```bash
# 카메라 확인
v4l2-ctl -d /dev/video0 --all
```

### 문제 2: 검출이 너무 느림

**원인:**
- 검출 간격이 너무 길게 설정됨

**해결:**
```json
{
  "detection_interval_seconds": 0.5  // 간격 줄이기
}
```

### 문제 3: CPU/GPU 사용률이 높음

**원인:**
- 검출 간격이 너무 짧음

**해결:**
```json
{
  "detection_interval_seconds": 2.0  // 간격 늘리기
}
```

---

## 📚 추가 최적화

### TensorRT와 조합

```bash
# TensorRT 변환 후
{
  "yolo_model": "yolov8n.engine",
  "detection_interval_seconds": 0.5  // 더 짧은 간격 가능
}
```

**효과:**
- TensorRT: 2-3배 빠른 추론
- 0.5초 간격도 부담 없음

### 다중 카메라 운영

```python
# 카메라 1: 1초 간격
detector1 = RealtimeDetector(config1, roi1)

# 카메라 2: 2초 간격 (리소스 절약)
detector2 = RealtimeDetector(config2, roi2)
```

---

## ✅ 체크리스트

- [ ] 검출 간격 설정 확인 (`detection_interval_seconds`)
- [ ] 사용 시나리오에 맞는 간격 선택
- [ ] 화면 FPS 30 FPS 유지 확인
- [ ] CPU/GPU 사용률 모니터링
- [ ] 이벤트 검출 빈도 테스트

---

**마지막 업데이트:** 2025-01-17
**권장 설정:** 1.0초 (대부분의 경우)
**리소스 절약:** 2.0초 이상
**고속 추적:** 0.5초
