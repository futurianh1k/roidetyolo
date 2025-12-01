# 🎓 YOLO ROI 실시간 사람 감지 시스템 - 3시간 강의 자료

---

## 📚 강의 자료 개요

이 디렉토리에는 **"YOLO ROI 실시간 사람 감지 시스템 구축 완전 가이드"** 3시간 강의를 위한 모든 자료가 포함되어 있습니다.

**강의 목표**: YOLO를 활용한 실시간 사람 감지 시스템을 처음부터 끝까지 직접 구축

---

## 📋 강의 자료 목록

### 1️⃣ **LECTURE_3HOURS_OUTLINE.md** (6.1KB)
**강의 전체 개요 문서**

**내용**:
- 강의 목표 및 학습 성과
- 3시간 타임라인 (6개 Part)
- 필수 준비물 (하드웨어, 소프트웨어, 사전 지식)
- 강의 특징 및 참고 자료

**용도**: 강의 기획, 수강생 사전 안내

---

### 2️⃣ **LECTURE_PART1_SLIDES.md** (20KB)
**Part 1: 이론 및 환경 설정 (40분)**

**슬라이드**: 14장 (Slide 1-14)

**주요 내용**:
- 강의 소개 및 시스템 데모
- YOLO 객체 탐지 알고리즘 기초
- 시스템 아키텍처 설계
- 개발 환경 구축 (GitHub 클론, 패키지 설치, 카메라 테스트)

**강의 스크립트**: 각 슬라이드별 상세 설명 포함

---

### 3️⃣ **LECTURE_PART2_SLIDES.md** (39KB)
**Part 2: 핵심 기능 구현 (80분)** - 가장 중요!

**슬라이드**: 19장 (Slide 15-33)

**주요 내용**:

**Module 2.1: 카메라 & YOLO 통합 (20분)**
- OpenCV 카메라 초기화
- YOLO 모델 로딩 및 추론
- 실습 1: 기본 사람 탐지기 (10분)

**Module 2.2: ROI 시스템 구현 (25분)**
- Polygon ROI 정의
- Point-in-Polygon 알고리즘
- 여러 ROI 동시 관리
- 실습 2: ROI 기반 탐지기 (15분)

**Module 2.3: 상태 관리 & API 연동 (20분)**
- Dwell Time 로직 (5초 검출, 3초 미검출)
- ROI별 상태 추적
- JSON API 이벤트 전송
- 실습 3: Dwell Time & API (15분)

**Module 2.4: 백그라운드 스레드 최적화 (15분)**
- 멀티스레딩 아키텍처
- Queue 기반 통신
- RealtimeDetector 클래스
- 실습 4: 멀티스레딩 구현 (10분)

**강의 스크립트**: 코드 한 줄씩 설명, 실습 진행 가이드 포함

---

### 4️⃣ **LECTURE_PART3456_SLIDES.md** (26KB)
**Part 3-6: 웹 UI, 배포, 최적화, Q&A (60분)**

**슬라이드**: 16장 (Slide 34-49)

**주요 내용**:

**Part 3: Streamlit 웹 UI 개발 (30분)**
- Streamlit 프레임워크 소개
- 레이아웃 구성 (사이드바, 탭, 컬럼)
- Session State 관리
- 실습 5: ROI 편집기 (10분)
- 실시간 검출 대시보드

**Part 4: 플랫폼별 배포 (20분)**
- x86_64 (일반 PC) 설치
- RK3588 (Rockchip ARM) 설치 및 V4L2 설정
- Jetson Orin (NVIDIA) 설치 및 TensorRT 최적화

**Part 5: 성능 최적화 & 문제 해결 (20분)**
- 6가지 최적화 전략 (탐지 간격, 해상도, Confidence, 모델 선택, 프레임 스킵, TensorRT)
- 일반적인 문제 해결 가이드 (NumPy 오류, 카메라 미감지, FPS 저하, API 실패)

