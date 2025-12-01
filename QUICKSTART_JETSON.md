# Jetson Orin 빠른 시작 가이드 (5분 설치)

## ⚡ 빠른 설치 (Jetson Orin Jetpack 6.0)

이 가이드는 **이미 Jetpack 6.0이 설치된** Jetson Orin에서 5분 안에 프로젝트를 실행하는 방법입니다.

---

## 📋 사전 요구사항

- ✅ Jetpack 6.0+b106 설치됨
- ✅ Python 3.10
- ✅ 인터넷 연결
- ✅ USB 카메라 연결

---

## 🚀 1단계: 가상환경 생성 및 활성화

```bash
# 가상환경 생성
python3 -m venv ~/py310

# 가상환경 활성화
source ~/py310/bin/activate
```

---

## 📦 2단계: PyTorch 설치 (Jetson 전용)

```bash
# PyTorch 2.4.0 (Jetpack 6.0 전용) 설치
pip install https://developer.download.nvidia.com/compute/redist/jp/v60/pytorch/torch-2.4.0a0+f70bd71a48.nv24.06.15634931-cp310-cp310-linux_aarch64.whl

# torchvision 설치
pip install --no-deps torchvision==0.19.0

# 설치 확인 (CUDA 지원 확인)
python3 -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

**예상 출력:** `CUDA: True`

---

## 📂 3단계: 프로젝트 클론 및 패키지 설치

```bash
# 프로젝트 클론
cd ~
git clone https://github.com/futurianh1k/roidetyolo.git
cd roidetyolo

# Jetson 전용 requirements 설치
pip install -r requirements_jetson.txt
```

---

## 🎥 4단계: 카메라 권한 설정

```bash
# 사용자를 video 그룹에 추가
sudo usermod -aG video $USER

# 현재 세션에 적용
newgrp video

# 카메라 확인
./check_camera_permissions.sh
```

---

## 🤖 5단계: YOLO 모델 다운로드

```bash
# YOLOv8n 모델 다운로드 (가장 빠름)
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
```

---

## ⚡ 6단계: 성능 최적화

```bash
# 최대 성능 모드
sudo nvpmodel -m 0
sudo jetson_clocks
```

---

## ▶️ 7단계: 앱 실행

```bash
# Streamlit 앱 실행
streamlit run streamlit_app.py
```

브라우저에서 자동으로 열립니다:
```
http://localhost:8501
```

**원격 접속:**
```bash
# IP 확인
hostname -I

# 외부 접속 허용으로 실행
streamlit run streamlit_app.py --server.address=0.0.0.0
```

다른 기기에서 접속:
```
http://<Jetson_IP>:8501
```

---

## ✅ 완료!

이제 웹 브라우저에서:
1. **카메라 검색** 버튼 클릭
2. **4분면 ROI 생성** 버튼 클릭
3. **실시간 검출 탭**으로 이동
4. **검출 시작** 버튼 클릭

---

## 🔧 문제 해결 (빠른 체크)

### PyTorch CUDA 인식 실패

```bash
python3 -c "import torch; print(torch.cuda.is_available())"
```
출력이 `False`면:
```bash
export CUDA_HOME=/usr/local/cuda
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH
```

### 카메라 미검출

```bash
# 카메라 장치 확인
ls -la /dev/video*

# 권한 확인
groups $USER | grep video

# 없으면 다시 추가 후 재로그인
sudo usermod -aG video $USER
```

### OpenCV 오류

```bash
# opencv-python 제거 (Jetpack OpenCV 사용)
pip uninstall opencv-python opencv-python-headless -y
```

---

## 📊 성능 확인

실시간 FPS를 확인하려면:
```bash
# 터미널에서 실행 중인 앱의 로그 확인
# FPS 정보가 출력됨
```

**예상 성능:**
- **Orin Nano:** 25-30 FPS (YOLOv8n)
- **AGX Orin:** 50-60 FPS (YOLOv8n)

---

## 🎯 다음 단계

1. **TensorRT 변환** (성능 2배 향상):
   ```bash
   python3 -c "from ultralytics import YOLO; YOLO('yolov8n.pt').export(format='engine', half=True)"
   ```
   
   `config.json`에서 모델 변경:
   ```json
   {
     "yolo_model": "yolov8n.engine"
   }
   ```

2. **상세 가이드 참고:**
   - `JETSON_ORIN_SETUP.md` - 전체 설정 가이드
   - `PLATFORM_COMPATIBILITY.md` - 플랫폼 비교
   - `TROUBLESHOOTING.md` - 문제 해결

---

## 📝 전체 명령어 (복사용)

```bash
# 1. 가상환경 생성
python3 -m venv ~/py310
source ~/py310/bin/activate

# 2. PyTorch 설치
pip install https://developer.download.nvidia.com/compute/redist/jp/v60/pytorch/torch-2.4.0a0+f70bd71a48.nv24.06.15634931-cp310-cp310-linux_aarch64.whl
pip install --no-deps torchvision==0.19.0

# 3. 프로젝트 설치
cd ~
git clone https://github.com/futurianh1k/roidetyolo.git
cd roidetyolo
pip install -r requirements_jetson.txt

# 4. 카메라 권한
sudo usermod -aG video $USER
newgrp video

# 5. YOLO 모델 다운로드
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt

# 6. 성능 최적화
sudo nvpmodel -m 0
sudo jetson_clocks

# 7. 앱 실행
streamlit run streamlit_app.py
```

---

**소요 시간:** 5-10분 (다운로드 속도에 따라)
**테스트 환경:** Jetson Orin Nano, AGX Orin
**Jetpack 버전:** 6.0+b106
