"""
WebSocket 엔드포인트 - 실시간 비디오 스트림 및 검출 결과
"""
import asyncio
import json
import cv2
import base64
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set

from ..services.session_manager import session_manager
from ..services.detection_service import detection_service_manager

router = APIRouter()


class ConnectionManager:
    """WebSocket 연결 관리자"""
    
    def __init__(self):
        # {session_id: Set[WebSocket]}
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """WebSocket 연결"""
        await websocket.accept()
        
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        
        self.active_connections[session_id].add(websocket)
        print(f"✅ WebSocket connected: session={session_id}, total={len(self.active_connections[session_id])}")
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        """WebSocket 연결 해제"""
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        
        print(f"❌ WebSocket disconnected: session={session_id}")
    
    async def send_message(self, message: dict, session_id: str):
        """특정 세션의 모든 클라이언트에게 메시지 전송"""
        if session_id not in self.active_connections:
            return
        
        disconnected = set()
        
        for connection in self.active_connections[session_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"❌ Send error: {e}")
                disconnected.add(connection)
        
        # 연결 실패한 클라이언트 제거
        for connection in disconnected:
            self.disconnect(connection, session_id)
    
    async def broadcast(self, message: dict):
        """모든 클라이언트에게 메시지 전송"""
        for session_id in list(self.active_connections.keys()):
            await self.send_message(message, session_id)


manager = ConnectionManager()


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket 엔드포인트
    
    메시지 포맷:
    - type: "frame" - 비디오 프레임 (JPEG base64)
    - type: "stats" - 통계 업데이트
    - type: "event" - 검출 이벤트
    - type: "fps" - FPS 정보
    """
    await manager.connect(websocket, session_id)
    
    # 세션 확인
    session = await session_manager.get_session(session_id)
    if not session:
        await websocket.close(code=1003, reason="Session not found")
        return
    
    # 프레임 스트리밍 태스크
    stream_task = asyncio.create_task(stream_frames(websocket, session_id))
    
    try:
        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 메시지 타입별 처리
            msg_type = message.get("type")
            
            if msg_type == "ping":
                # Heartbeat
                await websocket.send_json({"type": "pong"})
            
            elif msg_type == "request_frame":
                # 프레임 요청 (이미 스트리밍 중이므로 무시)
                pass
            
            elif msg_type == "request_stats":
                # 통계 요청
                session = await session_manager.get_session(session_id)
                if session:
                    await websocket.send_json({
                        "type": "stats",
                        "data": session.statistics.dict()
                    })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
    
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        manager.disconnect(websocket, session_id)
    
    finally:
        # 스트리밍 태스크 종료
        stream_task.cancel()
        try:
            await stream_task
        except asyncio.CancelledError:
            pass


async def stream_frames(websocket: WebSocket, session_id: str):
    """비디오 프레임 스트리밍"""
    try:
        while True:
            # 검출 서비스에서 최신 프레임 가져오기
            service = detection_service_manager.get_service(session_id)
            
            if service:
                frame = service.get_latest_frame()
                
                if frame is not None:
                    # JPEG로 인코딩
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    
                    # Base64 인코딩
                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                    
                    # FPS 정보
                    fps = service.get_fps()
                    
                    # 프레임 전송
                    await websocket.send_json({
                        "type": "frame",
                        "data": frame_base64,
                        "fps": fps,
                        "timestamp": asyncio.get_event_loop().time()
                    })
            
            # 세션 통계 전송 (5초마다)
            if asyncio.get_event_loop().time() % 5 < 0.1:
                session = await session_manager.get_session(session_id)
                if session:
                    await websocket.send_json({
                        "type": "stats",
                        "data": session.statistics.dict()
                    })
            
            # 프레임 레이트 제한 (30 FPS)
            await asyncio.sleep(1 / 30)
    
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"❌ Frame streaming error: {e}")
