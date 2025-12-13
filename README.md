# YOLO 기반 ROI 사람 검출 및 이벤트 전송 시스템

## 📋 개요

이 프로젝트는 YOLO 최신 버전(YOLOv8/YOLOv11)을 사용하여 카메라 영상에서 ROI(Region of Interest) 영역을 설정하고, 해당 영역에서 사람을 검출하여 API 엔드포인트로 이벤트를 전송하는 시스템입니다.

## ✨ 주요 기능

- **🎯 다중 ROI 영역 설정**: 여러 개의 관심 영역(ROI) 동시 모니터링
- **👤 실시간 사람 검출**: YOLO를 사용한 고정밀 사람 검출
- **⏱️ 체류 시간 측정**: 각 ROI에서 사람의 체류 시간 추적
- **📤 자동 이벤트 전송**: 조건 충족 시 API 엔드포인트로 이벤트 자동 전송
- **🔄 실시간 모니터링**: 검출 상태 실시간 시각화
- **📹 다양한 카메라 소스 지원**: USB 웹캠, RTSP/HTTP 스트림, 비디오 파일, 이미지 시퀀스, GStreamer 파이프라인

## 🎮 동작 방식

### 검출 로직

1. **사람 검출 시작**: ROI 영역에 사람이 들어오면 검출 시작
2. **존재 확인 (Present)**: 
   - ROI에서 사람이 **5초 이상** 검출되면
   - API로 `status: 1` (present) 이벤트 전송
3. **부재 확인 (Absent)**:
   - 사람이 검출되다가 검출되지 않는 상태가 **3초 이상** 지속되면
   - API로 `status: 0` (absent) 이벤트 전송

### 카운팅 시스템

- 각 ROI 영역마다 **1초에 1회씩** 검출 횟수 카운트
- 연속된 검출 시간을 누적하여 임계값 비교

## 🚀 설치 방법

### 1. 패키지 설치

```bash
# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows

# 필요한 패키지 설치
pip install -r requirements.txt
```

### 2. YOLO 모델 다운로드

첫 실행 시 YOLO 모델이 자동으로 다운로드됩니다.
수동으로 다운로드하려면:

```bash
# YOLOv8 nano 모델 (가장 빠름)
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt

# YOLOv8 small 모델 (더 정확함)
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt

# YOLOv8 medium 모델 (균형잡힌 성능)
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8m.pt
```

## ⚙️ 설정 파일 (config.json)

```json
{
  "yolo_model": "yolov8n.pt",
  "camera_source": 0,
  "frame_width": 1280,
  "frame_height": 720,
  "confidence_threshold": 0.5,
  "presence_threshold_seconds": 5,
  "absence_threshold_seconds": 3,
  "count_interval_seconds": 1,
  "api_endpoint": "http://10.10.11.23:10008/api/emergency",
  "watch_id": "watch_1760663070591_8022",
  "include_image_url": false,
  "roi_regions": [
    {
      "id": "ROI1",
      "x": 100,
      "y": 100,
      "width": 400,
      "height": 300,
      "description": "첫 번째 관심 영역"
    }
  ]
}
```

### 설정 항목 설명

| 항목 | 설명 | 기본값 |
|------|------|--------|
| `yolo_model` | YOLO 모델 파일명 | yolov8n.pt |
| `camera_source` | 카메라 소스 (USB 번호, RTSP URL, 파일 경로 등) | 0 |
| `camera_source_type` | 카메라 소스 타입 (usb, rtsp, http, file, image_sequence, gstreamer) | 자동 감지 |
| `frame_width` | 프레임 너비 | 1280 |
| `frame_height` | 프레임 높이 | 720 |
| `confidence_threshold` | 검출 신뢰도 임계값 (0.0~1.0) | 0.5 |
| `presence_threshold_seconds` | 존재 확인 임계값 (초) | 5 |
| `absence_threshold_seconds` | 부재 확인 임계값 (초) | 3 |
| `count_interval_seconds` | 카운팅 간격 (초) | 1 |
| `api_endpoint` | API 엔드포인트 URL | - |
| `watch_id` | Watch ID | - |
| `roi_regions` | ROI 영역 목록 | [] |

### ROI 영역 설정

각 ROI 영역은 다음 정보를 포함합니다:

