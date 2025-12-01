# NumPy RuntimeError 해결 가이드

## ❌ 발생한 오류

```
RuntimeError: Numpy is not available
```

이 오류는 PyTorch와 NumPy 버전 호환성 문제로 발생합니다.

---

## ✅ 해결 방법

### 방법 1: 패키지 재설치 (권장)

```bash
# 1. 기존 패키지 제거
pip uninstall -y torch torchvision ultralytics numpy

# 2. NumPy 먼저 설치 (호환 버전)
pip install "numpy>=1.24.0,<2.0.0"

# 3. PyTorch 설치 (CPU 버전)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 4. Ultralytics YOLO 설치
pip install ultralytics

# 5. 나머지 패키지 설치
pip install -r requirements.txt
```

### 방법 2: Jetson Orin 환경 (GPU 사용)

**Jetson Orin Jetpack 6.0+의 경우:**

```bash
# 1. NumPy 설치
pip install "numpy>=1.24.0,<2.0.0"

# 2. Jetson 전용 PyTorch 설치
pip install https://developer.download.nvidia.com/compute/redist/jp/v60/pytorch/torch-2.4.0a0+f70bd71a48.nv24.06.15634931-cp310-cp310-linux_aarch64.whl

# 3. torchvision 설치
pip install torchvision

# 4. Ultralytics 설치
pip install ultralytics

# 5. 나머지 패키지
pip install -r requirements_jetson.txt
```

---

## 🔧 코드 수정 사항

### realtime_detector.py 개선

```python
# NumPy 호환성 개선
try:
    # NumPy 배열을 명시적으로 contiguous하게 변환
    frame_input = np.ascontiguousarray(frame)
    results = self.model(frame_input, verbose=False)
except RuntimeError as e:
    print(f"[RealtimeDetector] ⚠️ YOLO 추론 실패: {e}")
    # 프레임을 복사하여 재시도
    frame_input = frame.copy()
    results = self.model(frame_input, verbose=False)
```

### Streamlit 경고 수정

```python
# ❌ 구버전 (Deprecated)
st.image(frame_rgb, use_container_width=True)

# ✅ 신버전 (2025-12-31 이후 필수)
st.image(frame_rgb, width='stretch')
```

---

## 🧪 테스트 방법

### 1. Python 환경 확인

```bash
python3 --version  # Python 3.8-3.11 권장
```

### 2. 패키지 버전 확인

```bash
pip list | grep -E "(numpy|torch|ultralytics|opencv)"
```

**예상 출력:**
```
numpy                     1.26.4
opencv-python             4.11.0.86
torch                     2.4.0
ultralytics               8.3.0
```

### 3. YOLO 모델 테스트

```bash
cd /home/user/yolo_roi_detector
python3 -c "from ultralytics import YOLO; model = YOLO('yolov8n.pt'); print('✅ YOLO 로딩 성공')"
```

### 4. Streamlit 앱 실행

```bash
streamlit run streamlit_app.py
```

---

## 📊 실시간 검출 화면 구성

**Streamlit UI 실행 시 다음과 같이 표시됩니다:**

```
┌─────────────────────────────────────────────────┐
│  카메라 화면 (1280x720)                         │
│                                                 │
│  [ROI1 - 녹색]  ← 사람 검출됨                    │
│    ┌─────────┐                                  │
│    │Person   │  ← BBox 검출 박스                │
│    │  0.95   │  ← 신뢰도                        │
│    └─────────┘                                  │
│                                                 │
│  [ROI2 - 빨간색]  ← 사람 없음                    │
│                                                 │
│  FPS: 30.0  (화면)                              │
│  Detection: 1.0 FPS  (YOLO 추론)                │
└─────────────────────────────────────────────────┘

통계:
- ROI1: 검출 (5초 지속) → API 전송 준비
- ROI2: 미검출 (1초)
```

---

## ⚙️ 성능 최적화

### Jetson Orin에서 TensorRT 사용

```python
# YOLOv8 → TensorRT 변환 (2-3배 속도 향상)
from ultralytics import YOLO

model = YOLO('yolov8n.pt')
model.export(format='engine', half=True)  # FP16 TensorRT

# 변환된 엔진 사용
model_trt = YOLO('yolov8n.engine')
```

### 성능 모드 설정

```bash
# Jetson 최대 성능 모드
sudo nvpmodel -m 0
sudo jetson_clocks
```

---

## 📚 관련 문서

- **PERFORMANCE_OPTIMIZATION.md** - 성능 최적화 가이드
- **JETSON_ORIN_SETUP.md** - Jetson Orin 설치 가이드
- **DETECTION_INTERVAL.md** - 탐지 간격 설정
- **requirements_jetson.txt** - Jetson 전용 패키지

---

## 🆘 추가 문제 해결

### 1. "cannot import name 'YOLO'" 오류

```bash
pip install --upgrade ultralytics
```

### 2. OpenCV 카메라 오류

```bash
# Linux 권한 확인
./check_camera_permissions.sh

# 카메라 테스트
python3 test_camera_detection.py
```

### 3. Streamlit 포트 충돌

```bash
# 다른 포트로 실행
streamlit run streamlit_app.py --server.port 8502
```

---

## ✅ 최종 체크리스트

- [ ] Python 3.8-3.11 설치 확인
- [ ] NumPy < 2.0.0 설치
- [ ] PyTorch 정상 설치
- [ ] Ultralytics YOLO 로딩 성공
- [ ] 카메라 접근 권한 확인
- [ ] Streamlit 앱 정상 실행
- [ ] 실시간 BBox 표시 확인

모든 항목이 체크되면 시스템이 정상 작동합니다! ✨
