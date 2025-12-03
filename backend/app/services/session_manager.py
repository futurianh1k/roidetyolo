"""
세션 관리 서비스
"""
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from ..models.session import (
    DetectionSession, SessionCreate, SessionUpdate, SessionStatus,
    DetectionResult, SessionStatistics
)
from ..core.config import settings


class SessionManager:
    """세션 관리자 - 메모리 기반 (확장 시 Redis로 전환 가능)"""
    
    def __init__(self):
        self.sessions: Dict[str, DetectionSession] = {}
        self.detection_results: Dict[str, List[DetectionResult]] = {}  # {session_id: [results]}
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """세션 관리자 시작"""
        print("✅ Session Manager started")
        # 주기적으로 만료된 세션 정리
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())
    
    async def stop(self):
        """세션 관리자 중지"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        print("⏹️ Session Manager stopped")
    
    async def create_session(self, session_create: SessionCreate) -> DetectionSession:
        """새 세션 생성"""
        # 최대 세션 수 확인
        if len(self.sessions) >= settings.MAX_SESSIONS:
            # 가장 오래된 세션 삭제
            oldest_session_id = min(
                self.sessions.keys(),
                key=lambda sid: self.sessions[sid].last_activity
            )
            await self.delete_session(oldest_session_id)
        
        session_id = str(uuid.uuid4())
        
        # 기본 설정 사용
        from ..models.session import DetectionConfig
        config = session_create.config or DetectionConfig()
        
        session = DetectionSession(
            session_id=session_id,
            user_id=session_create.user_id,
            status=SessionStatus.IDLE,
            config=config,
            roi_regions=[],
            statistics=SessionStatistics()
        )
        
        self.sessions[session_id] = session
        self.detection_results[session_id] = []
        
        print(f"✅ Session created: {session_id}")
        return session
    
    async def get_session(self, session_id: str) -> Optional[DetectionSession]:
        """세션 조회"""
        session = self.sessions.get(session_id)
        if session:
            session.last_activity = datetime.now()
        return session
    
    async def update_session(self, session_id: str, update: SessionUpdate) -> Optional[DetectionSession]:
        """세션 업데이트"""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        if update.status is not None:
            session.status = update.status
        if update.config is not None:
            session.config = update.config
        if update.roi_regions is not None:
            session.roi_regions = update.roi_regions
        
        session.updated_at = datetime.now()
        session.last_activity = datetime.now()
        
        return session
    
    async def delete_session(self, session_id: str) -> bool:
        """세션 삭제"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            if session_id in self.detection_results:
                del self.detection_results[session_id]
            print(f"🗑️ Session deleted: {session_id}")
            return True
        return False
    
    async def list_sessions(self, user_id: Optional[str] = None) -> List[DetectionSession]:
        """세션 목록 조회"""
        sessions = list(self.sessions.values())
        if user_id:
            sessions = [s for s in sessions if s.user_id == user_id]
        return sessions
    
    async def add_detection_result(self, session_id: str, result: DetectionResult):
        """검출 결과 저장"""
        if session_id not in self.detection_results:
            self.detection_results[session_id] = []
        
        self.detection_results[session_id].append(result)
        
        # 통계 업데이트
        session = self.sessions.get(session_id)
        if session:
            session.statistics.total_detections += 1
            
            # ROI 통계
            if result.roi_id not in session.statistics.roi_stats:
                session.statistics.roi_stats[result.roi_id] = {"present": 0, "absent": 0}
            
            if result.status in ["present", "absent"]:
                session.statistics.roi_stats[result.roi_id][result.status] += 1
            
            # 얼굴 분석 통계
            if result.face_analysis and result.face_analysis.face_detected:
                stats = session.statistics.face_stats
                stats["total_faces"] += 1
                
                # 표정
                expr_info = result.face_analysis.expression
                if isinstance(expr_info, dict):
                    expression = expr_info.get("expression", "neutral")
                    if expression in stats:
                        stats[expression] += 1
                
                # 눈 상태
                if result.face_analysis.eyes_open:
                    stats["eyes_open"] += 1
                else:
                    stats["eyes_closed"] += 1
                
                # 입 상태
                mouth_state = result.face_analysis.mouth_state
                if mouth_state == "closed":
                    stats["mouth_closed"] += 1
                elif mouth_state == "speaking":
                    stats["mouth_speaking"] += 1
                elif mouth_state == "wide_open":
                    stats["mouth_wide_open"] += 1
                
                # 마스크/호흡기
                if result.face_analysis.has_mask_or_ventilator:
                    stats["mask_detected"] += 1
            
            session.last_activity = datetime.now()
    
    async def get_detection_results(
        self, 
        session_id: str, 
        limit: int = 100,
        roi_id: Optional[str] = None
    ) -> List[DetectionResult]:
        """검출 결과 조회"""
        results = self.detection_results.get(session_id, [])
        
        if roi_id:
            results = [r for r in results if r.roi_id == roi_id]
        
        # 최신 결과부터 반환
        return list(reversed(results[-limit:]))
    
    async def clear_detection_results(self, session_id: str):
        """검출 결과 초기화"""
        if session_id in self.detection_results:
            self.detection_results[session_id] = []
            
        session = self.sessions.get(session_id)
        if session:
            session.statistics = SessionStatistics()
    
    async def _cleanup_expired_sessions(self):
        """만료된 세션 정리 (주기적 실행)"""
        while True:
            try:
                await asyncio.sleep(60)  # 1분마다 실행
                
                now = datetime.now()
                expire_time = timedelta(minutes=settings.SESSION_EXPIRE_MINUTES)
                
                expired_sessions = [
                    sid for sid, session in self.sessions.items()
                    if now - session.last_activity > expire_time
                ]
                
                for session_id in expired_sessions:
                    await self.delete_session(session_id)
                    print(f"🧹 Expired session cleaned: {session_id}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Cleanup error: {e}")


# 전역 세션 관리자 인스턴스
session_manager = SessionManager()
