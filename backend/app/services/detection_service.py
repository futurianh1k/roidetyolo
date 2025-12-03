"""
YOLO 검출 서비스 - realtime_detector.py 래퍼
"""
import asyncio
import queue
from typing import Optional, Dict, Any
from pathlib import Path
import sys

# 기존 realtime_detector 임포트
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from realtime_detector import RealtimeDetector

from ..models.session import DetectionSession, DetectionResult, FaceAnalysisResult


class DetectionService:
    """검출 서비스 - RealtimeDetector를 비동기로 래핑"""
    
    def __init__(self, session: DetectionSession):
        self.session = session
        self.detector: Optional[RealtimeDetector] = None
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """검출 시작"""
        if self._running:
            return
        
        # RealtimeDetector 설정 준비
        config = {
            "yolo_model": self.session.config.yolo_model,
            "camera_source": self.session.config.camera_source,
            "confidence_threshold": self.session.config.confidence_threshold,
            "detection_interval_seconds": self.session.config.detection_interval,
            "presence_threshold_seconds": self.session.config.presence_threshold,
            "absence_threshold_seconds": self.session.config.absence_threshold,
            "enable_face_analysis": self.session.config.enable_face_analysis,
            "face_analysis_roi_only": self.session.config.face_analysis_roi_only,
        }
        
        # ROI 영역 변환
        roi_regions = [
            {
                "id": roi.id,
                "description": roi.description,
                "type": roi.type,
                "points": roi.points,
            }
            for roi in self.session.roi_regions
        ]
        
        # RealtimeDetector 생성 및 시작
        self.detector = RealtimeDetector(config, roi_regions)
        self.detector.start()
        
        self._running = True
        
        # 모니터링 태스크 시작 (결과 수집)
        self._monitor_task = asyncio.create_task(self._monitor_detection())
        
        print(f"✅ Detection started for session: {self.session.session_id}")
    
    async def stop(self):
        """검출 중지"""
        if not self._running:
            return
        
        self._running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        if self.detector:
            self.detector.stop()
            self.detector = None
        
        print(f"⏹️ Detection stopped for session: {self.session.session_id}")
    
    def get_latest_frame(self):
        """최신 프레임 가져오기"""
        if self.detector:
            return self.detector.get_latest_frame()
        return None
    
    def get_fps(self) -> float:
        """현재 FPS 가져오기"""
        if self.detector:
            return self.detector.fps
        return 0.0
    
    async def _monitor_detection(self):
        """검출 결과 모니터링 (백그라운드 태스크)"""
        while self._running:
            try:
                await asyncio.sleep(0.1)  # 100ms 간격
                
                if not self.detector:
                    continue
                
                # 통계 업데이트 가져오기
                stats = self.detector.get_latest_stats()
                for stat in stats:
                    # DetectionResult 생성 (간단 버전)
                    result = DetectionResult(
                        session_id=self.session.session_id,
                        roi_id=stat.get("roi_id", "unknown"),
                        status=stat.get("status", "unknown"),
                        person_detected=stat.get("status") == "present",
                        confidence=0.0,  # 통계에는 confidence 없음
                    )
                    
                    # 세션 매니저에 결과 저장 (여기서는 직접 호출 대신 외부에서 처리)
                    # await session_manager.add_detection_result(self.session.session_id, result)
                
                # 얼굴 분석 결과 가져오기
                if hasattr(self.detector, 'last_face_results') and self.detector.last_face_results:
                    for bbox, face_result in self.detector.last_face_results.items():
                        if face_result and face_result.get('face_detected'):
                            # FaceAnalysisResult 생성
                            expr_info = face_result.get('expression', {})
                            if isinstance(expr_info, dict):
                                expression = {
                                    "expression": expr_info.get("expression", "neutral"),
                                    "confidence": expr_info.get("confidence", 0.0)
                                }
                            else:
                                expression = {"expression": "neutral", "confidence": 0.0}
                            
                            face_analysis = FaceAnalysisResult(
                                face_detected=True,
                                eyes_open=face_result.get('eyes_open', False),
                                mouth_state=face_result.get('mouth_state', 'closed'),
                                expression=expression,
                                has_mask_or_ventilator=face_result.get('has_mask_or_ventilator', False),
                                device_confidence=face_result.get('device_confidence')
                            )
                            
                            # 얼굴 분석 결과 포함한 DetectionResult 생성
                            # (실제로는 어떤 ROI에 속하는지 판단 필요)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Monitoring error: {e}")


class DetectionServiceManager:
    """검출 서비스 관리자 - 세션별 DetectionService 관리"""
    
    def __init__(self):
        self.services: Dict[str, DetectionService] = {}
    
    async def start_detection(self, session: DetectionSession) -> DetectionService:
        """세션의 검출 시작"""
        session_id = session.session_id
        
        # 기존 서비스가 있으면 중지
        if session_id in self.services:
            await self.stop_detection(session_id)
        
        # 새 서비스 생성 및 시작
        service = DetectionService(session)
        await service.start()
        
        self.services[session_id] = service
        return service
    
    async def stop_detection(self, session_id: str):
        """세션의 검출 중지"""
        service = self.services.get(session_id)
        if service:
            await service.stop()
            del self.services[session_id]
    
    def get_service(self, session_id: str) -> Optional[DetectionService]:
        """검출 서비스 조회"""
        return self.services.get(session_id)
    
    async def stop_all(self):
        """모든 검출 중지"""
        tasks = [self.stop_detection(sid) for sid in list(self.services.keys())]
        await asyncio.gather(*tasks, return_exceptions=True)


# 전역 검출 서비스 관리자 인스턴스
detection_service_manager = DetectionServiceManager()
