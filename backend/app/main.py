"""
FastAPI 메인 애플리케이션
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from .core.config import settings
from .api import sessions, websocket
from .services.session_manager import session_manager
from .services.detection_service import detection_service_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # Startup
    print("🚀 Starting YOLO ROI Detection API...")
    await session_manager.start()
    print("✅ API started successfully!")
    
    yield
    
    # Shutdown
    print("⏹️ Shutting down API...")
    await detection_service_manager.stop_all()
    await session_manager.stop()
    print("👋 API shutdown complete")


# FastAPI 앱 생성
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    lifespan=lifespan
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 라우터 등록
app.include_router(sessions.router, prefix=settings.API_V1_STR)
app.include_router(websocket.router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """API 루트"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "description": settings.DESCRIPTION,
        "docs_url": "/docs",
        "api_v1": settings.API_V1_STR
    }


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "sessions": len(session_manager.sessions),
        "active_detections": len(detection_service_manager.services)
    }


@app.get(settings.API_V1_STR + "/info")
async def api_info():
    """API 정보"""
    return {
        "version": settings.VERSION,
        "max_sessions": settings.MAX_SESSIONS,
        "session_expire_minutes": settings.SESSION_EXPIRE_MINUTES,
        "default_yolo_model": settings.DEFAULT_YOLO_MODEL,
        "endpoints": {
            "sessions": settings.API_V1_STR + "/sessions",
            "websocket": settings.API_V1_STR + "/ws/{session_id}",
            "health": "/health",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
