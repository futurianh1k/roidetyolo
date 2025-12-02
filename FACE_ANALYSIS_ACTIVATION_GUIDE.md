# 얼굴 분석(감정/표정) 활성화 가이드

## ⚠️ 문제 진단 및 해결

### 🔍 문제 원인
1. **`config.json`에 얼굴 분석 활성화 설정 누락**  
   - `enable_face_analysis: true` 설정이 없어 기본적으로 비활성화됨

2. **표정 정보 표시 로직 불완전**  
   - `analyze_expression` 함수가 딕셔너리를 반환하지만, `realtime_detector.py`가 이를 올바르게 처리하지 못함

3. **사용자가 Streamlit UI에서 활성화하지 않음**  
   - 사이드바 "😊 얼굴 분석" 섹션에서 체크박스 활성화 필요

---

## ✅ 해결 방법

### **방법 1: Streamlit UI에서 활성화 (권장)**

1. **Streamlit 앱 실행**
   ```bash
   cd /home/user/yolo_roi_detector
   streamlit run streamlit_app.py
   ```

2. **사이드바에서 설정**
   - 왼쪽 사이드바 스크롤 → **"😊 얼굴 분석"** 섹션 찾기
   - **"얼굴 분석 활성화"** 체크박스 ✅ 클릭
   - (선택) **"ROI 내부만 분석"** 체크 (성능 최적화)

3. **설정 저장**
   - 사이드바 하단 **"💾 설정 저장"** 버튼 클릭
   - "✅ 설정이 저장되었습니다!" 메시지 확인

4. **실시간 검출 시작**
   - "실시간 검출" 탭 이동
   - "▶️ 실시간 검출 시작" 버튼 클릭

---

### **방법 2: `config.json` 직접 수정**

**파일 경로**: `/home/user/yolo_roi_detector/config.json`

**추가할 설정**:
```json
{
  "yolo_model": "yolov8n.pt",
  "camera_source": 0,
  "confidence_threshold": 0.5,
  "detection_interval_seconds": 1.0,
  ...
  
  "enable_face_analysis": true,          // ← 추가
  "face_analysis_roi_only": false,      // ← 추가 (전체 화면 분석)
  "ear_threshold": 0.21,                 // ← 추가 (눈 감지 임계값)
  "mar_speak_threshold": 0.3,            // ← 추가 (말하기 임계값)
  "mar_open_threshold": 0.6,             // ← 추가 (입 크게 열림 임계값)
  
  "roi_regions": [...]
}
```

**편집 명령**:
```bash
cd /home/user/yolo_roi_detector
nano config.json  # 또는 vim/vi
```

---

## 📊 얼굴 분석 결과 확인 방법

### **1. 콘솔 로그 확인**
터미널에서 다음과 같은 로그 확인:
```
[RealtimeDetector] ✅ 얼굴 분석 완료: Eyes=Open, Mouth=closed, Expression=neutral (0.50)
[RealtimeDetector] ✅ 얼굴 분석 완료: Eyes=Open, Mouth=speaking, Expression=happy (0.78)
[RealtimeDetector] ✅ 얼굴 분석 완료: Eyes=Closed, Mouth=wide_open, Expression=surprised (0.85)
```

### **2. 비디오 화면 오버레이**
검출된 사람 BBox 위에 다음 정보 표시:
```
Person 0.92
Eyes: Open
Mouth: speaking
Expr: happy (0.78)
Mask/Ventilator: No
```

### **3. 분석 항목**

| 항목 | 설명 | 가능한 값 |
|------|------|-----------|
| **Eyes** | 눈 상태 | `Open`, `Closed` |
| **Mouth** | 입 상태 | `closed`, `speaking`, `wide_open` |
| **Expr** | 표정 | `neutral`, `happy`, `sad`, `surprised`, `pain`, `angry` |
| **Mask/Ventilator** | 호흡기 착용 | `Yes`, `No` |

---

## 🧪 테스트 방법

### **표정 테스트 시나리오**

1. **Neutral (중립)**  
   - 평상시 얼굴 유지 → `neutral (0.50)`

