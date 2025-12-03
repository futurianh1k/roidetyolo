# YOLO ROI 사람 검출 시스템 - PyQt5 버전

## 📋 개요

Streamlit 기반 웹 UI를 PyQt5 데스크톱 애플리케이션으로 완전 변환한 버전입니다.

## 🎯 주요 기능

### 1️⃣ **ROI 편집** (📐 ROI 편집 탭)
- ✅ **실시간 카메라 프리뷰**: 카메라 화면을 보면서 ROI 편집
- ✅ **마우스 클릭 기반 ROI 그리기**: 화면을 직접 클릭하여 다각형 ROI 생성
- ✅ **자동 ROI 생성**: 좌/우 2분할, 4사분면 자동 생성
- ✅ **ROI 관리**: 모든 ROI 삭제, 개별 ROI 수정

**사용 방법:**
1. "✏️ ROI 편집 시작 (카메라 켜기)" 버튼 클릭
2. 화면에서 원하는 위치를 클릭하여 점 추가 (최소 3개 이상)
3. "✅ ROI 완성" 버튼으로 ROI 저장
4. "⏹️ ROI 편집 중지 (카메라 끄기)" 버튼으로 종료

### 2️⃣ **실시간 검출** (🎥 실시간 검출 탭)
- ✅ **YOLO 기반 사람 검출**: YOLOv8 모델로 실시간 사람 검출
- ✅ **ROI 내 사람 추적**: 각 ROI 영역별 사람 존재/부재 상태 추적
- ✅ **얼굴 분석 통합**: MediaPipe Face Mesh 기반 얼굴 분석
  - 👁️ 눈 개폐 상태 (EAR)
  - 👄 입 상태 (MAR - 닫힘/말하기/크게 열림)
  - 😊 표정 분석 (6가지 감정: neutral, happy, sad, surprised, pain, angry)
  - 😷 마스크/호흡기 착용 검출
- ✅ **실시간 FPS 표시**: 검출 성능 모니터링
- ✅ **ROI별 상태 표시**: 각 ROI의 현재 상태 실시간 업데이트

### 3️⃣ **통계 & 로그** (📊 통계 & 로그 탭)

#### 😊 얼굴 분석 통계
- **총 검출 얼굴**: 누적 검출된 얼굴 수
- **표정 분포**: 6가지 감정별 카운트 및 퍼센트
  - 😐 Neutral (중립)
  - 😊 Happy (행복)
  - 😢 Sad (슬픔)
  - 😲 Surprised (놀람)
  - 😖 Pain (고통)
  - 😠 Angry (화남)
- **눈 상태**: 눈 뜸/감음 카운트 및 개안율 프로그레스 바
- **입 상태**: 닫힘/말하기/크게 열림 3단계 상태
- **마스크/호흡기 검출**: 착용 감지 횟수
- **통계 초기화**: 모든 얼굴 분석 통계 리셋

#### 📊 YOLO 검출 통계
- ROI별 검출 상태 (present/absent)
- ROI별 누적 검출 카운트

#### 📝 이벤트 로그
- 시간순 이벤트 기록 (최대 50개)
- 로그 초기화 기능

### 4️⃣ **API 테스트** (🔗 API 테스트 탭)
- ✅ **API 엔드포인트 테스트**: 구성된 API로 테스트 전송
- ✅ **Watch ID 설정**: API 전송 시 사용할 Watch ID
- ✅ **테스트 데이터 전송**: 커스텀 메시지 전송 테스트
- ✅ **응답 확인**: API 응답 상태 코드 및 본문 표시

### ⚙️ **설정 패널** (왼쪽 사이드바)

#### 🤖 YOLO 모델
- 모델 선택: yolov8n.pt / yolov8s.pt / yolov8m.pt / yolov8l.pt

#### 📹 카메라
- 카메라 번호: 0~10 (기본값: 0)

#### 🎯 검출 설정
- **YOLO 검출 간격 (초)**: 0.5 ~ 5.0초 (기본값: 1.0초)
  - 이 간격으로 YOLO 추론 및 얼굴 분석 동시 실행
- **신뢰도 임계값**: 0.0 ~ 1.0 (기본값: 0.5)
- **존재 확인 시간 (초)**: 1 ~ 60초 (기본값: 5초)
- **부재 확인 시간 (초)**: 1 ~ 60초 (기본값: 3초)

#### 😊 얼굴 분석
- ✅ **얼굴 분석 활성화**: 얼굴 분석 기능 켜기/끄기
- ✅ **ROI 내부만 분석**: ROI 내부 사람만 얼굴 분석
- **분석 항목**:
  - 👁️ 눈 개폐 (EAR)
  - 👄 입 상태 (MAR)
  - 😊 표정 분석
  - 😷 호흡기 검출

#### 🌐 API 설정
- **Watch ID**: API 전송 시 사용할 Watch ID
- **API 엔드포인트**: 이벤트 전송 API URL

#### 💾 설정 저장
- 모든 설정을 `config.json`에 저장

## 🚀 실행 방법

### 1. 의존성 설치
```bash
# PyQt5 버전 전용 의존성
pip install -r requirements_pyqt.txt
```

### 2. 애플리케이션 실행
```bash
python pyqt_app.py
```

## 📦 필수 패키지

### Core Dependencies
- **ultralytics>=8.0.0**: YOLOv8 모델
- **opencv-python>=4.8.0**: 카메라 및 이미지 처리
- **requests>=2.31.0**: API 전송
- **numpy>=1.24.0,<2.0.0**: 수치 연산
- **Pillow>=10.0.0**: 이미지 처리

