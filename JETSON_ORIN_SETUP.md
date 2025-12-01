# Jetson Orin 개발환경 셋업 가이드

## 🎯 개요

이 가이드는 **Jetson Orin (Jetpack 6.0)** 환경에서 YOLO ROI Person Detector를 설치하고 실행하는 방법을 설명합니다.

---

## 📋 시스템 환경 확인

### 현재 검증된 환경

```
OS: Ubuntu 22.04 (Jetpack 6.0)
Python: 3.10
CUDA: 12.2
cuDNN: 8.9.4
Jetpack: 6.0+b106
```

### 환경 확인 명령

```bash
# Jetpack 버전 확인
dpkg -l | grep nvidia-jetpack

# Python 버전 확인
python3 --version

# CUDA 버전 확인
nvcc --version

# cuDNN 버전 확인
ls /usr/lib/aarch64-linux-gnu/libcudnn.so*

# GPU 정보 확인
nvidia-smi
```

**예상 출력:**
```
ii  nvidia-jetpack          6.0+b106    arm64
ii  nvidia-jetpack-dev      6.0+b106    arm64
ii  nvidia-jetpack-runtime  6.0+b106    arm64

Python 3.10.x

CUDA Version 12.2

/usr/lib/aarch64-linux-gnu/libcudnn.so
/usr/lib/aarch64-linux-gnu/libcudnn.so.8
/usr/lib/aarch64-linux-gnu/libcudnn.so.8.9.4
```

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

# Git (필요시)
sudo apt-get install -y git

# V4L2 도구 (카메라 지원)
sudo apt-get install -y v4l-utils

# 시스템 라이브러리
sudo apt-get install -y libhdf5-dev libhdf5-serial-dev
sudo apt-get install -y libjpeg-dev libtiff-dev libpng-dev
sudo apt-get install -y libavcodec-dev libavformat-dev libswscale-dev
```

---

## 🐍 2단계: Python 가상환경 생성 (권장)

### 2.1 가상환경 생성

```bash
# Python venv 설치 확인
sudo apt-get install -y python3-venv

# 가상환경 생성
python3 -m venv ~/py310
# 또는 원하는 이름으로: python3 -m venv ~/yolo_env

# 가상환경 활성화
source ~/py310/bin/activate

# 프롬프트가 (py310)으로 변경되는지 확인
```

### 2.2 pip 업그레이드

```bash
pip install --upgrade pip setuptools wheel
```

---

## 🔥 3단계: PyTorch 설치 (Jetson 전용)

### 3.1 PyTorch Wheel 다운로드 및 설치

**중요:** Jetpack 6.0에는 특정 PyTorch 빌드가 필요합니다.

```bash
# PyTorch 2.4.0 (Jetpack 6.0 전용) 직접 설치
pip install https://developer.download.nvidia.com/compute/redist/jp/v60/pytorch/torch-2.4.0a0+f70bd71a48.nv24.06.15634931-cp310-cp310-linux_aarch64.whl

# 또는 미리 다운로드 후 설치
wget https://developer.download.nvidia.com/compute/redist/jp/v60/pytorch/torch-2.4.0a0+f70bd71a48.nv24.06.15634931-cp310-cp310-linux_aarch64.whl
pip install torch-2.4.0a0+f70bd71a48.nv24.06.15634931-cp310-cp310-linux_aarch64.whl
```

### 3.2 torchvision 설치

```bash
# torchvision 0.19.0 설치 (의존성 체크 없이)
pip install --no-deps torchvision==0.19.0
```

### 3.3 설치 확인

```bash
python3 << 'EOF'
import torch
print(f"PyTorch Version: {torch.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA Version: {torch.version.cuda}")
    print(f"cuDNN Version: {torch.backends.cudnn.version()}")
    print(f"GPU Device: {torch.cuda.get_device_name(0)}")
    print(f"GPU Count: {torch.cuda.device_count()}")
EOF
```

**예상 출력:**
```
PyTorch Version: 2.4.0a0+f70bd71a48.nv24.06
CUDA Available: True
CUDA Version: 12.2
cuDNN Version: 8904
GPU Device: Orin
GPU Count: 1
```

---

## 📦 4단계: 프로젝트 설치

### 4.1 저장소 클론

```bash
cd ~
git clone https://github.com/futurianh1k/roidetyolo.git
cd roidetyolo
```

### 4.2 OpenCV 확인

Jetpack에는 최적화된 OpenCV가 포함되어 있습니다:

```bash
# Jetpack의 OpenCV 확인
python3 -c "import cv2; print(f'OpenCV Version: {cv2.__version__}')"

# OpenCV CUDA 지원 확인
python3 -c "import cv2; print(f'CUDA Enabled: {cv2.cuda.getCudaEnabledDeviceCount() > 0}')"
```

**주의:** `opencv-python`을 설치하지 마세요! Jetpack의 OpenCV를 사용하는 것이 성능상 유리합니다.

### 4.3 프로젝트 패키지 설치

```bash
# Jetson 전용 requirements 파일 사용
pip install -r requirements_jetson.txt

