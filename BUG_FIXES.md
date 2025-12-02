# 🐛 버그 수정 로그

---

## 📅 2025-12-02 - v2.0.1 패치

### **🔧 수정된 버그**

#### **1. 미디어 파일 처리 오류**

**증상**:
```
2025-12-02 16:25:31.053 MediaFileHandler: Missing file 9db06585fb90689ae5f29a2450055a7a99fcda406f0163ba094e5fe4.jpg
KeyError: '9db06585fb90689ae5f29a2450055a7a99fcda406f0163ba094e5fe4'
```

**원인**:
- Streamlit의 `st.image()`가 NumPy 배열을 내부적으로 임시 파일로 저장
- 빠른 프레임 업데이트 시 파일 ID 불일치 발생

**해결 방법**:
- NumPy 배열 → PIL Image 변환 후 표시
- `Image.fromarray()` 사용으로 메모리 내 처리

**수정 코드**:
```python
# Before (문제 발생)
frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
video_placeholder.image(frame_rgb, width='stretch')

# After (수정됨)
frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
pil_image = Image.fromarray(frame_rgb)
video_placeholder.image(pil_image, use_container_width=True)
```

**결과**:
✅ 실시간 검출 프레임 표시 시 오류 없음
✅ 메모리 효율성 개선

---

#### **2. API 엔드포인트 multipart/form-data 지원 추가**

**요구사항**:
```
Swagger API 스펙:
POST /api/emergency/quick/{watchId}
Content-Type: multipart/form-data

Path Parameters:
- watchId (필수)

Form Data:
- senderId (필수)
- note (선택)
- image (선택, binary)
```

**기존 문제**:
- JSON (application/json) 방식만 지원
- 이미지 파일 업로드 불가능
- Path parameter 미지원

**해결 방법**:
1. API 타입 선택 추가 (JSON / Multipart)
2. Multipart 방식 구현:
   - Path parameter `{watchId}` 처리
   - Form data 전송
   - 파일 업로드 지원

**수정 코드**:
```python
# Multipart 방식 API 호출
api_url = selected_api['url'].replace('{watchId}', test_watch_id)

form_data = {
    'senderId': test_sender_id,
    'note': test_note
}

files = {}
if uploaded_file is not None:
    files['image'] = (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)

response = requests.post(
    api_url,
    data=form_data,
    files=files,
    timeout=10
)
```

**결과**:
✅ JSON API 지원 (기존)
✅ Multipart API 지원 (신규)
✅ 이미지 파일 업로드 가능
✅ Path parameter 처리

---

## 📝 테스트 방법

### **1. 미디어 파일 오류 테스트**

```bash
# 1. Streamlit 실행
streamlit run streamlit_app.py

# 2. ROI 설정
# - 좌/우 2분할 또는 4사분면 클릭

# 3. 실시간 검출 시작
# - "▶️ 검출 시작" 버튼 클릭

# 4. 프레임 표시 확인
# - 오류 메시지 없이 정상 표시되는지 확인
# - 콘솔에 "MediaFileHandler: Missing file" 오류 없음
```

**예상 결과**:
- ✅ 실시간 프레임 정상 표시
- ✅ FPS 표시 정상
- ✅ 콘솔 오류 없음

---

### **2. Multipart API 테스트**

```bash
# 1. API 테스트 탭 이동

# 2. API 선택
# - "Emergency Alert API (Multipart)" 선택

# 3. API 타입 선택
# - "Multipart (multipart/form-data)" 선택

# 4. 필수 필드 입력
# - watchId: watch_1764653561585_7956
# - senderId: test-user

# 5. 선택 필드 입력
# - note: 응급상황 메시지
# - image: 이미지 파일 업로드 (JPG/PNG)

# 6. "🚀 API 테스트 실행" 버튼 클릭
```

**예상 결과**:
- ✅ API 호출 성공 (200/201 상태 코드)
- ✅ 요청 데이터 정상 표시
- ✅ 이미지 파일 정상 전송

---

## 📋 변경된 파일

| 파일 | 변경 사항 |
|------|----------|
| `streamlit_app.py` | PIL Image 사용, Multipart API 지원 추가 |
| `BUG_FIXES.md` | 버그 수정 로그 문서 (신규) |

---

## 🔍 추가 개선 사항

### **카메라 오류 경고 처리**

**증상**:
```
[ WARN:0@95.075] global cap_v4l.cpp:913 open VIDEOIO(V4L2:/dev/video0): can't open camera by index
```

**원인**:
- 카메라 인덱스가 유효하지 않거나 사용 중
- V4L2 백엔드 초기화 실패

**권장 해결 방법**:
```bash
# 1. 사용 가능한 카메라 확인
ls -l /dev/video*

# 2. 카메라 권한 확인
sudo chmod 666 /dev/video0

# 3. Streamlit에서 카메라 자동 검색
# - 사이드바 → "🔍 카메라 자동 검색" 클릭
```

---

### **MediaPipe 경고 처리**

**증상**:
```
W0000 00:00:1764660280.337801 landmark_projection_calculator.cc:186] 
Using NORM_RECT without IMAGE_DIMENSIONS is only supported for the square ROI
```

**원인**:
- MediaPipe Face Mesh 내부 경고
- 기능에는 영향 없음

**대응**:
- ✅ 정상 작동 (무시 가능)
- 향후 MediaPipe 버전 업데이트 시 해결 예정

---

## ✅ 테스트 체크리스트

배포 전 확인 사항:

- [x] 미디어 파일 오류 수정 확인
- [x] PIL Image 정상 작동
- [x] Multipart API 구현
- [x] 파일 업로드 기능 테스트
- [x] JSON API 호환성 유지
- [x] 문서 업데이트
- [ ] Jetson Orin에서 실제 테스트
- [ ] 장시간 실행 안정성 테스트

---

## 📚 관련 문서

- `README_STREAMLIT.md` - Streamlit UI 가이드
- `RELEASE_NOTES.md` - v2.0 릴리스 노트
- `CUSTOM_ROI_GUIDE.md` - 커스텀 ROI 가이드

---

## 🔮 향후 계획

### **v2.0.2 예정**

- [ ] 카메라 오류 자동 복구
- [ ] API 응답 로깅 개선
- [ ] 설정 검증 기능 추가
- [ ] 에러 리포팅 시스템

---

## 🙏 감사합니다!

버그 리포트와 피드백에 감사드립니다!

**GitHub**: https://github.com/futurianh1k/roidetyolo

**이슈 제보**: https://github.com/futurianh1k/roidetyolo/issues
