# YOLO ROI Detection System - 인증 및 장비 관리

## 🔐 JWT 인증 시스템

### 주요 기능
- **JWT 기반 인증**: 안전한 토큰 기반 인증 시스템
- **Redis 세션 관리**: 확장 가능한 세션 스토리지
- **역할 기반 접근 제어**: Admin, Operator 권한 관리
- **자동 토큰 갱신**: 세션 유지 및 자동 재인증

### 기본 계정
```
관리자 계정:
- Username: admin
- Password: admin123
- 권한: 전체 시스템 관리

운영자 계정:
- Username: operator
- Password: admin123
- 권한: 장비 모니터링, 검출 제어
```

### API 엔드포인트

#### 인증 API (`/api/v1/auth`)

**로그인**
```bash
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=admin&password=admin123
```

**응답**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1...",
  "token_type": "bearer",
  "user": {
    "username": "admin",
    "email": "admin@example.com",
    "full_name": "System Administrator",
    "role": "admin"
  }
}
```

**로그아웃**
```bash
POST /api/v1/auth/logout
Authorization: Bearer {token}
```

**현재 사용자 정보**
```bash
GET /api/v1/auth/me
Authorization: Bearer {token}
```

**토큰 갱신**
```bash
POST /api/v1/auth/refresh
Authorization: Bearer {token}
```

**사용자 목록 (관리자 전용)**
```bash
GET /api/v1/auth/users
Authorization: Bearer {admin_token}
```

**활성 세션 목록 (관리자 전용)**
```bash
GET /api/v1/auth/sessions/active
Authorization: Bearer {admin_token}
```

---

## 🖥️ Jetson 장비 관리 시스템

### 주요 기능
- **장비 등록/수정/삭제**: 여러 Jetson 장비 중앙 관리
- **실시간 상태 모니터링**: 온라인/오프라인/사용중/오류 상태 추적
- **하트비트 시스템**: 장비 연결 상태 자동 감지
- **통계 수집**: 장비별 검출 통계 및 성능 데이터

### 장비 상태
- **ONLINE**: 정상 작동 중
- **OFFLINE**: 연결 끊김
- **BUSY**: 검출 작업 진행 중
- **ERROR**: 오류 발생
- **MAINTENANCE**: 점검 중

### API 엔드포인트

#### 장비 관리 API (`/api/v1/devices`)

**장비 등록 (관리자 전용)**
```bash
POST /api/v1/devices/
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "device_id": "jetson-01",
  "name": "Jetson Orin 1번기",
  "ip_address": "10.10.11.99",
  "port": 8000,
  "location": "1층 출입구",
  "description": "메인 출입구 모니터링"
}
```

**장비 목록 조회**
```bash
GET /api/v1/devices/
Authorization: Bearer {token}

# 상태별 필터링
GET /api/v1/devices/?status_filter=online
```

**특정 장비 조회**
```bash
GET /api/v1/devices/{device_id}
Authorization: Bearer {token}
```

**장비 정보 수정 (관리자 전용)**
```bash
PATCH /api/v1/devices/{device_id}
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "name": "Jetson Orin 업데이트",
  "location": "2층 회의실"
}
```

**장비 삭제 (관리자 전용)**
```bash
DELETE /api/v1/devices/{device_id}
Authorization: Bearer {admin_token}
```

**장비 하트비트 전송 (인증 불필요)**
```bash
POST /api/v1/devices/{device_id}/heartbeat
Content-Type: application/json

{
  "device_id": "jetson-01",
  "status": "online",
  "cpu_usage": 45.5,
  "memory_usage": 60.2,
  "gpu_usage": 80.0,
  "temperature": 55.0,
  "detection_count": 150
}
```

**장비 통계 조회**
```bash
GET /api/v1/devices/{device_id}/stats?limit=100
Authorization: Bearer {token}
```

**전체 장비 상태 요약**
```bash
GET /api/v1/devices/status/summary
Authorization: Bearer {token}
```

**응답 예시**:
```json
{
  "total": 5,
  "online": 3,
  "offline": 1,
  "busy": 1,
  "error": 0,
  "maintenance": 0
}
```

---

## 🚀 실행 방법

### 개발 환경 (로컬)

**1. Backend 실행**
```bash
cd backend
pip install -r requirements.txt

# Redis 실행 (Docker)
docker run -d -p 6379:6379 redis:7-alpine

# 또는 로컬 Redis 사용
redis-server

