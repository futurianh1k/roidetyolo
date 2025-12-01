# Part 2: 핵심 기능 구현 (80분)

---

## Slide 15: Part 2 개요
```
💻 Part 2: 핵심 기능 구현 (80분)

이번 파트에서 만들 것:

┌──────────────────────────────────────┐
│  📹 카메라 → YOLO → ROI → API       │
└──────────────────────────────────────┘

Module 2.1: 카메라 & YOLO 통합 (20분)
  → 실시간 사람 탐지 구현

Module 2.2: ROI 시스템 (25분)
  → 특정 영역만 감시

Module 2.3: 상태 관리 & API (20분)
  → Dwell Time & 이벤트 전송

Module 2.4: 백그라운드 스레드 (15분)
  → 성능 최적화

⚡ 실습 중심! 직접 코드를 작성합니다
```

**강의 스크립트**:
> "Part 2는 오늘 강의의 핵심입니다. 80분 동안 실제로 작동하는 시스템을 처음부터 만들어봅니다. 4개 모듈로 구성되어 있고, 각 모듈마다 실습 시간이 포함되어 있습니다. 첫 번째 모듈에서는 카메라와 YOLO를 연결해서 실시간으로 사람을 탐지합니다. 두 번째는 ROI, 즉 특정 영역만 감시하는 시스템을 만듭니다. 세 번째는 상태를 추적하고 API로 전송하는 기능입니다. 마지막은 백그라운드 스레드로 성능을 최적화합니다. 자, 시작해봅시다!"

---

## Module 2.1: 카메라 & YOLO 통합

### Slide 16: OpenCV 카메라 기초
```python
🎥 OpenCV 카메라 초기화

# 기본 카메라 열기
import cv2

cap = cv2.VideoCapture(0)  # 0 = 첫 번째 카메라

# 해상도 설정
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# 프레임 읽기
ret, frame = cap.read()

if ret:
    print(f"프레임 크기: {frame.shape}")  # (720, 1280, 3)
    # frame은 NumPy 배열 (높이, 너비, BGR)
else:
    print("프레임 읽기 실패!")

# 카메라 해제
cap.release()
```

**강의 스크립트**:
> "OpenCV로 카메라를 다루는 것은 매우 간단합니다. VideoCapture에 카메라 번호를 넣으면 됩니다. 보통 0이 메인 카메라입니다. set 메서드로 해상도를 1280x720으로 설정합니다. read 메서드를 호출하면 프레임을 하나 읽어옵니다. ret은 성공 여부, frame은 실제 이미지 데이터입니다. frame은 NumPy 배열로, 높이, 너비, 색상 채널 순서입니다. 중요한 점은 OpenCV는 BGR 순서를 사용한다는 것입니다. 다 사용하고 나면 release로 카메라를 해제해야 합니다."

---

### Slide 17: YOLO 모델 로딩
```python
🤖 YOLO 모델 초기화

from ultralytics import YOLO

# YOLOv8 nano 모델 로드 (가장 가벼운 버전)
model = YOLO('yolov8n.pt')

# 첫 실행 시 자동 다운로드:
# Downloading yolov8n.pt ... 6.2MB

# 다른 모델 옵션:
# yolov8n.pt  - Nano   (가장 빠름, 정확도 낮음)
# yolov8s.pt  - Small
# yolov8m.pt  - Medium
# yolov8l.pt  - Large
# yolov8x.pt  - XLarge (가장 느림, 정확도 높음)

💡 권장: yolov8n.pt (실시간 처리에 최적)
```

**강의 스크립트**:
> "YOLO 모델을 로딩하는 것도 한 줄이면 됩니다. ultralytics 패키지에서 YOLO 클래스를 가져와서, 모델 파일 이름을 넣으면 됩니다. 우리는 yolov8n, nano 버전을 사용합니다. 이게 가장 가볍고 빠릅니다. 처음 실행하면 자동으로 인터넷에서 다운로드하는데, 6.2MB밖에 안 됩니다. 다른 옵션으로는 s, m, l, x 버전이 있는데, 뒤로 갈수록 더 정확하지만 느립니다. 실시간 처리에는 nano가 최적입니다."

---

### Slide 18: YOLO로 사람 탐지
```python
👤 실시간 사람 탐지

# 프레임에서 객체 탐지
results = model(frame, verbose=False)

# 결과 파싱
for result in results:
    boxes = result.boxes  # 검출된 모든 박스
    
    for box in boxes:
        # 클래스 ID (0 = person in COCO dataset)
        cls = int(box.cls[0])
        
        # 신뢰도
        conf = float(box.conf[0])
        
        # 바운딩 박스 좌표 (x1, y1, x2, y2)
        bbox = box.xyxy[0].cpu().numpy()
        x1, y1, x2, y2 = map(int, bbox)
        
        # Person 클래스만 필터링
        if cls == 0 and conf >= 0.5:  # confidence >= 50%
            print(f"사람 발견! 신뢰도: {conf:.2f}")
            print(f"위치: ({x1}, {y1}) - ({x2}, {y2})")
```

