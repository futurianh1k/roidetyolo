# Part 3, 4, 5, 6: 웹 UI, 배포, 최적화, Q&A (60분)

---

## Part 3: Streamlit 웹 UI 개발 (30분)

### Slide 34: Streamlit 소개
```
🌐 Streamlit - Python으로 웹 앱 만들기

기존 방식 (Flask/Django):        Streamlit:
─────────────────────────────────────────────
HTML + CSS + JavaScript      ❌    Python만 ✅
복잡한 라우팅               ❌    자동 처리 ✅  
프론트엔드 지식 필요         ❌    불필요 ✅

# 3줄로 웹 앱 만들기
import streamlit as st
st.title("YOLO ROI Detector")
st.button("시작")

# 실행: streamlit run app.py
# 자동으로 브라우저 열림!

💡 특징:
• 반응형 UI 자동 생성
• 실시간 업데이트
• 위젯 풍부 (버튼, 슬라이더, 차트...)
• 배포 간편
```

**강의 스크립트**:
> "Streamlit은 Python만으로 웹 앱을 만드는 프레임워크입니다. HTML, CSS, JavaScript 몰라도 됩니다. [코드 예시] 단 3줄로 버튼이 있는 웹 페이지가 만들어집니다. streamlit run 명령어로 실행하면 자동으로 브라우저가 열립니다. 반응형 UI가 자동으로 생성되고, 코드를 바꾸면 즉시 반영됩니다. 데이터 과학자나 AI 엔지니어가 빠르게 프로토타입을 만들 때 최적입니다."

---

### Slide 35: Streamlit 레이아웃
```python
📐 Streamlit 레이아웃 구조

import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="YOLO ROI Detector",
    page_icon="🎥",
    layout="wide"  # 전체 너비 사용
)

# 타이틀
st.title("🎥 YOLO ROI 실시간 사람 감지 시스템")

# 사이드바
with st.sidebar:
    st.header("⚙️ 설정")
    camera = st.selectbox("카메라", [0, 1, 2])
    confidence = st.slider("신뢰도", 0.0, 1.0, 0.5)
    st.button("설정 저장")

# 탭
tab1, tab2, tab3 = st.tabs(["📝 ROI 편집", "📹 실시간 검출", "📊 통계"])

with tab1:
    st.write("ROI를 편집하세요")

with tab2:
    col1, col2 = st.columns([2, 1])  # 2:1 비율
    with col1:
        st.image("camera.jpg")
    with col2:
        st.metric("FPS", "30.0")

with tab3:
    st.line_chart(data)
```

**강의 스크립트**:
> "Streamlit 레이아웃은 매우 직관적입니다. [코드 설명] set_page_config로 페이지 제목과 아이콘을 설정합니다. layout='wide'는 전체 너비를 사용합니다. 사이드바는 with st.sidebar 블록으로 만듭니다. selectbox는 드롭다운, slider는 슬라이더입니다. tabs로 탭을 만들고, columns로 화면을 분할합니다. 2:1 비율이면 왼쪽이 오른쪽보다 두 배 큽니다. metric은 숫자를 크게 표시하는 위젯입니다. 이렇게 간단하게 복잡한 레이아웃을 만들 수 있습니다."

---

### Slide 36: Session State 관리
```python
🗂️ Session State - 상태 유지

# Streamlit은 코드가 실행될 때마다 새로 시작
# → 변수가 초기화됨!

# 해결: Session State 사용
if 'detector' not in st.session_state:
    st.session_state.detector = None

if 'roi_regions' not in st.session_state:
    st.session_state.roi_regions = []

if 'is_detecting' not in st.session_state:
    st.session_state.is_detecting = False

# 사용
if st.button("시작"):
    st.session_state.is_detecting = True
    st.session_state.detector = RealtimeDetector(...)
    st.session_state.detector.start()

if st.session_state.is_detecting:
    frame = st.session_state.detector.get_frame()
    st.image(frame)

💡 Session State는 사용자별로 독립적으로 유지됨
```

