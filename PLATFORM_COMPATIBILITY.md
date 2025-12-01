# 플랫폼 호환성 가이드

## 🖥️ 지원 플랫폼

YOLO ROI Person Detector는 다음 플랫폼에서 테스트되고 검증되었습니다:

| 플랫폼 | OS | Python | CUDA | 상태 |
|--------|----|----|------|------|
| **RK3588** | Debian Linaro Bookworm 12 | 3.10 | N/A (CPU) | ✅ 지원 |
| **Jetson Orin** | Jetpack 6.2 (Ubuntu 22.04) | 3.10 | 12.x | ✅ 지원 |
| **x86_64** | Ubuntu 20.04+ / Windows 10+ | 3.8+ | 11.0+ | ✅ 지원 |
| **Raspberry Pi 4/5** | Raspberry Pi OS | 3.9+ | N/A (CPU) | ⚠️ 제한적 |

---

## 📋 플랫폼별 상세 가이드

### 1️⃣ RK3588 (Rockchip)

**하드웨어:**
- RK3588 기반 SBC (예: Orange Pi 5, Rock 5B)
- ARM64 아키텍처
- CPU 기반 추론 (RKNN NPU 지원 예정)

**OS:**
- Debian Linaro Bookworm 12
- Ubuntu 20.04/22.04 (ARM64)

**설치 가이드:**
```bash
# 카메라 권한 체크
./check_camera_permissions.sh

# 기본 설치
pip install -r requirements.txt

# 앱 실행
streamlit run streamlit_app.py
```

**특징:**
- ✅ V4L2 카메라 지원
- ✅ USB 웹캠 지원 (LifeCam HD-3000 등)
- ✅ OpenCV 기반 검출
- ⚠️ CPU 추론 (느린 속도)

**예상 성능:**
- YOLOv8n: ~5-8 FPS (1280x720)
- YOLOv8s: ~3-5 FPS (1280x720)

**최적화 팁:**
```bash
# 해상도 낮추기
v4l2-ctl -d /dev/video0 --set-fmt-video=width=640,height=480

# 경량 모델 사용
# config.json에서 yolo_model: "yolov8n.pt" 사용
```

**문제 해결:**
- 📖 [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) 참고

---

### 2️⃣ NVIDIA Jetson Orin (Jetpack 6.2)

**하드웨어:**
- Jetson Orin Nano (8GB)
- Jetson Orin NX (8GB/16GB)
- Jetson AGX Orin (32GB/64GB)

**OS:**
- Jetpack 6.2 (Ubuntu 22.04 기반)
- CUDA 12.x, cuDNN 8.9.x 포함

**설치 가이드:**
- 📖 **상세 가이드:** [JETSON_SETUP.md](./JETSON_SETUP.md)

```bash
# PyTorch 설치 (Jetson 전용)
pip install torch torchvision --index-url https://developer.download.nvidia.com/compute/redist/jp/v62

# 프로젝트 패키지 설치
pip install ultralytics requests streamlit Pillow flask numpy

# 앱 실행
streamlit run streamlit_app.py
```

**특징:**
- ✅ GPU 가속 (CUDA)
- ✅ TensorRT 최적화 지원
- ✅ 고성능 실시간 검출
- ✅ CSI 카메라 / USB 카메라 지원

**예상 성능:**
- **Orin Nano:** YOLOv8n ~30-40 FPS
- **AGX Orin:** YOLOv8n ~60-80 FPS

**최적화 팁:**
```bash
# 최대 성능 모드
sudo nvpmodel -m 0
sudo jetson_clocks

# TensorRT 엔진 변환
python3 -c "from ultralytics import YOLO; YOLO('yolov8n.pt').export(format='engine', half=True)"
```

---

### 3️⃣ x86_64 (Intel/AMD PC)

**하드웨어:**
- Intel Core i5 이상 / AMD Ryzen 5 이상
- NVIDIA GPU (GTX 1060 이상 권장)
- 8GB RAM 이상

**OS:**
- Ubuntu 20.04 / 22.04
- Windows 10 / 11
- macOS (Apple Silicon 포함)

**설치 가이드:**

**Linux:**
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

**Windows:**
```powershell
pip install -r requirements.txt
streamlit run streamlit_app.py
```

**macOS:**
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

**특징:**
- ✅ GPU 가속 (NVIDIA CUDA)
- ✅ CPU 추론 지원
- ✅ 모든 USB 웹캠 지원
- ✅ 높은 성능

**예상 성능:**
- **NVIDIA RTX 3060:** YOLOv8n ~100+ FPS
- **Intel i5 CPU:** YOLOv8n ~15-20 FPS

---

### 4️⃣ Raspberry Pi 4/5 (제한적 지원)

