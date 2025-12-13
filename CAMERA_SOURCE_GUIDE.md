# 카메라 소스 다변화 가이드

## 📋 개요

YOLO ROI Detector는 다양한 카메라 입력 소스를 지원합니다:
- ✅ USB 웹캠 (로컬 카메라)
- ✅ RTSP 스트림 (IP 카메라)
- ✅ HTTP/HTTPS 스트림 (MJPEG)
- ✅ 비디오 파일 (.mp4, .avi, .mkv 등)
- ✅ 이미지 시퀀스 (연속된 이미지 파일)
- ✅ GStreamer 파이프라인 (고급)

---

## 🎯 빠른 시작

### Streamlit UI에서 설정

1. **Streamlit 앱 실행**
```bash
streamlit run streamlit_app.py
```

2. **좌측 사이드바에서 "📹 카메라" 섹션 찾기**

3. **소스 타입 선택**
   - USB 웹캠
   - RTSP 스트림
   - HTTP 스트림
   - 비디오 파일
   - 기타 (이미지 시퀀스, GStreamer)

4. **소스 입력 및 저장**

### config.json에서 설정

```json
{
  "camera_source": "rtsp://admin:1234@192.168.1.100:554/stream1",
  "camera_source_type": "rtsp"
}
```

---

## 📹 카메라 소스 타입별 가이드

### 1. USB 웹캠 (기본)

**설명**: 로컬에 연결된 USB 웹캠 또는 내장 카메라

**설정 예시**:
```json
{
  "camera_source": 0,
  "camera_source_type": "usb"
}
```

**카메라 번호**:
- `0`: 첫 번째 카메라 (기본)
- `1`: 두 번째 카메라
- `2`: 세 번째 카메라

**자동 검색**:
```python
from camera_utils import detect_available_cameras

cameras = detect_available_cameras(max_cameras=5)
for cam in cameras:
    print(f"Camera {cam['index']}: {cam['resolution']}")
```

**Linux 장치 확인**:
```bash
# 연결된 카메라 확인
ls -la /dev/video*

# 카메라 상세 정보
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --list-formats-ext
```

**추천 설정**:
```json
{
  "camera_source": 0,
  "camera_source_type": "usb",
  "frame_width": 1280,
  "frame_height": 720,
  "confidence_threshold": 0.5
}
```

---

### 2. RTSP 스트림 (IP 카메라)

**설명**: RTSP 프로토콜을 사용하는 IP 카메라 또는 NVR

**URL 형식**:
```
rtsp://[username]:[password]@[ip]:[port]/[path]
```

**설정 예시**:

**일반 IP 카메라**:
```json
{
  "camera_source": "rtsp://admin:password123@192.168.1.100:554/stream1",
  "camera_source_type": "rtsp"
}
```

**Hikvision 카메라**:
```json
{
  "camera_source": "rtsp://admin:12345@192.168.1.64:554/Streaming/Channels/101",
  "camera_source_type": "rtsp"
}
```

**Dahua 카메라**:
```json
{
  "camera_source": "rtsp://admin:admin@192.168.1.108:554/cam/realmonitor?channel=1&subtype=0",
  "camera_source_type": "rtsp"
}
```

**공개 테스트 스트림**:
```json
{
  "camera_source": "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4",
  "camera_source_type": "rtsp"
}
```

**연결 테스트 (ffplay)**:
```bash
# RTSP 스트림 테스트
ffplay -rtsp_transport tcp "rtsp://admin:password@192.168.1.100:554/stream1"
```

**추천 설정**:
```json
{
  "camera_source": "rtsp://admin:password@192.168.1.100:554/stream1",
  "camera_source_type": "rtsp",
  "frame_width": 1920,
  "frame_height": 1080,
  "detection_interval_seconds": 2.0,
  "confidence_threshold": 0.5
}
```

**주의사항**:
- ⚠️ 네트워크 지연이 발생할 수 있습니다
- ⚠️ `detection_interval_seconds`를 2.0 이상으로 설정 권장
- ⚠️ 방화벽에서 RTSP 포트(기본 554) 개방 필요

**문제 해결**:

| 문제 | 해결 방법 |
|------|----------|
| 연결 실패 | URL, 사용자명, 비밀번호 확인 |
| 지연 심함 | `detection_interval_seconds` 증가 (2.0~5.0) |
| 끊김 현상 | 네트워크 안정성 확인, 해상도 낮추기 |
| 타임아웃 | 카메라 펌웨어 업데이트, 네트워크 설정 확인 |

---

### 3. HTTP 스트림 (MJPEG)

**설명**: HTTP를 통한 MJPEG 스트림

**URL 형식**:
```
http://[ip]:[port]/[path]
https://[ip]:[port]/[path]
```

**설정 예시**:

**IP Webcam (Android 앱)**:
```json
{
  "camera_source": "http://192.168.1.100:8080/video",
  "camera_source_type": "http"
}
```

**DroidCam**:
```json
{
  "camera_source": "http://192.168.1.100:4747/video",
  "camera_source_type": "http"
}
```

**일반 MJPEG 스트림**:
```json
{
  "camera_source": "http://admin:password@192.168.1.100:8080/stream.mjpg",
  "camera_source_type": "http"
}
```

**추천 설정**:
```json
{
  "camera_source": "http://192.168.1.100:8080/video",
  "camera_source_type": "http",
  "frame_width": 1280,
  "frame_height": 720,
  "detection_interval_seconds": 1.0
}
```