**강의 스크립트**:
> "Streamlit의 중요한 개념이 Session State입니다. Streamlit은 버튼을 누르거나 슬라이더를 움직일 때마다 코드를 처음부터 다시 실행합니다. 그러면 변수가 전부 초기화됩니다. Session State로 해결합니다. [코드 설명] if 'detector' not in st.session_state로 처음 한 번만 초기화합니다. 그 다음부터는 값이 유지됩니다. 시작 버튼을 누르면 detector를 만들고 시작합니다. is_detecting이 True면 계속 프레임을 가져와서 표시합니다. Session State는 각 사용자(브라우저 세션)별로 독립적입니다."

---

### Slide 37: ROI 편집 UI 실습
```python
📝 실습 5: Streamlit ROI 편집기 (10분)

파일: streamlit_roi_editor.py

import streamlit as st
import cv2
import numpy as np

st.set_page_config(page_title="ROI Editor", layout="wide")
st.title("🎥 ROI 편집기")

# Session State 초기화
if 'roi_points' not in st.session_state:
    st.session_state.roi_points = []

# 사이드바
with st.sidebar:
    st.header("📍 ROI 좌표 입력")
    x = st.number_input("X", 0, 1280, 100)
    y = st.number_input("Y", 0, 720, 100)
    
    if st.button("➕ 점 추가"):
        st.session_state.roi_points.append((x, y))
        st.success(f"점 추가: ({x}, {y})")
    
    if st.button("🗑️ 모두 지우기"):
        st.session_state.roi_points = []
    
    if st.button("💾 ROI 저장"):
        st.success("ROI 저장됨!")

# 메인 영역
st.subheader("현재 ROI 점들:")
st.write(st.session_state.roi_points)

# 카메라 프레임 (가상)
frame = np.ones((720, 1280, 3), dtype=np.uint8) * 200

# ROI 그리기
if len(st.session_state.roi_points) >= 2:
    points = np.array(st.session_state.roi_points, dtype=np.int32)
    cv2.polylines(frame, [points], True, (0, 255, 0), 2)
    
    # 각 점에 번호 표시
    for i, (x, y) in enumerate(st.session_state.roi_points):
        cv2.circle(frame, (x, y), 5, (255, 0, 0), -1)
        cv2.putText(frame, str(i), (x+10, y+10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

st.image(frame, width='stretch')

🎯 목표: Streamlit으로 ROI 편집 UI 만들기
⏱️ 시간: 10분
```

**강의 스크립트**:
> "Streamlit으로 ROI 편집기를 만들어봅시다. [코드 설명] 사이드바에 X, Y 좌표 입력 필드를 만들고, 점 추가 버튼을 누르면 session_state.roi_points에 추가됩니다. 메인 영역에는 점 목록을 표시하고, 가상의 프레임에 ROI를 그립니다. polylines로 선을 긋고, circle로 점을 표시합니다. width='stretch'는 화면 너비에 맞춥니다. 10분 동안 구현하고 실행해보세요. 점을 추가하면 실시간으로 ROI가 그려지는 것을 볼 수 있습니다!"

[10분 실습 시간]

---

### Slide 38: 실시간 검출 대시보드
```python
📊 실시간 검출 대시보드 구현

import streamlit as st
import time

# 탭 구성
tab1, tab2 = st.tabs(["📹 실시간 검출", "📊 통계"])

with tab1:
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("카메라 화면")
        video_placeholder = st.empty()
        fps_text = st.empty()
    
    with col2:
        st.subheader("ROI 상태")
        roi_status = st.empty()
        
        if st.button("🟢 시작"):
            st.session_state.is_detecting = True
            st.session_state.detector.start()
        
        if st.button("🔴 중지"):
            st.session_state.is_detecting = False
            st.session_state.detector.stop()
    
    # 실시간 업데이트 루프
    while st.session_state.is_detecting:
        # 프레임 가져오기
        frame = st.session_state.detector.get_frame()
        if frame is not None:
            video_placeholder.image(frame, width='stretch')
        
        # FPS 표시
        fps = st.session_state.detector.fps
        fps_text.caption(f"FPS: {fps:.1f}")
        
        # ROI 상태
        stats = st.session_state.detector.get_stats()
        roi_status.json(stats)  # JSON 형식으로 표시
        
        time.sleep(0.03)  # 30 FPS

with tab2:
    st.subheader("📈 검출 통계")
    
    # 메트릭 표시
    col1, col2, col3 = st.columns(3)
    col1.metric("총 검출", "127회")
    col2.metric("평균 FPS", "28.5")
    col3.metric("가동 시간", "1시간 23분")
    
    # 이벤트 로그
    st.subheader("📜 최근 이벤트")
    events = st.session_state.detector.get_events()
    st.dataframe(events)  # 테이블로 표시
```

