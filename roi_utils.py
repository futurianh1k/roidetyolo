"""
ROI 유틸리티 함수
- 4사분면 ROI 자동 생성
- ROI 검증
- 정규화된 좌표 (0.0~1.0) 지원으로 해상도 독립적 ROI 관리
"""

import numpy as np


def create_fullscreen_roi(normalized=True):
    """
    전체 화면을 하나의 ROI로 생성

    Args:
        normalized: True면 0.0~1.0 비율 좌표 사용

    Returns:
        list: 1개의 ROI 정보 리스트
    """
    if normalized:
        m = 0.02  # 2% 여백
        rois = [
            {
                "id": "ROI_FULL",
                "type": "polygon",
                "normalized": True,
                "points_normalized": [
                    [m, m],
                    [1.0 - m, m],
                    [1.0 - m, 1.0 - m],
                    [m, 1.0 - m],
                ],
                "description": "전체 화면",
            }
        ]
    else:
        raise ValueError("전체 화면 ROI는 normalized=True만 지원합니다")

    return rois


def create_top_bottom_rois(normalized=True):
    """
    화면을 상/하 2등분하여 ROI 생성

    Args:
        normalized: True면 0.0~1.0 비율 좌표 사용

    Returns:
        list: 2개의 ROI 정보 리스트
    """
    if normalized:
        m = 0.02  # 2% 여백
        rois = [
            {
                "id": "ROI_TOP",
                "type": "polygon",
                "normalized": True,
                "points_normalized": [
                    [m, m],
                    [1.0 - m, m],
                    [1.0 - m, 0.5 - m],
                    [m, 0.5 - m],
                ],
                "description": "상단 영역",
            },
            {
                "id": "ROI_BOTTOM",
                "type": "polygon",
                "normalized": True,
                "points_normalized": [
                    [m, 0.5 + m],
                    [1.0 - m, 0.5 + m],
                    [1.0 - m, 1.0 - m],
                    [m, 1.0 - m],
                ],
                "description": "하단 영역",
            },
        ]
    else:
        raise ValueError("상/하 ROI는 normalized=True만 지원합니다")

    return rois


def create_left_right_rois(
    frame_width=None, frame_height=None, margin=20, normalized=True
):
    """
    화면을 좌/우 2등분하여 ROI 생성

    Args:
        frame_width: 프레임 너비 (normalized=False일 때 필수)
        frame_height: 프레임 높이 (normalized=False일 때 필수)
        margin: 중앙 여백 (픽셀)
        normalized: True면 0.0~1.0 비율 좌표 사용

    Returns:
        list: 2개의 ROI 정보 리스트
    """
    if normalized:
        # 정규화된 좌표 (0.0 ~ 1.0) - 해상도 독립적
        m = 0.02  # 2% 여백
        rois = [
            {
                "id": "ROI_LEFT",
                "type": "polygon",
                "normalized": True,
                "points_normalized": [
                    [m, m],
                    [0.5 - m, m],
                    [0.5 - m, 1.0 - m],
                    [m, 1.0 - m],
                ],
                "description": "좌측 영역",
            },
            {
                "id": "ROI_RIGHT",
                "type": "polygon",
                "normalized": True,
                "points_normalized": [
                    [0.5 + m, m],
                    [1.0 - m, m],
                    [1.0 - m, 1.0 - m],
                    [0.5 + m, 1.0 - m],
                ],
                "description": "우측 영역",
            },
        ]
    else:
        # 절대 픽셀 좌표 (기존 방식)
        center_x = frame_width // 2
        rois = [
            {
                "id": "ROI_LEFT",
                "type": "polygon",
                "normalized": False,
                "points": [
                    [margin, margin],
                    [center_x - margin, margin],
                    [center_x - margin, frame_height - margin],
                    [margin, frame_height - margin],
                ],
                "description": "좌측 영역",
            },
            {
                "id": "ROI_RIGHT",
                "type": "polygon",
                "normalized": False,
                "points": [
                    [center_x + margin, margin],
                    [frame_width - margin, margin],
                    [frame_width - margin, frame_height - margin],
                    [center_x + margin, frame_height - margin],
                ],
                "description": "우측 영역",
            },
        ]

    return rois


