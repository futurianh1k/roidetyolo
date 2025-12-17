"""
DetectionEngine - YOLO 객체 검출 + 얼굴 분석 엔진

VideoSourceManager와 분리되어 독립적으로 동작합니다.
- YOLO 모델 로딩 (앱 시작 시 1회)
- Frame Queue에서 프레임 가져와서 처리
- ROI는 참조로 받아서 런타임 변경 가능
- 검출 결과를 Result Queue로 전달

참고자료:
- Ultralytics YOLO: https://docs.ultralytics.com/
- MediaPipe Face Mesh: https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker
"""

import cv2
import numpy as np
import threading
import time
import queue
import traceback
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from ultralytics import YOLO

from video_source_manager import VideoSourceManager
from roi_utils import denormalize_rois


# 얼굴 분석기 임포트 (선택적)
try:
    from face_analyzer import FaceAnalyzer

    FACE_ANALYZER_AVAILABLE = True
    print("[DetectionEngine] ✅ FaceAnalyzer 모듈 로드 완료")
except ImportError:
    FACE_ANALYZER_AVAILABLE = False
    print("[DetectionEngine] ⚠️  FaceAnalyzer 모듈 없음 - 얼굴 분석 비활성화")


@dataclass
class DetectionResult:
    """검출 결과"""

    timestamp: float
    frame: np.ndarray
    detections: List[Dict[str, Any]]
    roi_states: Dict[str, Dict[str, Any]]
    face_results: Dict[tuple, Dict[str, Any]]
    annotated_frame: Optional[np.ndarray] = None