**강의 스크립트**:
> "실시간 검출 대시보드입니다. [코드 설명] 두 개 탭으로 나눕니다. 첫 번째 탭은 실시간 검출입니다. 3:1 비율로 나눠서 왼쪽에 카메라 화면, 오른쪽에 ROI 상태와 버튼을 배치합니다. empty는 나중에 내용을 넣을 빈 공간입니다. 시작 버튼을 누르면 detector를 시작하고, while 루프에서 계속 프레임을 가져와서 표시합니다. json 메서드는 딕셔너리를 JSON 형식으로 예쁘게 표시합니다. 두 번째 탭은 통계입니다. metric으로 큰 숫자를 표시하고, dataframe으로 이벤트 로그를 테이블로 보여줍니다. 이렇게 하면 전문적인 대시보드가 완성됩니다."

---

## Part 4: 플랫폼별 배포 (20분)

### Slide 39: 플랫폼 개요
```
🚀 지원하는 플랫폼

┌─────────────────────────────────────────────┐
│ x86_64 (일반 PC/노트북)                      │
│  • CPU: Intel/AMD                           │
│  • 추론: PyTorch CPU                        │
│  • 성능: 10-15 FPS (YOLOv8n)                │
│  • 용도: 개발, 테스트                       │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ RK3588 (Rockchip ARM)                       │
│  • CPU: ARM Cortex-A76/A55                  │
│  • 추론: CPU (NPU 선택)                     │
│  • 성능: 5-8 FPS                            │
│  • 용도: 저전력 엣지 디바이스               │
│  • 특징: V4L2 백엔드 필수                   │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Jetson Orin (NVIDIA)                        │
│  • GPU: Ampere (CUDA 12.2)                  │
│  • 추론: GPU + TensorRT                     │
│  • 성능: 30-60 FPS (YOLOv8n)                │
│  • 용도: 고성능 엣지 AI                     │
│  • 특징: 2-3배 속도 향상 가능               │
└─────────────────────────────────────────────┘
```

**강의 스크립트**:
> "세 가지 플랫폼을 지원합니다. x86_64는 여러분의 일반 PC나 노트북입니다. CPU로 추론하고 10-15 FPS 나옵니다. 개발과 테스트용으로 적합합니다. RK3588은 Rockchip의 ARM 프로세서입니다. 저전력으로 작동하고 5-8 FPS 나옵니다. 엣지 디바이스에 적합합니다. V4L2 백엔드를 사용해야 카메라가 인식됩니다. Jetson Orin은 NVIDIA의 엣지 AI 플랫폼입니다. 강력한 GPU가 있어서 30-60 FPS가 나옵니다. TensorRT를 사용하면 2-3배 더 빠릅니다. 고성능이 필요한 응용에 최적입니다."

---

### Slide 40: x86_64 설치
```bash
💻 x86_64 (일반 PC) 설치

# 1. Python 환경 확인
python3 --version  # 3.8-3.11

# 2. 패키지 설치
pip install -r requirements.txt

# 주요 패키지:
# - ultralytics (YOLO)
# - opencv-python (카메라)
# - streamlit (UI)
# - numpy, requests

# 3. 카메라 테스트
python test_camera_detection.py

# 4. Streamlit 앱 실행
streamlit run streamlit_app.py

# 5. 브라우저 자동 열림
# → http://localhost:8501

✅ 가장 간단한 환경!
```

**강의 스크립트**:
> "x86_64 설치는 가장 간단합니다. Python 버전만 확인하고, requirements.txt로 패키지를 설치하고, 카메라를 테스트하고, Streamlit을 실행하면 끝입니다. 브라우저가 자동으로 열리고 localhost:8501로 접속됩니다. 여러분 대부분이 이 환경에서 개발할 겁니다."

