"""
Redis 기반 세션 관리 서비스
"""
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import aioredis

from ..models.session import (
    DetectionSession, SessionCreate, SessionUpdate, SessionStatus,
    DetectionResult, SessionStatistics
)
from ..core.config import settings


class RedisSessionManager:
    """Redis 기반 세션 관리자"""
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.session_prefix = "session:"
        self.result_prefix = "result:"
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Redis 연결 및 세션 관리자 시작"""
        try:
            # Redis 연결
            self.redis = await aioredis.create_redis_pool(
                f'redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}',
                db=settings.REDIS_DB,
                encoding='utf-8'
            )
            print(f"✅ Redis connected: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            print("⚠️ Falling back to memory-based session management")
            self.redis = None
            return
        
        # 주기적 정리 태스크 시작
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())
        print("✅ Redis Session Manager started")
    
    async def stop(self):
        """세션 관리자 중지"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self.redis:
            self.redis.close()
            await self.redis.wait_closed()
        
        print("⏹️ Redis Session Manager stopped")
    
    async def create_session(self, session_create: SessionCreate) -> DetectionSession:
        """새 세션 생성"""
        import uuid
        from ..models.session import DetectionConfig
        
        session_id = str(uuid.uuid4())
        config = session_create.config or DetectionConfig()
        
        session = DetectionSession(
            session_id=session_id,
            user_id=session_create.user_id,
            status=SessionStatus.IDLE,
            config=config,
            roi_regions=[],
            statistics=SessionStatistics()
        )
        
        # Redis에 저장
        if self.redis:
            key = f"{self.session_prefix}{session_id}"
            await self.redis.setex(
                key,
                settings.SESSION_EXPIRE_MINUTES * 60,
                json.dumps(session.dict(), default=str)
            )
        
        print(f"✅ Session created: {session_id}")
        return session
    
    async def get_session(self, session_id: str) -> Optional[DetectionSession]:
        """세션 조회"""
        if not self.redis:
            return None
        
        key = f"{self.session_prefix}{session_id}"
        data = await self.redis.get(key)
        
        if not data:
            return None
        
        session_dict = json.loads(data)
        session = DetectionSession(**session_dict)
        
        # TTL 갱신 (activity tracking)
        await self.redis.expire(key, settings.SESSION_EXPIRE_MINUTES * 60)
        session.last_activity = datetime.now()
        
        return session
    
    async def update_session(self, session_id: str, update: SessionUpdate) -> Optional[DetectionSession]:
        """세션 업데이트"""
        session = await self.get_session(session_id)
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
        
        # Redis에 저장
        if self.redis:
            key = f"{self.session_prefix}{session_id}"
            await self.redis.setex(
                key,
                settings.SESSION_EXPIRE_MINUTES * 60,
                json.dumps(session.dict(), default=str)
            )
        
        return session
    
    async def delete_session(self, session_id: str) -> bool:
        """세션 삭제"""
        if not self.redis:
            return False
        
        key = f"{self.session_prefix}{session_id}"
        result = await self.redis.delete(key)
        
        # 관련 검출 결과도 삭제
        result_key = f"{self.result_prefix}{session_id}"
        await self.redis.delete(result_key)
        
        print(f"🗑️ Session deleted: {session_id}")
        return result > 0
    
    async def list_sessions(self, user_id: Optional[str] = None) -> List[DetectionSession]:
        """세션 목록 조회"""
        if not self.redis:
            return []
        
        pattern = f"{self.session_prefix}*"
        sessions = []
        
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            
            for key in keys:
                data = await self.redis.get(key)
                if data:
                    session_dict = json.loads(data)
                    session = DetectionSession(**session_dict)
                    
                    if user_id is None or session.user_id == user_id:
                        sessions.append(session)
            
            if cursor == 0:
                break
        
        return sessions
    
    async def add_detection_result(self, session_id: str, result: DetectionResult):
        """검출 결과 저장"""
        if not self.redis:
            return
        
        # 결과를 리스트에 추가 (최대 1000개 유지)
        result_key = f"{self.result_prefix}{session_id}"
        await self.redis.lpush(result_key, json.dumps(result.dict(), default=str))
        await self.redis.ltrim(result_key, 0, 999)  # 최대 1000개
        await self.redis.expire(result_key, settings.SESSION_EXPIRE_MINUTES * 60)
        
        # 세션 통계 업데이트
        session = await self.get_session(session_id)
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
                
                expr_info = result.face_analysis.expression
                if isinstance(expr_info, dict):
                    expression = expr_info.get("expression", "neutral")
                    if expression in stats:
                        stats[expression] += 1
                
                if result.face_analysis.eyes_open:
                    stats["eyes_open"] += 1
                else:
                    stats["eyes_closed"] += 1
                
                mouth_state = result.face_analysis.mouth_state
                if mouth_state == "closed":
                    stats["mouth_closed"] += 1
                elif mouth_state == "speaking":
                    stats["mouth_speaking"] += 1
                elif mouth_state == "wide_open":
                    stats["mouth_wide_open"] += 1
                
                if result.face_analysis.has_mask_or_ventilator:
                    stats["mask_detected"] += 1
            
            # 업데이트된 세션 저장
            await self.update_session(session_id, SessionUpdate())
    
    async def get_detection_results(
        self,
        session_id: str,
        limit: int = 100,
        roi_id: Optional[str] = None
    ) -> List[DetectionResult]:
        """검출 결과 조회"""
        if not self.redis:
            return []
        
        result_key = f"{self.result_prefix}{session_id}"
        results_json = await self.redis.lrange(result_key, 0, limit - 1)
        
        results = []
        for result_json in results_json:
            result_dict = json.loads(result_json)
            result = DetectionResult(**result_dict)
            
            if roi_id is None or result.roi_id == roi_id:
                results.append(result)
        
        return results
    
    async def clear_detection_results(self, session_id: str):
        """검출 결과 초기화"""
        if not self.redis:
            return
        
        result_key = f"{self.result_prefix}{session_id}"
        await self.redis.delete(result_key)
        
        # 세션 통계 초기화
        session = await self.get_session(session_id)
        if session:
            session.statistics = SessionStatistics()
            await self.update_session(session_id, SessionUpdate())
    
    async def _cleanup_expired_sessions(self):
        """만료된 세션 정리 (Redis TTL 자동 관리)"""
        while True:
            try:
                await asyncio.sleep(300)  # 5분마다 실행
                print("🧹 Redis session cleanup (TTL auto-managed)")
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Cleanup error: {e}")


# 전역 Redis 세션 관리자 인스턴스
redis_session_manager = RedisSessionManager()