### Face Analysis
- **mediapipe>=0.10.0**: Face Mesh 기반 얼굴 분석

### PyQt5 UI
- **PyQt5>=5.15.0**: Qt5 Python 바인딩
- **PyQt5-Qt5>=5.15.0**: Qt5 런타임
- **PyQt5-sip>=12.11.0**: SIP 런타임

### Optional
- **pyqtgraph>=0.13.0**: 그래프 플로팅 (선택사항)

## 🆚 Streamlit vs PyQt 비교

| 기능 | Streamlit | PyQt5 |
|------|-----------|-------|
| **실행 방식** | 웹 브라우저 | 데스크톱 앱 |
| **ROI 편집** | streamlit-image-coordinates | 네이티브 마우스 클릭 |
| **성능** | 웹 오버헤드 있음 | 네이티브 성능 |
| **배포** | 웹 서버 필요 | 단독 실행 파일 |
| **UI 반응성** | 재실행 기반 | 이벤트 기반 |
| **얼굴 분석 통계** | ✅ 지원 | ✅ 지원 |
| **실시간 API 전송** | ✅ 지원 | ✅ 지원 |

## 🔧 기술 스택

### 백엔드
- **YOLO**: ultralytics YOLOv8 (사람 검출)
- **MediaPipe**: Face Mesh (얼굴 분석)
- **OpenCV**: 카메라 및 이미지 처리
- **Threading**: 백그라운드 검출 스레드

### 프론트엔드 (PyQt5)
- **QMainWindow**: 메인 윈도우
- **QTabWidget**: 탭 기반 UI
- **QTimer**: 실시간 업데이트 (30 FPS)
- **ClickableLabel**: 커스텀 마우스 클릭 위젯
- **QImage/QPixmap**: OpenCV → Qt 이미지 변환

## 📊 성능 최적화

### YOLO-얼굴 분석 동기화
- **YOLO 검출 간격 = 얼굴 분석 간격**: 하나의 타이머로 통합
- **기본 1초 간격**: CPU/GPU 사용률 최적화
- **Jetson Orin Nano 목표**: 25-35 FPS

### 추천 설정
```json
{
  "detection_interval_seconds": 1.0,  // 1초마다 YOLO + 얼굴 분석
  "frame_width": 640,                 // 해상도 낮춤
  "frame_height": 480,
  "face_analysis_roi_only": true      // ROI 내부만 분석
}
```

## 🐛 트러블슈팅

### 카메라가 열리지 않을 때
```python
# 카메라 번호 확인
camera_source = 0  # 또는 1, 2, ...
```

### 얼굴 분석 통계가 너무 빨리 증가할 때
- **원인**: YOLO 검출 간격보다 UI 업데이트가 더 빠름
- **해결**: 코드에 이미 중복 방지 로직 구현됨
  ```python
  detection_interval = self.config.get('detection_interval_seconds', 1.0)
  if current_timestamp - self._last_face_stats_update >= detection_interval * 0.9:
      # 얼굴 분석 통계 업데이트
  ```

### ROI 클릭 좌표가 정확하지 않을 때
- **원인**: 라벨 크기와 실제 프레임 크기 비율 불일치
- **해결**: 스케일 비율 자동 계산 구현됨
  ```python
  scale_x = frame_w / label_w
  scale_y = frame_h / label_h
  real_x = int(x * scale_x)
  real_y = int(y * scale_y)
  ```

## 📂 프로젝트 구조

```
yolo_roi_detector/
├── pyqt_app.py                 # PyQt5 메인 애플리케이션
├── realtime_detector.py        # YOLO 검출 백엔드 (공통)
├── face_analyzer.py            # 얼굴 분석 모듈 (공통)
├── roi_utils.py                # ROI 유틸리티 (공통)
├── camera_utils.py             # 카메라 유틸리티 (공통)
├── config.json                 # 설정 파일
├── requirements_pyqt.txt       # PyQt5 의존성
└── README_PYQT.md              # 이 문서
```

## 🎯 주요 개선사항 (Streamlit → PyQt5)

1. ✅ **마우스 클릭 기반 ROI 편집**: 화면 직접 클릭으로 ROI 생성
2. ✅ **네이티브 성능**: 웹 오버헤드 없이 빠른 반응성
3. ✅ **실시간 카메라 프리뷰**: ROI 편집 시 실시간 카메라 화면
4. ✅ **얼굴 분석 통계 정확도**: YOLO 간격과 동기화하여 중복 집계 방지
5. ✅ **단독 실행**: 웹 서버 없이 독립 실행 가능
6. ✅ **이벤트 기반 UI**: Qt 이벤트 루프로 더 효율적인 UI 업데이트

## 📖 추가 문서

- **Streamlit 버전**: `streamlit_app.py`
- **얼굴 분석 가이드**: `FACE_ANALYSIS_ACTIVATION_GUIDE.md`
- **YOLO-얼굴 동기화**: `FACE_YOLO_SYNC_EXPLANATION.md`
- **얼굴 통계 업데이트**: `FACE_STATS_UPDATE_GUIDE.md`

## 🔗 관련 링크

- **GitHub 저장소**: https://github.com/futurianh1k/roidetyolo
- **PyQt5 브랜치**: `pyqt-ui`
- **Main 브랜치**: Streamlit 버전

## 📝 라이선스

이 프로젝트는 원본 YOLO ROI 사람 검출 시스템의 PyQt5 버전입니다.

---

**버전**: 1.0.0  
**날짜**: 2025-01-09  
**작성자**: AI Assistant  
**기반 프로젝트**: YOLO ROI Person Detector (Streamlit)
