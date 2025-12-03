"""
FastAPI 설정 관리
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # API 설정
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "YOLO ROI Detection API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "실시간 YOLO ROI 사람 검출 시스템 - FastAPI Backend"
    
    # CORS 설정
    BACKEND_CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    
    # 데이터베이스 설정
    DATABASE_URL: str = "sqlite+aiosqlite:///./yolo_detection.db"
    
    # Redis 설정 (세션 관리용)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    USE_REDIS: bool = True  # True면 Redis 세션 관리, False면 메모리 기반
    
    # YOLO 모델 설정
    DEFAULT_YOLO_MODEL: str = "yolov8n.pt"
    YOLO_CONFIDENCE_THRESHOLD: float = 0.5
    DETECTION_INTERVAL_SECONDS: float = 1.0
    
    # 세션 설정
    SESSION_EXPIRE_MINUTES: int = 60
    MAX_SESSIONS: int = 100
    
    # 업로드 설정
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: str = "./uploads"
    
    # WebSocket 설정
    WS_HEARTBEAT_INTERVAL: int = 30  # seconds
    
    # 보안 설정
    SECRET_KEY: str = "your-secret-key-change-in-production-YOLO-ROI-2025"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8시간
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
