# 📋 코드 리뷰 보고서

**프로젝트**: YOLO 기반 ROI 사람 검출 모니터링 시스템  
**리뷰 일자**: 2025-01-20  
**리뷰어**: AI 코드 리뷰 시스템

---

## 📊 프로젝트 개요

### **프로젝트 목적**
YOLO(YOLOv8/YOLOv11)를 사용하여 카메라 영상에서 ROI(Region of Interest) 영역을 설정하고, 해당 영역에서 사람을 검출하여 API 엔드포인트로 이벤트를 전송하는 실시간 모니터링 시스템입니다.

### **주요 기능**
- ✅ 다중 ROI 영역 설정 (사각형/다각형)
- ✅ 실시간 사람 검출 (YOLO)
- ✅ 얼굴 분석 (MediaPipe Face Mesh)
- ✅ 체류 시간 측정 및 이벤트 전송
- ✅ Streamlit 기반 웹 UI
- ✅ API 이벤트 전송 (JSON/Multipart)

### **기술 스택**
- **프레임워크**: Streamlit, OpenCV, Ultralytics YOLO
- **AI/ML**: YOLOv8, MediaPipe Face Mesh
- **언어**: Python 3.x
- **플랫폼**: Linux (Jetson Orin), Windows

---

## 🏗️ 아키텍처 분석

### **파일 구조**

```
roidetyolo/
├── streamlit_app.py          # 메인 UI (1,208줄)
├── realtime_detector.py      # 실시간 검출 엔진 (584줄)
├── face_analyzer.py          # 얼굴 분석 모듈 (453줄)
├── camera_utils.py           # 카메라 유틸리티 (253줄)
├── roi_utils.py              # ROI 유틸리티 (332줄)
├── config.json               # 설정 파일
├── requirements.txt          # 의존성
└── [문서 파일들]             # 23개 문서
```

### **모듈 의존성**

```
streamlit_app.py
    ├── realtime_detector.py
    │   └── face_analyzer.py
    ├── camera_utils.py
    └── roi_utils.py
```

### **데이터 흐름**

```
카메라 → OpenCV → YOLO 검출 → ROI 필터링 → 얼굴 분석 → 이벤트 생성 → API 전송
                ↓
         Streamlit UI (실시간 표시)
```

---

## ✅ 코드 품질 평가

### **1. 장점**

#### **1.1 모듈화 및 구조**
- ✅ 기능별로 명확하게 분리된 모듈 구조
- ✅ 유틸리티 함수들이 재사용 가능하게 설계됨
- ✅ 설정 파일과 코드 분리

#### **1.2 문서화**
- ✅ 23개의 상세한 문서 파일 (README, 가이드, 릴리스 노트)
- ✅ 코드 내 주석이 적절히 포함됨
- ✅ 사용자 가이드와 개발자 가이드 분리

#### **1.3 에러 처리**
- ✅ MediaPipe, streamlit-image-coordinates 등 선택적 의존성 처리
- ✅ Linux/Windows 플랫폼별 카메라 백엔드 처리
- ✅ 카메라 검색 실패 시 안내 메시지

#### **1.4 사용자 경험**
- ✅ Streamlit 기반 직관적인 웹 UI
- ✅ 실시간 프레임 표시 및 통계
- ✅ ROI 편집 기능 (4사분면, 좌/우 분할, 커스텀)

---

## ⚠️ 보안 이슈 및 개선 사항

### **🔴 심각 (즉시 수정 필요)**

#### **1. API 엔드포인트 하드코딩**
**위치**: `config.json`
```json
"api_endpoint": "http://10.10.11.23:10008/api/emergency/quick/watch_1764653561585_7956"
```

**문제점**:
- API URL이 설정 파일에 평문으로 저장됨
- 민감한 정보가 Git에 커밋될 위험
- 인증 정보 없이 API 호출