**강의 스크립트**:
> "YOLO로 탐지하는 것도 아주 간단합니다. model에 frame을 넣으면 results가 나옵니다. verbose=False는 로그를 끄는 옵션입니다. 결과를 파싱할 때는 먼저 boxes를 가져오고, 각 box마다 클래스 ID, 신뢰도, 좌표를 추출합니다. COCO 데이터셋에서 0번이 'person' 클래스입니다. cls가 0이고 신뢰도가 0.5 이상인 것만 필터링합니다. 즉, 50% 이상 확신하는 사람만 검출하는 겁니다. bbox는 CPU로 가져와서 NumPy 배열로 변환하고, x1, y1은 좌상단, x2, y2는 우하단 좌표입니다."

---

### Slide 19: 실습 1 - 기본 사람 탐지기
```python
📝 실습 1: 기본 사람 탐지기 만들기 (10분)

파일: basic_detector.py

import cv2
from ultralytics import YOLO

# 1. 카메라와 YOLO 초기화
cap = cv2.VideoCapture(0)
model = YOLO('yolov8n.pt')

while True:
    # 2. 프레임 읽기
    ret, frame = cap.read()
    if not ret:
        break
    
    # 3. YOLO 추론
    results = model(frame, verbose=False)
    
    # 4. 사람만 필터링 및 박스 그리기
    for result in results:
        boxes = result.boxes
        for box in boxes:
            if int(box.cls[0]) == 0:  # Person
                bbox = box.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = map(int, bbox)
                conf = float(box.conf[0])
                
                # 파란색 박스 그리기
                cv2.rectangle(frame, (x1, y1), (x2, y2), 
                            (255, 0, 0), 2)
                cv2.putText(frame, f'Person {conf:.2f}',
                          (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX,
                          0.5, (255, 0, 0), 2)
    
    # 5. 화면 표시
    cv2.imshow('Person Detector', frame)
    
    # ESC 키로 종료
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()

🎯 목표: 카메라 화면에 사람 검출 박스 표시
⏱️ 시간: 10분
```

**강의 스크립트**:
> "자, 첫 번째 실습입니다. 10분 동안 기본 사람 탐지기를 만들어봅시다. [코드 설명] 카메라를 열고, YOLO 모델을 로딩하고, 무한 루프에서 프레임을 읽고, YOLO로 추론하고, person 클래스만 필터링해서 파란색 박스를 그립니다. 그리고 화면에 표시합니다. ESC 키를 누르면 종료됩니다. 이 코드를 basic_detector.py로 저장하고 실행해보세요. 카메라 앞에서 움직이면 여러분을 검출하는 것을 볼 수 있을 겁니다. 자, 시작하세요! 10분 드립니다."

[10분 실습 시간]

---

## Module 2.2: ROI 시스템 구현

### Slide 20: ROI란 무엇인가?
```
🎯 ROI (Region of Interest) - 관심 영역

전체 화면 감시 vs ROI 감시

❌ 전체 화면:              ✅ ROI만:
┌─────────────────┐        ┌─────────────────┐
│ 👤               │        │ ╔═══════╗       │
│                 │        │ ║  👤   ║       │
│                 │        │ ╚═══════╝       │
│        👤        │        │        👤        │
└─────────────────┘        └─────────────────┘
모든 사람 감지              ROI 안의 사람만 감지

💡 왜 ROI를 사용하나?
1️⃣ 불필요한 영역 무시 → 오탐지 감소
2️⃣ 특정 구역만 감시 → 목적에 맞는 감지
3️⃣ 여러 영역 독립적 관리 → 영역별 이벤트

📐 ROI 형태:
• Rectangle (직사각형) - 간단하지만 제한적
• Polygon (다각형) - 유연하고 정확 ✅
```

**강의 스크립트**:
> "ROI는 Region of Interest, 관심 영역을 의미합니다. 전체 화면을 다 감시하는 게 아니라, 우리가 관심 있는 특정 영역만 감시합니다. 왼쪽 그림처럼 전체를 보면 모든 사람이 검출되지만, 오른쪽처럼 ROI를 설정하면 그 안에 있는 사람만 검출됩니다. 왜 이렇게 할까요? 첫째, 불필요한 영역을 무시해서 오탐지를 줄입니다. 둘째, 특정 구역만 감시해서 목적에 맞는 감지를 합니다. 예를 들어 출입문만 감시하거나, 계산대 앞만 감시할 수 있습니다. 셋째, 여러 영역을 독립적으로 관리할 수 있습니다. ROI 형태는 직사각형과 다각형이 있는데, 우리는 더 유연한 다각형을 사용합니다."