# FastAPI 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**2. Frontend 실행**
```bash
cd frontend
npm install
npm run dev
```

**3. 접속**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Docker Compose 환경

**1. 환경 변수 설정**
```bash
# 루트 디렉터리에 .env 파일 생성
cp .env.example .env

# 프로덕션 환경에서는 SECRET_KEY 변경 필수!
```

**2. Docker Compose 실행**
```bash
# 빌드 및 실행
docker-compose up --build

# 백그라운드 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 중지
docker-compose down
```

**3. 접속**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Redis: localhost:6379

---

## 🔧 Jetson 장비 설정

### Jetson에서 하트비트 전송 설정

**Python 스크립트 예시** (`jetson_heartbeat.py`):
```python
import requests
import psutil
import time

BACKEND_URL = "http://YOUR_SERVER_IP:8000/api/v1"
DEVICE_ID = "jetson-01"
HEARTBEAT_INTERVAL = 30  # 30초마다 전송

def get_system_stats():
    """시스템 리소스 정보 수집"""
    return {
        "cpu_usage": psutil.cpu_percent(interval=1),
        "memory_usage": psutil.virtual_memory().percent,
        "temperature": 55.0,  # Jetson에서 실제 온도 읽기
        "gpu_usage": 0.0,  # GPU 사용률 (jtop 사용 권장)
    }

def send_heartbeat():
    """하트비트 전송"""
    stats = get_system_stats()
    
    payload = {
        "device_id": DEVICE_ID,
        "status": "online",
        **stats,
        "detection_count": 0  # 실제 검출 카운트
    }
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/devices/{DEVICE_ID}/heartbeat",
            json=payload,
            timeout=5
        )
        if response.status_code == 200:
            print(f"✅ Heartbeat sent: {stats}")
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    while True:
        send_heartbeat()
        time.sleep(HEARTBEAT_INTERVAL)
```

**systemd 서비스 등록** (`/etc/systemd/system/jetson-heartbeat.service`):
```ini
[Unit]
Description=Jetson Heartbeat Service
After=network.target

[Service]
Type=simple
User=jetson
WorkingDirectory=/home/jetson
ExecStart=/usr/bin/python3 /home/jetson/jetson_heartbeat.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**서비스 시작**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable jetson-heartbeat
sudo systemctl start jetson-heartbeat
sudo systemctl status jetson-heartbeat
```

---

## 📦 Redis 세션 구조

### 세션 키 구조
```
user_session:{username} → 사용자 세션 정보 (8시간 TTL)
user_token:{token} → 토큰 검증용 (8시간 TTL)
device:{device_id}:stats → 장비 통계 (1시간 TTL)
```

### Redis 명령어 예시
```bash
# 사용자 세션 확인
redis-cli GET "user_session:admin"

# 모든 사용자 세션 조회
redis-cli KEYS "user_session:*"

# 장비 통계 확인
redis-cli GET "device:jetson-01:stats"
```

---

## 🔒 보안 고려사항

### 프로덕션 배포 체크리스트
- [ ] `.env` 파일에서 `SECRET_KEY` 변경
- [ ] 기본 admin 비밀번호 변경
- [ ] HTTPS 설정 (nginx 리버스 프록시 권장)
- [ ] Redis 비밀번호 설정
- [ ] CORS 설정 확인 및 제한
- [ ] 방화벽 규칙 설정
- [ ] JWT 토큰 만료 시간 조정
- [ ] Rate limiting 설정

### HTTPS 설정 (nginx 예시)
```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        proxy_pass http://localhost:3000;
    }
}
```

---

## 📊 모니터링 및 로깅

### Backend 로그
```bash
# Docker 환경
docker-compose logs -f backend

# 로컬 환경 (uvicorn 로그)
# stdout에 출력됨
```

### Redis 모니터링
```bash
# Redis 통계
docker exec -it yolo_redis redis-cli INFO

# 실시간 모니터링
docker exec -it yolo_redis redis-cli MONITOR
```

---

## 🧪 테스트

### API 테스트 (curl)
```bash
# 로그인
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin&password=admin123" \
  | jq -r '.access_token')

# 장비 목록 조회
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/devices/

# 장비 등록
curl -X POST http://localhost:8000/api/v1/devices/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "jetson-test",
    "name": "Test Device",
    "ip_address": "10.10.11.99",
    "port": 8000
  }'
```

---

## 📝 문의 및 지원
- API 문서: http://localhost:8000/docs
- GitHub Issues: (프로젝트 저장소)