**Part 6: 마무리 & Q&A (10분)**
- 프로젝트 요약 및 확장 아이디어
- 추가 학습 자료
- Q&A 및 강의 평가

**강의 스크립트**: 각 파트별 핵심 설명 포함

---

### 5️⃣ **LECTURE_SCRIPT_FULL.md** (13KB)
**강사용 전체 강의 진행 가이드**

**내용**:
- 강의 타임라인 (분 단위)
- 강사 준비사항 체크리스트
- 각 슬라이드별 강의 스크립트 요약
- 실습 진행 방법 (타이머, 학생 도움, 공통 오류 처리)
- 휴식 시간 안내
- 강의 성공 팁 (강의 전/중/후)
- 강의 평가 항목

**용도**: 강의 당일 진행 가이드, 타이밍 관리

---

## 🎯 강의 구성 요약

| Part | 시간 | 슬라이드 | 실습 | 내용 |
|------|------|----------|------|------|
| Part 1 | 40분 | 1-14 | 0개 | 이론 및 환경 설정 |
| 휴식 | 5분 | - | - | - |
| Part 2 | 80분 | 15-33 | 4개 | 핵심 기능 구현 |
| 휴식 | 10분 | - | - | - |
| Part 3 | 30분 | 34-38 | 1개 | Streamlit 웹 UI |
| Part 4 | 20분 | 39-42 | 0개 | 플랫폼별 배포 |
| Part 5 | 20분 | 43-44 | 0개 | 성능 최적화 |
| Part 6 | 10분 | 45-49 | 0개 | 마무리 & Q&A |
| **총계** | **3시간** | **49장** | **5개** | - |

---

## 👥 대상 학습자

**필수 지식**:
- Python 기초 문법
- 기본 터미널/명령 프롬프트 사용

**선택 지식** (없어도 됨):
- OpenCV
- 머신러닝/딥러닝
- 컴퓨터 비전

**적합한 학습자**:
- Python 개발자
- 컴퓨터 비전 입문자
- AI/ML 엔지니어
- 임베디드 시스템 개발자
- 데이터 과학자

---

## 💻 필수 준비물

### 하드웨어
- 개발용 PC (권장: i5 이상, 8GB RAM 이상)
- 웹캠 또는 USB 카메라
- (선택) Jetson Orin 또는 RK3588 보드

### 소프트웨어
- Python 3.8 - 3.11
- Git
- 텍스트 에디터 (VS Code 권장)

### 사전 설치
```bash
# 프로젝트 클론
git clone https://github.com/futurianh1k/roidetyolo.git
cd roidetyolo

# 패키지 설치
pip install -r requirements.txt

# 카메라 테스트
python test_camera_detection.py
```

---

## 📖 강의 진행 방법

### 강사 입장

1. **강의 전 준비**:
   - `LECTURE_3HOURS_OUTLINE.md` 읽기 (전체 흐름 파악)
   - `LECTURE_SCRIPT_FULL.md` 읽기 (진행 가이드 숙지)
   - 데모 환경 구축 및 테스트
   - 각 실습 코드 사전 작성 (참고용)

2. **강의 진행**:
   - `LECTURE_PART1_SLIDES.md` → `LECTURE_PART2_SLIDES.md` → `LECTURE_PART3456_SLIDES.md` 순서로 진행
   - 각 슬라이드의 강의 스크립트 참고
   - 실습 시간 타이머 설정 (엄수)
   - 학습자 질문 적극 응답

3. **강의 후**:
   - 피드백 수집
   - GitHub Issues로 질문 답변
   - 추가 자료 공유

### 학습자 입장

1. **강의 전 준비**:
   - `LECTURE_3HOURS_OUTLINE.md` 읽기 (강의 개요 파악)
   - 개발 환경 설치 (Python, Git, 패키지)
   - 카메라 연결 테스트