```json
{
  "id": "ROI1",          // 고유 ID
  "x": 100,              // 좌상단 X 좌표
  "y": 100,              // 좌상단 Y 좌표
  "width": 400,          // 너비
  "height": 300,         // 높이
  "description": "설명"   // 영역 설명
}
```

## 🎯 ROI 영역 설정 방법

### 1. 수동 설정

`config.json` 파일의 `roi_regions` 배열에 ROI 정보를 직접 입력합니다.

### 2. 마우스로 설정 (선택적 구현)

ROI 설정 도구를 사용하여 마우스로 영역을 드래그하여 설정할 수 있습니다:

```bash
python roi_selector.py
```

이 기능은 필요 시 별도로 구현할 수 있습니다.

## 📹 카메라 소스 설정

이 프로젝트는 다양한 카메라 입력 소스를 지원합니다:

### 지원하는 카메라 소스

| 소스 타입 | 설명 | 예시 |
|-----------|------|------|
| **USB 웹캠** | 로컬 USB 카메라 | `camera_source: 0` |
| **RTSP 스트림** | IP 카메라 RTSP 스트림 | `camera_source: "rtsp://admin:1234@192.168.1.100:554/stream1"` |
| **HTTP 스트림** | HTTP MJPEG 스트림 | `camera_source: "http://192.168.1.100:8080/video"` |
| **비디오 파일** | 로컬 비디오 파일 | `camera_source: "./videos/sample.mp4"` |
| **이미지 시퀀스** | 연속된 이미지 파일 | `camera_source: "./images/frame_%04d.jpg"` |
| **GStreamer** | 커스텀 GStreamer 파이프라인 | `camera_source: "videotestsrc ! videoconvert ! appsink"` |

### 설정 예시

**USB 웹캠**:
```json
{
  "camera_source": 0,
  "camera_source_type": "usb"
}
```

**RTSP IP 카메라**:
```json
{
  "camera_source": "rtsp://admin:password@192.168.1.100:554/stream1",
  "camera_source_type": "rtsp"
}
```

**비디오 파일**:
```json
{
  "camera_source": "./videos/sample.mp4",
  "camera_source_type": "file"
}
```

### Streamlit UI에서 설정

Streamlit 앱을 실행하면 좌측 사이드바에서 카메라 소스를 쉽게 선택할 수 있습니다:

1. "📹 카메라" 섹션 찾기
2. "소스 타입" 선택 (USB 웹캠, RTSP 스트림, HTTP 스트림, 비디오 파일, 기타)
3. 각 타입에 맞는 설정 입력

**더 자세한 내용은 [CAMERA_SOURCE_GUIDE.md](./CAMERA_SOURCE_GUIDE.md)를 참조하세요.**

## 🏃 실행 방법

```bash
# 기본 실행
python roi_person_detector.py

# 백그라운드 실행 (Linux/Mac)
nohup python roi_person_detector.py > detector.log 2>&1 &

# 백그라운드 실행 (Windows)
start /B python roi_person_detector.py
```

## 📤 API 이벤트 형식

프로그램이 전송하는 이벤트 데이터 형식:

```json
{
  "eventId": "fc4d54d0-717c-4fe8-95be-fdf8f188a401",
  "roiId": "ROI1",
  "objectType": "human",
  "status": 1,
  "createdAt": "2025-12-01T05:30:00",
  "watchId": "watch_1760663070591_8022"
}
```

### 필드 설명

- `eventId`: 이벤트 고유 ID (UUID)
- `roiId`: ROI 영역 ID
- `objectType`: 객체 타입 (항상 "human")
- `status`: 상태 (1: 검출됨/present, 0: 검출 안됨/absent)
- `createdAt`: 이벤트 생성 시간 (ISO 8601 형식)
- `watchId`: Watch ID

## 🖥️ 사용 예시

### 예시 1: 단일 ROI 모니터링

```json
{
  "roi_regions": [
    {
      "id": "ROI1",
      "x": 200,
      "y": 150,
      "width": 400,
      "height": 300
    }
  ]
}
```

### 예시 2: 다중 ROI 모니터링

```json
{
  "roi_regions": [
    {
      "id": "entrance",
      "x": 100,
      "y": 100,
      "width": 300,
      "height": 400,
      "description": "입구 영역"
    },
    {
      "id": "waiting_area",
      "x": 500,
      "y": 100,
      "width": 400,
      "height": 400,
      "description": "대기 영역"
    },
    {
      "id": "exit",
      "x": 1000,
      "y": 100,
      "width": 300,
      "height": 400,
      "description": "출구 영역"
    }
  ]
}
```

