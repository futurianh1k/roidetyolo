# 🚀 얼굴 분석 기능 빠른 시작 가이드

---

## 📋 개요

**YOLO ROI 사람 검출 시스템**에 **얼굴 분석 기능**이 추가되었습니다!

**분석 항목**:
- 👁️ **눈 상태**: 뜨기/감기 (EAR - Eye Aspect Ratio)
- 👄 **입 상태**: 닫기/말하기/크게 열기 (MAR - Mouth Aspect Ratio)
- 😊 **표정 분석**: neutral / sad / surprised
- 😷 **호흡기 검출**: 인공호흡기/마스크 착용 여부

---

## 🎯 주요 특징

✅ **MediaPipe Face Mesh 기반** - 경량, 정확, GPU 가속  
✅ **실시간 처리** - 15-30 FPS (얼굴당)  
✅ **선택적 분석** - ROI 내부 사람만 분석 옵션  
✅ **Jetson Orin 최적화** - 병렬 처리 및 메모리 관리  
✅ **Streamlit UI 통합** - 웹 브라우저에서 간편한 설정

---

## 📦 설치

### 1️⃣ MediaPipe 설치

```bash
# 기본 설치
pip install mediapipe>=0.10.0

# 또는 requirements.txt로 일괄 설치
pip install -r requirements.txt
```

### 2️⃣ 파일 확인

프로젝트에 다음 파일들이 있는지 확인:

```
yolo_roi_detector/
├── face_analyzer.py           # ✅ 새로 추가 (얼굴 분석 엔진)
├── realtime_detector.py       # ✅ 업데이트 (얼굴 분석 통합)
├── streamlit_app.py           # ✅ 업데이트 (UI 컨트롤 추가)
├── test_face_analyzer.py      # ✅ 테스트 스크립트
└── requirements.txt           # ✅ MediaPipe 추가
```

---

## 🚀 사용 방법

### **방법 1: Streamlit UI로 실행 (추천)**

```bash
# Streamlit 앱 실행
streamlit run streamlit_app.py
```

#### 웹 브라우저에서 설정:

1. **사이드바** → **😊 얼굴 분석** 섹션
2. **"얼굴 분석 활성화"** 체크박스 클릭 ✅
3. (선택) **"ROI 내부만 분석"** - ROI 영역 내 사람만 분석
4. **"실시간 검출 시작"** 버튼 클릭
5. 카메라 화면에서 **얼굴 분석 결과 확인**

#### 화면 표시 내용:

```
Person 0.95
Eyes: Open
Mouth: closed
Expr: neutral
```

호흡기 착용 시:
```
Person 0.92
Eyes: Open
Mouth: closed
Expr: neutral
Ventilator: Yes (0.78)
```

---

### **방법 2: config.json으로 설정**

```json
{
  "yolo_model": "yolov8n.pt",
  "camera_source": 0,
  "detection_interval_seconds": 1.0,
  "confidence_threshold": 0.5,
  
  "enable_face_analysis": true,
  "face_analysis_roi_only": true,
  
  "roi_regions": [
    {
      "id": "ROI1",
      "type": "polygon",
      "points": [[100, 100], [500, 100], [500, 400], [100, 400]]
    }
  ]
}
```

---

## 🎛️ 설정 옵션

| 설정 | 기본값 | 설명 |
|------|--------|------|
| `enable_face_analysis` | `false` | 얼굴 분석 활성화 여부 |
| `face_analysis_roi_only` | `true` | ROI 내부 사람만 분석 |
| `detection_interval_seconds` | `1.0` | YOLO 검출 간격 (초) |

---

## 📊 성능 최적화

### **Jetson Orin Nano 기준**

| 모드 | YOLO FPS | Face FPS | 총 FPS | CPU | GPU | 전력 |
|------|----------|----------|--------|-----|-----|------|
| **YOLO만** | 30-40 | - | 30-40 | 40% | 50% | 8-10W |
| **얼굴 분석 ON** | 30 | 15 | 25-30 | 50% | 60% | 10-12W |
| **ROI만 분석** | 35 | 10-15 | 30-35 | 45% | 55% | 9-11W |

