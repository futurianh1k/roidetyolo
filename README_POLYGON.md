# Polygon ROI 사람 검출 시스템

## 🎯 개요

이 시스템은 **다각형(Polygon)** 형태로 ROI 영역을 자유롭게 설정할 수 있는 YOLO 기반 사람 검출 시스템입니다.

## ✨ 주요 변경사항

### 기존 버전 vs Polygon 버전

| 기능 | 기존 버전 | Polygon 버전 |
|------|----------|-------------|
| ROI 형태 | 사각형(Rectangle)만 지원 | **다각형(Polygon) 자유 설정** |
| 설정 방법 | 드래그로 사각형 그리기 | **클릭으로 꼭지점 추가** |
| 유연성 | 제한적 | **복잡한 형태 자유롭게 설정** |
| 정확도 | 사각형 영역만 가능 | **실제 관심 영역만 정확히 설정** |

## 🚀 빠른 시작

### 1. Polygon ROI 선택 도구 사용

```bash
# Polygon ROI 선택 도구 실행
python roi_polygon_selector.py

# 또는 비디오 파일 사용
python roi_polygon_selector.py video.mp4
```

### 사용 방법

1. **마우스 좌클릭**: 다각형의 꼭지점 추가
   - 첫 번째 클릭: 시작점
   - 이후 클릭: 다각형의 각 꼭지점
   - 최소 3개의 점이 필요

2. **다각형 완성**:
   - 마우스 우클릭 또는
   - `Enter` 키

3. **저장 및 편집**:
   - `s` 키: 완성된 다각형을 ROI로 저장
   - `u` 키: 마지막으로 추가한 점 삭제 (Undo)
   - `d` 키: 마지막 ROI 삭제
   - `c` 키: 모든 ROI 초기화

4. **종료**:
   - `q` 키: 완료 및 config.json에 저장

### 화면 표시 설명

- **빨간색 점과 선**: 현재 그리는 중인 다각형
- **노란색 영역**: 완성되었지만 아직 저장하지 않은 다각형 (Press 'S' to Save)
- **녹색 영역**: 저장된 ROI 다각형들

## 📋 Config 파일 형식

### Polygon ROI 형식

```json
{
  "roi_regions": [
    {
      "id": "ROI1",
      "type": "polygon",
      "points": [
        [100, 150],
        [300, 100],
        [500, 150],
        [450, 400],
        [150, 400]
      ],
      "description": "오각형 형태의 관심 영역"
    }
  ]
}
```

### 필드 설명

- `id`: ROI 고유 식별자
- `type`: **"polygon"** (필수)
- `points`: 다각형의 꼭지점 좌표 배열 `[[x1, y1], [x2, y2], ...]`
- `description`: ROI 설명 (선택적)

## 🎮 검출 프로그램 실행

### Polygon ROI 검출 프로그램 사용

```bash
# Polygon 버전 실행
python roi_person_detector_polygon.py
```

이 프로그램은:
- ✅ **Polygon 타입 ROI** 지원
- ✅ **Rectangle 타입 ROI** 하위 호환성 지원
- ✅ 자동으로 ROI 타입을 감지하여 처리

### 동작 방식

1. **Polygon 내부 점 검사**: `cv2.pointPolygonTest()` 사용
   - 사람 바운딩 박스의 중심점이 다각형 내부에 있는지 정확히 판단

2. **검출 시간 측정**: 기존과 동일
   - 5초 이상 검출 → `status: 1` (present)
   - 3초 이상 부재 → `status: 0` (absent)

3. **API 이벤트 전송**: 기존과 동일
   - JSON 형식으로 이벤트 전송

## 📊 사용 예시

### 예시 1: 복잡한 형태의 출입구 영역

```json
{
  "id": "entrance",
  "type": "polygon",
  "points": [
    [120, 200],
    [280, 180],
    [350, 250],
    [340, 450],
    [100, 450]
  ],
  "description": "비정형 출입구 영역"
}
```

### 예시 2: L자 형태의 복도

```json
{
  "id": "corridor",
  "type": "polygon",
  "points": [
    [100, 100],
    [300, 100],
    [300, 300],
    [500, 300],
    [500, 400],
    [100, 400]
  ],
  "description": "L자 형태 복도"
}
```

### 예시 3: 원형에 가까운 영역 (8각형)

```json
{
  "id": "round_area",
  "type": "polygon",
  "points": [
    [400, 200],
    [500, 220],
    [560, 300],
    [560, 400],
    [500, 480],
    [400, 500],
    [300, 480],
    [240, 400],
    [240, 300],
    [300, 220]
  ],
  "description": "원형에 가까운 영역"
}
```

## 🔧 파일 구조

