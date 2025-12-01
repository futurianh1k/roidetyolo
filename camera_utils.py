"""
카메라 유틸리티 함수
- 카메라 자동 인식
- 카메라 정보 조회
"""

import cv2
import platform


def detect_available_cameras(max_cameras=10):
    """
    사용 가능한 카메라 자동 검색
    
    Args:
        max_cameras: 검색할 최대 카메라 번호 (기본값: 10)
    
    Returns:
        list: 사용 가능한 카메라 정보 리스트
        [
            {
                'index': 0,
                'name': 'Camera 0',
                'resolution': (1280, 720),
                'fps': 30.0
            },
            ...
        ]
    """
    available_cameras = []
    
    print(f"[Camera] 카메라 검색 중 (최대 {max_cameras}개)...")
    
    for camera_idx in range(max_cameras):
        cap = cv2.VideoCapture(camera_idx)
        
        if cap.isOpened():
            # 카메라 정보 가져오기
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # 실제로 프레임을 읽을 수 있는지 확인
            ret, frame = cap.read()
            
            if ret and frame is not None:
                camera_info = {
                    'index': camera_idx,
                    'name': f'Camera {camera_idx}',
                    'resolution': (width, height),
                    'fps': fps if fps > 0 else 30.0,
                    'available': True
                }
                
                available_cameras.append(camera_info)
                print(f"[Camera] ✅ Camera {camera_idx} 발견: {width}x{height} @ {fps:.1f}fps")
            
            cap.release()
        
        # 카메라가 없으면 다음 번호 건너뛰기 (연속으로 2개 실패하면 종료)
        if camera_idx > 0 and len(available_cameras) == 0:
            break
    
    print(f"[Camera] 총 {len(available_cameras)}개의 카메라 발견")
    
    return available_cameras


def get_camera_info(camera_index):
    """
    특정 카메라의 상세 정보 조회
    
    Args:
        camera_index: 카메라 인덱스
    
    Returns:
        dict: 카메라 정보 또는 None
    """
    cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        return None
    
    # 카메라 속성 조회
    info = {
        'index': camera_index,
        'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        'fps': cap.get(cv2.CAP_PROP_FPS),
        'backend': cap.getBackendName(),
        'fourcc': int(cap.get(cv2.CAP_PROP_FOURCC)),
        'brightness': cap.get(cv2.CAP_PROP_BRIGHTNESS),
        'contrast': cap.get(cv2.CAP_PROP_CONTRAST),
        'saturation': cap.get(cv2.CAP_PROP_SATURATION),
    }
    
    cap.release()
    
    return info


def test_camera(camera_index, duration=2):
    """
    카메라 테스트 (프레임 읽기 테스트)
    
    Args:
        camera_index: 카메라 인덱스
        duration: 테스트 시간 (초)
    
    Returns:
        bool: 테스트 성공 여부
    """
    cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        print(f"[Camera] ❌ Camera {camera_index} 열기 실패")
        return False
    
    import time
    start_time = time.time()
    frame_count = 0
    
    while time.time() - start_time < duration:
        ret, frame = cap.read()
        if ret:
            frame_count += 1
        else:
            break
    
    cap.release()
    
    success = frame_count > 0
    if success:
        avg_fps = frame_count / duration
        print(f"[Camera] ✅ Camera {camera_index} 테스트 성공: {frame_count}프레임, 평균 {avg_fps:.1f}fps")
    else:
        print(f"[Camera] ❌ Camera {camera_index} 테스트 실패")
    
    return success


def get_camera_frame(camera_index):
    """
    카메라에서 단일 프레임 가져오기
    
    Args:
        camera_index: 카메라 인덱스
    
    Returns:
        numpy.ndarray: 프레임 또는 None
    """
    cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        return None
    
    ret, frame = cap.read()
    cap.release()
    
    if ret:
        return frame
    else:
        return None


def format_camera_list_for_ui(cameras):
    """
    UI 표시용 카메라 목록 포맷팅
    
    Args:
        cameras: detect_available_cameras() 결과
    
    Returns:
        list: UI 표시용 문자열 리스트
    """
    if not cameras:
        return ["카메라를 찾을 수 없습니다"]
    
    formatted = []
    for cam in cameras:
        resolution = f"{cam['resolution'][0]}x{cam['resolution'][1]}"
        fps = f"{cam['fps']:.0f}fps"
        formatted.append(f"Camera {cam['index']}: {resolution} @ {fps}")
    
    return formatted


# 테스트 코드
if __name__ == '__main__':
    print("=" * 60)
    print("카메라 자동 검색 시작")
    print("=" * 60)
    
    # 카메라 검색
    cameras = detect_available_cameras(max_cameras=5)
    
    if cameras:
        print(f"\n✅ {len(cameras)}개의 카메라를 찾았습니다:\n")
        
        for cam in cameras:
            print(f"  📹 Camera {cam['index']}")
            print(f"     해상도: {cam['resolution'][0]}x{cam['resolution'][1]}")
            print(f"     FPS: {cam['fps']:.1f}")
            print()
        
        # 첫 번째 카메라 테스트
        if cameras:
            print("=" * 60)
            print(f"Camera {cameras[0]['index']} 테스트 중...")
            print("=" * 60)
            test_camera(cameras[0]['index'], duration=2)
    
    else:
        print("\n❌ 사용 가능한 카메라를 찾지 못했습니다.")
        print("   - 카메라가 연결되어 있는지 확인하세요.")
        print("   - 다른 프로그램이 카메라를 사용 중인지 확인하세요.")