---

### Slide 21: Point-in-Polygon 알고리즘
```python
📐 점이 다각형 내부에 있는지 확인

Ray Casting 알고리즘:

    점 ●────────────────→ (무한히 오른쪽으로 광선)
      ╱                      
     ╱ Polygon              교차 횟수 세기:
    ╱                       홀수 = 내부 ✅
   ╱                        짝수 = 외부 ❌
  ╱
 ╱

코드 구현:
def is_point_in_polygon(point, polygon):
    x, y = point
    n = len(polygon)
    inside = False
    
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    
    return inside

💡 OpenCV 제공: cv2.pointPolygonTest() 사용 권장
```

**강의 스크립트**:
> "점이 다각형 안에 있는지 확인하는 알고리즘은 Ray Casting이라고 합니다. 점에서 오른쪽으로 무한히 긴 광선을 쏴서, 다각형의 변과 몇 번 교차하는지 세는 겁니다. 홀수 번 교차하면 내부, 짝수 번이면 외부입니다. 직접 구현할 수도 있지만, OpenCV가 이미 pointPolygonTest 함수를 제공하니까 그걸 사용하는 게 더 간단하고 빠릅니다."

---

### Slide 22: 사람이 ROI 안에 있는지 확인
```python
👤 사람이 ROI 내부에 있는지 확인

def is_person_in_roi(bbox, roi_polygon):
    """
    BBox의 중심점이 ROI 내부에 있는지 확인
    
    Args:
        bbox: (x1, y1, x2, y2) - 사람의 바운딩 박스
        roi_polygon: [(x, y), ...] - ROI 좌표 리스트
    
    Returns:
        bool: True if 중심점이 ROI 내부
    """
    # BBox 중심점 계산
    x1, y1, x2, y2 = bbox
    center_x = int((x1 + x2) / 2)
    center_y = int((y1 + y2) / 2)
    center = (center_x, center_y)
    
    # OpenCV로 점-다각형 테스트
    result = cv2.pointPolygonTest(
        np.array(roi_polygon, dtype=np.int32),
        center,
        False  # 거리 계산 안 함 (속도 향상)
    )
    
    return result >= 0  # 0 이상이면 내부 or 경계

# 사용 예:
bbox = (100, 100, 200, 300)  # 검출된 사람
roi = [(50, 50), (300, 50), (300, 400), (50, 400)]  # 사각형 ROI

if is_person_in_roi(bbox, roi):
    print("✅ ROI 안에 사람이 있습니다!")
```

**강의 스크립트**:
> "사람의 바운딩 박스가 ROI 안에 있는지 확인하는 방법입니다. 바운딩 박스의 중심점을 계산합니다. x 좌표는 x1과 x2의 평균, y 좌표는 y1과 y2의 평균입니다. 그리고 OpenCV의 pointPolygonTest 함수를 호출합니다. ROI 좌표를 NumPy 배열로 변환하고, 중심점을 넣고, False는 거리 계산을 안 한다는 의미입니다. 결과가 0 이상이면 내부거나 경계선 위에 있다는 뜻입니다. 음수면 외부입니다. 이렇게 하면 사람이 ROI 안에 있는지 쉽게 확인할 수 있습니다."

---

### Slide 23: 여러 ROI 관리
```python
🗂️ 여러 ROI 동시 관리

# ROI 데이터 구조
roi_regions = [
    {
        'id': 'ROI1',
        'points': [(100, 100), (400, 100), (400, 400), (100, 400)],
        'description': '출입문 구역'
    },
    {
        'id': 'ROI2',
        'points': [(600, 100), (900, 100), (900, 400), (600, 400)],
        'description': '계산대 구역'
    },
    {
        'id': 'ROI3',
        'points': [(300, 500), (700, 500), (700, 700), (300, 700)],
        'description': '대기 구역'
    }
]

# 각 ROI 확인
for roi in roi_regions:
    person_detected = False
    
    for bbox in detected_persons:
        if is_person_in_roi(bbox, roi['points']):
            person_detected = True
            print(f"✅ {roi['id']}: 사람 검출!")
            break
    
    if not person_detected:
        print(f"❌ {roi['id']}: 사람 없음")

💡 ROI별 독립적인 상태 관리 가능
```

**강의 스크립트**:
> "여러 ROI를 동시에 관리하는 방법입니다. ROI는 딕셔너리 리스트로 저장합니다. 각 ROI는 ID, 좌표 points, 설명 description을 가집니다. 이 예제에서는 출입문, 계산대, 대기 구역 세 곳을 감시합니다. 각 ROI마다 루프를 돌면서, 검출된 모든 사람의 바운딩 박스를 확인합니다. 한 명이라도 ROI 안에 있으면 person_detected를 True로 설정하고 break합니다. 이렇게 하면 ROI별로 독립적인 상태를 관리할 수 있습니다. 예를 들어 ROI1에는 사람이 있지만 ROI2에는 없을 수 있죠."

