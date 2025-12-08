# 카메라 소스 다변화 업데이트

## 📋 업데이트 개요

**업데이트 날짜**: 2025-12-08  
**버전**: 2.0.0  
**주요 변경사항**: 다양한 카메라 입력 소스 지원 추가

---

## ✨ 새로운 기능

### 1. 다양한 카메라 소스 지원

이제 다음 6가지 카메라 입력 소스를 지원합니다:

| 소스 타입 | 설명 | 사용 사례 |
|-----------|------|----------|
| 🎥 **USB 웹캠** | 로컬 USB 카메라 | 테스트, 데모, 소규모 모니터링 |
| 📡 **RTSP 스트림** | IP 카메라 RTSP 프로토콜 | 상업용 IP 카메라, NVR 시스템 |
| 🌐 **HTTP 스트림** | HTTP MJPEG 스트림 | 모바일 앱 카메라, 웹 스트림 |
| 📁 **비디오 파일** | 로컬 비디오 파일 재생 | 테스트, 개발, 오프라인 분석 |
| 🖼️ **이미지 시퀀스** | 연속된 이미지 파일 | 데이터셋 처리, 프레임 단위 분석 |
| ⚙️ **GStreamer** | 커스텀 파이프라인 | 고급 사용자, 특수 하드웨어 |

---

## 🔧 변경된 파일

### 1. `camera_utils.py` (확장)

**추가된 클래스 및 함수**:

```python
class CameraSourceType:
    """카메라 소스 타입 상수"""
    USB = "usb"
    RTSP = "rtsp"
    HTTP = "http"
    FILE = "file"
    IMAGE_SEQ = "image_sequence"
    GSTREAMER = "gstreamer"

class CameraSourceManager:
    """다양한 카메라 소스 관리 클래스"""
    
    @staticmethod
    def detect_source_type(source) -> str:
        """소스 타입 자동 감지"""
        
    @staticmethod
    def open_camera(source, source_type=None, **kwargs) -> cv2.VideoCapture:
        """카메라 소스 열기"""
        
    @staticmethod
    def validate_source(source) -> Dict[str, Any]:
        """소스 유효성 검사"""
        
    @staticmethod
    def get_source_info(source) -> Dict[str, Any]:
        """소스 정보 조회"""
```

**주요 기능**:
- ✅ 소스 타입 자동 감지
- ✅ 통합된 카메라 열기 인터페이스
- ✅ 소스 유효성 검증
- ✅ RTSP TCP/UDP 전송 프로토콜 설정
- ✅ 버퍼 크기 조정 (지연 최소화)

---

### 2. `realtime_detector.py` (수정)

**변경 사항**:

```python
# CameraSourceManager 임포트 추가
from camera_utils import CameraSourceManager, CameraSourceType

class RealtimeDetector:
    def __init__(self, config, roi_regions):
        # camera_source_type 설정 추가
        self.camera_source_type = config.get('camera_source_type', None)
        
        # 소스 정보 출력
        if CAMERA_UTILS_AVAILABLE:
            source_info = CameraSourceManager.get_source_info(self.camera_source)
            print(f"[RealtimeDetector] 카메라 소스: {source_info['description']}")
    
    def run(self):
        # CameraSourceManager로 카메라 열기
        if CAMERA_UTILS_AVAILABLE:
            self.cap = CameraSourceManager.open_camera(
                self.camera_source, 
                self.camera_source_type,
                **camera_options
            )
        else:
            # 기본 방식 (하위 호환성)
            self.cap = cv2.VideoCapture(self.camera_source)
```

**주요 변경점**:
- ✅ `CameraSourceManager` 통합
- ✅ `camera_source_type` 설정 지원
- ✅ 하위 호환성 유지 (기존 코드 동작)

---

### 3. `streamlit_app.py` (UI 개선)

**변경 사항**:

```python
# 카메라 소스 타입 선택 (확장)
camera_type = st.sidebar.radio(
    "소스 타입", 
    ["USB 웹캠", "RTSP 스트림", "HTTP 스트림", "비디오 파일", "기타"]
)

# 각 타입별 맞춤 UI
if camera_type == "RTSP 스트림":
    config['camera_source'] = st.sidebar.text_input("RTSP URL", ...)
    st.sidebar.code("rtsp://admin:1234@192.168.1.100:554/stream1")
    st.sidebar.info("⚠️ RTSP는 네트워크 지연이 있을 수 있습니다.")
```

**UI 개선 사항**:
- ✅ 5가지 소스 타입 선택 옵션
- ✅ 각 타입별 맞춤 입력 필드
- ✅ 예제 URL 및 패턴 표시
- ✅ 주의사항 및 팁 제공

---

### 4. 새 파일 추가

**`config_camera_examples.json`**:
- 다양한 카메라 소스 설정 예제 모음
- USB, RTSP, HTTP, 파일, 이미지 시퀀스, GStreamer 예제
- 추천 설정 및 문제 해결 가이드

**`CAMERA_SOURCE_GUIDE.md`**:
- 카메라 소스 다변화 완전 가이드
- 각 소스 타입별 상세 설명
- 설정 예시 및 문제 해결
- Python API 사용법
- 성능 비교 및 추천 설정

**`CAMERA_SOURCE_UPDATE.md`** (이 문서):
- 업데이트 개요 및 변경사항 요약

