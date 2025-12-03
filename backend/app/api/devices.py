"""
Jetson 장비 관리 API 엔드포인트
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional

from ..models.device import (
    DeviceInfo, DeviceCreate, DeviceUpdate, DeviceResponse,
    DeviceStatus, DeviceStats, DeviceHeartbeat
)
from ..services.device_manager import device_manager
from ..core.security import get_current_user, get_current_admin

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("/", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def register_device(
    device_create: DeviceCreate,
    current_admin: dict = Depends(get_current_admin)
):
    """장비 등록 (관리자 전용)"""
    device = await device_manager.register_device(device_create)
    return device


@router.get("/", response_model=List[DeviceResponse])
async def list_devices(
    status_filter: Optional[DeviceStatus] = None,
    current_user: dict = Depends(get_current_user)
):
    """장비 목록 조회"""
    devices = await device_manager.list_devices(status=status_filter)
    return devices


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    current_user: dict = Depends(get_current_user)
):
    """장비 조회"""
    device = await device_manager.get_device(device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )
    return device


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: str,
    update: DeviceUpdate,
    current_admin: dict = Depends(get_current_admin)
):
    """장비 정보 업데이트 (관리자 전용)"""
    device = await device_manager.update_device(device_id, update)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )
    return device


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    """장비 삭제 (관리자 전용)"""
    success = await device_manager.delete_device(device_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )


@router.post("/{device_id}/heartbeat", status_code=status.HTTP_200_OK)
async def device_heartbeat(
    device_id: str,
    heartbeat: DeviceHeartbeat
):
    """
    장비 하트비트 전송
    (장비에서 주기적으로 호출 - 인증 불필요)
    """
    if heartbeat.device_id != device_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device ID mismatch"
        )
    
    await device_manager.update_heartbeat(heartbeat)
    return {"message": "Heartbeat received"}


@router.get("/{device_id}/stats", response_model=List[DeviceStats])
async def get_device_stats(
    device_id: str,
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """장비 통계 조회"""
    device = await device_manager.get_device(device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )
    
    stats = await device_manager.get_device_stats(device_id, limit)
    return stats


@router.get("/status/summary")
async def get_status_summary(current_user: dict = Depends(get_current_user)):
    """전체 장비 상태 요약"""
    all_devices = await device_manager.list_devices()
    
    summary = {
        "total": len(all_devices),
        "online": len([d for d in all_devices if d.status == DeviceStatus.ONLINE]),
        "offline": len([d for d in all_devices if d.status == DeviceStatus.OFFLINE]),
        "busy": len([d for d in all_devices if d.status == DeviceStatus.BUSY]),
        "error": len([d for d in all_devices if d.status == DeviceStatus.ERROR]),
        "maintenance": len([d for d in all_devices if d.status == DeviceStatus.MAINTENANCE]),
    }
    
    return summary
