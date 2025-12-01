# Jetson Orin Jetpack 6.2 설치 가이드

## 🚀 Jetson Orin (Jetpack 6.2) 환경 설정

이 가이드는 NVIDIA Jetson Orin (Jetpack 6.2) 환경에서 YOLO ROI Person Detector를 설정하는 방법을 설명합니다.

---

## 📋 시스템 요구사항

- **하드웨어:** NVIDIA Jetson Orin Nano / Orin NX / AGX Orin
- **OS:** Jetpack 6.2 (Ubuntu 22.04 기반)
- **Python:** 3.10 이상
- **CUDA:** 12.x (Jetpack 6.2에 포함)
- **cuDNN:** 8.9.x (Jetpack 6.2에 포함)

---

## 🔧 1단계: 시스템 준비

### 1.1 시스템 업데이트

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### 1.2 필수 패키지 설치

```bash
# 개발 도구
sudo apt-get install -y python3-pip python3-dev build-essential

# OpenCV 의존성
sudo apt-get install -y libopencv-dev python3-opencv

# V4L2 도구 (카메라 지원)
sudo apt-get install -y v4l-utils

# 시스템 라이브러리
sudo apt-get install -y libhdf5-dev libhdf5-serial-dev
sudo apt-get install -y libjpeg-dev libtiff-dev libpng-dev
sudo apt-get install -y libavcodec-dev libavformat-dev libswscale-dev
```

---

## 🐍 2단계: Python 환경 설정

### 2.1 가상환경 생성 (권장)

```bash
# Python venv 설치
sudo apt-get install -y python3-venv

# 가상환경 생성
python3 -m venv ~/yolo_env

# 가상환경 활성화
source ~/yolo_env/bin/activate
```

### 2.2 pip 업그레이드

```bash
pip install --upgrade pip setuptools wheel
```

---

## 🔥 3단계: PyTorch 설치 (Jetson 전용)

**중요:** Jetson에서는 NVIDIA 공식 PyTorch 빌드를 사용해야 합니다.

### 3.1 PyTorch 설치 (Jetpack 6.2)

```bash
# Jetpack 6.2용 PyTorch 2.3.0 설치
pip install torch torchvision torchaudio --index-url https://developer.download.nvidia.com/compute/redist/jp/v62

# 또는 pip wheel 직접 설치
wget https://developer.download.nvidia.com/compute/redist/jp/v62/pytorch/torch-2.3.0-cp310-cp310-linux_aarch64.whl
pip install torch-2.3.0-cp310-cp310-linux_aarch64.whl
```

### 3.2 설치 확인

```bash
python3 -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'CUDA Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
```

**예상 출력:**
```
PyTorch: 2.3.0
CUDA Available: True
CUDA Device: Orin
```

---

## 📦 4단계: 프로젝트 패키지 설치

### 4.1 저장소 클론

```bash
cd ~
git clone https://github.com/futurianh1k/roidetyolo.git
cd roidetyolo
```

### 4.2 OpenCV 설정 (Jetson 최적화)

Jetpack에는 이미 최적화된 OpenCV가 포함되어 있습니다:

```bash
# Jetpack의 OpenCV 사용 (권장)
# requirements.txt에서 opencv-python 주석 처리 또는 제거
pip install --no-deps ultralytics requests streamlit Pillow flask

# 또는 opencv-python 설치 (선택사항)
pip install opencv-python
```

### 4.3 나머지 패키지 설치

```bash
# Ultralytics YOLO 설치
pip install ultralytics

# 기타 필수 패키지
pip install requests streamlit Pillow flask numpy

# 또는 requirements.txt 사용 (opencv-python 제외)
sed '/opencv-python/d' requirements.txt > requirements_jetson.txt
pip install -r requirements_jetson.txt
```

---

## 🎥 5단계: 카메라 설정

### 5.1 카메라 권한 설정

```bash
# 사용자를 video 그룹에 추가
sudo usermod -aG video $USER

# 변경사항 적용 (로그아웃 후 재로그인 필요)
# 또는 현재 세션에서 확인
newgrp video
```

### 5.2 카메라 장치 확인

```bash
# 연결된 카메라 확인
v4l2-ctl --list-devices

# 카메라 포맷 확인
v4l2-ctl -d /dev/video0 --list-formats-ext

# USB 카메라 확인
lsusb
```

### 5.3 카메라 테스트

```bash
# 프로젝트 스크립트 사용
./check_camera_permissions.sh

# 또는 Python 테스트
python3 test_camera_detection.py
```

---

## 🚀 6단계: YOLO 모델 다운로드

### 6.1 YOLOv8 모델 다운로드

