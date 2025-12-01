# 🎓 YOLO ROI 실시간 사람 감지 시스템 - 3시간 강의 개요

## 📋 강의 개요

**강의 제목**: YOLO ROI 실시간 사람 감지 시스템 구축 완전 가이드  
**강의 시간**: 3시간 (180분)  
**난이도**: 중급  
**대상**: Python 기본 지식 보유자, 컴퓨터 비전 입문자, 임베디드 AI 개발자

---

## 🎯 강의 목표

본 강의를 수강한 후 학습자는:

1. **YOLO 객체 탐지의 원리와 실전 활용법**을 이해합니다
2. **ROI 기반 실시간 감지 시스템**을 처음부터 구축할 수 있습니다
3. **Streamlit을 활용한 웹 UI** 개발 능력을 습득합니다
4. **RK3588, Jetson Orin 등 임베디드 플랫폼**에 배포할 수 있습니다
5. **성능 최적화 및 문제 해결** 능력을 갖춥니다

---

## 📚 강의 구성 (3시간)

### **Part 1: 이론 및 환경 설정** (40분)

#### Module 1.1: 강의 소개 및 시스템 개요 (10분)
- 강의 목표 및 구성
- 완성된 시스템 데모 시연
- 실제 활용 사례 소개

#### Module 1.2: YOLO 객체 탐지 기초 (15분)
- YOLO 알고리즘 원리
- YOLOv8 특징 및 장점
- 객체 탐지 vs 분류 vs 세그멘테이션
- Confidence, BBox, NMS 개념

#### Module 1.3: 개발 환경 구축 (15분)
- Python 환경 설정
- 필수 패키지 설치
- 카메라 연결 및 테스트
- GitHub 리포지토리 클론

---

### **Part 2: 핵심 기능 구현** (80분)

#### Module 2.1: 카메라 입력 및 YOLO 통합 (20분)
- OpenCV 카메라 초기화
- YOLO 모델 로딩
- 실시간 프레임 처리
- Person 클래스 필터링
- **실습**: 기본 사람 탐지 코드 작성

#### Module 2.2: ROI (관심 영역) 시스템 구현 (25분)
- Polygon ROI 정의 방법
- Point-in-Polygon 알고리즘
- ROI 내부 사람 감지 로직
- 여러 ROI 동시 관리
- **실습**: ROI 편집기 구현

#### Module 2.3: 상태 관리 및 API 연동 (20분)
- ROI별 상태 추적 (presence/absence)
- Dwell Time 로직 (5초 검출, 3초 미검출)
- JSON API 이벤트 전송
- 에러 핸들링 및 재시도 로직
- **실습**: API 목서버 테스트

#### Module 2.4: 백그라운드 스레드 최적화 (15분)
- 멀티스레딩 아키텍처
- Queue 기반 프레임 전달
- FPS 제어 및 성능 튜닝
- 메모리 누수 방지
- **실습**: RealtimeDetector 클래스 구현

---

### **Part 3: Streamlit 웹 UI 개발** (30분)

#### Module 3.1: Streamlit 기초 (10분)
- Streamlit 프레임워크 소개
- 레이아웃 구성 (사이드바, 탭, 컬럼)
- Session State 관리
- 실시간 업데이트 패턴

#### Module 3.2: ROI 편집 UI 구현 (10분)
- 캔버스에 Polygon 그리기
- 좌표 입력 인터페이스
- ROI 저장 및 로딩
- 시각적 피드백

#### Module 3.3: 실시간 검출 대시보드 (10분)
- 비디오 스트리밍 표시
- ROI별 상태 모니터링
- 이벤트 로그 표시
- FPS 및 성능 지표
- **실습**: 완전한 Streamlit 앱 실행

---

### **Part 4: 플랫폼별 배포 및 최적화** (20분)

#### Module 4.1: x86_64 환경 배포 (5분)
- 일반 PC/노트북 환경 설정
- CPU 추론 최적화
- 성능 벤치마크