# 또는 수동 설치
pip install ultralytics==8.3.0
pip install streamlit==1.28.0
pip install requests==2.31.0
pip install Pillow==10.0.0
pip install flask==3.0.0
pip install numpy>=1.24.0
pip install PyYAML tqdm
```

---

## 🎥 5단계: 카메라 설정

### 5.1 카메라 권한 설정

```bash
# 사용자를 video 그룹에 추가
sudo usermod -aG video $USER

# 현재 세션에 적용
newgrp video

# 또는 로그아웃 후 재로그인
```

### 5.2 카메라 장치 확인

```bash
# USB 카메라 확인
lsusb

# 비디오 장치 확인
ls -la /dev/video*

# v4l2-ctl로 상세 정보 확인
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --all
```

### 5.3 카메라 테스트

```bash
# 프로젝트의 카메라 권한 체크 스크립트 실행
./check_camera_permissions.sh

# 또는 Python 테스트 스크립트
python3 test_camera_detection.py
```

---

## 🚀 6단계: YOLO 모델 다운로드

### 6.1 YOLOv8 모델 다운로드

```bash
# 프로젝트 디렉토리에서
cd ~/roidetyolo

# YOLOv8n (가장 빠름, 권장)
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt

# 또는 다른 모델 (선택사항)
# wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt
# wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8m.pt
```

### 6.2 모델 테스트

```bash
python3 << 'EOF'
from ultralytics import YOLO
import torch

# 모델 로드
model = YOLO('yolov8n.pt')

# GPU 사용 확인
print(f"Model Device: {model.device}")
print(f"CUDA Available: {torch.cuda.is_available()}")

# 간단한 추론 테스트 (더미 이미지)
import numpy as np
dummy_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
results = model(dummy_image, verbose=False)
print(f"✅ Model inference test passed!")
EOF
```

---

## ⚡ 7단계: 성능 최적화 (중요!)

### 7.1 전력 모드 설정

```bash
# 현재 전력 모드 확인
sudo nvpmodel -q

# 최대 성능 모드로 설정 (Mode 0)
sudo nvpmodel -m 0

# 모든 클럭 최대화
sudo jetson_clocks

# 확인
sudo jetson_clocks --show
```

### 7.2 팬 제어 (냉각)

```bash
# 팬 속도 최대로 설정 (과열 방지)
sudo sh -c 'echo 255 > /sys/devices/pwm-fan/target_pwm'
```

### 7.3 TensorRT 엔진 변환 (선택사항)

TensorRT로 변환하면 추론 속도가 2-3배 향상됩니다:

```bash
python3 << 'EOF'
from ultralytics import YOLO

# YOLOv8n을 TensorRT 엔진으로 변환
model = YOLO('yolov8n.pt')
model.export(format='engine', half=True)  # FP16 정밀도

print("✅ TensorRT engine created: yolov8n.engine")
EOF
```

변환 후 `config.json`에서 모델 경로를 변경:
```json
{
  "yolo_model": "yolov8n.engine"
}
```

---

## ▶️ 8단계: 애플리케이션 실행

### 8.1 가상환경 활성화 확인

```bash
# 가상환경이 활성화되어 있는지 확인
source ~/py310/bin/activate
```

### 8.2 Streamlit 앱 실행

```bash
cd ~/roidetyolo

# 로컬 실행
streamlit run streamlit_app.py

# 또는 외부 접속 허용
streamlit run streamlit_app.py --server.address=0.0.0.0 --server.port=8501
```

### 8.3 브라우저 접속

**로컬:**
```
http://localhost:8501
```

**원격 접속:**
```
http://<Jetson_IP>:8501
```

Jetson IP 확인:
```bash
hostname -I
```

---

## 🔧 9단계: 환경 변수 설정 (선택사항)

### 9.1 .bashrc 설정

가상환경 자동 활성화 및 환경 변수 설정:

```bash
nano ~/.bashrc
```

파일 끝에 추가:
```bash
# Jetson Orin YOLO 환경
export CUDA_HOME=/usr/local/cuda
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

# 가상환경 자동 활성화 (선택사항)
# source ~/py310/bin/activate

# Jetson 성능 모드 (부팅 시 자동 적용)
alias jetson_perf='sudo nvpmodel -m 0 && sudo jetson_clocks'
```

저장 후:
```bash
source ~/.bashrc
```

---

## 🐛 문제 해결

### 문제 1: PyTorch CUDA 인식 실패

```bash
# CUDA 환경 변수 확인
echo $CUDA_HOME
echo $LD_LIBRARY_PATH

# 환경 변수 재설정
export CUDA_HOME=/usr/local/cuda
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

# Python에서 재확인
python3 -c "import torch; print(torch.cuda.is_available())"
```

### 문제 2: OpenCV ImportError

```bash
# Jetpack OpenCV 경로 확인
python3 -c "import cv2; print(cv2.__file__)"

# opencv-python이 설치되어 있으면 제거
pip uninstall opencv-python opencv-python-headless -y

