"""
카메라 유틸리티 함수
- 카메라 자동 인식
- 카메라 정보 조회
- 다양한 카메라 소스 타입 지원 (USB, RTSP, HTTP, 파일, 이미지 시퀀스)
"""

import cv2
import platform
import os
import glob
from urllib.parse import urlparse
from typing import Optional, Dict, Any, List


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
    
    # Linux 환경 감지
    is_linux = platform.system() == 'Linux'
    
    for camera_idx in range(max_cameras):
        # Linux에서는 V4L2 백엔드 명시
        if is_linux:
            cap = cv2.VideoCapture(camera_idx, cv2.CAP_V4L2)
            print(f"[Camera] Linux 환경: /dev/video{camera_idx} 검색 중 (V4L2 백엔드)...")
        else:
            cap = cv2.VideoCapture(camera_idx)
        
        if cap.isOpened():
            # 카메라 정보 가져오기
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # FPS가 0이면 기본값 설정 및 경고 출력 제거
            if fps <= 0:
                fps = 30.0
            
            # 실제로 프레임을 읽을 수 있는지 확인 (타임아웃 추가)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 버퍼 크기 최소화
            ret, frame = cap.read()
            
            if ret and frame is not None:
                backend = cap.getBackendName()
                camera_info = {
                    'index': camera_idx,
                    'name': f'Camera {camera_idx}',
                    'resolution': (width, height),
                    'fps': fps,
                    'available': True,
                    'backend': backend
                }
                
                available_cameras.append(camera_info)
                print(f"[Camera] ✅ Camera {camera_idx} 발견: {width}x{height} @ {fps:.1f}fps (Backend: {backend})")
            else:
                print(f"[Camera] ⚠️ Camera {camera_idx} 열림 성공하나 프레임 읽기 실패")
            
            cap.release()
        else:
            # 디버깅을 위한 상세 정보
            if camera_idx < 3:  # 처음 3개만 자세히 출력
                print(f"[Camera] ❌ Camera {camera_idx} 열기 실패")
    
    print(f"[Camera] 총 {len(available_cameras)}개의 카메라 발견")
    
    # Linux에서 카메라를 찾지 못한 경우 권한 체크
    if is_linux and len(available_cameras) == 0:
        print("\n[Camera] ⚠️ Linux에서 카메라를 찾지 못했습니다.")
        print("[Camera] 다음을 확인해주세요:")
        print("[Camera]   1. 카메라가 연결되어 있는지 확인: lsusb")
        print("[Camera]   2. 비디오 장치 확인: ls -la /dev/video*")
        print("[Camera]   3. 사용자 권한 확인: groups $USER")
        print("[Camera]   4. 권한 추가: sudo usermod -aG video $USER")
        print("[Camera]   5. v4l-utils 설치: sudo apt-get install v4l-utils")
        print("[Camera]   6. 장치 정보 확인: v4l2-ctl --list-devices")
    
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
    # Linux에서는 V4L2 백엔드 사용
    if platform.system() == 'Linux':
        cap = cv2.VideoCapture(camera_index, cv2.CAP_V4L2)
    else:
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
    # Linux에서는 V4L2 백엔드 사용
    if platform.system() == 'Linux':
        cap = cv2.VideoCapture(camera_index, cv2.CAP_V4L2)
    else:
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


class CameraSourceType:
    """카메라 소스 타입 정의"""
    USB = "usb"           # USB 카메라 (0, 1, 2...)
    RTSP = "rtsp"         # RTSP 스트림 (rtsp://...)
    HTTP = "http"         # HTTP/HTTPS 스트림
    FILE = "file"         # 비디오 파일 (.mp4, .avi, .mkv 등)
    IMAGE_SEQ = "image_sequence"  # 이미지 시퀀스 (image_%04d.jpg)
    GSTREAMER = "gstreamer"  # GStreamer 파이프라인
    