---

### Slide 41: RK3588 설치
```bash
🔧 RK3588 (Rockchip ARM) 설치

# 1. 카메라 권한 확인 (중요!)
./check_camera_permissions.sh

# 출력 확인:
# ❌ 권한 없음 → sudo usermod -aG video $USER
# ✅ 권한 있음 → 바로 진행

# 2. 패키지 설치
pip install -r requirements.txt

# 3. V4L2 백엔드 확인
python test_camera_detection.py
# "V4L2" 백엔드가 표시되어야 함

# 4. config.json 수정
{
  "camera_source": 0,
  "frame_width": 640,   # 해상도 낮춰서 성능 향상
  "frame_height": 480,
  "detection_interval_seconds": 2.0  # 2초마다 추론
}

# 5. 실행
streamlit run streamlit_app.py

⚠️ 주의: 해상도와 탐지 간격 조정 필수!
```

**강의 스크립트**:
> "RK3588은 몇 가지 추가 설정이 필요합니다. 첫째, 카메라 권한입니다. check_camera_permissions.sh 스크립트로 확인하고, 권한이 없으면 usermod 명령어로 video 그룹에 추가합니다. 둘째, V4L2 백엔드를 사용해야 합니다. test_camera_detection에서 확인할 수 있습니다. 셋째, config.json에서 해상도를 640x480으로 낮추고, 탐지 간격을 2초로 늘려서 성능을 확보합니다. 이렇게 하면 RK3588에서도 부드럽게 작동합니다."

---

### Slide 42: Jetson Orin 설치 & TensorRT
```bash
🚀 Jetson Orin (NVIDIA) 설치 및 최적화

# 1. Jetson 전용 PyTorch 설치
pip install https://developer.download.nvidia.com/compute/redist/jp/v60/pytorch/torch-2.4.0a0+f70bd71a48.nv24.06.15634931-cp310-cp310-linux_aarch64.whl

# 2. 패키지 설치
pip install -r requirements_jetson.txt

# 3. TensorRT 엔진 변환 (2-3배 속도 향상!)
python convert_to_tensorrt.py

# 코드:
from ultralytics import YOLO
model = YOLO('yolov8n.pt')
model.export(format='engine', half=True)  # FP16
# → yolov8n.engine 생성

# 4. config.json 수정
{
  "yolo_model": "yolov8n.engine",  # TensorRT 엔진 사용
  "frame_width": 1280,
  "frame_height": 720,
  "detection_interval_seconds": 1.0
}

# 5. 성능 모드 설정
sudo nvpmodel -m 0      # 최대 성능 모드
sudo jetson_clocks      # 클럭 고정

# 6. 실행
streamlit run streamlit_app.py

⚡ 성능:
• Orin Nano: 30-40 FPS → 60-80 FPS (TensorRT)
• AGX Orin: 50-60 FPS → 100-120 FPS (TensorRT)
```

**강의 스크립트**:
> "Jetson Orin은 최고 성능을 뽑아낼 수 있습니다. Jetson 전용 PyTorch 휠을 설치하고, TensorRT 엔진으로 변환하는 게 핵심입니다. [TensorRT 변환 설명] model.export로 .engine 파일을 만듭니다. half=True는 FP16 정밀도를 사용한다는 뜻입니다. 정확도는 거의 동일하지만 속도가 2배 빨라집니다. config.json에서 엔진 파일을 사용하도록 설정합니다. nvpmodel과 jetson_clocks로 성능 모드를 켭니다. 이렇게 하면 Orin Nano에서 60-80 FPS, AGX Orin에서 100-120 FPS가 나옵니다. 실시간 멀티 카메라도 가능합니다."

---

## Part 5: 고급 기능 & 문제 해결 (20분)