# Jetpack OpenCV 재확인
python3 -c "import cv2; print(cv2.__version__)"
```

### 문제 3: 메모리 부족

```bash
# Swap 파일 생성 (8GB)
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 영구 설정
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 확인
free -h
```

### 문제 4: Streamlit 포트 충돌

```bash
# 다른 포트 사용
streamlit run streamlit_app.py --server.port=8502

# 또는 기존 프로세스 종료
lsof -ti:8501 | xargs kill -9
```

### 문제 5: 카메라 권한 오류

```bash
# 현재 사용자 그룹 확인
groups $USER

# video 그룹에 없으면 추가
sudo usermod -aG video $USER

# 로그아웃 후 재로그인 또는
newgrp video

# 카메라 장치 권한 직접 부여 (임시)
sudo chmod 666 /dev/video0
```

---

## 📊 성능 벤치마크

### Jetson Orin Nano (8GB)

**YOLOv8n (1280x720):**
- PyTorch: ~25-30 FPS
- TensorRT (FP16): ~40-50 FPS

**YOLOv8s (1280x720):**
- PyTorch: ~15-20 FPS
- TensorRT (FP16): ~25-30 FPS

### Jetson AGX Orin (32GB/64GB)

**YOLOv8n (1280x720):**
- PyTorch: ~50-60 FPS
- TensorRT (FP16): ~80-100 FPS

**YOLOv8m (1280x720):**
- PyTorch: ~20-25 FPS
- TensorRT (FP16): ~35-45 FPS

---

## 🔄 자동 시작 설정 (선택사항)

### systemd 서비스 생성

```bash
sudo nano /etc/systemd/system/yolo-detector.service
```

내용:
```ini
[Unit]
Description=YOLO ROI Person Detector
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/roidetyolo
Environment="PATH=/home/ubuntu/py310/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStartPre=/usr/bin/nvidia-smi
ExecStartPre=/usr/bin/sudo /usr/sbin/nvpmodel -m 0
ExecStartPre=/usr/bin/sudo /usr/bin/jetson_clocks
ExecStart=/home/ubuntu/py310/bin/streamlit run streamlit_app.py --server.address=0.0.0.0 --server.port=8501
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

서비스 등록:
```bash
# 서비스 활성화
sudo systemctl daemon-reload
sudo systemctl enable yolo-detector.service

# 서비스 시작
sudo systemctl start yolo-detector.service

# 상태 확인
sudo systemctl status yolo-detector.service

# 로그 확인
sudo journalctl -u yolo-detector.service -f
```

---

## ✅ 설치 완료 체크리스트

### 필수 항목
- [ ] Jetpack 6.0 설치 확인 (`dpkg -l | grep nvidia-jetpack`)
- [ ] Python 3.10 확인 (`python3 --version`)
- [ ] 가상환경 생성 및 활성화
- [ ] PyTorch 2.4.0 설치 (Jetson 전용 wheel)
- [ ] torchvision 0.19.0 설치
- [ ] PyTorch CUDA 지원 확인 (`torch.cuda.is_available()`)
- [ ] 프로젝트 클론 (`git clone`)
- [ ] requirements_jetson.txt 패키지 설치
- [ ] 카메라 권한 설정 (`sudo usermod -aG video $USER`)
- [ ] 카메라 테스트 성공 (`./check_camera_permissions.sh`)
- [ ] YOLO 모델 다운로드 (`yolov8n.pt`)
- [ ] 모델 추론 테스트 성공

### 성능 최적화 (권장)
- [ ] 최대 성능 모드 설정 (`sudo nvpmodel -m 0`)
- [ ] Jetson clocks 활성화 (`sudo jetson_clocks`)
- [ ] TensorRT 엔진 변환 (선택사항)

### 실행 확인
- [ ] Streamlit 앱 실행 성공
- [ ] 브라우저에서 접속 성공
- [ ] 카메라 스트림 확인
- [ ] 실시간 검출 작동 확인
- [ ] BBox 표시 확인
- [ ] ROI 설정 및 저장 테스트

---

## 📚 추가 자료

- **NVIDIA Jetson 공식 문서:** https://developer.nvidia.com/embedded/jetson-orin
- **Jetpack 6.0 릴리스 노트:** https://developer.nvidia.com/embedded/jetpack
- **PyTorch for Jetson:** https://forums.developer.nvidia.com/t/pytorch-for-jetson
- **Ultralytics YOLO:** https://docs.ultralytics.com/

---

## 📞 지원

문제가 발생하면:
1. `TROUBLESHOOTING.md` 확인
2. GitHub Issues: https://github.com/futurianh1k/roidetyolo/issues
3. Jetson 커뮤니티 포럼: https://forums.developer.nvidia.com/c/agx-autonomous-machines/jetson-embedded-systems

---

**마지막 업데이트:** 2025-01-17
**테스트 환경:** Jetson Orin Nano, Jetson AGX Orin
**Jetpack 버전:** 6.0+b106
**Python 버전:** 3.10
**PyTorch 버전:** 2.4.0a0+f70bd71a48.nv24.06
