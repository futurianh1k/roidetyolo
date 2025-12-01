"""
ROI 유틸리티 함수
- 4사분면 ROI 자동 생성
- ROI 검증
"""

import numpy as np


def create_quadrant_rois(frame_width, frame_height, margin=20):
    """
    화면을 4등분하여 4사분면 ROI 생성
    
    Args:
        frame_width: 프레임 너비
        frame_height: 프레임 높이
        margin: 중앙 여백 (픽셀)
    
    Returns:
        list: 4개의 ROI 정보 리스트
    """
    # 중앙점 계산
    center_x = frame_width // 2
    center_y = frame_height // 2
    
    # 4사분면 ROI 생성
    rois = [
        {
            'id': 'ROI1',
            'type': 'polygon',
            'points': [
                [margin, margin],                           # 좌상단
                [center_x - margin, margin],                # 우상단
                [center_x - margin, center_y - margin],     # 우하단
                [margin, center_y - margin]                 # 좌하단
            ],
            'description': '1사분면 (좌상단)'
        },
        {
            'id': 'ROI2',
            'type': 'polygon',
            'points': [
                [center_x + margin, margin],                # 좌상단
                [frame_width - margin, margin],             # 우상단
                [frame_width - margin, center_y - margin],  # 우하단
                [center_x + margin, center_y - margin]      # 좌하단
            ],
            'description': '2사분면 (우상단)'
        },
        {
            'id': 'ROI3',
            'type': 'polygon',
            'points': [
                [margin, center_y + margin],                # 좌상단
                [center_x - margin, center_y + margin],     # 우상단
                [center_x - margin, frame_height - margin], # 우하단
                [margin, frame_height - margin]             # 좌하단
            ],
            'description': '3사분면 (좌하단)'
        },
        {
            'id': 'ROI4',
            'type': 'polygon',
            'points': [
                [center_x + margin, center_y + margin],     # 좌상단
                [frame_width - margin, center_y + margin],  # 우상단
                [frame_width - margin, frame_height - margin], # 우하단
                [center_x + margin, frame_height - margin]  # 좌하단
            ],
            'description': '4사분면 (우하단)'
        }
    ]
    
    return rois


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
                'id': f'ROI{roi_index}',
                'type': 'polygon',
                'points': [
                    [x1, y1],  # 좌상단
                    [x2, y1],  # 우상단
                    [x2, y2],  # 우하단
                    [x1, y2]   # 좌하단
                ],
                'description': f'영역 {roi_index} (행{row+1}, 열{col+1})'
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
    if 'id' not in roi:
        return False, "ROI ID가 없습니다"
    
    if 'type' not in roi:
        return False, "ROI 타입이 없습니다"
    
    if roi['type'] == 'polygon':
        if 'points' not in roi:
            return False, "Polygon 타입인데 points가 없습니다"
        
        points = roi['points']
        
        # 최소 3개의 점 필요
        if len(points) < 3:
            return False, f"Polygon은 최소 3개의 점이 필요합니다 (현재: {len(points)}개)"
        
        # 모든 점이 프레임 내부에 있는지 확인
        for i, point in enumerate(points):
            x, y = point
            
            if x < 0 or x >= frame_width:
                return False, f"점 {i+1}의 X 좌표({x})가 프레임 범위(0~{frame_width})를 벗어났습니다"
            
            if y < 0 or y >= frame_height:
                return False, f"점 {i+1}의 Y 좌표({y})가 프레임 범위(0~{frame_height})를 벗어났습니다"
    
    return True, "유효한 ROI입니다"


def get_roi_center(roi):
    """
    ROI의 중심점 계산
    
    Args:
        roi: ROI 정보 딕셔너리
    
    Returns:
        tuple: (center_x, center_y) 또는 None
    """
    if roi.get('type') == 'polygon' and 'points' in roi:
        points = np.array(roi['points'], dtype=np.int32)
        
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
    if roi.get('type') == 'polygon' and 'points' in roi:
        points = roi['points']
        
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
    if roi.get('type') == 'polygon' and 'points' in roi:
        import cv2
        points = np.array(roi['points'], dtype=np.int32)
        area = cv2.contourArea(points)
        return area
    
    return 0.0


# 테스트 코드
if __name__ == '__main__':
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
