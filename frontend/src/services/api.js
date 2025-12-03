import axios from 'axios';

const API_BASE_URL = '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 세션 관리
export const sessionAPI = {
  // 세션 생성
  createSession: async (userId = null) => {
    const response = await api.post('/sessions/', { user_id: userId });
    return response.data;
  },

  // 세션 목록 조회
  listSessions: async (userId = null) => {
    const params = userId ? { user_id: userId } : {};
    const response = await api.get('/sessions/', { params });
    return response.data;
  },

  // 세션 조회
  getSession: async (sessionId) => {
    const response = await api.get(`/sessions/${sessionId}`);
    return response.data;
  },

  // 세션 업데이트
  updateSession: async (sessionId, updateData) => {
    const response = await api.patch(`/sessions/${sessionId}`, updateData);
    return response.data;
  },

  // 세션 삭제
  deleteSession: async (sessionId) => {
    await api.delete(`/sessions/${sessionId}`);
  },

  // ROI 영역 추가
  addROI: async (sessionId, roi) => {
    const response = await api.post(`/sessions/${sessionId}/roi`, roi);
    return response.data;
  },

  // ROI 영역 삭제
  removeROI: async (sessionId, roiId) => {
    const response = await api.delete(`/sessions/${sessionId}/roi/${roiId}`);
    return response.data;
  },

  // 검출 시작
  startDetection: async (sessionId) => {
    const response = await api.post(`/sessions/${sessionId}/start`);
    return response.data;
  },

  // 검출 중지
  stopDetection: async (sessionId) => {
    const response = await api.post(`/sessions/${sessionId}/stop`);
    return response.data;
  },

  // 통계 조회
  getStatistics: async (sessionId) => {
    const response = await api.get(`/sessions/${sessionId}/statistics`);
    return response.data;
  },

  // 통계 초기화
  resetStatistics: async (sessionId) => {
    const response = await api.post(`/sessions/${sessionId}/statistics/reset`);
    return response.data;
  },

  // 검출 결과 조회
  getResults: async (sessionId, limit = 100, roiId = null) => {
    const params = { limit };
    if (roiId) params.roi_id = roiId;
    const response = await api.get(`/sessions/${sessionId}/results`, { params });
    return response.data;
  },
};

// 헬스 체크
export const healthCheck = async () => {
  const response = await api.get('/health');
  return response.data;
};

export default api;