def create_quadrant_rois(
    frame_width=None, frame_height=None, margin=20, normalized=True
):
    """
    화면을 4등분하여 4사분면 ROI 생성

    Args:
        frame_width: 프레임 너비 (normalized=False일 때 필수)
        frame_height: 프레임 높이 (normalized=False일 때 필수)
        margin: 중앙 여백 (픽셀)
        normalized: True면 0.0~1.0 비율 좌표 사용

    Returns:
        list: 4개의 ROI 정보 리스트
    """
    if normalized:
        # 정규화된 좌표 (0.0 ~ 1.0) - 해상도 독립적
        m = 0.02  # 2% 여백
        rois = [
            {
                "id": "ROI1",
                "type": "polygon",
                "normalized": True,
                "points_normalized": [
                    [m, m],
                    [0.5 - m, m],
                    [0.5 - m, 0.5 - m],
                    [m, 0.5 - m],
                ],
                "description": "1사분면 (좌상단)",
            },
            {
                "id": "ROI2",
                "type": "polygon",
                "normalized": True,
                "points_normalized": [
                    [0.5 + m, m],
                    [1.0 - m, m],
                    [1.0 - m, 0.5 - m],
                    [0.5 + m, 0.5 - m],
                ],
                "description": "2사분면 (우상단)",
            },
            {
                "id": "ROI3",
                "type": "polygon",
                "normalized": True,
                "points_normalized": [
                    [m, 0.5 + m],
                    [0.5 - m, 0.5 + m],
                    [0.5 - m, 1.0 - m],
                    [m, 1.0 - m],
                ],
                "description": "3사분면 (좌하단)",
            },
            {
                "id": "ROI4",
                "type": "polygon",
                "normalized": True,
                "points_normalized": [
                    [0.5 + m, 0.5 + m],
                    [1.0 - m, 0.5 + m],
                    [1.0 - m, 1.0 - m],
                    [0.5 + m, 1.0 - m],
                ],
                "description": "4사분면 (우하단)",
            },
        ]
    else:
        # 절대 픽셀 좌표 (기존 방식)
        center_x = frame_width // 2
        center_y = frame_height // 2
        rois = [
            {
                "id": "ROI1",
                "type": "polygon",
                "normalized": False,
                "points": [
                    [margin, margin],
                    [center_x - margin, margin],
                    [center_x - margin, center_y - margin],
                    [margin, center_y - margin],
                ],
                "description": "1사분면 (좌상단)",
            },
            {
                "id": "ROI2",
                "type": "polygon",
                "normalized": False,
                "points": [
                    [center_x + margin, margin],
                    [frame_width - margin, margin],
                    [frame_width - margin, center_y - margin],
                    [center_x + margin, center_y - margin],
                ],
                "description": "2사분면 (우상단)",
            },
            {
                "id": "ROI3",
                "type": "polygon",
                "normalized": False,
                "points": [
                    [margin, center_y + margin],
                    [center_x - margin, center_y + margin],
                    [center_x - margin, frame_height - margin],
                    [margin, frame_height - margin],
                ],
                "description": "3사분면 (좌하단)",
            },
            {
                "id": "ROI4",
                "type": "polygon",
                "normalized": False,
                "points": [
                    [center_x + margin, center_y + margin],
                    [frame_width - margin, center_y + margin],
                    [frame_width - margin, frame_height - margin],
                    [center_x + margin, frame_height - margin],
                ],
                "description": "4사분면 (우하단)",
            },
        ]

    return rois


