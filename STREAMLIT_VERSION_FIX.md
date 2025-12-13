# Streamlit 버전 호환성 수정 가이드

## 🚨 발생한 오류

```
TypeError: ImageMixin.image() got an unexpected keyword argument 'use_container_width'
File "streamlit_app.py", line 576
```

---

## 🔍 원인 분석

**문제**: 사용 중인 Streamlit 버전이 구버전입니다.

**Streamlit API 버전별 지원**:
- **Streamlit < 0.88.0**: `use_column_width=True` 사용 (구버전)
- **Streamlit >= 0.88.0**: `use_container_width=True` 사용 (신버전)

---

## ✅ 최종 수정 (구버전 Streamlit 호환)

총 **2곳** 수정:

### 1️⃣ 576번 라인
```python
# ❌ 신버전 API (구버전 Streamlit에서 오류)
st.image(pil_image_roi, use_container_width=True)

# ✅ 구버전 호환
st.image(pil_image_roi, use_column_width=True)
```

### 2️⃣ 823번 라인
```python
# ❌ 신버전 API (구버전 Streamlit에서 오류)
video_placeholder.image(pil_image, use_container_width=True)

# ✅ 구버전 호환
video_placeholder.image(pil_image, use_column_width=True)
```

---

## 📥 로컬 환경 적용 방법

### 방법 1: sed 명령어로 자동 수정 (가장 빠름 ⚡)

```bash
cd ~/yolo/roidetyolo

# 백업 생성
cp streamlit_app.py streamlit_app.py.backup

# 자동 수정 (2곳 모두 수정)
sed -i "s/st\.image(pil_image_roi, width='stretch')/st.image(pil_image_roi, use_column_width=True)/g" streamlit_app.py
sed -i 's/video_placeholder\.image(pil_image, width="stretch")/video_placeholder.image(pil_image, use_column_width=True)/g' streamlit_app.py

# 수정 확인
grep -n "use_column_width" streamlit_app.py

# Streamlit 앱 재시작
streamlit run streamlit_app.py
```

---

### 방법 2: 직접 수정

```bash
cd ~/yolo/roidetyolo
nano streamlit_app.py  # 또는 vim, code 등
```

**2곳 수정**:
1. **576번 라인**: `width='stretch'` → `use_column_width=True`
2. **823번 라인**: `width="stretch"` → `use_column_width=True`

저장 후:
```bash
streamlit run streamlit_app.py
```

---

## 🔍 Streamlit 버전 확인

현재 사용 중인 Streamlit 버전을 확인하세요:

```bash
streamlit --version
# 또는
pip show streamlit | grep Version
```

**권장 조치**:
- **Streamlit < 0.88.0**: `use_column_width=True` 사용 (현재 적용된 수정)
- **Streamlit >= 0.88.0**: `use_container_width=True` 사용 가능

---

## 🎯 빠른 적용 명령어 (복사해서 사용)

```bash
cd ~/yolo/roidetyolo
cp streamlit_app.py streamlit_app.py.backup
sed -i "s/st\.image(pil_image_roi, width='stretch')/st.image(pil_image_roi, use_column_width=True)/g" streamlit_app.py
sed -i 's/video_placeholder\.image(pil_image, width="stretch")/video_placeholder.image(pil_image, use_column_width=True)/g' streamlit_app.py
streamlit run streamlit_app.py
```

---

## 🧪 수정 후 테스트

### 1. ROI 편집 기능
1. 좌측 **"ROI 편집"** 탭 선택
2. **"🖱️ 마우스로 ROI 그리기"** 버튼 클릭
3. ✅ TypeError 없이 이미지가 정상 표시

### 2. 실시간 검출 기능
1. **"실시간 검출 시작"** 버튼 클릭
2. ✅ 비디오 스트림이 정상 표시

### 3. 자동 ROI 생성
- **"⬅️➡️ 좌/우 2분할"** → 정상 작동
- **"🎯 4사분면"** → 정상 작동

---

## 📊 Streamlit API 비교표

| Streamlit 버전 | 이미지 너비 설정 API | 비고 |
|---------------|-------------------|------|
| < 0.88.0 | `use_column_width=True` | ✅ 현재 적용 |
| >= 0.88.0 | `use_container_width=True` | 신버전 권장 |
| 모든 버전 | `width=640` (정수) | 고정 픽셀 크기 |

---

## ⚠️ 중요 참고사항

### 버튼의 width는 문제없음
```python
# ✅ 이것은 괜찮습니다
st.button("버튼", width="stretch")
```

### st.image()만 수정 필요
```python
# ❌ 구버전에서 오류
st.image(image, width="stretch")
st.image(image, use_container_width=True)

# ✅ 구버전 호환
st.image(image, use_column_width=True)
```

---

## 💡 Streamlit 업그레이드 (선택사항)

최신 기능을 사용하고 싶다면 Streamlit 업그레이드:

```bash
pip install --upgrade streamlit

# 업그레이드 후 use_container_width 사용 가능
# 단, 기존 코드 호환성 테스트 필요
```

**주의**: 업그레이드 시 다른 코드에 영향을 줄 수 있으니 테스트 필요!

---

## 📝 수정 이력

| 시도 | 수정 내용 | 결과 |
|------|----------|------|
| 1차 | `width='stretch'` → `use_container_width=True` | ❌ 구버전 Streamlit에서 오류 |
| 2차 | `use_container_width=True` → `use_column_width=True` | ✅ 구버전 호환 성공 |

---

**수정 완료일**: 2025-06-01  
**수정자**: Gemini AI Assistant  
**호환성**: Streamlit < 0.88.0 (구버전)