---

### Slide 24: 실습 2 - ROI 시스템 구현
```python
📝 실습 2: ROI 기반 탐지기 (15분)

파일: roi_detector.py

import cv2
import numpy as np
from ultralytics import YOLO

def is_person_in_roi(bbox, roi_points):
    x1, y1, x2, y2 = bbox
    center = (int((x1+x2)/2), int((y1+y2)/2))
    result = cv2.pointPolygonTest(
        np.array(roi_points, dtype=np.int32),
        center, False
    )
    return result >= 0

# ROI 정의 (화면 왼쪽 절반)
roi = [(0, 0), (640, 0), (640, 720), (0, 720)]

cap = cv2.VideoCapture(0)
model = YOLO('yolov8n.pt')

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # YOLO 추론
    results = model(frame, verbose=False)
    
    person_in_roi = False
    
    for result in results:
        for box in result.boxes:
            if int(box.cls[0]) == 0:  # Person
                bbox = box.xyxy[0].cpu().numpy()
                
                if is_person_in_roi(bbox, roi):
                    person_in_roi = True
                    # 녹색 박스
                    x1, y1, x2, y2 = map(int, bbox)
                    cv2.rectangle(frame, (x1, y1), (x2, y2),
                                (0, 255, 0), 2)
    
    # ROI 그리기 (녹색 = 검출, 빨간색 = 미검출)
    color = (0, 255, 0) if person_in_roi else (0, 0, 255)
    cv2.polylines(frame, [np.array(roi)], True, color, 2)
    
    cv2.imshow('ROI Detector', frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()

🎯 목표: ROI 안의 사람만 검출, ROI 색상 변경
⏱️ 시간: 15분
```

**강의 스크립트**:
> "두 번째 실습입니다. ROI 기반 탐지기를 만들어봅시다. [코드 설명] is_person_in_roi 함수를 먼저 정의합니다. ROI는 화면 왼쪽 절반로 설정했습니다. 메인 루프에서 YOLO로 사람을 찾고, ROI 안에 있는 사람만 녹색 박스로 표시합니다. ROI는 사람이 있으면 녹색, 없으면 빨간색으로 그립니다. polylines 함수로 다각형을 그립니다. 이 코드를 roi_detector.py로 저장하고 실행해보세요. 화면 왼쪽에 있을 때만 검출되고, 오른쪽으로 가면 검출되지 않는 것을 확인할 수 있습니다. 15분 드립니다!"

[15분 실습 시간]

---

## Module 2.3: 상태 관리 & API 연동

### Slide 25: Dwell Time 로직
```
⏱️ Dwell Time (체류 시간) 기반 이벤트

문제: 순간적인 검출로 이벤트 전송 → 오탐지

해결: 일정 시간 지속되어야 이벤트 전송

┌────────────────────────────────────────────┐
│  ROI 상태 변화 타임라인                     │
├────────────────────────────────────────────┤
│                                            │
│  0초  1초  2초  3초  4초  5초  6초  7초  8초│
│  │    │    │    │    │    │    │    │    ││
│  ✅──✅──✅──✅──✅──✅────────────────────────│
│  검출 시작         ▲                       │
│                5초 지속                    │
│              → 'present' API 전송          │
│                                            │
│  ──────────────────❌──❌──❌──────────────│
│                    미검출 시작  ▲          │
│                             3초 지속       │
│                           → 'absent' 전송  │
└────────────────────────────────────────────┘

💡 설정값:
• presence_threshold: 5초 (검출 지속)
• absence_threshold: 3초 (미검출 지속)
• count_interval: 1초 (상태 체크 간격)
```

**강의 스크립트**:
> "Dwell Time은 체류 시간을 의미합니다. 왜 필요할까요? 만약 순간적으로 검출될 때마다 이벤트를 보내면, 사람이 ROI를 스쳐 지나가기만 해도 알림이 갑니다. 그래서 일정 시간 지속되어야 이벤트를 보냅니다. [타임라인 설명] 사람이 검출되기 시작하면 타이머를 켭니다. 5초 동안 계속 검출되면 'present' 이벤트를 API로 전송합니다. 반대로 사람이 없어지면 또 타이머를 켭니다. 3초 동안 계속 없으면 'absent' 이벤트를 보냅니다. 이렇게 하면 오탐지를 크게 줄일 수 있습니다. 설정값은 presence_threshold 5초, absence_threshold 3초, 그리고 1초마다 상태를 체크합니다."

---

