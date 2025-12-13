# YOLO ROI Detection System - 코드 리뷰 및 구현 내용

## 📋 프로젝트 개요

**GitHub Repository**: https://github.com/futurianh1k/roidetyolo  
**프로젝트명**: YOLO 기반 ROI 사람 검출 및 이벤트 전송 시스템  
**최종 업데이트**: 2025-12-03

---

## 🌿 브랜치 구조

| 브랜치 | 용도 | UI 프레임워크 | 상태 |
|--------|------|--------------|------|
| **main** | Streamlit 웹 애플리케이션 | Streamlit | ✅ 활성 |
| **pyqt-ui** | PyQt5 데스크톱 애플리케이션 | PyQt5 | ✅ 활성 |
| **react-fastapi** | 풀스택 웹 애플리케이션 | React + FastAPI | ✅ 활성 |

---

## 🎯 핵심 기능

### 1. **실시간 YOLO 객체 검출**
- **YOLOv8** 기반 사람 검출
- 신뢰도 임계값 설정 (기본: 0.5)
- 검출 간격 조정 가능 (기본: 1초)
- 25-35 FPS 성능 (Jetson Orin)

### 2. **ROI (Region of Interest) 관리**
- **다중 ROI 동시 모니터링**
- **2가지 ROI 타입**:
  - Rectangle (사각형)
  - Polygon (다각형)
- **자동 ROI 생성**:
  - 좌/우 2분할
  - 4사분면 분할
- **마우스 클릭 ROI 편집** (PyQt, React)

### 3. **얼굴 분석 통합 (MediaPipe)**
- **6가지 감정 분석**: Neutral, Happy, Sad, Angry, Surprise, Fear
- **눈 상태 감지**: EAR (Eye Aspect Ratio) 기반
- **입 상태 감지**: 
  - 말하는 중 (Speaking)
  - 크게 벌림 (Open)
- **마스크 착용 감지**
- **SAD 표정 실시간 알림**

### 4. **이벤트 전송 시스템**
- **자동 API 전송**:
  - 사람 존재 감지 (5초 이상)
  - 사람 부재 감지 (3초 이상)
  - SAD 표정 감지 (설정 가능한 임계값)
- **API Payload 구조**:
```json
{
  "eventId": "roi_1_absence_1733456789",
  "roi_id": "roi_1",
  "status": "absence",
  "reason": "부재 감지",
  "timestamp": "2025-12-03T04:59:49.123456",
  "watch_id": "watch_1764653561585_7956",
  "sender_id": "yolo_detector",
  "note": "",
  "method": "realtime_detection"
}
```

### 5. **JWT 인증 시스템** (react-fastapi 브랜치)
- **역할 기반 접근 제어**: Admin, Operator
- **Redis 세션 관리**
- **토큰 자동 갱신**
- **기본 계정**:
  - admin / admin123
  - operator / admin123

### 6. **Jetson 장비 관리** (react-fastapi 브랜치)
- **장비 등록/수정/삭제**
- **실시간 상태 모니터링**: ONLINE, OFFLINE, BUSY, ERROR
- **하트비트 시스템** (30초 간격)
- **시스템 리소스 추적**: CPU, 메모리, GPU, 온도

---

## 📁 프로젝트 구조

### 🐍 Python Backend

```
yolo_roi_detector/
├── realtime_detector.py          # 실시간 검출 엔진 (25KB, 700+ 라인)
├── streamlit_app.py              # Streamlit UI (49KB, 1400+ 라인)
├── pyqt_app.py                   # PyQt5 UI (43KB, 1044 라인)
├── face_analyzer.py              # 얼굴 분석 (16KB, 450+ 라인)
├── roi_utils.py                  # ROI 유틸리티
├── camera_utils.py               # 카메라 유틸리티
├── backend/                      # FastAPI Backend
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py           # JWT 인증 API
│   │   │   ├── devices.py        # 장비 관리 API
│   │   │   ├── sessions.py       # 세션 관리 API
│   │   │   └── websocket.py      # WebSocket API
│   │   ├── core/
│   │   │   ├── config.py         # 설정 관리
│   │   │   └── security.py       # JWT 보안
│   │   ├── models/
│   │   │   ├── user.py           # 사용자 모델
│   │   │   ├── device.py         # 장비 모델
│   │   │   └── session.py        # 세션 모델
│   │   ├── services/
│   │   │   ├── redis_session_manager.py
│   │   │   ├── device_manager.py
│   │   │   └── detection_service.py
│   │   └── main.py               # FastAPI 메인
│   ├── Dockerfile
│   └── requirements.txt
└── frontend/                     # React Frontend
    ├── src/
    │   ├── context/
    │   │   └── AuthContext.jsx   # 인증 컨텍스트
    │   ├── pages/
    │   │   ├── LoginPage.jsx     # 로그인 페이지
    │   │   ├── DevicesPage.jsx   # 장비 관리
    │   │   ├── HomePage.jsx
    │   │   ├── DetectionPage.jsx
    │   │   └── StatsPage.jsx
    │   ├── services/
    │   │   ├── authService.js
    │   │   └── deviceService.js
    │   └── App.jsx
    ├── Dockerfile
    └── package.json
```