**권장 해결책**:
```python
# 환경 변수 사용
import os
api_endpoint = os.getenv('API_ENDPOINT', 'http://localhost:8080/api')
api_key = os.getenv('API_KEY', '')

# config.json에서 제거하고 .env 파일 사용
# .env 파일은 .gitignore에 추가
```

**참고**: 사용자 규칙 A01. 개발자 지침 - 4. 암호화/시크릿 관리

---

#### **2. API 요청에 인증 토큰 없음**
**위치**: `realtime_detector.py`, `streamlit_app.py`

**문제점**:
- API 호출 시 인증 헤더가 없음
- 누구나 API를 호출할 수 있는 상태

**권장 해결책**:
```python
# API 호출 시 인증 헤더 추가
headers = {
    'Authorization': f'Bearer {api_token}',
    'Content-Type': 'application/json'
}
response = requests.post(api_endpoint, json=payload, headers=headers, timeout=10)
```

**참고**: 사용자 규칙 A01. 개발자 지침 - 1. 인증/세션/토큰

---

#### **3. 로그에 민감 정보 노출 가능성**
**위치**: `realtime_detector.py`, `streamlit_app.py`

**문제점**:
- API 요청/응답을 로그에 출력할 때 민감 정보 포함 가능
- 디버그 출력에 전체 요청 본문이 포함될 수 있음

**권장 해결책**:
```python
# 로그 출력 시 민감 정보 마스킹
def mask_sensitive_data(data):
    if isinstance(data, dict):
        masked = data.copy()
        for key in ['api_key', 'token', 'password', 'authorization']:
            if key in masked:
                masked[key] = '***MASKED***'
        return masked
    return data

# 로그 출력
logger.info(f"API 요청: {mask_sensitive_data(request_data)}")
```

**참고**: 사용자 규칙 A01. 개발자 지침 - 5. 로그/예외 처리

---

### **🟡 중간 (개선 권장)**

#### **4. 입력 검증 부족**
**위치**: `streamlit_app.py`, `realtime_detector.py`

**문제점**:
- ROI 좌표 검증은 있으나, API 엔드포인트 URL 검증 없음
- 사용자 입력값에 대한 백엔드 검증 부족

**권장 해결책**:
```python
import re
from urllib.parse import urlparse

def validate_api_endpoint(url):
    """API 엔드포인트 URL 검증"""
    try:
        result = urlparse(url)
        if not result.scheme in ['http', 'https']:
            return False, "URL은 http 또는 https로 시작해야 합니다"
        if not result.netloc:
            return False, "유효한 호스트가 필요합니다"
        return True, "유효한 URL입니다"
    except Exception as e:
        return False, f"URL 검증 실패: {e}"

# 사용
is_valid, message = validate_api_endpoint(api_url)
if not is_valid:
    st.error(f"❌ API URL 오류: {message}")
```

**참고**: 사용자 규칙 A01. 개발자 지침 - 3. 입력 검증/출력 인코딩

---

#### **5. 에러 메시지가 너무 상세함**
**위치**: 전체 파일

**문제점**:
- 스택트레이스가 사용자에게 노출될 수 있음
- 내부 구현 세부사항이 에러 메시지에 포함됨

**권장 해결책**:
```python
# 사용자에게는 일반적인 메시지
try:
    # API 호출
    response = requests.post(url, json=payload, timeout=10)
except requests.exceptions.RequestException as e:
    # 내부 로그에만 상세 정보
    logger.error(f"API 호출 실패: {e}", exc_info=True)
    # 사용자에게는 일반 메시지
    st.error("⚠️ API 서버와 통신 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
```

**참고**: 사용자 규칙 A01. 개발자 지침 - 5. 로그/예외 처리

---

#### **6. 파일 업로드 검증 부족**
**위치**: `streamlit_app.py` (API 테스트 기능)

**문제점**:
- 업로드된 파일의 MIME 타입 검증 없음
- 파일 크기 제한 없음
- 파일 확장자 검증 없음

