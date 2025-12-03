"""
세션 관리 API 엔드포인트
"""
from fastapi import APIRouter, HTTPException, status
from typing import List, Optional

from ..models.session import (
    DetectionSession, SessionCreate, SessionUpdate, SessionResponse,
    SessionStatus, ROIRegion
)
from ..services.session_manager import session_manager
from ..services.detection_service import detection_service_manager

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(session_create: SessionCreate):
    """새 검출 세션 생성"""
    session = await session_manager.create_session(session_create)
    return session


@router.get("/", response_model=List[SessionResponse])
async def list_sessions(user_id: Optional[str] = None):
    """세션 목록 조회"""
    sessions = await session_manager.list_sessions(user_id)
    return sessions


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """세션 조회"""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    return session


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(session_id: str, update: SessionUpdate):
    """세션 업데이트"""
    session = await session_manager.update_session(session_id, update)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str):
    """세션 삭제"""
    # 검출 중이면 먼저 중지
    await detection_service_manager.stop_detection(session_id)
    
    success = await session_manager.delete_session(session_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )


@router.post("/{session_id}/roi", response_model=SessionResponse)
async def add_roi_region(session_id: str, roi: ROIRegion):
    """ROI 영역 추가"""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    # ROI 추가
    session.roi_regions.append(roi)
    
    update = SessionUpdate(roi_regions=session.roi_regions)
    updated_session = await session_manager.update_session(session_id, update)
    
    return updated_session


@router.delete("/{session_id}/roi/{roi_id}", response_model=SessionResponse)
async def remove_roi_region(session_id: str, roi_id: str):
    """ROI 영역 삭제"""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    # ROI 삭제
    session.roi_regions = [roi for roi in session.roi_regions if roi.id != roi_id]
    
    update = SessionUpdate(roi_regions=session.roi_regions)
    updated_session = await session_manager.update_session(session_id, update)
    
    return updated_session


@router.post("/{session_id}/start", response_model=SessionResponse)
async def start_detection(session_id: str):
    """검출 시작"""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    if not session.roi_regions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No ROI regions defined. Please add at least one ROI region."
        )
    
    # 검출 서비스 시작
    await detection_service_manager.start_detection(session)
    
    # 세션 상태 업데이트
    update = SessionUpdate(status=SessionStatus.DETECTING)
    updated_session = await session_manager.update_session(session_id, update)
    
    return updated_session


@router.post("/{session_id}/stop", response_model=SessionResponse)
async def stop_detection(session_id: str):
    """검출 중지"""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    # 검출 서비스 중지
    await detection_service_manager.stop_detection(session_id)
    
    # 세션 상태 업데이트
    update = SessionUpdate(status=SessionStatus.STOPPED)
    updated_session = await session_manager.update_session(session_id, update)
    
    return updated_session


@router.get("/{session_id}/statistics")
async def get_statistics(session_id: str):
    """세션 통계 조회"""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    return session.statistics


@router.post("/{session_id}/statistics/reset", response_model=SessionResponse)
async def reset_statistics(session_id: str):
    """세션 통계 초기화"""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    await session_manager.clear_detection_results(session_id)
    
    updated_session = await session_manager.get_session(session_id)
    return updated_session


@router.get("/{session_id}/results")
async def get_detection_results(
    session_id: str,
    limit: int = 100,
    roi_id: Optional[str] = None
):
    """검출 결과 조회"""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    results = await session_manager.get_detection_results(session_id, limit, roi_id)
    return results