### 📊 코드 통계

| 항목 | 수량 | 라인 수 |
|------|------|---------|
| Python 파일 | 25+ | 5,000+ |
| React 파일 | 15+ | 2,700+ |
| 문서 파일 | 30+ | - |
| 설정 파일 | 5+ | - |

---

## 🔧 주요 기술 스택

### Backend
- **Python 3.10+**
- **YOLOv8** (ultralytics)
- **MediaPipe** (얼굴 분석)
- **OpenCV** (영상 처리)
- **FastAPI** (REST API)
- **Redis** (세션 관리)
- **JWT** (인증)

### Frontend
- **Streamlit** (웹 UI - main 브랜치)
- **PyQt5** (데스크톱 UI - pyqt-ui 브랜치)
- **React 18** (웹 UI - react-fastapi 브랜치)
- **Axios** (HTTP 클라이언트)
- **WebSocket** (실시간 통신)

### Infrastructure
- **Docker & Docker Compose**
- **Redis 7**
- **nginx** (리버스 프록시)

---

## 🎨 UI 비교

### 1. Streamlit 웹 UI (main 브랜치)

**장점**:
- ✅ 빠른 프로토타이핑
- ✅ Python만으로 웹 UI 구현
- ✅ 자동 UI 업데이트

**단점**:
- ❌ 커스터마이징 제한
- ❌ 멀티 세션 관리 복잡

**주요 기능**:
- ROI 편집 (자동 생성, 커스텀)
- 실시간 검출 화면
- 통계 대시보드
- API 테스트

### 2. PyQt5 데스크톱 UI (pyqt-ui 브랜치)

**장점**:
- ✅ 네이티브 데스크톱 성능
- ✅ 풍부한 UI 컴포넌트
- ✅ 마우스 클릭 ROI 편집
- ✅ 오프라인 작동

**단점**:
- ❌ 설치 필요 (python + 의존성)
- ❌ 멀티 플랫폼 배포 복잡

**주요 기능**:
- 클릭 기반 ROI 편집
- 실시간 비디오 표시
- 설정 관리 탭
- API 테스트 탭

### 3. React + FastAPI (react-fastapi 브랜치)

**장점**:
- ✅ 풀스택 웹 아키텍처
- ✅ 멀티 사용자 지원 (최대 100 세션)
- ✅ JWT 인증 시스템
- ✅ 장비 관리 기능
- ✅ 확장 가능한 구조

**단점**:
- ❌ 복잡한 설정
- ❌ 프론트/백엔드 분리 관리

**주요 기능**:
- 로그인/인증
- 장비 관리 대시보드
- 실시간 검출 (WebSocket)
- 통계 차트

---

## 🚀 실행 방법

### 1. Streamlit 앱 (main 브랜치)

```bash
git checkout main
pip install -r requirements.txt
streamlit run streamlit_app.py
```

**접속**: http://localhost:8501

### 2. PyQt5 앱 (pyqt-ui 브랜치)

```bash
git checkout pyqt-ui
pip install -r requirements_pyqt.txt
python pyqt_app.py
```

### 3. React + FastAPI (react-fastapi 브랜치)

**Docker Compose (권장)**:
```bash
git checkout react-fastapi
docker-compose up --build
```

**수동 실행**:
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

**접속**:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 📊 성능 최적화

### Jetson Orin 최적화
- **목표 FPS**: 25-35 FPS
- **YOLO 모델**: yolov8n.pt (nano - 가장 빠름)
- **검출 간격**: 1초 (조정 가능)
- **해상도**: 1280x720 (권장)

### 메모리 관리
- **Frame Queue**: 최대 2개 프레임 버퍼링
- **Stats Queue**: 최대 10개 통계
- **Event Queue**: 최대 50개 이벤트

---

## 🔒 보안 기능

### 1. JWT 인증 (react-fastapi)
- **토큰 만료**: 8시간
- **자동 갱신**
- **역할 기반 접근 제어**