**하드웨어:**
- Raspberry Pi 4 (4GB/8GB)
- Raspberry Pi 5 (4GB/8GB)

**OS:**
- Raspberry Pi OS (64-bit)

**설치 가이드:**
```bash
# 경량 패키지 설치
pip install ultralytics opencv-python-headless requests streamlit

# 앱 실행
streamlit run streamlit_app.py
```

**특징:**
- ⚠️ CPU 추론만 지원
- ⚠️ 낮은 성능
- ✅ USB 웹캠 지원

**예상 성능:**
- YOLOv8n: ~2-4 FPS (640x480)

**최적화 필수:**
- 해상도: 640x480
- 모델: yolov8n.pt (가장 경량)
- Confidence threshold: 0.7 이상

---

## 🔧 카메라 호환성

### USB 웹캠

| 카메라 | RK3588 | Jetson Orin | x86_64 | Raspberry Pi |
|--------|--------|-------------|--------|--------------|
| Microsoft LifeCam HD-3000 | ✅ | ✅ | ✅ | ✅ |
| Logitech C920 | ✅ | ✅ | ✅ | ✅ |
| Logitech C270 | ✅ | ✅ | ✅ | ✅ |
| Generic USB Webcam | ✅ | ✅ | ✅ | ✅ |

### CSI/MIPI 카메라

| 카메라 | RK3588 | Jetson Orin | x86_64 | Raspberry Pi |
|--------|--------|-------------|--------|--------------|
| Jetson CSI Camera | ❌ | ✅ | ❌ | ❌ |
| Raspberry Pi Camera v2 | ❌ | ❌ | ❌ | ✅ |
| RK3588 MIPI Camera | ✅ | ❌ | ❌ | ❌ |

---

## 📊 성능 비교

### YOLOv8n (1280x720 해상도)

| 플랫폼 | FPS | 전력 소비 | 가격대 |
|--------|-----|----------|--------|
| **Jetson AGX Orin** | 60-80 | ~60W | $$$$ |
| **Jetson Orin Nano** | 30-40 | ~15W | $$$ |
| **RK3588** | 5-8 | ~10W | $$ |
| **x86 RTX 3060** | 100+ | ~200W | $$$ |
| **Raspberry Pi 5** | 2-4 | ~8W | $ |

---

## 🚀 플랫폼별 권장 설정

### RK3588 (CPU 기반)

```json
{
  "yolo_model": "yolov8n.pt",
  "camera_source": 0,
  "frame_width": 640,
  "frame_height": 480,
  "confidence_threshold": 0.6,
  "presence_threshold_seconds": 5,
  "absence_threshold_seconds": 3
}
```

### Jetson Orin (GPU 가속)

```json
{
  "yolo_model": "yolov8n.engine",
  "camera_source": 0,
  "frame_width": 1280,
  "frame_height": 720,
  "confidence_threshold": 0.5,
  "presence_threshold_seconds": 5,
  "absence_threshold_seconds": 3
}
```

### x86_64 (고성능)

```json
{
  "yolo_model": "yolov8s.pt",
  "camera_source": 0,
  "frame_width": 1920,
  "frame_height": 1080,
  "confidence_threshold": 0.5,
  "presence_threshold_seconds": 5,
  "absence_threshold_seconds": 3
}
```

---

## 🔍 플랫폼 감지 코드

프로젝트는 자동으로 플랫폼을 감지합니다:

```python
import platform
import os

def detect_platform():
    system = platform.system()
    machine = platform.machine()
    
    # Jetson 감지
    if os.path.exists('/etc/nv_tegra_release'):
        return 'jetson'
    
    # RK3588 감지
    if machine == 'aarch64' and 'rockchip' in platform.platform().lower():
        return 'rk3588'
    
    # Raspberry Pi 감지
    if os.path.exists('/proc/device-tree/model'):
        with open('/proc/device-tree/model', 'r') as f:
            if 'Raspberry Pi' in f.read():
                return 'raspberry_pi'
    
    # x86_64
    if machine in ['x86_64', 'AMD64']:
        return 'x86_64'
    
    return 'unknown'
```

---

## 📞 플랫폼별 지원

### RK3588
- 📖 [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- 🔧 `./check_camera_permissions.sh`

### Jetson Orin
- 📖 [JETSON_SETUP.md](./JETSON_SETUP.md)
- 🚀 성능 최적화 가이드 포함

### 공통 이슈
- 📖 [README.md](./README.md)
- 💬 GitHub Issues: https://github.com/futurianh1k/roidetyolo/issues

---

**마지막 업데이트:** 2025-01-17
**지원 플랫폼:** RK3588, Jetson Orin, x86_64, Raspberry Pi