---

## 🚀 사용 방법

### Streamlit UI에서 사용

1. **앱 실행**:
```bash
streamlit run streamlit_app.py
```

2. **좌측 사이드바에서 "📹 카메라" 섹션 찾기**

3. **소스 타입 선택**:
   - USB 웹캠
   - RTSP 스트림
   - HTTP 스트림
   - 비디오 파일
   - 기타 (이미지 시퀀스, GStreamer)

4. **각 타입에 맞는 소스 입력**

### config.json에서 설정

**USB 웹캠**:
```json
{
  "camera_source": 0,
  "camera_source_type": "usb"
}
```

**RTSP 스트림**:
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

### Python 코드에서 사용

```python
from camera_utils import CameraSourceManager

# 소스 타입 자동 감지
source = "rtsp://192.168.1.100:554/stream1"
source_type = CameraSourceManager.detect_source_type(source)

# 카메라 열기
cap = CameraSourceManager.open_camera(source, source_type)

# 소스 유효성 검증
validation = CameraSourceManager.validate_source(source)
if validation['valid']:
    print(f"✅ {validation['message']}")
```

---

## 📊 하위 호환성

### 기존 설정 파일 호환

✅ **기존 config.json은 수정 없이 그대로 작동합니다**:

```json
{
  "camera_source": 0
}
```

위 설정은 자동으로 USB 웹캠으로 인식됩니다.

### 기존 코드 호환

✅ **기존 코드는 수정 없이 동작합니다**:

```python
detector = RealtimeDetector(config, roi_regions)
detector.start()
```

`CameraSourceManager`가 없어도 기본 방식으로 폴백됩니다.

---

## 🎯 주요 개선사항

### 1. 유연성 증가

- **이전**: USB 웹캠과 비디오 파일만 지원
- **이후**: 6가지 다양한 소스 지원

### 2. IP 카메라 지원

- **이전**: IP 카메라 사용 불가
- **이후**: RTSP/HTTP 스트림 완전 지원

### 3. 개발 및 테스트 편의성

- **이전**: 실제 카메라 필요
- **이후**: 비디오 파일, 이미지 시퀀스로 테스트 가능

### 4. 자동화 및 확장성

- **이전**: 카메라 타입별 별도 코드 필요
- **이후**: 통합 인터페이스로 모든 소스 처리

---

## 📈 성능 영향

### 리소스 사용

| 소스 타입 | CPU 사용량 | 메모리 | 네트워크 | 지연 시간 |
|-----------|-----------|--------|----------|----------|
| USB 웹캠 | 중간 | 낮음 | 없음 | 낮음 (~30ms) |
| RTSP | 높음 | 중간 | 높음 | 높음 (100-500ms) |
| HTTP | 중간 | 중간 | 중간 | 중간 (50-200ms) |
| 비디오 파일 | 낮음 | 낮음 | 없음 | 낮음 |
| 이미지 시퀀스 | 낮음 | 낮음 | 없음 | 낮음 |

### 추천 설정

**RTSP 스트림 사용 시**:
```json
{
  "detection_interval_seconds": 2.0,
  "confidence_threshold": 0.5
}
```

**비디오 파일 사용 시**:
```json
{
  "detection_interval_seconds": 0.5,
  "confidence_threshold": 0.5
}
```

---

## 🐛 알려진 제한사항

### 1. RTSP 네트워크 지연

- **문제**: RTSP 스트림은 네트워크 상태에 따라 지연 발생
- **해결**: `detection_interval_seconds`를 2.0~5.0으로 설정

### 2. GStreamer 의존성

- **문제**: GStreamer 파이프라인 사용 시 별도 설치 필요
- **해결**: 
```bash
sudo apt-get install gstreamer1.0-tools gstreamer1.0-plugins-*
```

### 3. 이미지 시퀀스 프레임 속도

- **문제**: 이미지 시퀀스는 실시간이 아님
- **해결**: 테스트/개발 용도로만 사용

---

## 🔮 향후 계획

### Phase 2 (예정)
- [ ] 다중 카메라 동시 처리
- [ ] 카메라 자동 재연결 (RTSP 끊김 시)
- [ ] 카메라 소스 핫스왑 (실행 중 소스 변경)

### Phase 3 (예정)
- [ ] WebRTC 지원
- [ ] NDI 프로토콜 지원
- [ ] 클라우드 스트림 (AWS Kinesis, Azure Media Services)

---

## 📚 추가 문서

- 📹 **[CAMERA_SOURCE_GUIDE.md](./CAMERA_SOURCE_GUIDE.md)** - 완전한 카메라 소스 가이드
- 📝 **[config_camera_examples.json](./config_camera_examples.json)** - 설정 예제 모음
- 🐛 **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)** - 문제 해결 가이드

---

## 🙏 피드백

카메라 소스 다변화 기능에 대한 피드백을 환영합니다!

- 버그 리포트: GitHub Issues
- 기능 제안: GitHub Discussions
- 문의사항: 프로젝트 이슈 등록

---

**업데이트 작성자**: AI Development Assistant  
**테스트 환경**: Windows 10, Ubuntu 22.04, Jetson Orin  
**테스트 카메라**: USB 웹캠, Hikvision IP 카메라, 비디오 파일

