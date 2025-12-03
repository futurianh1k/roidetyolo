import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

class AuthService {
  constructor() {
    this.token = null;
    this.apiClient = axios.create({
      baseURL: API_BASE_URL
    });

    // 요청 인터셉터 - 토큰 자동 추가
    this.apiClient.interceptors.request.use(
      (config) => {
        if (this.token) {
          config.headers.Authorization = `Bearer ${this.token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // 응답 인터셉터 - 401 에러 처리
    this.apiClient.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401) {
          // 토큰 만료 시 로그아웃 처리
          this.setToken(null);
          localStorage.removeItem('access_token');
          localStorage.removeItem('user');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  setToken(token) {
    this.token = token;
  }

  async login(username, password) {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    try {
      const response = await this.apiClient.post('/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || '로그인 실패');
    }
  }

  async logout() {
    try {
      await this.apiClient.post('/auth/logout');
    } catch (error) {
      console.error('Logout error:', error);
    }
  }

  async getCurrentUser() {
    try {
      const response = await this.apiClient.get('/auth/me');
      return response.data;
    } catch (error) {
      throw new Error('사용자 정보 조회 실패');
    }
  }

  async refreshToken() {
    try {
      const response = await this.apiClient.post('/auth/refresh');
      return response.data;
    } catch (error) {
      throw new Error('토큰 갱신 실패');
    }
  }

  async listUsers() {
    try {
      const response = await this.apiClient.get('/auth/users');
      return response.data;
    } catch (error) {
      throw new Error('사용자 목록 조회 실패');
    }
  }

  async getActiveSessions() {
    try {
      const response = await this.apiClient.get('/auth/sessions/active');
      return response.data;
    } catch (error) {
      throw new Error('활성 세션 조회 실패');
    }
  }
}

export const authService = new AuthService();