2. **강의 수강**:
   - 강사 설명을 따라 코드 작성
   - 실습 시간에 직접 구현
   - 막히면 질문하기
   - 완성 코드는 GitHub에서 참고

3. **강의 후**:
   - 프로젝트 코드 복습
   - 자신의 Use Case에 맞게 수정
   - 추가 학습 자료 참고

---

## 🎓 학습 성과

강의 수료 후 학습자는:

✅ **YOLO 객체 탐지 시스템을 처음부터 끝까지 만들 수 있습니다**  
✅ **ROI 기반 영역 감시 시스템을 구축할 수 있습니다**  
✅ **Streamlit 웹 대시보드를 개발할 수 있습니다**  
✅ **멀티플랫폼(x86_64, RK3588, Jetson Orin)에 배포할 수 있습니다**  
✅ **성능 최적화로 40-60% 리소스를 절감할 수 있습니다**  

---

## 📦 완성 프로젝트

강의를 통해 완성하는 시스템:

```
roidetyolo/
├── streamlit_app.py          ← Streamlit 메인 앱
├── realtime_detector.py      ← 실시간 탐지 엔진
├── camera_utils.py           ← 카메라 유틸리티
├── roi_utils.py              ← ROI 관리
├── requirements.txt          ← 패키지 목록
├── config.json               ← 설정 파일
└── README.md                 ← 프로젝트 설명
```

**기능**:
- ✅ 실시간 YOLO 사람 탐지 (30 FPS)
- ✅ Polygon ROI 영역 설정
- ✅ Dwell Time 기반 이벤트 (5초/3초)
- ✅ JSON API 통합
- ✅ 웹 대시보드 (Streamlit)
- ✅ 멀티플랫폼 지원

**성능**:
- x86_64: 10-15 FPS
- RK3588: 5-8 FPS
- Jetson Orin: 30-60 FPS
- Jetson Orin + TensorRT: 60-120 FPS

---

## 🔗 관련 자료

### 프로젝트 문서
- `README.md` - 프로젝트 메인 문서
- `README_STREAMLIT.md` - Streamlit UI 가이드
- `PERFORMANCE_OPTIMIZATION.md` - 성능 최적화
- `JETSON_ORIN_SETUP.md` - Jetson Orin 설치
- `FIX_NUMPY_ERROR.md` - NumPy 오류 해결
- `BBOX_DISPLAY_GUIDE.md` - BBox 표시 가이드
- `TROUBLESHOOTING.md` - 문제 해결

### 온라인 자료
- **GitHub**: https://github.com/futurianh1k/roidetyolo
- **YOLO 공식 문서**: https://docs.ultralytics.com
- **Streamlit 문서**: https://docs.streamlit.io

---

## 💬 질문 및 지원

### 강의 관련 질문
- GitHub Issues: https://github.com/futurianh1k/roidetyolo/issues
- 태그: `lecture`, `question`

### 기술적 문제
- GitHub Issues: `bug`, `help wanted`
- 문서 참고: `TROUBLESHOOTING.md`, `FIX_NUMPY_ERROR.md`

### 피드백
- GitHub Discussions
- 강의 평가 설문

---

## 📄 라이선스

**프로젝트 코드**: MIT License (자유롭게 사용 가능)  
**YOLO 모델**: Ultralytics AGPL-3.0 (상업 사용 시 라이선스 구매 필요)  
**강의 자료**: CC BY-NC-SA 4.0 (비상업적 교육 목적으로 자유롭게 사용 가능)

---

## ✨ 기여

강의 자료 개선 제안:
1. Fork 이 저장소
2. 수정 후 Pull Request
3. 리뷰 및 머지

---

## 🙏 감사

이 강의 자료가 여러분의 학습과 교육에 도움이 되기를 바랍니다!

**강의를 통해 배우고, 만들고, 공유하세요!** 💪

---

**Repository**: https://github.com/futurianh1k/roidetyolo  
**Latest Update**: 2025년 12월  
**Version**: 1.0