**Android IP Webcam 앱 사용**:
1. Google Play에서 "IP Webcam" 앱 설치
2. 앱 실행 → "Start server" 클릭
3. 표시되는 URL 사용 (예: http://192.168.1.100:8080)

---

### 4. 비디오 파일

**설명**: 로컬에 저장된 비디오 파일 재생

**지원 형식**:
- MP4, AVI, MKV, MOV, FLV, WMV, WebM, M4V

**설정 예시**:

**Windows**:
```json
{
  "camera_source": "C:\\Users\\user\\Videos\\sample.mp4",
  "camera_source_type": "file"
}
```

**Linux/Mac**:
```json
{
  "camera_source": "/home/user/videos/sample.mp4",
  "camera_source_type": "file"
}
```

**상대 경로**:
```json
{
  "camera_source": "./videos/sample.mp4",
  "camera_source_type": "file"
}
```

**추천 설정**:
```json
{
  "camera_source": "./videos/sample.mp4",
  "camera_source_type": "file",
  "detection_interval_seconds": 0.5,
  "confidence_threshold": 0.5
}
```

**무한 반복 재생** (코드 수정 필요):
```python
# realtime_detector.py의 process_frame() 메서드에서
# 비디오 끝에 도달하면 다시 처음으로
if not ret:
    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
```

---

### 5. 이미지 시퀀스

**설명**: 연속된 번호가 매겨진 이미지 파일

**파일명 패턴**:
```
frame_0001.jpg
frame_0002.jpg
frame_0003.jpg
...
```

**설정 예시**:
```json
{
  "camera_source": "/path/to/images/frame_%04d.jpg",
  "camera_source_type": "image_sequence"
}
```

**패턴 설명**:
- `%04d`: 4자리 숫자 (0001, 0002, ...)
- `%03d`: 3자리 숫자 (001, 002, ...)
- `%05d`: 5자리 숫자 (00001, 00002, ...)

**예시**:
```json
{
  "camera_source": "./dataset/images/img_%05d.png",
  "camera_source_type": "image_sequence"
}
```

**이미지 파일 준비**:
```bash
# 비디오에서 이미지 추출 (ffmpeg)
ffmpeg -i input.mp4 -qscale:v 2 frame_%04d.jpg

# 특정 FPS로 추출
ffmpeg -i input.mp4 -vf fps=10 frame_%04d.jpg
```

---

### 6. GStreamer 파이프라인 (고급)

**설명**: 커스텀 GStreamer 파이프라인

**사전 요구사항**:
```bash
# Ubuntu/Debian
sudo apt-get install gstreamer1.0-tools gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly

# OpenCV with GStreamer 지원 확인
python3 -c "import cv2; print(cv2.getBuildInformation())" | grep GStreamer
```

**설정 예시**:

**테스트 패턴**:
```json
{
  "camera_source": "videotestsrc ! videoconvert ! appsink",
  "camera_source_type": "gstreamer"
}
```

**V4L2 카메라 (Linux)**:
```json
{
  "camera_source": "v4l2src device=/dev/video0 ! videoconvert ! appsink",
  "camera_source_type": "gstreamer"
}
```

**RTSP with GStreamer**:
```json
{
  "camera_source": "rtspsrc location=rtsp://192.168.1.100:554/stream1 ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! appsink",
  "camera_source_type": "gstreamer"
}
```

**CSI 카메라 (Jetson)**:
```json
{
  "camera_source": "nvarguscamerasrc ! video/x-raw(memory:NVMM), width=1280, height=720, format=NV12, framerate=30/1 ! nvvidconv ! video/x-raw, format=BGRx ! videoconvert ! video/x-raw, format=BGR ! appsink",
  "camera_source_type": "gstreamer"
}
```

---

## 🔧 CameraSourceManager API

### Python 코드에서 사용

```python
from camera_utils import CameraSourceManager, CameraSourceType

# 1. 소스 타입 자동 감지
source = "rtsp://192.168.1.100:554/stream1"
source_type = CameraSourceManager.detect_source_type(source)
print(f"Source Type: {source_type}")  # rtsp

# 2. 카메라 열기
cap = CameraSourceManager.open_camera(source, source_type)
if cap and cap.isOpened():
    ret, frame = cap.read()
    cap.release()

# 3. 소스 유효성 검증
validation = CameraSourceManager.validate_source(source)
print(f"Valid: {validation['valid']}")
print(f"Message: {validation['message']}")
print(f"Details: {validation['details']}")

# 4. 소스 정보 조회
info = CameraSourceManager.get_source_info(source)
print(f"Description: {info['description']}")
```

### 소스 타입 상수

```python
from camera_utils import CameraSourceType

CameraSourceType.USB          # "usb"
CameraSourceType.RTSP         # "rtsp"
CameraSourceType.HTTP         # "http"
CameraSourceType.FILE         # "file"
CameraSourceType.IMAGE_SEQ    # "image_sequence"
CameraSourceType.GSTREAMER    # "gstreamer"
```

---

## 📊 성능 비교

| 소스 타입 | 지연 시간 | 안정성 | 해상도 | 추천 detection_interval |
|-----------|----------|--------|--------|------------------------|
| USB 웹캠 | 낮음 (~30ms) | 높음 | 720p-1080p | 1.0초 |
| RTSP 스트림 | 높음 (100-500ms) | 중간 | 1080p-4K | 2.0-5.0초 |
| HTTP 스트림 | 중간 (50-200ms) | 중간 | 720p-1080p | 1.0-2.0초 |
| 비디오 파일 | 낮음 | 높음 | 제한 없음 | 0.5초 |
| 이미지 시퀀스 | 낮음 | 높음 | 제한 없음 | 0.5초 |
| GStreamer | 가변 | 높음 | 제한 없음 | 1.0초 |

---

## ⚙️ 고급 설정

### RTSP 전송 프로토콜 설정

```python
from camera_utils import CameraSourceManager

# TCP 전송 (안정적, 지연 증가)
cap = CameraSourceManager.open_camera(
    "rtsp://192.168.1.100:554/stream1",
    "rtsp",
    rtsp_transport="tcp"
)

# UDP 전송 (빠름, 패킷 손실 가능)
cap = CameraSourceManager.open_camera(
    "rtsp://192.168.1.100:554/stream1",
    "rtsp",
    rtsp_transport="udp"
)
```

### 버퍼 크기 조정

```python
# 지연 최소화 (버퍼 1프레임)
cap = CameraSourceManager.open_camera(
    source,
    source_type,
    buffer_size=1
)
```

### 백엔드 지정

```python
import cv2

# V4L2 백엔드 (Linux USB 카메라)
cap = CameraSourceManager.open_camera(
    0,
    "usb",
    backend=cv2.CAP_V4L2
)

# FFMPEG 백엔드 (RTSP, HTTP)
cap = CameraSourceManager.open_camera(
    "rtsp://...",
    "rtsp",
    backend=cv2.CAP_FFMPEG
)
```

---

## 🐛 문제 해결

### USB 카메라를 찾을 수 없음

**증상**: `detect_available_cameras()`가 빈 리스트 반환

**해결**:
```bash
# 1. 카메라 연결 확인
lsusb

# 2. 비디오 장치 확인
ls -la /dev/video*

# 3. 권한 확인
groups $USER

# 4. video 그룹에 사용자 추가
sudo usermod -aG video $USER

# 5. 로그아웃 후 다시 로그인
```

### RTSP 연결 실패

**증상**: `[RealtimeDetector] ❌ 카메라를 열 수 없습니다`

**해결**:
```bash
# 1. RTSP URL 테스트
ffplay -rtsp_transport tcp "rtsp://admin:password@192.168.1.100:554/stream1"

# 2. 카메라 웹 인터페이스 접속 확인
curl http://192.168.1.100

# 3. 네트워크 연결 확인
ping 192.168.1.100

# 4. 방화벽 확인
sudo ufw allow 554/tcp
```

### 비디오 파일 재생 안됨

**증상**: `process_frame()` 실패

**해결**:
```bash
# 1. 파일 존재 확인
ls -la /path/to/video.mp4

# 2. 코덱 정보 확인
ffprobe video.mp4

# 3. 호환 가능한 형식으로 변환
ffmpeg -i video.mp4 -c:v libx264 -c:a aac output.mp4

# 4. OpenCV 빌드 정보 확인
python3 -c "import cv2; print(cv2.getBuildInformation())"
```

### GStreamer 파이프라인 오류

**증상**: `[CameraSourceManager] ❌ 오류 발생`

**해결**:
```bash
# 1. GStreamer 설치 확인
gst-inspect-1.0 --version

# 2. 파이프라인 테스트
gst-launch-1.0 videotestsrc ! videoconvert ! autovideosink

# 3. OpenCV GStreamer 지원 확인
python3 -c "import cv2; print(cv2.getBuildInformation())" | grep GStreamer
```

---

## 📚 예제 코드

### 예제 1: 여러 소스 순차 테스트

```python
from camera_utils import CameraSourceManager

test_sources = [
    (0, "usb"),
    ("rtsp://example.com:554/stream", "rtsp"),
    ("./video.mp4", "file"),
]

for source, source_type in test_sources:
    print(f"\n=== Testing {source_type}: {source} ===")
    
    validation = CameraSourceManager.validate_source(source)
    print(f"Valid: {validation['valid']}")
    print(f"Message: {validation['message']}")
    
    if validation['valid']:
        cap = CameraSourceManager.open_camera(source, source_type)
        if cap and cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"✅ Frame shape: {frame.shape}")
            cap.release()
```

### 예제 2: RTSP 스트림 모니터링

```python
from camera_utils import CameraSourceManager
import cv2

source = "rtsp://admin:1234@192.168.1.100:554/stream1"
cap = CameraSourceManager.open_camera(source, "rtsp", rtsp_transport="tcp")

if cap and cap.isOpened():
    print("✅ RTSP 연결 성공")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ 프레임 읽기 실패")
            break
        
        cv2.imshow("RTSP Stream", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
else:
    print("❌ RTSP 연결 실패")
```

### 예제 3: 다중 카메라 동시 처리

```python
from camera_utils import CameraSourceManager
import cv2
import threading

def process_camera(source, source_type, name):
    cap = CameraSourceManager.open_camera(source, source_type)
    
    if not cap or not cap.isOpened():
        print(f"❌ {name} 열기 실패")
        return
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        cv2.imshow(name, frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()

# 스레드로 여러 카메라 동시 처리
cameras = [
    (0, "usb", "Camera 1"),
    (1, "usb", "Camera 2"),
]

threads = []
for source, source_type, name in cameras:
    t = threading.Thread(target=process_camera, args=(source, source_type, name))
    t.start()
    threads.append(t)

for t in threads:
    t.join()

cv2.destroyAllWindows()
```

---

## 📖 참고 자료

### OpenCV VideoCapture
- https://docs.opencv.org/4.x/d8/dfe/classcv_1_1VideoCapture.html

### RTSP 프로토콜
- https://en.wikipedia.org/wiki/Real_Time_Streaming_Protocol

### GStreamer
- https://gstreamer.freedesktop.org/documentation/

### IP 카메라 RTSP URL 찾기
- https://www.ispyconnect.com/camera/hikvision
- https://www.ispyconnect.com/camera/dahua

---

**마지막 업데이트**: 2025-12-08  
**버전**: 1.0.0  
**작성자**: AI Development Assistant

