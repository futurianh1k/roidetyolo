"""
Jetson 장비 관리 서비스
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import aiohttp

from ..models.device import (
    DeviceInfo, DeviceCreate, DeviceUpdate, DeviceStatus,
    DeviceStats, DeviceHeartbeat, DeviceType
)


class DeviceManager:
    """Jetson 장비 관리자"""
    
    def __init__(self):
        self.devices: Dict[str, DeviceInfo] = {}
        self.device_stats: Dict[str, List[DeviceStats]] = {}
        self._monitor_task: Optional[asyncio.Task] = None
        self.max_stats_history = 100  # 최대 통계 히스토리 개수
    
    async def start(self):
        """장비 관리자 시작"""
        print("✅ Device Manager started")
        # 주기적으로 장비 상태 모니터링
        self._monitor_task = asyncio.create_task(self._monitor_devices())
    
    async def stop(self):
        """장비 관리자 중지"""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        print("⏹️ Device Manager stopped")
    
    async def register_device(self, device_create: DeviceCreate) -> DeviceInfo:
        """장비 등록"""
        import uuid
        
        device_id = str(uuid.uuid4())
        
        device = DeviceInfo(
            device_id=device_id,
            name=device_create.name,
            device_type=device_create.device_type,
            ip_address=device_create.ip_address,
            port=device_create.port,
            status=DeviceStatus.OFFLINE,
            description=device_create.description,
            location=device_create.location,
            owner=device_create.owner,
            tags=device_create.tags
        )
        
        self.devices[device_id] = device
        self.device_stats[device_id] = []
        
        print(f"✅ Device registered: {device_id} ({device.name} at {device.ip_address})")
        
        # 즉시 상태 체크
        await self._check_device_status(device_id)
        
        return device
    
    async def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """장비 조회"""
        return self.devices.get(device_id)
    
    async def list_devices(self, status: Optional[DeviceStatus] = None) -> List[DeviceInfo]:
        """장비 목록 조회"""
        devices = list(self.devices.values())
        
        if status:
            devices = [d for d in devices if d.status == status]
        
        return devices
    
    async def update_device(self, device_id: str, update: DeviceUpdate) -> Optional[DeviceInfo]:
        """장비 정보 업데이트"""
        device = self.devices.get(device_id)
        if not device:
            return None
        
        if update.name is not None:
            device.name = update.name
        if update.status is not None:
            device.status = update.status
        if update.description is not None:
            device.description = update.description
        if update.location is not None:
            device.location = update.location
        if update.owner is not None:
            device.owner = update.owner
        if update.tags is not None:
            device.tags = update.tags
        
        device.updated_at = datetime.now()
        
        return device
    
    async def delete_device(self, device_id: str) -> bool:
        """장비 삭제"""
        if device_id in self.devices:
            del self.devices[device_id]
            if device_id in self.device_stats:
                del self.device_stats[device_id]
            print(f"🗑️ Device deleted: {device_id}")
            return True
        return False
    
    async def update_heartbeat(self, heartbeat: DeviceHeartbeat):
        """장비 하트비트 업데이트"""
        device = self.devices.get(heartbeat.device_id)
        if not device:
            return
        
        device.status = heartbeat.status
        device.last_heartbeat = heartbeat.timestamp
        device.updated_at = datetime.now()
        
        # 통계 저장
        if heartbeat.stats:
            if heartbeat.device_id not in self.device_stats:
                self.device_stats[heartbeat.device_id] = []
            
            self.device_stats[heartbeat.device_id].append(heartbeat.stats)
            
            # 최대 개수 유지
            if len(self.device_stats[heartbeat.device_id]) > self.max_stats_history:
                self.device_stats[heartbeat.device_id] = \
                    self.device_stats[heartbeat.device_id][-self.max_stats_history:]
    
    async def get_device_stats(self, device_id: str, limit: int = 100) -> List[DeviceStats]:
        """장비 통계 조회"""
        stats = self.device_stats.get(device_id, [])
        return stats[-limit:]
    
    async def _check_device_status(self, device_id: str):
        """장비 상태 체크 (HTTP 헬스체크)"""
        device = self.devices.get(device_id)
        if not device:
            return
        
        try:
            url = f"http://{device.ip_address}:{device.port}/health"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        device.status = DeviceStatus.ONLINE
                        device.last_heartbeat = datetime.now()
                        
                        # 응답에서 통계 정보 추출 (선택사항)
                        try:
                            data = await response.json()
                            # TODO: DeviceStats 파싱
                        except:
                            pass
                    else:
                        device.status = DeviceStatus.ERROR
        
        except asyncio.TimeoutError:
            device.status = DeviceStatus.OFFLINE
        except Exception as e:
            device.status = DeviceStatus.OFFLINE
            print(f"❌ Device check failed ({device_id}): {e}")
    
    async def _monitor_devices(self):
        """주기적으로 모든 장비 상태 모니터링"""
        while True:
            try:
                await asyncio.sleep(30)  # 30초마다 체크
                
                for device_id in list(self.devices.keys()):
                    await self._check_device_status(device_id)
                
                # Offline 판단 (하트비트 90초 초과)
                for device in self.devices.values():
                    if device.last_heartbeat:
                        elapsed = (datetime.now() - device.last_heartbeat).total_seconds()
                        if elapsed > 90 and device.status != DeviceStatus.OFFLINE:
                            device.status = DeviceStatus.OFFLINE
                            print(f"⚠️ Device went offline: {device.device_id} ({device.name})")
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Monitor error: {e}")


# 전역 장비 관리자 인스턴스
device_manager = DeviceManager()