def denormalize_roi(roi, frame_width, frame_height):
    """
    정규화된 ROI 좌표를 현재 프레임 크기에 맞게 변환

    Args:
        roi: ROI 정보 딕셔너리
        frame_width: 현재 프레임 너비
        frame_height: 현재 프레임 높이

    Returns:
        dict: 픽셀 좌표가 포함된 ROI (원본 + points 추가)
    """
    roi_copy = roi.copy()

    if roi.get("normalized", False) and "points_normalized" in roi:
        # 정규화된 좌표를 픽셀 좌표로 변환
        points = []
        for px, py in roi["points_normalized"]:
            x = int(px * frame_width)
            y = int(py * frame_height)
            points.append([x, y])
        roi_copy["points"] = points

    return roi_copy


def denormalize_rois(rois, frame_width, frame_height):
    """
    여러 ROI를 한번에 변환

    Args:
        rois: ROI 리스트
        frame_width: 현재 프레임 너비
        frame_height: 현재 프레임 높이

    Returns:
        list: 픽셀 좌표가 포함된 ROI 리스트
    """
    return [denormalize_roi(roi, frame_width, frame_height) for roi in rois]


def normalize_roi_points(roi, frame_width, frame_height):
    """
    픽셀 좌표 ROI를 정규화된 좌표로 변환

    Args:
        roi: ROI 정보 딕셔너리 (points 필드 필요)
        frame_width: 원본 프레임 너비
        frame_height: 원본 프레임 높이

    Returns:
        dict: 정규화된 좌표가 추가된 ROI
    """
    roi_copy = roi.copy()

    if "points" in roi and not roi.get("normalized", False):
        points_normalized = []
        for x, y in roi["points"]:
            px = x / frame_width
            py = y / frame_height
            points_normalized.append([px, py])
        roi_copy["points_normalized"] = points_normalized
        roi_copy["normalized"] = True

    return roi_copy


def create_grid_rois(frame_width, frame_height, rows=2, cols=2, margin=20):
    """
    화면을 그리드로 나누어 ROI 생성

    Args:
        frame_width: 프레임 너비
        frame_height: 프레임 높이
        rows: 행 개수
        cols: 열 개수
        margin: 영역 간 여백 (픽셀)

    Returns:
        list: ROI 정보 리스트
    """
    rois = []

    # 각 셀의 크기 계산
    cell_width = frame_width // cols
    cell_height = frame_height // rows

    roi_index = 1

    for row in range(rows):
        for col in range(cols):
            # 셀의 좌상단 좌표
            x1 = col * cell_width + margin
            y1 = row * cell_height + margin

            # 셀의 우하단 좌표
            x2 = (col + 1) * cell_width - margin
            y2 = (row + 1) * cell_height - margin

            # 마지막 열/행은 프레임 끝까지
            if col == cols - 1:
                x2 = frame_width - margin
            if row == rows - 1:
                y2 = frame_height - margin

            roi = {
                "id": f"ROI{roi_index}",
                "type": "polygon",
                "points": [
                    [x1, y1],  # 좌상단
                    [x2, y1],  # 우상단
                    [x2, y2],  # 우하단
                    [x1, y2],  # 좌하단
                ],
                "description": f"영역 {roi_index} (행{row+1}, 열{col+1})",
            }

            rois.append(roi)
            roi_index += 1

    return rois