## 🎨 화면 표시

프로그램 실행 시 다음 정보가 화면에 표시됩니다:

- **ROI 영역**: 녹색(사람 검출) 또는 빨간색(사람 없음) 박스
- **ROI ID**: 각 영역의 고유 식별자
- **검출 상태**: Present/Absent/None
- **검출 카운트**: 누적 검출 횟수
- **사람 바운딩 박스**: 검출된 사람 주위에 파란색 박스

## ⌨️ 키보드 컨트롤

- `q`: 프로그램 종료

## 🔧 문제 해결

### 카메라가 열리지 않는 경우

```python
# config.json에서 camera_source 변경
"camera_source": 0  # 다른 번호 시도 (1, 2, ...)
# 또는 비디오 파일 사용
"camera_source": "path/to/video.mp4"
```

### API 연결 오류

- API 엔드포인트 URL이 올바른지 확인
- 네트워크 연결 확인
- 방화벽 설정 확인

### YOLO 모델 로딩 오류

```bash
# YOLO 모델 수동 다운로드
pip install ultralytics
yolo export model=yolov8n.pt format=pytorch
```

## 📊 성능 최적화

### 모델 선택

- **yolov8n.pt**: 가장 빠름, 낮은 정확도 (실시간 처리 권장)
- **yolov8s.pt**: 빠름, 중간 정확도
- **yolov8m.pt**: 보통 속도, 높은 정확도
- **yolov8l.pt**: 느림, 매우 높은 정확도
- **yolov8x.pt**: 매우 느림, 최고 정확도

### 해상도 조정

```json
{
  "frame_width": 640,   // 낮은 해상도 = 빠른 처리
  "frame_height": 480
}
```

### 신뢰도 임계값 조정

```json
{
  "confidence_threshold": 0.3  // 낮추면 더 많이 검출 (false positive 증가)
}
```

## 📝 로그 및 디버깅

프로그램 실행 시 콘솔에 다음 정보가 출력됩니다:

- ✅ 초기화 완료 메시지
- 🔍 사람 검출 시작/종료
- 👤 존재 확인 이벤트
- 🚫 부재 확인 이벤트
- 📤 API 전송 결과

## 🔐 보안 고려사항

- API 엔드포인트에 인증이 필요한 경우 코드 수정 필요
- HTTPS 사용 권장
- 민감한 정보는 환경 변수로 관리

## 📚 관련 문서

### 핵심 가이드
- 📹 **[CAMERA_SOURCE_GUIDE.md](./CAMERA_SOURCE_GUIDE.md)** - 카메라 소스 다변화 가이드 (USB, RTSP, HTTP, 파일 등)
- 📐 **[CUSTOM_ROI_GUIDE.md](./CUSTOM_ROI_GUIDE.md)** - ROI 영역 편집 가이드
- 😊 **[FACE_ANALYSIS_INTEGRATION.md](./FACE_ANALYSIS_INTEGRATION.md)** - 얼굴 분석 통합 가이드

### 설정 및 최적화
- ⚡ **[PERFORMANCE_OPTIMIZATION.md](./PERFORMANCE_OPTIMIZATION.md)** - 성능 최적화 가이드
- 🖥️ **[PLATFORM_COMPATIBILITY.md](./PLATFORM_COMPATIBILITY.md)** - 플랫폼 호환성 가이드
- 🔧 **[JETSON_SETUP.md](./JETSON_SETUP.md)** - Jetson 설치 및 설정

### 예제 설정 파일
- 📝 **[config_camera_examples.json](./config_camera_examples.json)** - 다양한 카메라 소스 예제
- 📝 **[config_polygon_example.json](./config_polygon_example.json)** - Polygon ROI 예제

### 문제 해결
- 🐛 **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)** - 문제 해결 가이드
- 🔍 **[BUG_FIXES.md](./BUG_FIXES.md)** - 버그 수정 내역

## 📄 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.

## 🤝 기여

버그 리포트, 기능 제안, 풀 리퀘스트를 환영합니다!

## 📧 문의

프로젝트 관련 문의사항이 있으시면 이슈를 등록해주세요.
