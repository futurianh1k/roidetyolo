# YOLO ROI 검출 시스템 - React + FastAPI 풀스택 웹 애플리케이션

## 📋 프로젝트 개요

Streamlit/PyQt 기반 UI를 React + FastAPI 풀스택 웹 애플리케이션으로 완전히 재구축한 버전입니다.

## 🏗️ 아키텍처

### 백엔드 (FastAPI)
```
backend/
├── app/
│   ├── api/              # API 엔드포인트
│   │   ├── sessions.py   # 세션 관리 REST API
│   │   └── websocket.py  # WebSocket 실시간 스트림
│   ├── core/             # 설정 및 핵심 로직
│   │   └── config.py     # 환경 설정
│   ├── models/           # 데이터 모델
│   │   └── session.py    # 세션, 검출 결과 모델
│   ├── services/         # 비즈니스 로직
│   │   ├── session_manager.py    # 세션 관리
│   │   └── detection_service.py  # YOLO 검출 서비스
│   └── main.py           # FastAPI 애플리케이션
└── requirements.txt      # Python 의존성
```

### 프론트엔드 (React)
```
frontend/
├── public/
├── src/
│   ├── components/       # 재사용 가능 컴포넌트
│   ├── pages/            # 페이지 컴포넌트
│   │   ├── HomePage.jsx  # 세션 관리 페이지
│   │   ├── DetectionPage.jsx  # 실시간 검출
│   │   └── StatsPage.jsx      # 통계 대시보드
│   ├── services/         # API 및 WebSocket 클라이언트
│   │   ├── api.js        # REST API 클라이언트
│   │   └── websocket.js  # WebSocket 클라이언트
│   ├── App.jsx           # 메인 앱
│   └── main.jsx          # 엔트리 포인트
├── package.json
└── vite.config.js        # Vite 설정
```

## 🎯 주요 기능

### 1️⃣ **세션 기반 관리 시스템**
- ✅ **다중 세션 지원**: 여러 검출 세션을 동시에 관리
- ✅ **세션별 격리**: 각 세션의 설정, ROI, 통계가 독립적으로 관리
- ✅ **자동 만료**: 60분 미활동 시 자동 세션 정리
- ✅ **최대 세션 수 제한**: 100개 (메모리 관리)

### 2️⃣ **RESTful API**
- ✅ **세션 CRUD**: 생성, 조회, 업데이트, 삭제
- ✅ **ROI 관리**: ROI 추가/삭제
- ✅ **검출 제어**: 시작/중지
- ✅ **통계 조회**: 실시간 통계 및 검출 결과

### 3️⃣ **WebSocket 실시간 스트림**
- ✅ **비디오 프레임**: JPEG base64 인코딩
- ✅ **통계 업데이트**: 5초마다 자동 전송
- ✅ **FPS 정보**: 실시간 프레임 레이트
- ✅ **재연결 로직**: 자동 재연결 (최대 5회)

### 4️⃣ **세션별 검출 결과 저장**
- ✅ **검출 결과 저장**: 세션별로 모든 검출 결과 저장
- ✅ **얼굴 분석 결과**: 표정, 눈/입 상태, 마스크 검출
- ✅ **통계 자동 집계**: 실시간 통계 업데이트
- ✅ **결과 조회 API**: ROI별 필터링 지원

### 5️⃣ **React SPA**
- ✅ **홈 페이지**: 세션 목록 및 생성
- ✅ **실시간 검출 페이지**: 비디오 스트림 및 제어
- ✅ **통계 대시보드**: 차트 및 데이터 시각화

## 🚀 실행 방법

### 백엔드 실행
```bash
# 의존성 설치
cd backend
pip install -r requirements.txt

# FastAPI 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 프론트엔드 실행
```bash
# 의존성 설치
cd frontend
npm install

# 개발 서버 실행
npm run dev
```

### 통합 실행
```bash
# 터미널 1: 백엔드
cd backend && uvicorn app.main:app --reload

# 터미널 2: 프론트엔드
cd frontend && npm run dev
```

## 📡 API 엔드포인트

### 세션 관리
```
POST   /api/v1/sessions/                    # 세션 생성
GET    /api/v1/sessions/                    # 세션 목록
GET    /api/v1/sessions/{session_id}        # 세션 조회
PATCH  /api/v1/sessions/{session_id}        # 세션 업데이트
DELETE /api/v1/sessions/{session_id}        # 세션 삭제
```

### ROI 관리
```
POST   /api/v1/sessions/{session_id}/roi        # ROI 추가
DELETE /api/v1/sessions/{session_id}/roi/{roi_id}  # ROI 삭제
```

### 검출 제어
```
POST   /api/v1/sessions/{session_id}/start   # 검출 시작
POST   /api/v1/sessions/{session_id}/stop    # 검출 중지
```

### 통계 및 결과
```
GET    /api/v1/sessions/{session_id}/statistics        # 통계 조회
POST   /api/v1/sessions/{session_id}/statistics/reset  # 통계 초기화
GET    /api/v1/sessions/{session_id}/results           # 검출 결과 조회
```

### WebSocket
```
WS     /api/v1/ws/{session_id}               # 실시간 스트림
```

### 헬스 체크
```
GET    /                                     # API 정보
GET    /health                               # 헬스 체크
GET    /api/v1/info                          # API 상세 정보
```

## 📊 데이터 모델

### DetectionSession
```python
{
  "session_id": "uuid",
  "user_id": "optional_user_id",
  "status": "idle|detecting|paused|stopped",
  "config": {
    "yolo_model": "yolov8n.pt",
    "camera_source": 0,
    "confidence_threshold": 0.5,
    "detection_interval": 1.0,
    "presence_threshold": 5,
    "absence_threshold": 3,
    "enable_face_analysis": true,
    "face_analysis_roi_only": false
  },
  "roi_regions": [
    {
      "id": "ROI_1",
      "description": "영역 1",
      "type": "polygon",
      "points": [[x1, y1], [x2, y2], ...],
      "enabled": true
    }
  ],
  "statistics": {
    "total_detections": 0,
    "roi_stats": {},
    "face_stats": {}
  },
  "created_at": "2025-01-09T...",
  "updated_at": "2025-01-09T...",
  "last_activity": "2025-01-09T..."
}
```

### DetectionResult
```python
{
  "session_id": "uuid",
  "roi_id": "ROI_1",
  "status": "present|absent",
  "person_detected": true,
  "confidence": 0.85,
  "bbox": [x1, y1, x2, y2],
  "face_analysis": {
    "face_detected": true,
    "eyes_open": true,
    "mouth_state": "closed|speaking|wide_open",
    "expression": {
      "expression": "happy",
      "confidence": 0.9
    },
    "has_mask_or_ventilator": false,
    "device_confidence": null
  },
  "timestamp": "2025-01-09T..."
}
```

## 🔧 설정

### 백엔드 설정 (backend/app/core/config.py)
```python
# API 설정
API_V1_STR = "/api/v1"
PROJECT_NAME = "YOLO ROI Detection API"