```
yolo_roi_detector/
├── roi_polygon_selector.py              # 🆕 Polygon ROI 선택 도구
├── roi_person_detector_polygon.py       # 🆕 Polygon ROI 검출 프로그램
├── config_polygon_example.json          # 🆕 Polygon 설정 예시
│
├── roi_selector.py                      # 기존: Rectangle ROI 선택 도구
├── roi_person_detector.py               # 기존: Rectangle ROI 검출 프로그램
├── config.json                          # 기존: Rectangle 설정
│
├── test_api.py                          # API 테스트 도구
├── mock_server.py                       # Mock API 서버
├── requirements.txt                     # 패키지 의존성
├── README.md                            # 기본 사용 가이드
└── README_POLYGON.md                    # 이 문서
```

## 💡 사용 팁

### 1. 정확한 영역 설정

- **불필요한 영역 제외**: Polygon을 사용하면 복잡한 형태의 관심 영역만 정확히 설정 가능
- **예시**: 복도의 벽면 제외, 출입구의 문틀 제외 등

### 2. 효율적인 다각형 그리기

- **시계방향 또는 반시계방향**: 일관된 방향으로 점을 찍으면 자연스러운 다각형 생성
- **적당한 점 개수**: 너무 많은 점보다는 필요한 만큼의 점으로 표현
- **Undo 기능 활용**: `u` 키로 잘못 찍은 점을 쉽게 수정

### 3. 여러 ROI 설정

```bash
# 한 번에 여러 개의 Polygon ROI 설정
1. 첫 번째 다각형 그리기 (클릭으로 점 추가)
2. 우클릭 또는 Enter로 완성
3. 's' 키로 저장
4. 두 번째 다각형 그리기...
5. 반복
6. 'q' 키로 모두 저장하고 종료
```

## 🎨 시각화 특징

### Polygon ROI 표시

- **반투명 채우기**: ROI 영역을 반투명하게 표시하여 배경 이미지도 확인 가능
- **테두리 강조**: 명확한 경계선 표시
- **중심점 정보**: ROI ID, 상태, 카운트를 다각형 중심에 표시

### 상태별 색상

- **녹색**: 사람이 검출된 ROI
- **빨간색**: 사람이 없는 ROI
- **파란색**: 검출된 사람의 바운딩 박스

## 🔄 Rectangle에서 Polygon으로 전환

기존 Rectangle ROI를 Polygon으로 변환하려면:

### 자동 변환 (수동)

```python
# Rectangle config
{
  "id": "ROI1",
  "x": 100,
  "y": 100,
  "width": 400,
  "height": 300
}

# Polygon으로 변환
{
  "id": "ROI1",
  "type": "polygon",
  "points": [
    [100, 100],           # 좌상단
    [500, 100],           # 우상단 (x + width)
    [500, 400],           # 우하단 (x + width, y + height)
    [100, 400]            # 좌하단 (y + height)
  ]
}
```

## ⚙️ 성능 비교

### Polygon vs Rectangle

| 항목 | Rectangle | Polygon |
|------|-----------|---------|
| 설정 시간 | 빠름 (드래그 한 번) | 보통 (여러 번 클릭) |
| 정확도 | 제한적 | **매우 높음** |
| 유연성 | 낮음 | **매우 높음** |
| CPU 사용 | 낮음 | 약간 높음 |
| 메모리 | 낮음 | 약간 높음 |

**권장사항**: 복잡한 형태의 영역이 필요한 경우 Polygon 사용, 단순한 영역은 Rectangle 사용

## 🐛 문제 해결

### Q: Polygon이 제대로 그려지지 않아요

**A**: 점을 너무 가까이 찍었거나 자기 자신과 교차하는 다각형일 수 있습니다.
- `u` 키로 마지막 점을 삭제하고 다시 시도
- 점 사이에 충분한 간격을 두고 클릭

### Q: 저장된 Polygon이 화면에 이상하게 표시돼요

**A**: config.json의 points 배열을 확인하세요.
- 좌표값이 음수이거나 화면을 벗어났는지 확인
- 점의 순서가 올바른지 확인

### Q: 검출 정확도가 떨어져요

**A**: 
- `confidence_threshold` 값 조정 (0.3 ~ 0.7 권장)
- Polygon 영역이 너무 크거나 작지 않은지 확인
- YOLO 모델 버전 변경 시도 (yolov8n.pt → yolov8s.pt)

## 📝 API 이벤트 형식

Polygon ROI도 기존과 동일한 API 형식 사용:

```json
{
  "eventId": "fc4d54d0-717c-4fe8-95be-fdf8f188a401",
  "roiId": "ROI1",
  "objectType": "human",
  "status": 1,
  "createdAt": "2025-12-01T05:30:00",
  "watchId": "watch_1760663070591_8022"
}
```

## 🚦 실행 흐름

```
1. roi_polygon_selector.py 실행
   ↓
2. 마우스 클릭으로 다각형 ROI 설정
   ↓
3. config.json에 저장
   ↓
4. roi_person_detector_polygon.py 실행
   ↓
5. 실시간 사람 검출 및 API 이벤트 전송
```

## 📞 지원

버그 리포트나 기능 제안이 있으시면 이슈를 등록해주세요!