### Slide 43: 성능 최적화 전략
```
⚡ 성능 최적화 체크리스트

1️⃣ 탐지 간격 조정 (40-60% 리소스 절감)
   detection_interval_seconds: 1.0 ~ 5.0
   • 1초: 균형 (권장)
   • 2초: 중간 절감
   • 5초: 최대 절감

2️⃣ 해상도 튜닝
   • 1280x720: 표준 (권장)
   • 640x480: 저성능 환경
   • 1920x1080: 고해상도 (고성능만)

3️⃣ Confidence Threshold
   • 0.3: 더 많이 검출 (오탐지 ↑)
   • 0.5: 균형 (권장)
   • 0.7: 확실한 것만 (놓침 ↑)

4️⃣ YOLO 모델 선택
   • yolov8n.pt: 가장 빠름 (권장)
   • yolov8s.pt: 정확도 ↑
   • yolov8m.pt: 고성능 환경만

5️⃣ 프레임 스킵
   # 매 2번째 프레임만 처리
   frame_count = 0
   if frame_count % 2 == 0:
       results = model(frame)
   frame_count += 1

6️⃣ TensorRT 변환 (Jetson)
   • 2-3배 속도 향상
   • FP16 정밀도 권장
```

**강의 스크립트**:
> "성능 최적화는 6가지 전략이 있습니다. 첫째, 탐지 간격입니다. 1초면 적당하고, 5초면 최대 절감입니다. 둘째, 해상도입니다. 720p가 표준이고, 저성능 환경은 480p로 낮춥니다. 셋째, confidence threshold입니다. 0.5가 균형점입니다. 낮추면 더 많이 검출하지만 오탐지가 늘고, 높이면 확실한 것만 검출합니다. 넷째, YOLO 모델입니다. nano가 가장 빠르고 권장합니다. 다섯째, 프레임 스킵입니다. 매 두 번째 프레임만 처리하면 절반으로 줄입니다. 여섯째, Jetson에서는 TensorRT를 꼭 사용하세요. 2-3배 빨라집니다."

---

### Slide 44: 일반적인 문제 해결
```
🔧 문제 해결 가이드

❌ 문제: "RuntimeError: Numpy is not available"
✅ 해결:
   pip uninstall -y numpy
   pip install "numpy>=1.24.0,<2.0.0"
   pip install --upgrade ultralytics

❌ 문제: 카메라를 찾을 수 없습니다
✅ 해결:
   1. USB 케이블 확인
   2. 다른 프로그램에서 사용 중인지 확인
   3. Linux: ./check_camera_permissions.sh
   4. camera_source를 0, 1, 2로 바꿔보기

❌ 문제: FPS가 너무 낮습니다 (< 5 FPS)
✅ 해결:
   1. 해상도 낮추기 (640x480)
   2. detection_interval 늘리기 (2.0~5.0)
   3. yolov8n.pt 사용 확인
   4. Jetson: TensorRT 변환

❌ 문제: API 전송 실패
✅ 해결:
   1. API 엔드포인트 확인
   2. 네트워크 연결 확인
   3. Timeout 설정 늘리기 (5초 → 10초)
   4. 에러 로그 확인

❌ 문제: Streamlit 느림/멈춤
✅ 해결:
   1. 백그라운드 스레드 확인
   2. Queue 크기 확인 (maxsize=2)
   3. 브라우저 캐시 지우기
   4. streamlit run --server.runOnSave false

📚 상세 문서:
   • FIX_NUMPY_ERROR.md
   • TROUBLESHOOTING.md
   • PERFORMANCE_OPTIMIZATION.md
```

**강의 스크립트**:
> "자주 발생하는 문제들과 해결책입니다. [각 문제 설명] NumPy 오류는 버전 충돌입니다. 2.0 미만으로 재설치하세요. 카메라 미감지는 USB 케이블, 권한, 카메라 번호를 확인합니다. FPS가 낮으면 해상도를 낮추고 탐지 간격을 늘립니다. API 실패는 엔드포인트와 네트워크를 확인합니다. Streamlit이 느리면 백그라운드 스레드와 Queue를 점검합니다. 자세한 내용은 프로젝트 문서들을 참고하세요."

---

## Part 6: 마무리 & Q&A (10분)