### Slide 26: ROI 상태 추적 구조
```python
🗂️ ROI별 상태 추적 데이터 구조

roi_states = {
    'ROI1': {
        'person_detected': False,           # 현재 검출 여부
        'detection_start_time': None,       # 검출 시작 시각
        'absence_start_time': None,         # 미검출 시작 시각
        'last_sent_status': None,           # 마지막 전송 상태
        'detection_count': 0,               # 총 검출 횟수
        'last_update': time.time()          # 마지막 업데이트 시각
    },
    'ROI2': {
        # ... 동일한 구조
    }
}

# 상태 업데이트 로직
def update_roi_state(roi_id, person_detected):
    state = roi_states[roi_id]
    current_time = time.time()
    
    if person_detected:
        # 사람 검출됨
        if not state['person_detected']:
            # 새로 검출 시작
            state['detection_start_time'] = current_time
            state['absence_start_time'] = None
        
        state['person_detected'] = True
        state['detection_count'] += 1
        
        # 5초 이상 지속 체크
        if state['detection_start_time']:
            duration = current_time - state['detection_start_time']
            if duration >= 5.0 and state['last_sent_status'] != 'present':
                send_api_event(roi_id, 'present')
                state['last_sent_status'] = 'present'
    
    else:
        # 사람 없음
        if state['person_detected']:
            # 새로 사라짐
            state['absence_start_time'] = current_time
            state['detection_start_time'] = None
        
        state['person_detected'] = False
        
        # 3초 이상 지속 체크
        if state['absence_start_time']:
            duration = current_time - state['absence_start_time']
            if duration >= 3.0 and state['last_sent_status'] != 'absent':
                send_api_event(roi_id, 'absent')
                state['last_sent_status'] = 'absent'
    
    state['last_update'] = current_time
```

**강의 스크립트**:
> "ROI별로 상태를 추적하는 데이터 구조입니다. 각 ROI는 6개 정보를 가집니다. person_detected는 현재 검출 여부, detection_start_time은 검출이 시작된 시각, absence_start_time은 사라진 시각, last_sent_status는 마지막으로 보낸 이벤트, detection_count는 총 검출 횟수, last_update는 마지막 업데이트 시각입니다. [update_roi_state 함수 설명] 사람이 검출되면, 이전에 없었다면 detection_start_time을 현재 시각으로 설정합니다. 그리고 5초 이상 지속되었는지 확인하고, present를 보낸 적이 없으면 API로 전송합니다. 반대로 사람이 없으면, 이전에 있었다면 absence_start_time을 설정하고, 3초 이상 지속되면 absent를 전송합니다."

---

### Slide 27: API 이벤트 전송
```python
📡 JSON API 이벤트 전송

import requests
from datetime import datetime

def send_api_event(roi_id, status):
    """
    ROI 이벤트를 API로 전송
    
    Args:
        roi_id: ROI 식별자 (예: 'ROI1')
        status: 'present' or 'absent'
    """
    api_endpoint = "http://10.10.11.23:10008/api/emergency"
    
    # JSON 페이로드 구성
    payload = {
        "eventId": f"{roi_id}_{int(time.time() * 1000)}",
        "fcmMessageId": f"fcm_{int(time.time() * 1000)}",
        "imageUrl": "",  # 선택사항
        "status": 1 if status == 'present' else 0,
        "createdAt": datetime.now().isoformat(),
        "watchId": "watch_1760663070591_8022",
        "roiId": roi_id,
        "detectionType": "person"
    }
    
    try:
        response = requests.post(
            api_endpoint,
            json=payload,
            timeout=5  # 5초 타임아웃
        )
        
        if response.status_code == 200:
            print(f"✅ API 전송 성공: {roi_id} - {status}")
        else:
            print(f"❌ API 오류: {response.status_code}")
    
    except requests.exceptions.Timeout:
        print(f"⏱️ API 타임아웃: {api_endpoint}")
    
    except requests.exceptions.ConnectionError:
        print(f"🔌 API 연결 실패: {api_endpoint}")
    
    except Exception as e:
        print(f"❌ API 전송 오류: {e}")

💡 에러 핸들링:
• Timeout: 5초 이내 응답 없으면 실패
• ConnectionError: 네트워크 문제
• 모든 예외 처리로 시스템 안정성 보장
```

**강의 스크립트**:
> "API로 이벤트를 전송하는 함수입니다. requests 라이브러리를 사용합니다. [payload 설명] JSON 페이로드는 eventId, fcmMessageId, status, createdAt, watchId, roiId 등을 포함합니다. status는 present면 1, absent면 0입니다. try-except로 에러를 처리합니다. Timeout은 5초 이내 응답이 없을 때, ConnectionError는 네트워크가 끊겼을 때 발생합니다. 모든 예외를 잡아서 시스템이 중단되지 않도록 합니다. 이렇게 하면 API 서버가 다운되어도 감지 시스템은 계속 작동합니다."

