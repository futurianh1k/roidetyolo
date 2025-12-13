# ROI TypeError 긴급 수정 가이드

## 🚨 발생한 오류

```
TypeError: '<=' not supported between instances of 'str' and 'int'
File "/home/ubuntu/yolo/roidetyolo/streamlit_app.py", line 576
```

---

## ✅ 수정 완료

총 **2곳** 수정:

### 1️⃣ 576번 라인 (ROI 편집 이미지 표시)
```python
# ❌ 수정 전
st.image(pil_image_roi, width='stretch')

# ✅ 수정 후
st.image(pil_image_roi, use_container_width=True)
```

### 2️⃣ 823번 라인 (실시간 검출 비디오 표시)
```python
# ❌ 수정 전
video_placeholder.image(pil_image, width="stretch")

# ✅ 수정 후
video_placeholder.image(pil_image, use_container_width=True)
```

---

## 📥 수정된 파일 적용 방법

### 방법 1: 직접 수정 (권장)

로컬 환경의 `streamlit_app.py` 파일을 직접 수정하세요:

```bash
cd ~/yolo/roidetyolo
nano streamlit_app.py  # 또는 vim, code 등 원하는 에디터 사용
```

**576번 라인 수정**:
- 찾기: `st.image(pil_image_roi, width='stretch')`
- 바꾸기: `st.image(pil_image_roi, use_container_width=True)`

**823번 라인 수정**:
- 찾기: `video_placeholder.image(pil_image, width="stretch")`
- 바꾸기: `video_placeholder.image(pil_image, use_container_width=True)`

저장 후 Streamlit 앱 재시작:
```bash
streamlit run streamlit_app.py
```

---

### 방법 2: 수정된 파일 다운로드

샌드박스에서 수정된 파일을 다운로드하여 교체:

```bash
# 백업 생성
cd ~/yolo/roidetyolo
cp streamlit_app.py streamlit_app.py.backup

# 수정된 파일로 교체
# (샌드박스에서 다운로드한 streamlit_app_fixed.py를 복사)
```

---

## 🧪 수정 후 테스트

### 1. Streamlit 앱 재시작
```bash
cd ~/yolo/roidetyolo
streamlit run streamlit_app.py
```

### 2. ROI 편집 테스트
1. 좌측 **"ROI 편집"** 탭 선택
2. **"🖱️ 마우스로 ROI 그리기"** 버튼 클릭
3. ✅ TypeError 없이 이미지가 정상 표시되는지 확인

### 3. 실시간 검출 테스트
1. **"실시간 검출 시작"** 버튼 클릭
2. ✅ 비디오 스트림이 정상 표시되는지 확인

---

## 📝 원인 설명

**Streamlit API 변경사항**:
- **구버전** (deprecated): `width='stretch'`
- **신버전** (권장): `use_container_width=True`

`width` 파라미터는 정수(int) 또는 None만 받아야 하는데, 문자열 `'stretch'`를 전달하여 내부적으로 `width <= 0` 비교 시 TypeError 발생.

---

## ⚠️ 주의사항

**버튼의 `width="stretch"`는 문제 없음**:
```python
# ✅ 이것은 괜찮습니다 (버튼의 width 파라미터)
st.button("버튼", width="stretch")
```

**오직 `st.image()` 함수의 `width` 파라미터만 수정 필요**:
```python
# ❌ 이것만 수정 필요 (st.image의 width 파라미터)
st.image(image, width="stretch")  # 오류!

# ✅ 이렇게 수정
st.image(image, use_container_width=True)
```

---

## 🔗 관련 정보

- **GitHub Repository**: https://github.com/futurianh1k/roidetyolo
- **브랜치**: main
- **Streamlit 버전 호환성**: 1.x 이상

---

**수정 완료일**: 2025-06-01  
**수정자**: Gemini AI Assistant