### Slide 45: 프로젝트 요약
```
✅ 오늘 만든 것

🎯 완성된 시스템:
  • YOLO 기반 실시간 사람 탐지
  • Polygon ROI 영역 설정
  • Dwell Time 기반 이벤트
  • JSON API 통합
  • Streamlit 웹 대시보드
  • 멀티플랫폼 지원

📊 성능 지표:
  • x86_64: 10-15 FPS
  • RK3588: 5-8 FPS
  • Jetson Orin: 30-60 FPS
  • TensorRT: 2-3배 향상

🔧 최적화:
  • 40-60% 리소스 절감
  • 백그라운드 스레드
  • Queue 기반 통신

📚 문서:
  • 13개 가이드 문서
  • 12개 Python 모듈
  • 3,910 라인 코드

🌐 GitHub:
  https://github.com/futurianh1k/roidetyolo
```

**강의 스크립트**:
> "오늘 3시간 동안 정말 많은 것을 배웠습니다. 여러분은 이제 YOLO로 실시간 사람을 탐지하고, ROI로 특정 영역만 감시하고, Dwell Time으로 오탐지를 줄이고, API로 이벤트를 전송하고, Streamlit으로 웹 대시보드를 만들 수 있습니다. 세 가지 플랫폼에 배포할 수 있고, 성능을 최적화해서 리소스를 절반 가까이 줄일 수 있습니다. 모든 코드와 문서는 GitHub에 있습니다. 13개의 상세 가이드가 있으니 나중에 참고하세요."

---

### Slide 46: 확장 아이디어
```
💡 프로젝트 확장 아이디어

1️⃣ 추가 기능:
   • 얼굴 인식 (Face Recognition)
   • 자세 추정 (Pose Estimation)
   • 객체 추적 (Object Tracking)
   • 다중 카메라 지원

2️⃣ 다른 객체 감지:
   • 차량 (Car, Truck)
   • 동물 (Dog, Cat)
   • 물체 (Backpack, Handbag)
   • COCO 80개 클래스 모두

3️⃣ 고급 분석:
   • 열 지도 (Heatmap)
   • 동선 추적 (Trajectory)
   • 체류 시간 분석
   • 군중 밀도 (Crowd Density)

4️⃣ 알림 시스템:
   • 이메일 알림
   • SMS/전화 알림
   • Slack/Discord 통합
   • 모바일 푸시 (FCM)

5️⃣ 저장 및 분석:
   • 이벤트 DB 저장 (PostgreSQL)
   • 영상 녹화 (FFmpeg)
   • 통계 리포트 (PDF)
   • 대시보드 (Grafana)

🚀 여러분의 창의력으로 확장하세요!
```

**강의 스크립트**:
> "이 시스템을 기반으로 다양하게 확장할 수 있습니다. 얼굴 인식을 추가해서 특정 사람을 찾거나, 자세 추정으로 행동을 분석하거나, 다중 카메라를 지원할 수 있습니다. 사람 외에 차량, 동물, 물체도 감지할 수 있습니다. 열 지도로 어디가 가장 붐비는지 보거나, 동선을 추적해서 고객 행동을 분석할 수 있습니다. 이메일, SMS, Slack으로 알림을 보내거나, 데이터베이스에 저장해서 장기 분석을 할 수도 있습니다. 여러분의 창의력으로 무한히 확장하세요!"

---

### Slide 47: 추가 학습 자료
```
📚 추가 학습 자료

공식 문서:
  • YOLO: https://docs.ultralytics.com
  • Streamlit: https://docs.streamlit.io
  • OpenCV: https://docs.opencv.org

온라인 강의:
  • Ultralytics YOLO Course (무료)
  • Coursera: Computer Vision
  • Udemy: OpenCV with Python

커뮤니티:
  • GitHub Discussions
  • Stack Overflow
  • Reddit: r/computervision
  • Discord: Ultralytics

논문:
  • YOLOv8 Technical Report
  • Real-Time Object Detection Survey
  • Edge AI Deployment Best Practices

프로젝트 예제:
  • GitHub Awesome YOLO
  • Ultralytics Solutions
  • OpenCV AI Kit Examples

💬 질문이 있으면 GitHub Issues에 올려주세요!
   https://github.com/futurianh1k/roidetyolo/issues
```