---

### Slide 28: 실습 3 - 상태 관리 & API
```python
📝 실습 3: Dwell Time & API 연동 (15분)

파일: stateful_detector.py

import cv2, time, requests
from ultralytics import YOLO

# Mock API 서버 (테스트용)
def send_event(roi_id, status):
    print(f"📡 API 전송: {roi_id} - {status}")
    # 실제: requests.post(...)

roi = [(0, 0), (640, 0), (640, 720), (0, 720)]

state = {
    'detected': False,
    'detection_start': None,
    'absence_start': None,
    'last_status': None
}

cap = cv2.VideoCapture(0)
model = YOLO('yolov8n.pt')

while True:
    ret, frame = cap.read()
    if not ret: break
    
    results = model(frame, verbose=False)
    person_in_roi = False
    
    for result in results:
        for box in result.boxes:
            if int(box.cls[0]) == 0:
                bbox = box.xyxy[0].cpu().numpy()
                # ROI 체크 (생략)
                person_in_roi = True
    
    current_time = time.time()
    
    if person_in_roi:
        if not state['detected']:
            state['detection_start'] = current_time
            state['absence_start'] = None
        state['detected'] = True
        
        # 5초 체크
        if state['detection_start']:
            duration = current_time - state['detection_start']
            if duration >= 5 and state['last_status'] != 'present':
                send_event('ROI1', 'present')
                state['last_status'] = 'present'
    
    else:
        if state['detected']:
            state['absence_start'] = current_time
            state['detection_start'] = None
        state['detected'] = False
        
        # 3초 체크
        if state['absence_start']:
            duration = current_time - state['absence_start']
            if duration >= 3 and state['last_status'] != 'absent':
                send_event('ROI1', 'absent')
                state['last_status'] = 'absent'
    
    # 상태 표시
    status_text = f"{'Detected' if person_in_roi else 'Absent'}"
    if state['detection_start']:
        dur = current_time - state['detection_start']
        status_text += f" ({dur:.1f}s)"
    cv2.putText(frame, status_text, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
    
    cv2.imshow('Stateful Detector', frame)
    if cv2.waitKey(1) & 0xFF == 27: break

cap.release()
cv2.destroyAllWindows()

🎯 목표: 5초/3초 Dwell Time 구현
⏱️ 시간: 15분
```

**강의 스크립트**:
> "세 번째 실습입니다. Dwell Time과 API 연동을 구현합니다. [코드 설명] state 딕셔너리로 상태를 추적합니다. person_in_roi가 True면 detection_start 시각을 기록하고, 5초 이상 지속되면 send_event를 호출합니다. 반대로 False면 absence_start를 기록하고 3초 체크합니다. 화면에는 현재 상태와 지속 시간을 표시합니다. send_event는 현재는 그냥 print하지만, 나중에 실제 requests.post로 바꾸면 됩니다. 자, 15분 동안 구현해보세요. ROI 안에 5초 이상 있으면 'present'가 출력되고, 나가서 3초 지나면 'absent'가 출력되어야 합니다!"

[15분 실습 시간]

---

## Module 2.4: 백그라운드 스레드 최적화

### Slide 29: 왜 멀티스레딩이 필요한가?
```
🐌 단일 스레드 문제점

┌──────────────────────────────────────┐
│  Main Thread                         │
│                                      │
│  ┌──────┐  ┌──────┐  ┌──────┐      │
│  │Camera│→ │YOLO  │→ │UI    │      │
│  │ 33ms │  │100ms │  │ 50ms │      │
│  └──────┘  └──────┘  └──────┘      │
│                                      │
│  Total: 183ms → 5.5 FPS 😞          │
└──────────────────────────────────────┘

⚡ 멀티스레딩 해결

┌──────────────────────────────────────┐
│  UI Thread (Streamlit)               │
│  ┌──────┐  ┌──────┐                 │
│  │Queue │→ │UI    │  30 FPS 😊      │
│  │ 1ms  │  │ 33ms │                 │
│  └──────┘  └──────┘                 │
└──────────────────────────────────────┘
        ↑
┌──────────────────────────────────────┐
│  Detection Thread (Background)       │
│  ┌──────┐  ┌──────┐  ┌──────┐      │
│  │Camera│→ │YOLO  │→ │Queue │      │
│  │ 33ms │  │100ms │  │ 1ms  │      │
│  └──────┘  └──────┘  └──────┘      │
│                                      │
│  Detection: 7.5 FPS (독립적)        │
└──────────────────────────────────────┘

💡 장점:
• UI 응답성 ↑ (30 FPS 유지)
• YOLO 처리 독립적
• 시스템 안정성 ↑
```

