"""
VideoSourceManager - 동적 비디오 소스 관리

다양한 입력 소스를 통합 관리하며 런타임에 소스 변경을 지원합니다.
- USB 카메라
- RTSP 스트림
- HTTP MJPEG 스트림
- HTTP POST 이미지 수신
- 비디오 파일

참고자료:
- OpenCV VideoCapture: https://docs.opencv.org/4.x/d8/dfe/classcv_1_1VideoCapture.html
"""

import cv2
import numpy as np
import threading
import time
import platform
from queue import Queue, Empty, Full
from typing import Optional, Callable, Dict, Any
from enum import Enum
from dataclasses import dataclass


class SourceType(Enum):
    """비디오 소스 타입"""

    NONE = "none"
    USB = "usb"
    RTSP = "rtsp"
    HTTP = "http"  # MJPEG 스트림
    HTTP_POST = "http_post"  # 장비가 POST하는 이미지
    FILE = "file"
    IMAGE_SEQUENCE = "image_sequence"


@dataclass
class SourceConfig:
    """소스 설정"""

    source_type: SourceType
    source: Any  # int (USB), str (URL/path)
    options: Dict[str, Any] = None

    def __post_init__(self):
        if self.options is None:
            self.options = {}


class VideoSourceManager:
    """
    비디오 소스 관리자

    - 다양한 입력 소스 지원
    - 런타임 소스 변경 (재시작 없이)
    - Frame Queue를 통한 프레임 제공
    - 스레드 안전

    사용법:
        manager = VideoSourceManager()
        manager.start()

        # 소스 변경
        manager.change_source(SourceConfig(SourceType.USB, 0))
        manager.change_source(SourceConfig(SourceType.HTTP, "http://ip:81/stream"))

        # 프레임 가져오기
        frame = manager.get_frame()

        manager.stop()
    """

    def __init__(self, frame_queue_size: int = 5):
        # 프레임 큐
        self.frame_queue = Queue(maxsize=frame_queue_size)

        # 현재 소스 설정
        self.current_config: Optional[SourceConfig] = None
        self._cap: Optional[cv2.VideoCapture] = None

        # 스레드 제어
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # 소스 변경 플래그
        self._source_change_requested = False
        self._new_config: Optional[SourceConfig] = None

        # HTTP POST 모드용
        self._http_post_queue: Optional[Queue] = None

        # 상태 정보
        self.stats = {
            "frames_captured": 0,
            "frames_dropped": 0,
            "last_frame_time": None,
            "current_fps": 0.0,
            "frame_width": 0,
            "frame_height": 0,
            "source_type": "none",
            "source_connected": False,
        }

        # FPS 계산용
        self._fps_start_time = time.time()
        self._fps_frame_count = 0

        # 콜백 (새 프레임 도착 시)
        self.on_frame_callback: Optional[Callable[[np.ndarray], None]] = None

        # Linux 환경 감지
        self._is_linux = platform.system() == "Linux"

        print("[VideoSourceManager] 초기화 완료")

    def start(self):
        """소스 관리자 시작"""
        if self._running:
            print("[VideoSourceManager] 이미 실행 중")
            return

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        print("[VideoSourceManager] ✅ 시작됨")

    def stop(self):
        """소스 관리자 중지"""
        self._running = False

        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

        self._close_source()
        print("[VideoSourceManager] 중지됨")

    def change_source(self, config: SourceConfig):
        """
        소스 변경 (런타임)

        Args:
            config: 새 소스 설정
        """
        with self._lock:
            self._new_config = config
            self._source_change_requested = True

        print(
            f"[VideoSourceManager] 소스 변경 요청: {config.source_type.value} - {config.source}"
        )

    def get_frame(self, timeout: float = 0.5) -> Optional[np.ndarray]:
        """
        최신 프레임 가져오기 (논블로킹)

        Args:
            timeout: 대기 시간 (초)

        Returns:
            프레임 또는 None
        """
        try:
            return self.frame_queue.get(timeout=timeout)
        except Empty:
            return None

    def get_frame_nowait(self) -> Optional[np.ndarray]:
        """프레임 가져오기 (즉시 반환)"""
        try:
            return self.frame_queue.get_nowait()
        except Empty:
            return None

    def clear_queue(self):
        """프레임 큐 비우기"""
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except Empty:
                break

    def set_http_post_queue(self, queue: Queue):
        """HTTP POST 모드용 외부 큐 설정"""
        self._http_post_queue = queue

    def get_stats(self) -> Dict[str, Any]:
        """상태 정보 반환"""
        return self.stats.copy()

    def is_connected(self) -> bool:
        """소스 연결 상태"""
        return self.stats["source_connected"]

    def _capture_loop(self):
        """프레임 캡처 루프 (스레드)"""
        print("[VideoSourceManager] 캡처 루프 시작")

        while self._running:
            # 소스 변경 체크
            if self._source_change_requested:
                self._apply_source_change()

            # 현재 소스에서 프레임 캡처
            frame = self._capture_frame()

            if frame is not None:
                # 큐에 프레임 추가
                self._enqueue_frame(frame)

                # 콜백 호출
                if self.on_frame_callback:
                    try:
                        self.on_frame_callback(frame)
                    except Exception as e:
                        print(f"[VideoSourceManager] 콜백 오류: {e}")
            else:
                # 프레임 없으면 잠시 대기
                time.sleep(0.01)

        self._close_source()
        print("[VideoSourceManager] 캡처 루프 종료")

    def _apply_source_change(self):
        """소스 변경 적용"""
        with self._lock:
            if not self._source_change_requested:
                return

            new_config = self._new_config
            self._source_change_requested = False
            self._new_config = None

        if new_config is None:
            return

        print(f"[VideoSourceManager] 소스 변경 중: {new_config.source_type.value}")

        # 기존 소스 닫기
        self._close_source()

        # 큐 비우기
        self.clear_queue()

        # 새 소스 열기
        self._open_source(new_config)
        self.current_config = new_config

    def _open_source(self, config: SourceConfig):
        """소스 열기"""
        self.stats["source_type"] = config.source_type.value
        self.stats["source_connected"] = False

        try:
            if config.source_type == SourceType.NONE:
                return

            elif config.source_type == SourceType.USB:
                self._open_usb_camera(config)

            elif config.source_type == SourceType.RTSP:
                self._open_rtsp_stream(config)

            elif config.source_type == SourceType.HTTP:
                self._open_http_stream(config)

            elif config.source_type == SourceType.HTTP_POST:
                self._open_http_post_receiver(config)

            elif config.source_type == SourceType.FILE:
                self._open_video_file(config)

            elif config.source_type == SourceType.IMAGE_SEQUENCE:
                self._open_image_sequence(config)

        except Exception as e:
            print(f"[VideoSourceManager] ❌ 소스 열기 실패: {e}")
            self.stats["source_connected"] = False

    def _open_usb_camera(self, config: SourceConfig):
        """USB 카메라 열기"""
        camera_idx = int(config.source)

        if self._is_linux:
            self._cap = cv2.VideoCapture(camera_idx, cv2.CAP_V4L2)
        else:
            self._cap = cv2.VideoCapture(camera_idx)

        if self._cap and self._cap.isOpened():
            # 해상도 설정 (옵션)
            if "width" in config.options:
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.options["width"])
            if "height" in config.options:
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.options["height"])

            self._update_frame_info()
            self.stats["source_connected"] = True
            print(f"[VideoSourceManager] ✅ USB 카메라 {camera_idx} 연결됨")
        else:
            print(f"[VideoSourceManager] ❌ USB 카메라 {camera_idx} 열기 실패")

    def _open_rtsp_stream(self, config: SourceConfig):
        """RTSP 스트림 열기"""
        import os

        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

        self._cap = cv2.VideoCapture(config.source, cv2.CAP_FFMPEG)

        if self._cap and self._cap.isOpened():
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self._update_frame_info()
            self.stats["source_connected"] = True
            print(f"[VideoSourceManager] ✅ RTSP 스트림 연결됨: {config.source}")
        else:
            print(f"[VideoSourceManager] ❌ RTSP 스트림 열기 실패: {config.source}")

    def _open_http_stream(self, config: SourceConfig):
        """HTTP MJPEG 스트림 열기"""
        self._cap = cv2.VideoCapture(config.source, cv2.CAP_FFMPEG)

        if self._cap and self._cap.isOpened():
            self._update_frame_info()
            self.stats["source_connected"] = True
            print(f"[VideoSourceManager] ✅ HTTP 스트림 연결됨: {config.source}")
        else:
            print(f"[VideoSourceManager] ❌ HTTP 스트림 열기 실패: {config.source}")

    def _open_http_post_receiver(self, config: SourceConfig):
        """HTTP POST 이미지 수신 모드"""
        # 이미지 수신 서버 시작
        from image_receiver import start_receiver_server, get_image_queue

        port = config.options.get("port", 8502)
        start_receiver_server(host="0.0.0.0", port=port)

        self._http_post_queue = get_image_queue()
        self.stats["source_connected"] = True
        print(f"[VideoSourceManager] ✅ HTTP POST 수신 모드 (포트 {port})")

    def _open_video_file(self, config: SourceConfig):
        """비디오 파일 열기"""
        self._cap = cv2.VideoCapture(config.source)

        if self._cap and self._cap.isOpened():
            self._update_frame_info()
            self.stats["source_connected"] = True
            print(f"[VideoSourceManager] ✅ 비디오 파일 열림: {config.source}")
        else:
            print(f"[VideoSourceManager] ❌ 비디오 파일 열기 실패: {config.source}")

    def _open_image_sequence(self, config: SourceConfig):
        """이미지 시퀀스 열기"""
        self._cap = cv2.VideoCapture(config.source)

        if self._cap and self._cap.isOpened():
            self._update_frame_info()
            self.stats["source_connected"] = True
            print(f"[VideoSourceManager] ✅ 이미지 시퀀스 열림: {config.source}")
        else:
            print(f"[VideoSourceManager] ❌ 이미지 시퀀스 열기 실패: {config.source}")

    def _close_source(self):
        """현재 소스 닫기"""
        if self._cap:
            self._cap.release()
            self._cap = None

        self.stats["source_connected"] = False
        print("[VideoSourceManager] 소스 닫힘")

    def _capture_frame(self) -> Optional[np.ndarray]:
        """현재 소스에서 프레임 캡처"""
        if self.current_config is None:
            time.sleep(0.1)
            return None

        # HTTP POST 모드
        if self.current_config.source_type == SourceType.HTTP_POST:
            return self._capture_from_http_post()

        # 일반 VideoCapture 모드
        if self._cap is None or not self._cap.isOpened():
            time.sleep(0.1)
            return None

        ret, frame = self._cap.read()

        if not ret or frame is None:
            # 비디오 파일 끝이면 처음으로
            if self.current_config.source_type == SourceType.FILE:
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return None

        # 통계 업데이트
        self._update_stats(frame)

        return frame

    def _capture_from_http_post(self) -> Optional[np.ndarray]:
        """HTTP POST 큐에서 프레임 가져오기"""
        if self._http_post_queue is None:
            time.sleep(0.1)
            return None

        try:
            frame = self._http_post_queue.get(timeout=0.5)
            self._update_stats(frame)
            return frame
        except Empty:
            return None

    def _enqueue_frame(self, frame: np.ndarray):
        """프레임을 큐에 추가"""
        try:
            # 큐가 가득 차면 오래된 프레임 제거
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                    self.stats["frames_dropped"] += 1
                except Empty:
                    pass

            self.frame_queue.put_nowait(frame)

        except Full:
            self.stats["frames_dropped"] += 1

    def _update_frame_info(self):
        """프레임 정보 업데이트"""
        if self._cap:
            self.stats["frame_width"] = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.stats["frame_height"] = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def _update_stats(self, frame: np.ndarray):
        """통계 업데이트"""
        self.stats["frames_captured"] += 1
        self.stats["last_frame_time"] = time.time()
        self.stats["frame_height"] = frame.shape[0]
        self.stats["frame_width"] = frame.shape[1]

        # FPS 계산
        self._fps_frame_count += 1
        elapsed = time.time() - self._fps_start_time

        if elapsed >= 1.0:
            self.stats["current_fps"] = self._fps_frame_count / elapsed
            self._fps_frame_count = 0
            self._fps_start_time = time.time()


# 편의 함수
def create_source_config(source_type: str, source: Any, **options) -> SourceConfig:
    """소스 설정 생성 헬퍼"""
    type_map = {
        "none": SourceType.NONE,
        "usb": SourceType.USB,
        "rtsp": SourceType.RTSP,
        "http": SourceType.HTTP,
        "http_post": SourceType.HTTP_POST,
        "file": SourceType.FILE,
        "image_sequence": SourceType.IMAGE_SEQUENCE,
    }

    return SourceConfig(
        source_type=type_map.get(source_type, SourceType.NONE),
        source=source,
        options=options,
    )