class DetectionEngine:
    """
    YOLO 객체 검출 엔진

    - VideoSourceManager에서 프레임을 받아서 처리
    - YOLO 모델은 앱 시작 시 1회 로드
    - ROI 영역은 동적으로 변경 가능
    - 얼굴 분석 통합 (선택적)

    사용법:
        source_manager = VideoSourceManager()
        engine = DetectionEngine(source_manager)

        engine.set_roi_regions(roi_list)  # 동적 ROI 설정
        engine.start()

        # 결과 가져오기
        result = engine.get_result()

        engine.stop()
    """

    def __init__(
        self,
        source_manager: VideoSourceManager,
        yolo_model: str = "yolov8n.pt",
        confidence_threshold: float = 0.5,
        detection_interval: float = 1.0,
        enable_face_analysis: bool = True,
        api_endpoint: Optional[str] = None,
    ):
        """
        Args:
            source_manager: 비디오 소스 관리자
            yolo_model: YOLO 모델 경로
            confidence_threshold: 검출 신뢰도 임계값
            detection_interval: YOLO 추론 간격 (초)
            enable_face_analysis: 얼굴 분석 활성화
            api_endpoint: API 엔드포인트 (이벤트 전송용)
        """
        self.source_manager = source_manager
        self.confidence_threshold = confidence_threshold
        self.detection_interval = detection_interval
        self.enable_face_analysis = enable_face_analysis and FACE_ANALYZER_AVAILABLE
        self.api_endpoint = api_endpoint

        # YOLO 모델 로드 (GPU 실패 시 CPU로 폴백)
        print(f"[DetectionEngine] YOLO 모델 로딩: {yolo_model}")

        import torch
        import os
        import numpy as np

        # 환경 변수로 CPU 강제 사용 가능 (Jetson 등 호환성 문제 시)
        force_cpu = os.environ.get("YOLO_FORCE_CPU", "").lower() in ("1", "true", "yes")

        # Jetson 장치 감지
        is_jetson = os.path.exists("/etc/nv_tegra_release")
        if is_jetson:
            print("[DetectionEngine] 🔍 Jetson 장치 감지됨")

        self.model = YOLO(yolo_model)

        # Device 설정: GPU 사용 가능하면 GPU, 아니면 CPU
        if force_cpu:
            self.device = "cpu"
            print(f"[DetectionEngine] ✅ CPU 강제 사용 (YOLO_FORCE_CPU=1)")
        elif torch.cuda.is_available():
            try:
                # GPU 테스트 - 실제 추론까지 테스트
                self.device = "cuda"
                self.model.to(self.device)

                # Warmup 테스트: 실제 추론으로 CUDA 커널 호환성 확인
                print("[DetectionEngine] GPU warmup 테스트 중...")
                test_img = np.zeros((640, 640, 3), dtype=np.uint8)
                _ = self.model(test_img, verbose=False, device=self.device)
                print(f"[DetectionEngine] ✅ YOLO 모델 GPU 로드 완료 (cuda)")

            except RuntimeError as e:
                error_msg = str(e).lower()
                if "cuda" in error_msg or "kernel" in error_msg:
                    print(f"[DetectionEngine] ⚠️ CUDA 커널 호환성 문제, CPU 사용: {e}")
                    if is_jetson:
                        print("[DetectionEngine] 💡 Jetson용 PyTorch 설치 권장:")
                        print(
                            "   https://forums.developer.nvidia.com/t/pytorch-for-jetson/72048"
                        )
                else:
                    print(f"[DetectionEngine] ⚠️ GPU 초기화 실패, CPU 사용: {e}")
                self.device = "cpu"
                # 모델을 CPU로 다시 로드
                self.model = YOLO(yolo_model)
                self.model.to(self.device)
            except Exception as e:
                print(f"[DetectionEngine] ⚠️ GPU 초기화 실패, CPU 사용: {e}")
                self.device = "cpu"
                self.model = YOLO(yolo_model)
                self.model.to(self.device)
        else:
            self.device = "cpu"
            print(f"[DetectionEngine] ✅ YOLO 모델 CPU 로드 완료")

        # 얼굴 분석기 초기화
        self.face_analyzer = None
        if self.enable_face_analysis:
            try:
                self.face_analyzer = FaceAnalyzer()
                print("[DetectionEngine] ✅ FaceAnalyzer 초기화 완료")
            except Exception as e:
                print(f"[DetectionEngine] ⚠️  FaceAnalyzer 초기화 실패: {e}")
                self.enable_face_analysis = False

        # ROI 영역 (동적 변경 가능)
        self._roi_regions: List[Dict] = []
        self._roi_lock = threading.Lock()
        self._rois_denormalized = False

        # ROI별 상태 추적
        self._roi_states: Dict[str, Dict[str, Any]] = {}

        # 결과 큐
        self.result_queue = queue.Queue(maxsize=5)

        # 시각화된 프레임 큐 (UI용)
        self.frame_queue = queue.Queue(maxsize=3)

        # 스레드 제어
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # 검출 상태
        self.last_detection_time = 0
        self.last_detections: List[Dict] = []
        self.last_face_results: Dict = {}

        # 통계
        self.stats = {
            "frames_processed": 0,
            "detections_count": 0,
            "inference_time_ms": 0,
            "current_fps": 0,
        }

        self._settings_lock = threading.Lock()

        # FPS 계산용
        self._fps_start_time = time.time()
        self._fps_frame_count = 0

        # API 전송 쿨다운
        self._absence_api_cooldown = 5.0  # 5초
        self._sad_api_cooldown = 10.0  # 10초
        self._last_sad_api_time: Dict[str, float] = {}

        # 콜백
        self.on_detection_callback: Optional[Callable[[DetectionResult], None]] = None
        self.on_event_callback: Optional[Callable[[str, str, Dict], None]] = None

        print("[DetectionEngine] 초기화 완료")

    def set_roi_regions(self, roi_regions: List[Dict]):
        """
        ROI 영역 설정 (런타임 변경 가능)

        Args:
            roi_regions: ROI 영역 리스트
        """
        with self._roi_lock:
            self._roi_regions = roi_regions.copy()
            self._rois_denormalized = False

            # ROI 상태 초기화
            self._roi_states = {}
            for roi in roi_regions:
                roi_id = roi.get("id", f"ROI_{len(self._roi_states)}")
                self._roi_states[roi_id] = {
                    "person_detected": False,
                    "detection_start_time": None,
                    "absence_start_time": None,
                    "last_status_sent": None,
                    "detection_count": 0,
                }

        print(f"[DetectionEngine] ROI 설정됨: {len(roi_regions)}개")

    def get_roi_regions(self) -> List[Dict]:
        """현재 ROI 영역 반환"""
        with self._roi_lock:
            return self._roi_regions.copy()

    def get_roi_states(self) -> Dict[str, Dict]:
        """ROI 상태 반환"""
        return self._roi_states.copy()

    def start(self):
        """엔진 시작"""
        if self._running:
            print("[DetectionEngine] 이미 실행 중")
            return

        self._running = True
        self._thread = threading.Thread(target=self._detection_loop, daemon=True)
        self._thread.start()
        print("[DetectionEngine] ✅ 검출 엔진 시작됨")

    def stop(self):
        """엔진 중지"""
        self._running = False

        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

        print("[DetectionEngine] 검출 엔진 중지됨")

    def is_running(self) -> bool:
        """실행 상태 확인"""
        return self._running

    def get_result(self, timeout: float = 0.5) -> Optional[DetectionResult]:
        """최신 검출 결과 가져오기"""
        try:
            return self.result_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_annotated_frame(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        """시각화된 프레임 가져오기 (UI용)"""
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_stats(self) -> Dict[str, Any]:
        """통계 반환"""
        return self.stats.copy()

    def update_runtime_settings(
        self,
        confidence_threshold: Optional[float] = None,
        detection_interval: Optional[float] = None,
        enable_face_analysis: Optional[bool] = None,
    ) -> bool:
        """
        런타임 설정 업데이트 (스트림릿 슬라이더/체크박스 즉시 반영)

        Returns:
            bool: 실제로 변경이 적용되었는지 여부
        """
        updated = False

        with self._settings_lock:
            if confidence_threshold is not None:
                if abs(confidence_threshold - self.confidence_threshold) > 1e-6:
                    self.confidence_threshold = confidence_threshold
                    updated = True

            if detection_interval is not None:
                new_interval = max(0.1, float(detection_interval))
                if abs(new_interval - self.detection_interval) > 1e-6:
                    self.detection_interval = new_interval
                    updated = True

            if enable_face_analysis is not None:
                desired = bool(enable_face_analysis) and FACE_ANALYZER_AVAILABLE
                if desired and not self.enable_face_analysis:
                    try:
                        self.face_analyzer = FaceAnalyzer()
                        self.enable_face_analysis = True
                        updated = True
                        print("[DetectionEngine] ✅ 얼굴 분석 재활성화")
                    except Exception as exc:
                        self.enable_face_analysis = False
                        self.face_analyzer = None
                        print(f"[DetectionEngine] ⚠️ 얼굴 분석 활성화 실패: {exc}")
                elif not desired and self.enable_face_analysis:
                    self.enable_face_analysis = False
                    self.face_analyzer = None
                    updated = True
                    print("[DetectionEngine] ⏸ 얼굴 분석 비활성화")

        return updated

    def _detection_loop(self):
        """검출 루프 (스레드)"""
        print("[DetectionEngine] 검출 루프 시작")

        while self._running:
            # 소스에서 프레임 가져오기
            frame = self.source_manager.get_frame(timeout=0.5)

            if frame is None:
                continue

            # ROI denormalize (첫 프레임에서)
            if not self._rois_denormalized and len(self._roi_regions) > 0:
                self._denormalize_rois(frame)

            # 프레임 처리
            result = self._process_frame(frame)

            if result:
                # 결과 큐에 추가
                self._enqueue_result(result)

                # 시각화 프레임 큐에 추가
                if result.annotated_frame is not None:
                    self._enqueue_frame(result.annotated_frame)

                # 콜백 호출
                if self.on_detection_callback:
                    try:
                        self.on_detection_callback(result)
                    except Exception as e:
                        print(f"[DetectionEngine] 콜백 오류: {e}")

        print("[DetectionEngine] 검출 루프 종료")

    def _denormalize_rois(self, frame: np.ndarray):
        """ROI를 현재 프레임 크기에 맞게 변환"""
        with self._roi_lock:
            frame_height, frame_width = frame.shape[:2]
            self._roi_regions = denormalize_rois(
                self._roi_regions, frame_width, frame_height
            )
            self._rois_denormalized = True
            print(f"[DetectionEngine] ROI denormalized: {frame_width}x{frame_height}")

    def _process_frame(self, frame: np.ndarray) -> Optional[DetectionResult]:
        """프레임 처리"""
        current_time = time.time()
        detections = []
        face_analysis_results = {}

        # YOLO 추론 (설정된 간격마다)
        if current_time - self.last_detection_time >= self.detection_interval:
            start_inference = time.time()

            # YOLO 추론 (device 명시)
            results = self.model(frame, verbose=False, device=self.device)

            # 결과 파싱
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])

                    # 사람만 검출 (class 0)
                    if cls == 0 and conf >= self.confidence_threshold:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        detections.append(
                            {
                                "bbox": [int(x1), int(y1), int(x2), int(y2)],
                                "confidence": conf,
                                "class": cls,
                            }
                        )

            # 추론 시간 기록
            inference_time = (time.time() - start_inference) * 1000
            self.stats["inference_time_ms"] = inference_time
            self.stats["detections_count"] = len(detections)

            # ROI 상태 업데이트
            self._update_roi_states(detections, frame)

            # 얼굴 분석 (사람 검출된 경우)
            if self.enable_face_analysis and self.face_analyzer and len(detections) > 0:
                face_analysis_results = self._analyze_faces(frame, detections)

            # 캐시 업데이트
            self.last_detections = detections
            self.last_face_results = face_analysis_results
            self.last_detection_time = current_time
        else:
            # 이전 검출 결과 재사용
            detections = self.last_detections
            face_analysis_results = self.last_face_results

        # 시각화
        annotated_frame = self._draw_visualization(frame, detections)

        # 통계 업데이트
        self._update_stats()

        return DetectionResult(
            timestamp=current_time,
            frame=frame,
            detections=detections,
            roi_states=self._roi_states.copy(),
            face_results=face_analysis_results,
            annotated_frame=annotated_frame,
        )

    def _update_roi_states(self, detections: List[Dict], frame: np.ndarray):
        """ROI별 상태 업데이트"""
        current_time = time.time()

        with self._roi_lock:
            for roi in self._roi_regions:
                roi_id = roi.get("id", "unknown")

                if roi_id not in self._roi_states:
                    continue

                state = self._roi_states[roi_id]
                person_in_roi = False

                # 각 검출에 대해 ROI 내부인지 확인
                for detection in detections:
                    if self._is_person_in_roi(detection["bbox"], roi):
                        person_in_roi = True
                        state["detection_count"] += 1
                        break

                # 상태 변경 처리
                prev_detected = state["person_detected"]
                state["person_detected"] = person_in_roi

                if person_in_roi and not prev_detected:
                    # 새로 검출됨
                    state["detection_start_time"] = current_time
                    state["absence_start_time"] = None
                elif not person_in_roi and prev_detected:
                    # 사라짐
                    state["absence_start_time"] = current_time

                    # 부재 API 전송
                    if self.on_event_callback:
                        self.on_event_callback("absence", roi_id, {"frame": frame})

    def _is_person_in_roi(self, bbox: List[int], roi: Dict) -> bool:
        """사람이 ROI 내부에 있는지 확인"""
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        center_point = (int(center_x), int(center_y))

        if roi.get("type") == "polygon" and "points" in roi:
            points = np.array(roi["points"], dtype=np.int32)
            result = cv2.pointPolygonTest(points, center_point, False)
            return result >= 0

        return False

    def _analyze_faces(self, frame: np.ndarray, detections: List[Dict]) -> Dict:
        """얼굴 분석 수행"""
        face_results = {}

        for detection in detections:
            bbox = detection["bbox"]

            try:
                result = self.face_analyzer.analyze_face(frame, bbox)
                if result:
                    face_results[tuple(bbox)] = result

                    # SAD 표정 감지 시 이벤트
                    expr_info = result.get("expression", {})
                    if isinstance(expr_info, dict):
                        expression = expr_info.get("expression", "unknown")
                        confidence = expr_info.get("confidence", 0)

                        if expression == "sad" and confidence > 0.6:
                            if self.on_event_callback:
                                self.on_event_callback(
                                    "sad_expression",
                                    "detected",
                                    {
                                        "confidence": confidence,
                                        "bbox": bbox,
                                    },
                                )
            except Exception as e:
                print(f"[DetectionEngine] 얼굴 분석 오류: {e}")

        return face_results

    def _draw_visualization(
        self, frame: np.ndarray, detections: List[Dict]
    ) -> np.ndarray:
        """시각화 그리기"""
        annotated = frame.copy()

        # ROI 그리기
        with self._roi_lock:
            for roi in self._roi_regions:
                roi_id = roi.get("id", "unknown")
                state = self._roi_states.get(roi_id, {})
                color = (
                    (0, 255, 0) if state.get("person_detected", False) else (0, 0, 255)
                )

                if "points" in roi:
                    points = np.array(roi["points"], dtype=np.int32)

                    # 반투명 채우기
                    overlay = annotated.copy()
                    cv2.fillPoly(overlay, [points], color)
                    cv2.addWeighted(overlay, 0.2, annotated, 0.8, 0, annotated)

                    # 테두리
                    cv2.polylines(annotated, [points], True, color, 2)

                    # 라벨
                    M = cv2.moments(points)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        cv2.putText(
                            annotated,
                            roi_id,
                            (cx - 20, cy),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (255, 255, 255),
                            2,
                        )

        # 검출 박스 그리기
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            conf = det["confidence"]

            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                annotated,
                f"Person {conf:.2f}",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2,
            )

        # FPS 표시
        cv2.putText(
            annotated,
            f"FPS: {self.stats['current_fps']:.1f}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )

        return annotated

    def _enqueue_result(self, result: DetectionResult):
        """결과 큐에 추가"""
        try:
            if self.result_queue.full():
                try:
                    self.result_queue.get_nowait()
                except queue.Empty:
                    pass
            self.result_queue.put_nowait(result)
        except queue.Full:
            pass

    def _enqueue_frame(self, frame: np.ndarray):
        """프레임 큐에 추가"""
        try:
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass
            self.frame_queue.put_nowait(frame)
        except queue.Full:
            pass

    def _update_stats(self):
        """통계 업데이트"""
        self.stats["frames_processed"] += 1

        # FPS 계산
        self._fps_frame_count += 1
        elapsed = time.time() - self._fps_start_time

        if elapsed >= 1.0:
            self.stats["current_fps"] = self._fps_frame_count / elapsed
            self._fps_frame_count = 0
            self._fps_start_time = time.time()