### 2. API 보안
- **CORS 설정**
- **Rate Limiting** (권장)
- **HTTPS 지원** (nginx)

### 3. 세션 관리
- **Redis 기반** (확장 가능)
- **세션 만료**: 60분
- **최대 세션**: 100개

---

## 📡 API 엔드포인트

### Authentication (`/api/v1/auth`)
- `POST /login` - 로그인
- `POST /logout` - 로그아웃
- `GET /me` - 현재 사용자 정보
- `POST /refresh` - 토큰 갱신

### Devices (`/api/v1/devices`)
- `POST /` - 장비 등록
- `GET /` - 장비 목록
- `GET /{device_id}` - 장비 조회
- `PATCH /{device_id}` - 장비 수정
- `DELETE /{device_id}` - 장비 삭제
- `POST /{device_id}/heartbeat` - 하트비트

### Sessions (`/api/v1/sessions`)
- `POST /` - 세션 생성
- `GET /` - 세션 목록
- `GET /{session_id}` - 세션 조회
- `DELETE /{session_id}` - 세션 삭제

### WebSocket (`/api/v1/ws`)
- `WS /{session_id}` - 실시간 비디오 스트림

---

## 📚 문서 목록

### 핵심 문서
1. **README.md** - 프로젝트 개요 및 빠른 시작
2. **API_PAYLOAD_UPDATE.md** - API payload 필드 설명
3. **BRANCH_SYNC_SUMMARY.md** - 브랜치 동기화 내역
4. **IMPLEMENTATION_SUMMARY.md** - JWT/장비 관리 구현

### 기능별 문서
- **FACE_ANALYSIS_INTEGRATION.md** - 얼굴 분석 통합 가이드
- **FACE_YOLO_SYNC_EXPLANATION.md** - YOLO-얼굴 분석 동기화
- **CUSTOM_ROI_GUIDE.md** - ROI 편집 가이드
- **DETECTION_INTERVAL.md** - 검출 간격 설정

### 설치 및 배포
- **JETSON_ORIN_SETUP.md** - Jetson Orin 설치 가이드
- **PLATFORM_COMPATIBILITY.md** - 플랫폼 호환성
- **PERFORMANCE_OPTIMIZATION.md** - 성능 최적화

### 강의 자료
- **LECTURE_3HOURS_OUTLINE.md** - 3시간 강의 개요
- **LECTURE_PART1_SLIDES.md** - Part 1 슬라이드
- **LECTURE_PART2_SLIDES.md** - Part 2 슬라이드

---

## 🧪 테스트

### 단위 테스트
```bash
# 얼굴 분석 테스트
python test_face_analyzer.py

# 카메라 검출 테스트
python test_camera_detection.py

# API 테스트
python test_api.py
```

### API 테스트 (curl)
```bash
# 로그인
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin&password=admin123"

# 장비 목록
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/devices/
```

---

## 🔄 CI/CD 및 배포

### Docker Compose
```yaml
services:
  - redis    # 세션 관리
  - backend  # FastAPI
  - frontend # React
```

### 배포 옵션
1. **로컬 개발**: Python + npm
2. **Docker**: docker-compose up
3. **Kubernetes**: (향후 계획)
4. **Jetson Orin**: systemd 서비스

---

## 📈 향후 계획

### Phase 2
- [ ] PostgreSQL 통합
- [ ] 사용자 관리 DB
- [ ] 검출 결과 영구 저장

### Phase 3
- [ ] WebSocket 실시간 알림
- [ ] 장비 그룹 관리
- [ ] 분석 대시보드

### Phase 4
- [ ] Kubernetes 배포
- [ ] CI/CD 파이프라인
- [ ] Prometheus + Grafana 모니터링

---

## 🐛 알려진 이슈

### 해결됨
- ✅ NumPy 2.0 호환성 오류
- ✅ PIL Image.fromarray 오류
- ✅ Streamlit MediaFileHandler 오류
- ✅ PyQt5 설치 오류

### 진행 중
- 🔄 Redis 연결 안정성 개선
- 🔄 WebSocket 재연결 로직

---

## 📞 지원 및 문의

- **GitHub**: https://github.com/futurianh1k/roidetyolo
- **Issues**: https://github.com/futurianh1k/roidetyolo/issues
- **API Docs**: http://localhost:8000/docs

---

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

---

## 🙏 기여자

- **Main Developer**: AI Development Assistant
- **Project Owner**: futurianh1k

---

**문서 버전**: 1.0.0  
**최종 업데이트**: 2025-12-03  
**문서 작성자**: AI Development Assistant
