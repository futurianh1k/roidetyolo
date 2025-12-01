# 🚀 Streamlit 앱 실행 가이드

## 빠른 시작

```bash
cd /home/user/yolo_roi_detector

# Streamlit 실행
streamlit run streamlit_app.py
```

브라우저가 자동으로 열립니다: `http://localhost:8501`

## 🔗 새로운 API 엔드포인트 관리 기능

### 📋 기능 개요

4개 탭으로 구성:
1. **📐 ROI 편집** - Polygon ROI 설정
2. **🎥 실시간 검출** - 사람 검출 실행
3. **📊 통계 & 로그** - 검출 결과 모니터링
4. **🔗 API 테스트** - 🆕 API 엔드포인트 테스트

### 🆕 API 설정 기능

#### 사이드바 - API 엔드포인트 관리

**기본 설정**:
- Watch ID 입력
- 이미지 URL 포함 여부
- 이미지 베이스 URL
- FCM Project ID

**API 엔드포인트 관리 (확장 패널)**:
- ➕ 여러 API 추가 가능
- ✅ 개별 활성화/비활성화
- 🗑️ 개별 삭제
- HTTP Method 선택 (POST, PUT, PATCH)

#### API 테스트 탭

**테스트 기능**:
1. 등록된 API 선택
2. 테스트 데이터 입력 (ROI ID, Status)
3. 🚀 API 테스트 실행 버튼 클릭
4. 실시간 결과 확인:
   - 요청 데이터 (JSON)
   - 응답 데이터 (JSON)
   - 상태 코드
   - 오류 메시지

## 📤 API 이벤트 데이터 형식

```json
{
  "eventId": "fc4d54d0-717c-4fe8-95be-fdf8f188a401",
  "fcmMessageId": "projects/emergency-alert-system-f27e6/messages/1234567890",
  "imageUrl": "http://10.10.11.79:8080/api/images/emergency_fc4d54d0.jpeg",
  "status": "SENT",
  "createdAt": "2025-12-01T10:30:00.123456",
  "watchId": "watch_1760663070591_8022"
}
```

### 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `eventId` | String (UUID) | 이벤트 고유 식별자 |
| `fcmMessageId` | String | Firebase Cloud Messaging ID |
| `imageUrl` | String | 이벤트 관련 이미지 URL (선택적) |
| `status` | String | 이벤트 상태 (SENT, PENDING, FAILED) |
| `createdAt` | String (ISO 8601) | 이벤트 생성 시간 |
| `watchId` | String | Watch 고유 식별자 |

## 🎯 사용 시나리오

### 시나리오 1: 단일 API 엔드포인트

```
1. 사이드바 열기
2. "🔗 API 엔드포인트 관리" 확장
3. 기본 API 정보 확인:
   - 이름: Emergency Alert API
   - URL: http://10.10.11.23:10008/api/emergency/quick
   - Method: POST
4. ✅ 활성화 체크
5. "💾 설정 저장" 클릭
```

### 시나리오 2: 다중 API 엔드포인트

```
1. 사이드바 → "🔗 API 엔드포인트 관리"
2. 새 API 추가:
   - API 이름: "Backup Emergency API"
   - API URL: "http://backup-server:8080/api/emergency"
   - HTTP Method: POST
3. ➕ API 추가 클릭
4. 각 API 개별 활성화/비활성화 가능
5. 활성화된 API들에 동시 전송됨
```

### 시나리오 3: API 테스트

```
1. "🔗 API 테스트" 탭 클릭
2. 테스트할 API 선택
3. 테스트 데이터 입력:
   - ROI ID: "ROI1"
   - Status: "SENT"
4. "🚀 API 테스트 실행" 클릭
5. 결과 확인:
   - ✅ 성공: 상태 코드 200/201
   - ❌ 실패: 오류 메시지 확인
```

## ⚙️ 설정 예시

### config.json 형식

```json
{
  "yolo_model": "yolov8n.pt",
  "camera_source": 0,
  "confidence_threshold": 0.5,
  "presence_threshold_seconds": 5,
  "absence_threshold_seconds": 3,
  
  "api_endpoints": [
    {
      "name": "Emergency Alert API",
      "url": "http://10.10.11.23:10008/api/emergency/quick",
      "enabled": true,
      "method": "POST"
    },
    {
      "name": "Backup API",
      "url": "http://backup-server:8080/api/emergency",
      "enabled": false,
      "method": "POST"
    }
  ],
  
  "watch_id": "watch_1760663070591_8022",
  "include_image_url": true,
  "image_base_url": "http://10.10.11.79:8080/api/images",
  "fcm_project_id": "emergency-alert-system-f27e6",
  
  "roi_regions": [...]
}
```

## 🔧 고급 기능

### 외부 네트워크 접속

```bash
# 모든 네트워크 인터페이스에서 접속 허용
streamlit run streamlit_app.py \
  --server.address=0.0.0.0 \
  --server.port=8501

# 접속 주소
http://your-ip-address:8501
```

### 백그라운드 실행

```bash
# nohup으로 백그라운드 실행
nohup streamlit run streamlit_app.py > streamlit.log 2>&1 &

# 프로세스 확인
ps aux | grep streamlit

# 종료
pkill -f streamlit
```

## 🐛 문제 해결

### Q: API 테스트에서 연결 오류가 발생해요

**A**: 다음을 확인하세요:
1. API URL이 올바른지 확인
2. 네트워크 연결 확인
3. 방화벽 설정 확인
4. API 서버가 실행 중인지 확인

```bash
# API 연결 테스트
curl -X POST http://10.10.11.23:10008/api/emergency/quick \
  -H "Content-Type: application/json" \
  -d '{"test": "connection"}'
```

### Q: 이미지 URL이 생성되지 않아요

**A**: 사이드바에서 확인:
1. "이미지 URL 포함" 체크박스 활성화
2. "이미지 베이스 URL" 입력
3. "💾 설정 저장" 클릭

### Q: 여러 API에 동시 전송이 안돼요

**A**: 
1. 각 API의 "활성" 체크박스 확인
2. 설정 저장 확인
3. 검출 재시작

## 📊 실시간 검출 시 API 전송

검출 프로그램 실행 중:
- ROI에서 사람이 **5초 이상** 검출 → `status: SENT` (present)
- ROI에서 사람이 **3초 이상** 부재 → `status: SENT` (absent)
- **활성화된 모든 API**에 동시 전송

## 🎉 요약

### 주요 개선사항

✅ **다중 API 엔드포인트 지원**
✅ **UI에서 API 추가/삭제/관리**
✅ **개별 API 활성화/비활성화**
✅ **API 테스트 기능**
✅ **실시간 요청/응답 확인**
✅ **표준 API 형식 지원** (FCM, 이미지 URL 등)

### 사용 흐름

```
1. Streamlit 앱 실행
   ↓
2. 사이드바에서 API 설정
   ↓
3. API 테스트 탭에서 연결 확인
   ↓
4. ROI 편집 탭에서 영역 설정
   ↓
5. 실시간 검출 탭에서 검출 시작
   ↓
6. 자동으로 API 이벤트 전송
   ↓
7. 통계 & 로그 탭에서 결과 확인
```

---

**이제 Streamlit UI에서 모든 API 설정을 관리할 수 있습니다!** 🚀
