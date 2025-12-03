"""
세션 모델 정의
"""
from datetime import datetime
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field
from enum import Enum


class SessionStatus(str, Enum):
    """세션 상태"""
    IDLE = "idle"
    DETECTING = "detecting"
    PAUSED = "paused"
    STOPPED = "stopped"


class ROIRegion(BaseModel):
    """ROI 영역 정의"""
    id: str
    description: str
    type: str = "polygon"
    points: List[List[int]]
    enabled: bool = True


class DetectionConfig(BaseModel):
    """검출 설정"""
    yolo_model: str = "yolov8n.pt"
    camera_source: int = 0
    confidence_threshold: float = 0.5
    detection_interval: float = 1.0
    presence_threshold: int = 5
    absence_threshold: int = 3
    enable_face_analysis: bool = True
    face_analysis_roi_only: bool = False


class FaceAnalysisResult(BaseModel):
    """얼굴 분석 결과"""
    face_detected: bool
    eyes_open: bool
    mouth_state: str  # closed, speaking, wide_open
    expression: Dict[str, Any]  # {expression: str, confidence: float}
    has_mask_or_ventilator: bool
    device_confidence: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class DetectionResult(BaseModel):
    """검출 결과"""
    session_id: str
    roi_id: str
    status: str  # present, absent
    person_detected: bool
    confidence: float
    bbox: Optional[List[int]] = None  # [x1, y1, x2, y2]
    face_analysis: Optional[FaceAnalysisResult] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class SessionStatistics(BaseModel):
    """세션 통계"""
    total_detections: int = 0
    roi_stats: Dict[str, Dict[str, int]] = {}  # {roi_id: {present: count, absent: count}}
    face_stats: Dict[str, int] = {
        "total_faces": 0,
        "neutral": 0,
        "happy": 0,
        "sad": 0,
        "surprised": 0,
        "pain": 0,
        "angry": 0,
        "eyes_open": 0,
        "eyes_closed": 0,
        "mouth_closed": 0,
        "mouth_speaking": 0,
        "mouth_wide_open": 0,
        "mask_detected": 0,
    }


class DetectionSession(BaseModel):
    """검출 세션"""
    session_id: str
    user_id: Optional[str] = None
    status: SessionStatus = SessionStatus.IDLE
    config: DetectionConfig
    roi_regions: List[ROIRegion] = []
    statistics: SessionStatistics = Field(default_factory=SessionStatistics)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SessionCreate(BaseModel):
    """세션 생성 요청"""
    user_id: Optional[str] = None
    config: Optional[DetectionConfig] = None


class SessionUpdate(BaseModel):
    """세션 업데이트 요청"""
    status: Optional[SessionStatus] = None
    config: Optional[DetectionConfig] = None
    roi_regions: Optional[List[ROIRegion]] = None


class SessionResponse(BaseModel):
    """세션 응답"""
    session_id: str
    status: SessionStatus
    config: DetectionConfig
    roi_regions: List[ROIRegion]
    statistics: SessionStatistics
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