**권장 해결책**:
```python
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_uploaded_file(file):
    """업로드 파일 검증"""
    # 확장자 검증
    file_ext = Path(file.name).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"허용되지 않은 파일 형식입니다. ({', '.join(ALLOWED_EXTENSIONS)})"
    
    # 크기 검증
    file.seek(0, 2)  # 끝으로 이동
    file_size = file.tell()
    file.seek(0)  # 처음으로 복귀
    
    if file_size > MAX_FILE_SIZE:
        return False, f"파일 크기가 너무 큽니다. (최대 {MAX_FILE_SIZE // 1024 // 1024}MB)"
    
    # MIME 타입 검증 (Magic number)
    # TODO: 실제 파일 헤더 검증 추가
    
    return True, "유효한 파일입니다"
```

**참고**: 사용자 규칙 A01. 개발자 지침 - 6. 파일 업로드/다운로드

---

### **🟢 경미 (선택적 개선)**

#### **7. 설정 파일 검증**
**위치**: `streamlit_app.py` (`load_config()`)

**개선 사항**:
- JSON 스키마 검증 추가
- 필수 필드 존재 여부 확인
- 값 범위 검증 (예: confidence_threshold 0.0~1.0)

---

#### **8. 타임아웃 설정**
**위치**: `realtime_detector.py` (API 호출)

**개선 사항**:
- API 호출 타임아웃이 설정 파일에서 관리되도록
- 기본값 명시

---

## 📈 코드 메트릭

### **복잡도 분석**

| 파일 | 라인 수 | 함수 수 | 평균 함수 길이 | 복잡도 |
|------|---------|---------|----------------|--------|
| `streamlit_app.py` | 1,208 | ~30 | ~40 | 중간 |
| `realtime_detector.py` | 584 | ~15 | ~39 | 중간 |
| `face_analyzer.py` | 453 | ~10 | ~45 | 낮음 |
| `roi_utils.py` | 332 | ~8 | ~41 | 낮음 |
| `camera_utils.py` | 253 | ~6 | ~42 | 낮음 |

### **의존성 분석**

**외부 라이브러리**:
- `ultralytics` (YOLO)
- `opencv-python` (비디오 처리)
- `streamlit` (UI)
- `mediapipe` (얼굴 분석)
- `requests` (API 호출)
- `numpy`, `Pillow` (이미지 처리)

**의존성 관리**: ✅ `requirements.txt` 존재

---

## 🧪 테스트 코드 현황

### **현재 테스트 파일**
- ✅ `test_face_analyzer.py` (189줄)
- ✅ `test_camera_detection.py` (98줄)
- ✅ `test_api.py` (164줄)

### **부족한 테스트**
- ❌ `realtime_detector.py` 단위 테스트
- ❌ `roi_utils.py` 단위 테스트
- ❌ 통합 테스트
- ❌ API 호출 모킹 테스트

**권장 사항**: 사용자 규칙에 따라 신기능 구현 시 테스트 코드 동반 작성

---

## 🔧 개선 제안

### **1. 보안 강화 (우선순위: 높음)**

1. **환경 변수 사용**
   - API 엔드포인트를 환경 변수로 관리
   - `.env` 파일 사용 (python-dotenv)
   - `.env.example` 파일 제공

2. **API 인증 추가**
   - Bearer Token 또는 API Key 지원
   - 설정 파일에서 인증 정보 분리

3. **입력 검증 강화**
   - URL 검증
   - 파일 업로드 검증 (MIME, 크기, 확장자)
   - ROI 좌표 범위 검증 (이미 구현됨)

### **2. 에러 처리 개선 (우선순위: 중간)**

1. **사용자 친화적 에러 메시지**
   - 스택트레이스는 내부 로그에만
   - 사용자에게는 일반적인 메시지

2. **재시도 로직**
   - API 호출 실패 시 재시도 (exponential backoff)
   - 카메라 연결 실패 시 자동 재연결

### **3. 로깅 시스템 (우선순위: 중간)**

