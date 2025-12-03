"""
Jetson 장비 관리 모델
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class DeviceStatus(str, Enum):
    """장비 상태"""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class DeviceType(str, Enum):
    """장비 타입"""
    JETSON_NANO = "jetson_nano"
    JETSON_ORIN_NANO = "jetson_orin_nano"
    JETSON_ORIN_NX = "jetson_orin_nx"
    JETSON_AGX_ORIN = "jetson_agx_orin"
    OTHER = "other"


class DeviceInfo(BaseModel):
    """장비 정보"""
    device_id: str
    name: str
    device_type: DeviceType
    ip_address: str
    port: int = 8000
    status: DeviceStatus = DeviceStatus.OFFLINE
    description: Optional[str] = None
    
    # 하드웨어 스펙
    cpu_cores: Optional[int] = None
    gpu_model: Optional[str] = None
    memory_gb: Optional[float] = None
    
    # 소프트웨어 버전
    jetpack_version: Optional[str] = None
    cuda_version: Optional[str] = None
    python_version: Optional[str] = None
    
    # 메타데이터
    location: Optional[str] = None
    owner: Optional[str] = None
    tags: list[str] = []
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_heartbeat: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DeviceCreate(BaseModel):
    """장비 등록 요청"""
    name: str
    device_type: DeviceType
    ip_address: str
    port: int = 8000
    description: Optional[str] = None
    location: Optional[str] = None
    owner: Optional[str] = None
    tags: list[str] = []


class DeviceUpdate(BaseModel):
    """장비 업데이트 요청"""
    name: Optional[str] = None
    status: Optional[DeviceStatus] = None
    description: Optional[str] = None
    location: Optional[str] = None
    owner: Optional[str] = None
    tags: Optional[list[str]] = None


class DeviceStats(BaseModel):
    """장비 상태 통계"""
    device_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # 시스템 리소스
    cpu_usage: float  # 0-100%
    memory_usage: float  # 0-100%
    gpu_usage: Optional[float] = None  # 0-100%
    temperature: Optional[float] = None  # Celsius
    
    # 네트워크
    network_rx_bytes: Optional[int] = None
    network_tx_bytes: Optional[int] = None
    
    # YOLO 검출 성능
    fps: Optional[float] = None
    active_sessions: int = 0
    total_detections: int = 0


class DeviceHeartbeat(BaseModel):
    """장비 하트비트"""
    device_id: str
    status: DeviceStatus
    timestamp: datetime = Field(default_factory=datetime.now)
    stats: Optional[DeviceStats] = None


class DeviceResponse(BaseModel):
    """장비 응답"""
    device_id: str
    name: str
    device_type: DeviceType
    ip_address: str
    port: int
    status: DeviceStatus
    description: Optional[str]
    location: Optional[str]
    owner: Optional[str]
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    last_heartbeat: Optional[datetime]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
