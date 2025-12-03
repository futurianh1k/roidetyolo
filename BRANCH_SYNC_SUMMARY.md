# 브랜치 동기화 완료 - API Payload 필드 추가

## 📋 작업 요약

**날짜**: 2025-12-03  
**작업**: `sender_id`, `note`, `method` 필드를 모든 브랜치에 추가

---

## ✅ 적용 완료 브랜치

### 1. **react-fastapi** 브랜치
- **커밋**: `eef8ebf`
- **상태**: ✅ 완료
- **적용 파일**:
  - `realtime_detector.py`
  - `config.json`
  - `streamlit_app.py`
  - `pyqt_app.py`
  - `API_PAYLOAD_UPDATE.md`

### 2. **main** 브랜치
- **커밋**: `61cfb54`
- **상태**: ✅ 완료
- **적용 파일**:
  - `realtime_detector.py`
  - `config.json`
  - `streamlit_app.py`
  - `API_PAYLOAD_UPDATE.md`

### 3. **pyqt-ui** 브랜치
- **커밋**: `d34b7ee`
- **상태**: ✅ 완료
- **적용 파일**:
  - `realtime_detector.py`
  - `config.json`
  - `streamlit_app.py`
  - `pyqt_app.py`
  - `API_PAYLOAD_UPDATE.md`

---

## 📤 업데이트된 API Payload

```json
{
  "eventId": "roi_1_absence_1733456789",
  "roi_id": "roi_1",
  "status": "absence",
  "reason": "부재 감지",
  "timestamp": "2025-12-03T04:59:49.123456",
  "watch_id": "watch_1764653561585_7956",
  "sender_id": "yolo_detector",      // ✨ NEW
  "note": "",                         // ✨ NEW
  "method": "realtime_detection"      // ✨ NEW
}
```

---

## 🌿 브랜치별 특성

| 브랜치 | 용도 | UI | API 전송 | 수정 완료 |
|--------|------|----|---------| ---------|
| **main** | Streamlit 웹 | Streamlit | ✅ | ✅ |
| **pyqt-ui** | PyQt5 데스크톱 | PyQt5 | ✅ | ✅ |
| **react-fastapi** | 풀스택 웹 | React + FastAPI | ✅ | ✅ |

---

## 🔄 동기화 방법

### 수동 동기화 (권장)
각 브랜치에 개별적으로 파일을 체크아웃하여 적용:

```bash
# main 브랜치
git checkout main
git checkout react-fastapi -- realtime_detector.py config.json streamlit_app.py API_PAYLOAD_UPDATE.md
git commit -m "Sync API payload fields from react-fastapi"
git push origin main

# pyqt-ui 브랜치
git checkout pyqt-ui
git checkout react-fastapi -- realtime_detector.py config.json streamlit_app.py pyqt_app.py API_PAYLOAD_UPDATE.md
git commit -m "Sync API payload fields from react-fastapi"
git push origin pyqt-ui
```

### Cherry-pick (충돌 발생 가능)
```bash
# main 브랜치
git checkout main
git cherry-pick eef8ebf

# pyqt-ui 브랜치
git checkout pyqt-ui
git cherry-pick eef8ebf
```

---

## 🎯 테스트 방법

### 1. Streamlit 앱 (main, pyqt-ui, react-fastapi)
```bash
git checkout main
streamlit run streamlit_app.py

# 사이드바 → 🌐 API 설정에서 확인:
# - Sender ID (필수)
# - 기본 메시지 (선택)
# - 검출 방법 (선택)
```

### 2. PyQt5 앱 (pyqt-ui, react-fastapi)
```bash
git checkout pyqt-ui
python pyqt_app.py

# ⚙️ 설정 탭 → 🌐 API 설정에서 확인:
# - Sender ID
# - Note (선택)
# - Method (선택)
```

### 3. API Payload 확인
```bash
# realtime_detector.py 로그 확인
# [RealtimeDetector] 🚨 실시간 API 전송: roi_1 - 부재 감지

# 서버 로그에서 payload 확인:
# {
#   "sender_id": "yolo_detector",
#   "note": "",
#   "method": "realtime_detection"
# }
```

---

## 📊 커밋 히스토리

```
* d34b7ee (pyqt-ui) Add sender_id, note, method fields to API payload (pyqt-ui branch)
* 61cfb54 (main) Add sender_id, note, method fields to API payload (main branch)
* eef8ebf (react-fastapi) Add sender_id, note, method fields to API payload
```

---

## 🔍 변경사항 상세

### realtime_detector.py
```python
# Before
payload = {
    'eventId': f"{roi_id}_{event_type}_{int(time.time())}",
    'roi_id': roi_id,
    'status': event_type,
    'reason': reason,
    'timestamp': datetime.now().isoformat(),
    'watch_id': self.config.get('watch_id', 'unknown')
}

# After
payload = {
    'eventId': f"{roi_id}_{event_type}_{int(time.time())}",
    'roi_id': roi_id,
    'status': event_type,
    'reason': reason,
    'timestamp': datetime.now().isoformat(),
    'watch_id': self.config.get('watch_id', 'unknown'),
    'sender_id': self.config.get('sender_id', 'yolo_detector'),  # NEW
    'note': self.config.get('note', ''),                          # NEW
    'method': self.config.get('method', 'realtime_detection')     # NEW
}
```

### config.json
```json
{
  "watch_id": "watch_1764653561585_7956",
  "sender_id": "yolo_detector",        // NEW
  "note": "",                          // NEW
  "method": "realtime_detection"       // NEW
}
```

---

## ⚠️ 주의사항

1. **하위 호환성**: 기존 서버가 새 필드를 인식하지 못해도 오류 없음
2. **필수/선택**: `sender_id`는 권장, `note`와 `method`는 선택적
3. **브랜치 독립성**: 각 브랜치는 독립적으로 작동하며 서로 영향 없음
4. **설정 파일**: 각 브랜치에서 `config.json` 수정 가능

---

## 📚 관련 문서

- **API_PAYLOAD_UPDATE.md**: 상세한 사용 방법 및 예제
- **GitHub**: https://github.com/futurianh1k/roidetyolo

---

## ✅ 완료 체크리스트

- [x] react-fastapi 브랜치에 적용
- [x] main 브랜치에 적용
- [x] pyqt-ui 브랜치에 적용
- [x] 모든 브랜치 GitHub에 푸시
- [x] 문서 작성 (API_PAYLOAD_UPDATE.md)
- [x] 브랜치 동기화 문서 작성 (BRANCH_SYNC_SUMMARY.md)

---

**작업 완료일**: 2025-12-03  
**작업자**: AI Development Assistant  
**상태**: ✅ 모든 브랜치 동기화 완료