#### Module 4.2: RK3588 플랫폼 (7분)
- V4L2 백엔드 설정
- 카메라 권한 문제 해결
- ARM 최적화 팁

#### Module 4.3: Jetson Orin 플랫폼 (8분)
- CUDA/TensorRT 가속
- Jetson 전용 PyTorch 설치
- TensorRT 엔진 변환 (2-3배 속도 향상)
- 성능 모드 설정

---

### **Part 5: 고급 기능 및 문제 해결** (20분)

#### Module 5.1: 성능 최적화 전략 (10분)
- 탐지 간격 조정 (1초 추론)
- 해상도 튜닝
- Confidence threshold 최적화
- 40-60% 리소스 절감 기법

#### Module 5.2: 일반적인 문제 및 해결책 (10분)
- NumPy RuntimeError 해결
- 카메라 미감지 문제
- API 연결 실패 처리
- ROI 포맷 호환성 문제

---

### **Part 6: 마무리 및 Q&A** (10분)

#### Module 6.1: 프로젝트 요약 및 확장 아이디어 (5분)
- 완성된 시스템 리뷰
- 추가 개선 아이디어
- 실전 응용 사례

#### Module 6.2: Q&A 및 토론 (5분)
- 질의응답
- 추가 학습 자료 안내
- GitHub 리포지토리 활용법

---

## 🎯 학습 성과물

강의 후 학습자가 얻게 되는 것:

1. **완전히 작동하는 ROI 기반 사람 감지 시스템**
2. **Streamlit 웹 UI 대시보드**
3. **멀티 플랫폼 배포 경험** (x86_64, RK3588, Jetson Orin)
4. **GitHub 오픈소스 프로젝트 접근** (https://github.com/futurianh1k/roidetyolo)
5. **실전 문제 해결 능력**

---

## 📦 필수 준비물

### 하드웨어
- 웹캠 또는 USB 카메라
- 개발용 PC (권장: i5 이상, 8GB RAM 이상)
- (선택) Jetson Orin 또는 RK3588 보드

### 소프트웨어
- Python 3.8-3.11
- Git
- 텍스트 에디터 (VS Code 권장)

### 사전 지식
- Python 기초 문법
- 기본 리눅스 명령어
- (선택) OpenCV 기초

---

## 🎓 강의 특징

✅ **실습 중심** - 이론 30%, 실습 70%  
✅ **완성된 코드 제공** - GitHub 오픈소스  
✅ **멀티 플랫폼** - PC, RK3588, Jetson Orin 모두 지원  
✅ **실전 적용** - 실제 프로젝트 수준의 코드  
✅ **문제 해결 가이드** - 트러블슈팅 문서 포함  

---

## 📖 참고 자료

- **GitHub Repository**: https://github.com/futurianh1k/roidetyolo
- **YOLO 공식 문서**: https://docs.ultralytics.com
- **Streamlit 문서**: https://docs.streamlit.io

---

## 👨‍🏫 강사 소개

**프로젝트 경험**:
- YOLO ROI 실시간 사람 감지 시스템 오픈소스 개발
- RK3588, Jetson Orin 플랫폼 최적화
- 백그라운드 스레드 아키텍처 설계
- 40-60% 리소스 절감 달성

**기술 스택**:
- Python, OpenCV, PyTorch
- YOLO, Ultralytics
- Streamlit, Flask
- Linux, ARM 플랫폼

---

## 📞 문의 및 지원

- **GitHub Issues**: https://github.com/futurianh1k/roidetyolo/issues
- **문서**: 프로젝트 내 13개의 상세 가이드 문서
- **예제 코드**: 12개의 Python 모듈

---

이 강의는 **실전 프로젝트 기반 학습**을 통해 YOLO ROI 시스템을 처음부터 끝까지 완성하는 것을 목표로 합니다! 🚀