**강의 스크립트**:
> "단일 스레드의 문제점을 봅시다. 카메라 읽기에 33ms, YOLO 추론에 100ms, UI 표시에 50ms가 걸리면 총 183ms입니다. 초당 5.5 프레임밖에 안 됩니다. UI가 버벅거리죠. 멀티스레딩으로 해결합니다. [멀티스레딩 다이어그램 설명] UI 스레드는 Queue에서 프레임을 가져와서 표시만 합니다. 33ms면 되니까 30 FPS를 유지합니다. 탐지 스레드는 백그라운드에서 독립적으로 돌아갑니다. 카메라 읽고, YOLO 돌리고, Queue에 넣습니다. 7.5 FPS지만 UI와 상관없습니다. 장점은 UI 응답성이 좋아지고, YOLO 처리가 독립적이고, 시스템이 안정적입니다."

---

### Slide 30: Queue 기반 통신
```python
🔄 Thread-Safe Queue 통신

import queue
import threading

# 스레드 간 공유 큐 생성
frame_queue = queue.Queue(maxsize=2)  # 최대 2개 프레임
stats_queue = queue.Queue(maxsize=10)  # 통계 데이터

# Detection Thread
def detection_loop():
    while running:
        ret, frame = cap.read()
        results = model(frame)
        # ... ROI 체크, 상태 업데이트
        
        # Queue에 프레임 넣기 (넘치면 제거)
        if frame_queue.full():
            try:
                frame_queue.get_nowait()  # 오래된 프레임 제거
            except queue.Empty:
                pass
        frame_queue.put(frame)
        
        # 통계 전송
        stats = {'roi1': True, 'roi2': False, ...}
        stats_queue.put(stats)

# UI Thread (Streamlit)
def update_ui():
    try:
        # 최신 프레임 가져오기 (non-blocking)
        frame = frame_queue.get(timeout=0.1)
        st.image(frame)
        
        # 통계 가져오기
        stats = stats_queue.get(timeout=0.1)
        st.write(stats)
    
    except queue.Empty:
        # 데이터 없으면 넘어감
        pass

💡 장점:
• Thread-safe (자동 동기화)
• Non-blocking (타임아웃 사용)
• 오래된 데이터 자동 제거
```

**강의 스크립트**:
> "Queue로 스레드 간 통신을 합니다. Python의 queue 모듈은 thread-safe합니다. 여러 스레드가 동시에 접근해도 안전합니다. [코드 설명] frame_queue는 프레임을, stats_queue는 통계 데이터를 전달합니다. maxsize를 2로 설정해서 오래된 프레임이 쌓이지 않게 합니다. 탐지 스레드에서 프레임을 넣을 때, 큐가 가득 차면 get_nowait으로 가장 오래된 걸 버립니다. UI 스레드에서는 timeout을 써서 non-blocking으로 가져옵니다. 데이터가 없으면 Empty 예외가 발생하는데, pass로 넘어갑니다. 이렇게 하면 UI가 블로킹되지 않습니다."

---

### Slide 31: RealtimeDetector 클래스
```python
⚙️ RealtimeDetector 클래스 설계

class RealtimeDetector:
    def __init__(self, config, roi_regions):
        self.config = config
        self.roi_regions = roi_regions
        self.model = YOLO(config['yolo_model'])
        self.cap = None
        self.running = False
        self.thread = None
        
        # Queue 초기화
        self.frame_queue = queue.Queue(maxsize=2)
        self.stats_queue = queue.Queue(maxsize=10)
        
        # ROI 상태
        self.roi_states = {}
        for roi in roi_regions:
            self.roi_states[roi['id']] = {
                'person_detected': False,
                'detection_start_time': None,
                # ...
            }
    
    def start(self):
        """백그라운드 스레드 시작"""
        self.running = True
        self.cap = cv2.VideoCapture(self.config['camera_source'])
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
    
    def stop(self):
        """스레드 중지"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        if self.cap:
            self.cap.release()
    
    def run(self):
        """메인 탐지 루프 (백그라운드)"""
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue
            
            # YOLO 추론
            results = self.model(frame, verbose=False)
            
            # ROI별 체크
            for roi in self.roi_regions:
                person_in_roi = False
                for result in results:
                    # ... 사람 검출 및 ROI 체크
                    pass
                
                # 상태 업데이트
                self.update_roi_state(roi['id'], person_in_roi)
            
            # 프레임에 BBox 그리기
            annotated_frame = self.draw_detections(frame, results)
            
            # Queue에 전송
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except:
                    pass
            self.frame_queue.put(annotated_frame)
    
    def get_latest_frame(self):
        """UI에서 최신 프레임 가져오기"""
        try:
            return self.frame_queue.get(timeout=0.1)
        except queue.Empty:
            return None
```