```bash
# 프로젝트 디렉토리에서
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
```

### 6.2 모델 테스트

```python
from ultralytics import YOLO

# 모델 로드
model = YOLO('yolov8n.pt')

# GPU 사용 확인
print(f"Device: {model.device}")
```

---

## ▶️ 7단계: 애플리케이션 실행

### 7.1 Streamlit 앱 실행

```bash
# 가상환경 활성화 (사용 중인 경우)
source ~/yolo_env/bin/activate

# Streamlit 앱 실행
cd ~/roidetyolo
streamlit run streamlit_app.py
```

### 7.2 웹 브라우저에서 접속

```
http://localhost:8501
```

또는 원격 접속:

```
http://<Jetson_IP>:8501
```

---

## ⚡ 성능 최적화 (Jetson Orin)

### 8.1 전력 모드 설정

```bash
# 최대 성능 모드로 설정
sudo nvpmodel -m 0

# 팬 속도 최대로 설정 (냉각)
sudo jetson_clocks
```

### 8.2 CUDA 최적화

```bash
# CUDA 환경 변수 설정 (선택사항)
export CUDA_VISIBLE_DEVICES=0
export TF_FORCE_GPU_ALLOW_GROWTH=true
```

### 8.3 모델 최적화

```python
# TensorRT 엔진으로 변환 (선택사항)
from ultralytics import YOLO

model = YOLO('yolov8n.pt')
model.export(format='engine', half=True)  # FP16 정밀도

# TensorRT 모델 사용
model = YOLO('yolov8n.engine')
```

---

## 🐛 문제 해결 (Jetson 특화)

### 문제 1: PyTorch CUDA 인식 실패

```bash
# CUDA 환경 확인
nvcc --version

# cuDNN 확인
dpkg -l | grep cudnn

# 환경 변수 설정
export CUDA_HOME=/usr/local/cuda
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH
```

### 문제 2: 메모리 부족

```bash
# Swap 파일 크기 증가 (8GB)
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 영구 설정
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 문제 3: OpenCV 카메라 문제

```bash
# GStreamer 백엔드 사용
export OPENCV_VIDEOIO_PRIORITY_GSTREAMER=1

# 또는 코드에서 설정
cap = cv2.VideoCapture(0, cv2.CAP_GSTREAMER)
```

### 문제 4: USB 카메라 지연

```bash
# 버퍼 크기 조정
v4l2-ctl -d /dev/video0 --set-fmt-video=width=1280,height=720,pixelformat=MJPG
```

---

## 📊 성능 벤치마크 (예상)

### Jetson Orin Nano (8GB)
- **YOLOv8n:** ~30-40 FPS (1280x720)
- **YOLOv8s:** ~20-25 FPS (1280x720)
- **YOLOv8m:** ~12-15 FPS (1280x720)

### Jetson AGX Orin (64GB)
- **YOLOv8n:** ~60-80 FPS (1280x720)
- **YOLOv8s:** ~40-50 FPS (1280x720)
- **YOLOv8m:** ~25-30 FPS (1280x720)

---

## 🔄 자동 시작 설정 (선택사항)

### systemd 서비스 생성

```bash
sudo nano /etc/systemd/system/yolo-detector.service
```

```ini
[Unit]
Description=YOLO ROI Person Detector
After=network.target

[Service]
Type=simple
User=<your_username>
WorkingDirectory=/home/<your_username>/roidetyolo
ExecStart=/home/<your_username>/yolo_env/bin/streamlit run streamlit_app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# 서비스 활성화
sudo systemctl daemon-reload
sudo systemctl enable yolo-detector.service
sudo systemctl start yolo-detector.service

# 상태 확인
sudo systemctl status yolo-detector.service
```

---

## 📚 추가 자료

- **NVIDIA Jetson 공식 문서:** https://developer.nvidia.com/embedded/jetson-orin
- **Jetpack 6.2 릴리스 노트:** https://developer.nvidia.com/embedded/jetpack
- **Ultralytics YOLO Jetson 가이드:** https://docs.ultralytics.com/guides/nvidia-jetson/

---

## ✅ 설치 완료 체크리스트

- [ ] Jetpack 6.2 설치 확인
- [ ] PyTorch CUDA 지원 확인
- [ ] 카메라 권한 설정
- [ ] v4l-utils 설치
- [ ] YOLO 모델 다운로드
- [ ] 카메라 테스트 성공
- [ ] Streamlit 앱 실행 성공
- [ ] 실시간 검출 작동 확인

---

**마지막 업데이트:** 2025-01-17
**Jetpack 버전:** 6.2
**테스트 환경:** Jetson Orin Nano, Jetson AGX Orin