def validate_roi(roi, frame_width, frame_height):
    """
    ROI 유효성 검증

    Args:
        roi: ROI 정보 딕셔너리
        frame_width: 프레임 너비
        frame_height: 프레임 높이

    Returns:
        tuple: (유효 여부, 오류 메시지)
    """
    # 필수 필드 확인
    if "id" not in roi:
        return False, "ROI ID가 없습니다"

    if "type" not in roi:
        return False, "ROI 타입이 없습니다"

    if roi["type"] == "polygon":
        if "points" not in roi:
            return False, "Polygon 타입인데 points가 없습니다"

        points = roi["points"]

        # 최소 3개의 점 필요
        if len(points) < 3:
            return (
                False,
                f"Polygon은 최소 3개의 점이 필요합니다 (현재: {len(points)}개)",
            )

        # 모든 점이 프레임 내부에 있는지 확인
        for i, point in enumerate(points):
            x, y = point

            if x < 0 or x >= frame_width:
                return (
                    False,
                    f"점 {i+1}의 X 좌표({x})가 프레임 범위(0~{frame_width})를 벗어났습니다",
                )

            if y < 0 or y >= frame_height:
                return (
                    False,
                    f"점 {i+1}의 Y 좌표({y})가 프레임 범위(0~{frame_height})를 벗어났습니다",
                )

    return True, "유효한 ROI입니다"


def get_roi_center(roi):
    """
    ROI의 중심점 계산

    Args:
        roi: ROI 정보 딕셔너리

    Returns:
        tuple: (center_x, center_y) 또는 None
    """
    if roi.get("type") == "polygon" and "points" in roi:
        points = np.array(roi["points"], dtype=np.int32)

        # 중심점 계산 (모든 점의 평균)
        center_x = int(np.mean([p[0] for p in points]))
        center_y = int(np.mean([p[1] for p in points]))

        return (center_x, center_y)

    return None


def get_roi_bounds(roi):
    """
    ROI의 경계 박스 계산

    Args:
        roi: ROI 정보 딕셔너리

    Returns:
        tuple: (min_x, min_y, max_x, max_y) 또는 None
    """
    if roi.get("type") == "polygon" and "points" in roi:
        points = roi["points"]

        xs = [p[0] for p in points]
        ys = [p[1] for p in points]

        return (min(xs), min(ys), max(xs), max(ys))

    return None


def calculate_roi_area(roi):
    """
    ROI 면적 계산

    Args:
        roi: ROI 정보 딕셔너리

    Returns:
        float: 면적 (픽셀 단위) 또는 0
    """
    if roi.get("type") == "polygon" and "points" in roi:
        import cv2

        points = np.array(roi["points"], dtype=np.int32)
        area = cv2.contourArea(points)
        return area

    return 0.0


# 테스트 코드
if __name__ == "__main__":
    print("=" * 60)
    print("ROI 유틸리티 테스트")
    print("=" * 60)

    # 테스트 프레임 크기
    test_width = 1280
    test_height = 720

    print(f"\n프레임 크기: {test_width}x{test_height}\n")

    # 4사분면 ROI 생성
    print("=" * 60)
    print("4사분면 ROI 생성")
    print("=" * 60)

    quadrant_rois = create_quadrant_rois(test_width, test_height, margin=20)

    for roi in quadrant_rois:
        print(f"\n📍 {roi['id']}: {roi['description']}")
        print(f"   타입: {roi['type']}")
        print(f"   점 개수: {len(roi['points'])}")

        # 중심점
        center = get_roi_center(roi)
        if center:
            print(f"   중심점: ({center[0]}, {center[1]})")

        # 면적
        area = calculate_roi_area(roi)
        print(f"   면적: {area:.0f} 픽셀²")

        # 유효성 검증
        valid, message = validate_roi(roi, test_width, test_height)
        print(f"   유효성: {'✅ ' + message if valid else '❌ ' + message}")

    # 그리드 ROI 생성 (3x3)
    print("\n" + "=" * 60)
    print("3x3 그리드 ROI 생성")
    print("=" * 60)

    grid_rois = create_grid_rois(test_width, test_height, rows=3, cols=3, margin=10)

    print(f"\n총 {len(grid_rois)}개의 ROI 생성됨\n")

    for roi in grid_rois:
        bounds = get_roi_bounds(roi)
        if bounds:
            print(f"{roi['id']}: {roi['description']}")
            print(f"  경계: ({bounds[0]}, {bounds[1]}) ~ ({bounds[2]}, {bounds[3]})")