**강의 스크립트**:
> "RealtimeDetector 클래스는 전체 시스템을 캡슐화합니다. [초기화 설명] __init__에서 설정, ROI, YOLO 모델을 초기화하고 Queue를 만듭니다. start 메서드는 카메라를 열고 daemon 스레드를 시작합니다. daemon=True는 메인 프로그램이 종료되면 자동으로 같이 종료된다는 뜻입니다. stop 메서드는 running을 False로 바꾸고 스레드가 끝날 때까지 기다립니다. run 메서드가 실제 탐지 루프입니다. 무한 루프에서 프레임을 읽고, YOLO 추론하고, ROI 체크하고, 상태를 업데이트하고, 프레임에 그림을 그리고, Queue에 넣습니다. get_latest_frame은 UI에서 호출해서 최신 프레임을 가져갑니다. 이렇게 하면 깔끔하게 분리됩니다."

---

### Slide 32: 실습 4 - 백그라운드 스레드
```python
📝 실습 4: 멀티스레딩 구현 (15분)

파일: threaded_detector.py

import cv2, queue, threading, time
from ultralytics import YOLO

class SimpleDetector:
    def __init__(self):
        self.model = YOLO('yolov8n.pt')
        self.cap = None
        self.running = False
        self.frame_queue = queue.Queue(maxsize=2)
    
    def start(self):
        self.running = True
        self.cap = cv2.VideoCapture(0)
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
    
    def stop(self):
        self.running = False
        self.thread.join(timeout=5)
        self.cap.release()
    
    def run(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue
            
            # YOLO 추론
            results = self.model(frame, verbose=False)
            
            # BBox 그리기
            for result in results:
                for box in result.boxes:
                    if int(box.cls[0]) == 0:
                        bbox = box.xyxy[0].cpu().numpy()
                        x1, y1, x2, y2 = map(int, bbox)
                        cv2.rectangle(frame, (x1, y1), (x2, y2),
                                    (255, 0, 0), 2)
            
            # Queue에 넣기
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except:
                    pass
            self.frame_queue.put(frame)
    
    def get_frame(self):
        try:
            return self.frame_queue.get(timeout=0.1)
        except queue.Empty:
            return None

# 메인
detector = SimpleDetector()
detector.start()

try:
    while True:
        frame = detector.get_frame()
        if frame is not None:
            cv2.imshow('Threaded Detector', frame)
        
        if cv2.waitKey(1) & 0xFF == 27:
            break
finally:
    detector.stop()
    cv2.destroyAllWindows()

🎯 목표: 백그라운드 스레드로 YOLO 실행
⏱️ 시간: 15분
```

**강의 스크립트**:
> "마지막 실습입니다. 멀티스레딩을 구현합니다. [코드 설명] SimpleDetector 클래스는 YOLO 모델, 카메라, 큐를 가집니다. start는 스레드를 시작하고, run은 백그라운드에서 계속 돌면서 프레임을 처리합니다. 메인 루프는 단순히 get_frame으로 프레임을 가져와서 표시만 합니다. YOLO 추론이 느려도 UI는 빠릅니다. 실행해보면 훨씬 부드러운 것을 느낄 수 있을 겁니다. 15분 동안 구현해보세요. try-finally로 종료 처리를 제대로 해야 카메라가 안 끊깁니다!"

[15분 실습 시간]

---

## Slide 33: Part 2 요약
```
✅ Part 2 완료! 80분간 배운 것:

💻 구현한 기능:
  ✓ OpenCV 카메라 입력 및 프레임 처리
  ✓ YOLO로 실시간 사람 탐지
  ✓ Polygon ROI 시스템 구현
  ✓ Point-in-Polygon 알고리즘
  ✓ Dwell Time 기반 상태 관리
  ✓ API 이벤트 전송 (present/absent)
  ✓ 백그라운드 스레드 최적화
  ✓ Queue 기반 스레드 간 통신

🎯 다음 Part 3에서는:
  → Streamlit 웹 UI 개발
  → ROI 편집 인터페이스
  → 실시간 대시보드
  → 통계 및 로그 표시

⏸️ 10분 휴식 후 Part 3로 이어집니다!
```

**강의 스크립트**:
> "Part 2가 끝났습니다! 정말 많은 것을 배웠습니다. 카메라 입력부터 YOLO 탐지, ROI 시스템, 상태 관리, API 연동, 그리고 멀티스레딩까지. 이제 여러분은 실시간 사람 감지 시스템의 핵심을 모두 구현할 수 있습니다. 다음 Part 3는 30분 동안 Streamlit으로 사용자 친화적인 웹 UI를 만듭니다. ROI를 마우스로 그리고, 실시간 대시보드를 보고, 통계를 확인하는 인터페이스입니다. 10분 휴식 후에 계속하겠습니다!"

---

**Part 2 슬라이드 종료 - 총 19장 (Slide 15-33)**
