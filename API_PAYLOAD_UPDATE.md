# API Payload 업데이트 - sender_id, note, method 필드 추가

## 📋 변경 사항

검출 결과를 서버로 전송할 때 JSON payload에 다음 필드가 추가되었습니다:

- **sender_id**: 발신자 식별자 (기본값: `yolo_detector`)
- **note**: 추가 메시지 또는 메모 (기본값: 빈 문자열)
- **method**: 검출 방법 식별자 (기본값: `realtime_detection`)

---

## 🔧 업데이트된 파일

### 1. **realtime_detector.py**
- `send_realtime_api()` 함수에 3개 필드 추가
- config에서 값을 읽어 payload에 포함

### 2. **config.json**
- 기본 설정 추가:
  ```json
  {
    "sender_id": "yolo_detector",
    "note": "",
    "method": "realtime_detection"
  }
  ```

### 3. **streamlit_app.py**
- 사이드바 API 설정에 "검출 방법 (선택)" 입력 필드 추가
- `config['note']` 필드명 통일
- `config['method']` 입력 필드 추가

### 4. **pyqt_app.py**
- API 설정 그룹에 3개 필드 입력창 추가
- 설정 저장 시 자동으로 config에 반영

---

## 📤 업데이트된 API Payload 구조

### 기존 Payload (Before)
```json
{
  "eventId": "roi_1_absence_1733456789",
  "roi_id": "roi_1",
  "status": "absence",
  "reason": "부재 감지",
  "timestamp": "2025-12-03T04:59:49.123456",
  "watch_id": "watch_1764653561585_7956"
}
```

### 새로운 Payload (After)
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

---

## 🎯 사용 방법

### Streamlit 앱
1. 사이드바 "🌐 API 설정" 섹션으로 이동
2. 다음 필드를 입력:
   - **Sender ID (필수)**: 발신자 식별자
   - **기본 메시지 (선택)**: 추가 메모
   - **검출 방법 (선택)**: 검출 방법 식별자
3. 설정은 자동으로 적용됨

### PyQt 앱
1. "⚙️ 설정" 탭으로 이동
2. "🌐 API 설정" 그룹에서 다음 필드 입력:
   - **Sender ID**: 발신자 식별자
   - **Note (선택)**: 추가 메모
   - **Method (선택)**: 검출 방법 식별자
3. "💾 설정 저장" 버튼 클릭

### config.json 직접 수정
```json
{
  "api_endpoint": "http://your-server.com/api/endpoint",
  "watch_id": "watch_1234567890",
  "sender_id": "camera_01",
  "note": "건물 1층 출입구",
  "method": "yolo_v8_detection"
}
```

---

## 🔍 필드 상세 설명

### sender_id
- **타입**: String
- **필수**: 권장 (기본값 사용 가능)
- **기본값**: `yolo_detector`
- **용도**: 발신 장비 또는 시스템 식별
- **예시**: 
  - `jetson_orin_01`
  - `camera_entrance`
  - `yolo_detector_main`

### note
- **타입**: String
- **필수**: 선택
- **기본값**: 빈 문자열 `""`
- **용도**: 추가 정보, 메모, 위치 정보 등
- **예시**:
  - `1층 출입구 카메라`
  - `긴급 상황 감지`
  - `테스트 환경`

### method
- **타입**: String
- **필수**: 선택
- **기본값**: `realtime_detection`
- **용도**: 검출 방법 또는 알고리즘 식별
- **예시**:
  - `realtime_detection` (실시간 검출)
  - `yolo_v8n` (YOLOv8 nano 모델)
  - `face_analysis_emotion` (얼굴 감정 분석)

---

## 🧪 테스트 예시

### Python 테스트 코드
```python
import requests
import json
from datetime import datetime

payload = {
    "eventId": f"test_{int(datetime.now().timestamp())}",
    "roi_id": "test_roi",
    "status": "test",
    "reason": "테스트 전송",
    "timestamp": datetime.now().isoformat(),
    "watch_id": "watch_test",
    "sender_id": "test_sender",
    "note": "API 테스트",
    "method": "manual_test"
}

response = requests.post(
    "http://your-server.com/api/endpoint",
    json=payload,
    timeout=5
)

print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
```

### curl 테스트
```bash
curl -X POST http://your-server.com/api/endpoint \
  -H "Content-Type: application/json" \
  -d '{
    "eventId": "test_1733456789",
    "roi_id": "roi_1",
    "status": "test",
    "reason": "테스트",
    "timestamp": "2025-12-03T05:00:00",
    "watch_id": "watch_test",
    "sender_id": "curl_test",
    "note": "커맨드라인 테스트",
    "method": "manual_curl"
  }'
```

---

## ⚠️ 주의사항

1. **하위 호환성**: 기존 서버가 새 필드를 인식하지 못해도 오류가 발생하지 않습니다
2. **필드 순서**: JSON 필드 순서는 중요하지 않습니다
3. **빈 값**: `note`와 `method`는 빈 문자열이어도 됩니다
4. **sender_id 중복**: 여러 장비가 같은 sender_id를 사용할 수 있지만 권장하지 않습니다

---

## 📞 문의
- GitHub Issues: https://github.com/futurianh1k/roidetyolo/issues
- 문서 위치: `API_PAYLOAD_UPDATE.md`

---

**업데이트 일자**: 2025-12-03  
**버전**: 1.1.0