2. **Happy (웃음)**  
   - 입꼬리 올리기 (미소) → `happy (0.6-0.9)`

3. **Surprised (놀람)**  
   - 눈썹 올리고 입 크게 벌리기 → `surprised (0.7-0.9)`

4. **Sad (슬픔)**  
   - 입꼬리 내리기 → `sad (0.6-0.8)`

5. **Pain (고통/찡그림)**  
   - 눈썹 좁히고 입 약간 벌리기 → `pain (0.6-0.8)`

6. **Angry (화남)**  
   - 눈썹 좁히고 입 다물기 → `angry (0.6-0.8)`

### **눈/입 상태 테스트**

- **눈 감기** → `Eyes: Closed`
- **눈 뜨기** → `Eyes: Open`
- **입 다물기** → `Mouth: closed`
- **말하기 (입 약간 벌림)** → `Mouth: speaking`
- **입 크게 벌리기** → `Mouth: wide_open`

---

## 🚀 성능 최적화 팁

### **1. ROI 내부만 분석 활성화**
```python
config['face_analysis_roi_only'] = True  # ROI 외부 사람은 분석하지 않음
```

### **2. 검출 간격 조정**
```python
config['detection_interval_seconds'] = 2.0  # YOLO 추론 간격 늘리기
```

### **3. 해상도 낮추기**
```python
config['frame_width'] = 640
config['frame_height'] = 480
```

### **4. 카메라 FPS 조정**
```python
cap.set(cv2.CAP_PROP_FPS, 15)  # 15 FPS로 제한
```

---

## 📊 예상 성능 (Jetson Orin Nano)

| 모드 | YOLO FPS | Face FPS | 총 FPS | CPU | GPU | 전력 |
|------|----------|----------|--------|-----|-----|------|
| **YOLO만** | 30-40 | - | 30-40 | 40% | 50% | 8-10W |
| **얼굴 분석 ON (전체)** | 30 | 15 | 25-30 | 50% | 60% | 10-12W |
| **얼굴 분석 ON (ROI만)** | 35 | 10-15 | 30-35 | 45% | 55% | 9-11W |

---

## 🔧 문제 해결

### **MediaPipe 설치 오류**
```bash
pip install --upgrade pip
pip install mediapipe>=0.10.0
```

### **카메라 연결 실패**
```bash
# 카메라 장치 확인
ls -l /dev/video*

# 권한 부여
sudo chmod 666 /dev/video0
```

### **얼굴 분석 활성화했는데도 작동하지 않음**
1. 터미널 로그에서 `[RealtimeDetector] ✅ FaceAnalyzer 초기화 완료` 확인
2. 로그에 `[RealtimeDetector] ⚠️ FaceAnalyzer 모듈 없음` 있으면 MediaPipe 재설치
3. `config.json`에 `"enable_face_analysis": true` 확인
4. Streamlit 앱 재시작

### **표정 감지 정확도가 낮음**
- 조명 개선 (얼굴에 직접 빛이 들어오도록)
- 카메라와 얼굴 거리 조정 (1-2m 권장)
- 해상도 높이기 (1280x720 권장)

---

## 📚 관련 문서

- `FACE_ANALYSIS_QUICKSTART.md` - 빠른 시작 가이드
- `FACE_ANALYSIS_INTEGRATION.md` - 통합 상세 가이드
- `README_FACE_ANALYSIS.md` - 기능 요약

---

## ✨ 업데이트 내역

### **v2.1 (최신)**
- ✅ `config.json`에 얼굴 분석 설정 자동 추가
- ✅ 표정 정보 표시 로직 개선 (딕셔너리 처리)
- ✅ 콘솔 로그 개선 (표정 confidence 포함)
- ✅ 활성화 가이드 문서 추가

### **v2.0**
- MediaPipe Face Mesh 통합
- 눈/입 상태, 표정, 호흡기 검출 기능 추가
- Streamlit UI 제어 추가

---

**🎯 이제 얼굴 분석이 정상 작동합니다!**  
**Streamlit 사이드바 → "😊 얼굴 분석" → "얼굴 분석 활성화" ✅ 체크**