# CORS 설정
BACKEND_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173"
]

# 세션 설정
SESSION_EXPIRE_MINUTES = 60
MAX_SESSIONS = 100

# YOLO 모델 설정
DEFAULT_YOLO_MODEL = "yolov8n.pt"
YOLO_CONFIDENCE_THRESHOLD = 0.5
DETECTION_INTERVAL_SECONDS = 1.0

# WebSocket 설정
WS_HEARTBEAT_INTERVAL = 30  # seconds
```

### 프론트엔드 설정 (frontend/vite.config.js)
```javascript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
```

## 🎨 기술 스택

### 백엔드
- **FastAPI**: 고성능 Python 웹 프레임워크
- **WebSockets**: 실시간 양방향 통신
- **Pydantic**: 데이터 검증 및 직렬화
- **Uvicorn**: ASGI 서버
- **YOLOv8**: 객체 검출 모델
- **MediaPipe**: 얼굴 분석

### 프론트엔드
- **React 18**: UI 라이브러리
- **React Router**: 클라이언트 사이드 라우팅
- **Axios**: HTTP 클라이언트
- **Recharts**: 데이터 시각화
- **Vite**: 빌드 도구

## 🆚 기존 버전과 비교

| 기능 | Streamlit | PyQt5 | React + FastAPI |
|------|-----------|-------|-----------------|
| **아키텍처** | 모노리식 | 데스크톱 앱 | 분리형 (Frontend/Backend) |
| **확장성** | 낮음 | 중간 | 높음 ✅ |
| **동시 사용자** | 제한적 | 단일 사용자 | 다중 사용자 ✅ |
| **세션 관리** | 없음 | 없음 | 세션별 격리 ✅ |
| **API** | 없음 | 없음 | RESTful + WebSocket ✅ |
| **배포** | Streamlit 서버 | 실행 파일 | Docker, K8s ✅ |
| **개발 속도** | 빠름 | 중간 | 중간 |
| **유지보수** | 중간 | 중간 | 쉬움 ✅ |

## 📈 성능 최적화

### 백엔드
- ✅ 비동기 I/O (asyncio)
- ✅ WebSocket 프레임 레이트 제한 (30 FPS)
- ✅ JPEG 압축 (quality=80)
- ✅ 세션 자동 정리

### 프론트엔드
- ✅ 컴포넌트 레이지 로딩
- ✅ Canvas 기반 비디오 렌더링
- ✅ 5초 간격 통계 폴링
- ✅ WebSocket 재연결 로직

## 🔐 보안 고려사항

### 현재 구현 (개발 환경)
- ✅ CORS 설정
- ✅ Pydantic 데이터 검증

### 프로덕션 고려사항
- ⚠️ 인증/인가 (JWT)
- ⚠️ HTTPS/WSS
- ⚠️ Rate Limiting
- ⚠️ 입력 검증 강화
- ⚠️ 환경 변수 관리 (.env)

## 📝 개발 가이드

### 새로운 API 엔드포인트 추가
1. `backend/app/api/` 에 라우터 생성
2. `backend/app/main.py` 에 라우터 등록
3. `frontend/src/services/api.js` 에 클라이언트 함수 추가

### 새로운 React 페이지 추가
1. `frontend/src/pages/` 에 컴포넌트 생성
2. `frontend/src/App.jsx` 에 라우트 추가
3. 네비게이션 링크 추가

## 🐛 알려진 이슈

1. **WebSocket 재연결**: 최대 5회 제한
2. **메모리 기반 세션**: 서버 재시작 시 세션 손실 (Redis 마이그레이션 필요)
3. **대용량 비디오**: 프레임 전송 시 네트워크 대역폭 고려 필요

## 🔮 향후 계획

- [ ] Redis 기반 세션 관리
- [ ] JWT 인증
- [ ] 데이터베이스 통합 (PostgreSQL)
- [ ] 검출 결과 영구 저장
- [ ] 실시간 알림 시스템
- [ ] Docker 컨테이너화
- [ ] Kubernetes 배포

## 📄 라이선스

이 프로젝트는 원본 YOLO ROI 사람 검출 시스템의 React + FastAPI 버전입니다.

---

**버전**: 1.0.0  
**날짜**: 2025-01-09  
**브랜치**: react-fastapi  
**GitHub**: https://github.com/futurianh1k/roidetyolo