### **최적화 팁**:

1. **ROI 내부만 분석** - `face_analysis_roi_only: true`
2. **검출 간격 조정** - YOLO 간격 1-2초로 설정
3. **해상도 조정** - 카메라 해상도 720p 사용
4. **사람 수 제한** - ROI 영역을 좁게 설정

---

## 🧪 테스트

### 단독 테스트 (웹캠)

```bash
python test_face_analyzer.py
```

- 'q' 키: 종료
- 실시간 얼굴 분석 결과 확인

### Streamlit 통합 테스트

```bash
streamlit run streamlit_app.py
```

1. 얼굴 분석 활성화
2. 카메라로 자신의 얼굴 비춰보기
3. 눈 깜빡이기 → "Eyes: Closed" 확인
4. 입 벌리기 → "Mouth: wide_open" 확인

---

## 🔧 문제 해결

### ❌ ModuleNotFoundError: No module named 'mediapipe'

```bash
pip install mediapipe>=0.10.0
```

### ❌ FaceAnalyzer 모듈 없음

`face_analyzer.py` 파일이 프로젝트 루트에 있는지 확인:

```bash
ls -la face_analyzer.py
```

없으면 제공된 파일을 복사해주세요.

### ❌ 카메라에서 얼굴이 검출되지 않음

- 조명이 충분한지 확인
- 카메라가 얼굴을 정면으로 향하는지 확인
- `confidence_threshold` 값을 낮춰보세요 (0.3으로)

### ❌ 성능이 느림 (FPS < 20)

1. **ROI만 분석** 옵션 활성화
2. **검출 간격 증가**: 2-3초로 설정
3. **해상도 낮추기**: 640x480으로 변경

---

## 📚 기술 세부사항

### **EAR (Eye Aspect Ratio)**

```
EAR = (|P2 - P6| + |P3 - P5|) / (2 * |P1 - P4|)
```

- EAR > 0.21: 눈 뜸
- EAR ≤ 0.21: 눈 감음

### **MAR (Mouth Aspect Ratio)**

```
MAR = (|P2 - P8| + |P3 - P7| + |P4 - P6|) / (3 * |P1 - P5|)
```

- MAR > 0.5: 크게 열림
- MAR > 0.3: 말하기
- MAR ≤ 0.3: 닫힘

### **호흡기 검출**

- 얼굴 아래 영역 HSV 색상 분석
- 흰색/청록색 마스크 검출
- 30% 이상 영역 비율 시 양성 판단

---

## 🎓 강의 자료 업데이트

기존 3시간 강의에 **추가할 수 있는 내용**:

### **Part 7: 얼굴 분석 시스템 (30분)**

- **이론** (10분): MediaPipe Face Mesh 소개
- **실습** (15분): Streamlit UI에서 얼굴 분석 활성화
- **최적화** (5분): Jetson Orin 성능 튜닝

---

## 🔗 관련 문서

- **통합 가이드**: `FACE_ANALYSIS_INTEGRATION.md` (상세 구현 설명)
- **API 문서**: `face_analyzer.py` (FaceAnalyzer 클래스)
- **테스트 스크립트**: `test_face_analyzer.py`

---

## ✅ 체크리스트

설치 및 실행 전 확인:

- [ ] `pip install mediapipe` 완료
- [ ] `face_analyzer.py` 파일 존재
- [ ] `streamlit run streamlit_app.py` 실행
- [ ] 사이드바에서 "얼굴 분석 활성화" 체크
- [ ] 카메라 화면에서 얼굴 분석 결과 확인

---

## 💡 요약

**3단계로 시작**:

```bash
# 1. MediaPipe 설치
pip install mediapipe

# 2. Streamlit 실행
streamlit run streamlit_app.py

# 3. 웹 UI에서 "얼굴 분석 활성화" 체크 ✅
```

**이제 카메라 화면에서 실시간 얼굴 분석 결과를 확인하세요!** 👁️👄😊

---

📍 **GitHub**: https://github.com/futurianh1k/roidetyolo
