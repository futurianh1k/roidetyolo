import { authService } from './authService';

class DeviceService {
  constructor() {
    this.apiClient = authService.apiClient;
  }

  async listDevices(statusFilter = null) {
    try {
      const params = statusFilter ? { status_filter: statusFilter } : {};
      const response = await this.apiClient.get('/devices/', { params });
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || '장비 목록 조회 실패');
    }
  }

  async getDevice(deviceId) {
    try {
      const response = await this.apiClient.get(`/devices/${deviceId}`);
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || '장비 조회 실패');
    }
  }

  async registerDevice(deviceData) {
    try {
      const response = await this.apiClient.post('/devices/', deviceData);
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || '장비 등록 실패');
    }
  }

  async updateDevice(deviceId, updateData) {
    try {
      const response = await this.apiClient.patch(`/devices/${deviceId}`, updateData);
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || '장비 정보 수정 실패');
    }
  }

  async deleteDevice(deviceId) {
    try {
      await this.apiClient.delete(`/devices/${deviceId}`);
      return true;
    } catch (error) {
      throw new Error(error.response?.data?.detail || '장비 삭제 실패');
    }
  }

  async getDeviceStats(deviceId, limit = 100) {
    try {
      const response = await this.apiClient.get(`/devices/${deviceId}/stats`, {
        params: { limit }
      });
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || '장비 통계 조회 실패');
    }
  }

  async getStatusSummary() {
    try {
      const response = await this.apiClient.get('/devices/status/summary');
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || '장비 상태 요약 조회 실패');
    }
  }

  async sendHeartbeat(deviceId, heartbeatData) {
    try {
      const response = await this.apiClient.post(
        `/devices/${deviceId}/heartbeat`,
        heartbeatData
      );
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || '하트비트 전송 실패');
    }
  }
}

export const deviceService = new DeviceService();