class CameraSourceManager:
    """
    다양한 카메라 소스를 관리하는 클래스
    - USB 카메라
    - RTSP 스트림
    - HTTP/HTTPS 스트림
    - 비디오 파일
    - 이미지 시퀀스
    - GStreamer 파이프라인
    """
    
    @staticmethod
    def detect_source_type(source) -> str:
        """
        소스 타입 자동 감지
        
        Args:
            source: 카메라 소스 (int, str)
        
        Returns:
            str: 소스 타입 (CameraSourceType의 값)
        """
        if isinstance(source, int):
            return CameraSourceType.USB
        
        if not isinstance(source, str):
            return CameraSourceType.USB
        
        source_lower = source.lower()
        
        # RTSP 스트림
        if source_lower.startswith('rtsp://'):
            return CameraSourceType.RTSP
        
        # HTTP 스트림
        if source_lower.startswith(('http://', 'https://')):
            return CameraSourceType.HTTP
        
        # GStreamer 파이프라인 (특정 키워드 포함)
        if 'appsrc' in source_lower or 'videotestsrc' in source_lower or 'v4l2src' in source_lower:
            return CameraSourceType.GSTREAMER
        
        # 이미지 시퀀스 (와일드카드 포함)
        if '%' in source or '*' in source:
            return CameraSourceType.IMAGE_SEQ
        
        # 파일 경로
        if os.path.exists(source):
            ext = os.path.splitext(source)[1].lower()
            video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv', '.webm', '.m4v']
            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
            
            if ext in video_extensions:
                return CameraSourceType.FILE
            elif ext in image_extensions:
                return CameraSourceType.IMAGE_SEQ
        
        # 숫자 문자열은 USB 카메라 인덱스로 처리
        if source.isdigit():
            return CameraSourceType.USB
        
        # 기본값: 파일로 간주
        return CameraSourceType.FILE
    
    @staticmethod
    def open_camera(source, source_type: Optional[str] = None, **kwargs) -> Optional[cv2.VideoCapture]:
        """
        카메라 소스 열기
        
        Args:
            source: 카메라 소스
            source_type: 소스 타입 (자동 감지 가능)
            **kwargs: 추가 옵션
                - backend: OpenCV 백엔드 (cv2.CAP_V4L2, cv2.CAP_FFMPEG 등)
                - rtsp_transport: RTSP 전송 프로토콜 ('tcp' 또는 'udp')
                - buffer_size: 버퍼 크기
        
        Returns:
            cv2.VideoCapture: 열린 카메라 객체 또는 None
        """
        if source_type is None:
            source_type = CameraSourceManager.detect_source_type(source)
        
        print(f"[CameraSourceManager] 소스 타입: {source_type}")
        print(f"[CameraSourceManager] 소스: {source}")
        
        cap = None
        
        try:
            if source_type == CameraSourceType.USB:
                # USB 카메라
                camera_index = int(source) if isinstance(source, str) else source
                backend = kwargs.get('backend', None)
                
                if platform.system() == 'Linux' and backend is None:
                    backend = cv2.CAP_V4L2
                
                if backend:
                    cap = cv2.VideoCapture(camera_index, backend)
                else:
                    cap = cv2.VideoCapture(camera_index)
                
            elif source_type == CameraSourceType.RTSP:
                # RTSP 스트림
                rtsp_transport = kwargs.get('rtsp_transport', 'tcp')
                
                # RTSP 옵션 설정
                os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = f'rtsp_transport;{rtsp_transport}'
                cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
                
                # 버퍼 크기 설정 (지연 최소화)
                buffer_size = kwargs.get('buffer_size', 1)
                if cap.isOpened():
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, buffer_size)
                
            elif source_type == CameraSourceType.HTTP:
                # HTTP 스트림
                cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
                
            elif source_type == CameraSourceType.FILE:
                # 비디오 파일
                if not os.path.exists(source):
                    print(f"[CameraSourceManager] ❌ 파일이 존재하지 않습니다: {source}")
                    return None
                
                cap = cv2.VideoCapture(source)
                
            elif source_type == CameraSourceType.IMAGE_SEQ:
                # 이미지 시퀀스
                cap = cv2.VideoCapture(source)
                
            elif source_type == CameraSourceType.GSTREAMER:
                # GStreamer 파이프라인
                cap = cv2.VideoCapture(source, cv2.CAP_GSTREAMER)
            
            # 카메라 열기 확인
            if cap and cap.isOpened():
                print(f"[CameraSourceManager] ✅ 카메라 소스 열기 성공")
                return cap
            else:
                print(f"[CameraSourceManager] ❌ 카메라 소스 열기 실패")
                if cap:
                    cap.release()
                return None
                
        except Exception as e:
            print(f"[CameraSourceManager] ❌ 오류 발생: {e}")
            if cap:
                cap.release()
            return None
    
    @staticmethod
    def validate_source(source) -> Dict[str, Any]:
        """
        카메라 소스 유효성 검사
        
        Args:
            source: 카메라 소스
        
        Returns:
            dict: 검증 결과
            {
                'valid': bool,
                'source_type': str,
                'message': str,
                'details': dict
            }
        """
        result = {
            'valid': False,
            'source_type': None,
            'message': '',
            'details': {}
        }
        
        source_type = CameraSourceManager.detect_source_type(source)
        result['source_type'] = source_type
        
        try:
            if source_type == CameraSourceType.USB:
                camera_index = int(source) if isinstance(source, str) else source
                if camera_index < 0:
                    result['message'] = f"잘못된 카메라 인덱스: {camera_index}"
                    return result
                
                # 카메라 열기 테스트
                cap = CameraSourceManager.open_camera(source, source_type)
                if cap and cap.isOpened():
                    result['valid'] = True
                    result['message'] = f"USB 카메라 {camera_index} 사용 가능"
                    result['details'] = {
                        'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                        'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                        'fps': cap.get(cv2.CAP_PROP_FPS)
                    }
                    cap.release()
                else:
                    result['message'] = f"USB 카메라 {camera_index}를 열 수 없습니다"
                
            elif source_type in [CameraSourceType.RTSP, CameraSourceType.HTTP]:
                # URL 유효성 검사
                parsed = urlparse(source)
                if not parsed.scheme or not parsed.netloc:
                    result['message'] = f"잘못된 URL 형식: {source}"
                    return result
                
                result['valid'] = True
                result['message'] = f"{source_type.upper()} 스트림 URL 유효"
                result['details'] = {
                    'url': source,
                    'scheme': parsed.scheme,
                    'host': parsed.netloc
                }
                
            elif source_type == CameraSourceType.FILE:
                if not os.path.exists(source):
                    result['message'] = f"파일이 존재하지 않습니다: {source}"
                    return result
                
                # 파일 열기 테스트
                cap = cv2.VideoCapture(source)
                if cap.isOpened():
                    result['valid'] = True
                    result['message'] = f"비디오 파일 사용 가능"
                    result['details'] = {
                        'path': source,
                        'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                        'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                        'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                        'fps': cap.get(cv2.CAP_PROP_FPS)
                    }
                    cap.release()
                else:
                    result['message'] = f"비디오 파일을 열 수 없습니다: {source}"
                
            elif source_type == CameraSourceType.IMAGE_SEQ:
                result['valid'] = True
                result['message'] = f"이미지 시퀀스 경로"
                result['details'] = {'pattern': source}
                
            elif source_type == CameraSourceType.GSTREAMER:
                result['valid'] = True
                result['message'] = f"GStreamer 파이프라인"
                result['details'] = {'pipeline': source}
            
        except Exception as e:
            result['message'] = f"검증 중 오류: {str(e)}"
        
        return result
    
    @staticmethod
    def get_source_info(source) -> Dict[str, Any]:
        """
        카메라 소스 정보 조회
        
        Args:
            source: 카메라 소스
        
        Returns:
            dict: 소스 정보
        """
        source_type = CameraSourceManager.detect_source_type(source)
        
        info = {
            'source': source,
            'source_type': source_type,
            'description': ''
        }
        
        if source_type == CameraSourceType.USB:
            info['description'] = f"USB 카메라 (인덱스: {source})"
        elif source_type == CameraSourceType.RTSP:
            info['description'] = f"RTSP 스트림"
        elif source_type == CameraSourceType.HTTP:
            info['description'] = f"HTTP 스트림"
        elif source_type == CameraSourceType.FILE:
            info['description'] = f"비디오 파일: {os.path.basename(source)}"
        elif source_type == CameraSourceType.IMAGE_SEQ:
            info['description'] = f"이미지 시퀀스"
        elif source_type == CameraSourceType.GSTREAMER:
            info['description'] = f"GStreamer 파이프라인"
        
        return info


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
    
    # CameraSourceManager 테스트
    print("\n" + "=" * 60)
    print("CameraSourceManager 테스트")
    print("=" * 60)
    
    test_sources = [
        0,
        "rtsp://example.com:554/stream",
        "http://example.com/stream.mjpg",
        "/path/to/video.mp4",
        "image_%04d.jpg",
    ]
    
    for source in test_sources:
        print(f"\n소스: {source}")
        source_type = CameraSourceManager.detect_source_type(source)
        print(f"  타입: {source_type}")
        
        validation = CameraSourceManager.validate_source(source)
        print(f"  유효: {validation['valid']}")
        print(f"  메시지: {validation['message']}")
        if validation['details']:
            print(f"  상세: {validation['details']}")