**강의 스크립트**:
> "더 학습하고 싶은 분들을 위한 자료입니다. 공식 문서는 가장 정확하고 최신 정보를 제공합니다. 온라인 강의는 Ultralytics 무료 강좌가 좋고, Coursera와 Udemy에도 좋은 강의들이 많습니다. 커뮤니티에 참여해서 질문하고 답변도 해보세요. 논문을 읽으면 더 깊이 이해할 수 있습니다. 프로젝트 예제들을 보면 영감을 얻을 수 있습니다. 질문이 있으면 GitHub Issues에 올려주세요. 제가 답변하겠습니다!"

---

### Slide 48: Q&A
```
💬 Q&A 시간

자주 묻는 질문:

Q: 상업적으로 사용해도 되나요?
A: YOLOv8은 AGPL-3.0 라이선스입니다.
   상업 사용은 Ultralytics 라이선스 구매 필요.
   자세한 내용: https://ultralytics.com/license

Q: 다른 객체도 감지할 수 있나요?
A: 네! COCO 80개 클래스 모두 가능합니다.
   cls == 0 (person)을 다른 번호로 바꾸면 됩니다.

Q: 정확도를 높이려면?
A: 1) 더 큰 모델 (yolov8m, yolov8l)
   2) Fine-tuning (자신의 데이터로 재학습)
   3) 해상도 높이기

Q: 여러 카메라를 동시에?
A: RealtimeDetector를 여러 개 만들면 됩니다.
   각각 다른 카메라 번호 사용.

Q: 클라우드 배포는?
A: Docker + AWS/GCP/Azure 가능
   Streamlit Cloud도 지원

📝 더 궁금한 점이 있으신가요?
```

**강의 스크립트**:
> "이제 여러분의 질문에 답변하는 시간입니다. [자주 묻는 질문 설명] 상업적 사용은 Ultralytics 라이선스를 구매해야 합니다. 다른 객체 감지는 클래스 번호만 바꾸면 됩니다. 정확도를 높이려면 더 큰 모델을 쓰거나 파인튜닝을 하면 됩니다. 여러 카메라는 탐지기를 여러 개 만들면 됩니다. 클라우드 배포도 가능합니다. 자, 이제 여러분의 질문을 받겠습니다. 무엇이든 물어보세요!"

---

### Slide 49: 마무리
```
🎓 강의 마무리

감사합니다! 🙏

오늘 배운 것:
  ✅ YOLO 객체 탐지 원리와 실전
  ✅ ROI 시스템 설계와 구현
  ✅ Streamlit 웹 앱 개발
  ✅ 멀티플랫폼 배포
  ✅ 성능 최적화 기법

여러분은 이제:
  🚀 실시간 AI 시스템을 만들 수 있습니다
  💻 엣지 디바이스에 배포할 수 있습니다
  🎯 실전 프로젝트를 시작할 수 있습니다

다음 단계:
  1. 프로젝트 코드 실행 및 테스트
  2. 자신의 Use Case에 맞게 수정
  3. 추가 기능 구현
  4. 커뮤니티에 공유

📦 GitHub: https://github.com/futurianh1k/roidetyolo
📧 문의: GitHub Issues
🌟 Star 부탁드립니다!

계속 학습하고, 만들고, 공유하세요! 💪
```

**강의 스크립트**:
> "3시간 강의가 끝났습니다! 정말 수고하셨습니다. 오늘 여러분은 YOLO 원리부터 실전 배포까지 모든 것을 배웠습니다. 이제 여러분은 실시간 AI 시스템을 처음부터 끝까지 만들 수 있습니다. 다음 단계는 직접 실행해보고, 여러분의 문제에 맞게 수정하고, 새로운 기능을 추가하는 겁니다. 그리고 커뮤니티에 공유해서 다른 사람들도 배울 수 있게 해주세요. GitHub에 Star도 눌러주시면 감사하겠습니다. 계속 학습하고, 만들고, 공유하세요. 여러분의 성공을 응원합니다! 감사합니다!"

---

**Part 3, 4, 5, 6 슬라이드 종료 - 총 16장 (Slide 34-49)**
**전체 강의 총 49장 슬라이드 완성!**