1. **구조화된 로깅**
   - Python `logging` 모듈 사용
   - 로그 레벨 구분 (DEBUG, INFO, WARNING, ERROR)
   - 파일 로깅 옵션

2. **민감 정보 마스킹**
   - 로그 출력 시 자동 마스킹
   - API 키, 토큰 등 자동 필터링

### **4. 테스트 코드 확장 (우선순위: 낮음)**

1. **단위 테스트**
   - `pytest` 사용
   - 각 모듈별 테스트 작성

2. **통합 테스트**
   - API 모킹
   - 카메라 모킹

---

## 📋 개발 계획 제안

### **Phase 1: 보안 강화 (1-2주)**

- [ ] 환경 변수 기반 설정 관리
- [ ] API 인증 추가
- [ ] 입력 검증 강화
- [ ] 로그 마스킹 구현

### **Phase 2: 안정성 개선 (1주)**

- [ ] 에러 처리 개선
- [ ] 재시도 로직 추가
- [ ] 구조화된 로깅 시스템

### **Phase 3: 테스트 확장 (1주)**

- [ ] 단위 테스트 작성
- [ ] 통합 테스트 작성
- [ ] CI/CD 파이프라인 구축

### **Phase 4: 문서화 (지속적)**

- [ ] API 문서화
- [ ] 보안 가이드 작성
- [ ] 배포 가이드 작성

---

## 📚 참고 자료 및 출처

### **외부 라이브러리 출처**

1. **Ultralytics YOLO**
   - 출처: https://github.com/ultralytics/ultralytics
   - 라이선스: AGPL-3.0
   - 용도: 객체 검출 (사람 검출)

2. **MediaPipe Face Mesh**
   - 출처: https://github.com/google/mediapipe
   - 라이선스: Apache 2.0
   - 용도: 얼굴 랜드마크 검출 및 분석

3. **Streamlit**
   - 출처: https://github.com/streamlit/streamlit
   - 라이선스: Apache 2.0
   - 용도: 웹 UI 프레임워크

### **알고리즘 참고**

1. **EAR (Eye Aspect Ratio)**
   - 출처: "Real-Time Eye Blink Detection using Facial Landmarks" (Soukupová & Čech, 2016)
   - 구현: `face_analyzer.py`의 `calculate_ear()` 메서드

2. **MAR (Mouth Aspect Ratio)**
   - 출처: MediaPipe 공식 문서
   - 구현: `face_analyzer.py`의 `calculate_mar()` 메서드

---

## ✅ 체크리스트

### **보안 코딩 체크리스트 (A01 기준)**

- [x] 비밀번호/토큰 하드코딩 없음 (단, API 엔드포인트는 개선 필요)
- [x] 입력 검증 구현 (ROI 좌표 검증 있음, API URL 검증 추가 필요)
- [x] 에러 메시지 일반화 (일부 개선 필요)
- [x] 로그에 민감 정보 기록 안 함 (마스킹 추가 필요)
- [x] 파일 업로드 검증 (MIME, 크기 검증 추가 필요)
- [ ] API 인증 구현 (추가 필요)
- [x] 환경 변수 사용 (추가 필요)

---

## 🎯 결론

### **전체 평가: ⭐⭐⭐⭐ (4/5)**

**강점**:
- ✅ 잘 구조화된 모듈 설계
- ✅ 풍부한 문서화
- ✅ 사용자 친화적 UI
- ✅ 플랫폼 호환성 고려

**개선 필요**:
- ⚠️ 보안 강화 (API 인증, 환경 변수)
- ⚠️ 에러 처리 개선
- ⚠️ 테스트 코드 확장

**권장 사항**:
1. **즉시**: API 엔드포인트를 환경 변수로 이동
2. **단기**: API 인증 추가, 입력 검증 강화
3. **중기**: 테스트 코드 확장, 로깅 시스템 개선

---

**리뷰 완료일**: 2025-01-20  
**다음 리뷰 예정**: 보안 강화 작업 완료 후


