import { createContext, useContext, useState, useEffect } from 'react';
import { authService } from '../services/authService';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 토큰 및 사용자 정보 복원
  useEffect(() => {
    const initAuth = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const userStr = localStorage.getItem('user');
        
        if (token && userStr) {
          const userData = JSON.parse(userStr);
          setUser(userData);
          authService.setToken(token);
        }
      } catch (err) {
        console.error('Failed to restore auth:', err);
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  const login = async (username, password) => {
    try {
      setError(null);
      const response = await authService.login(username, password);
      
      // 토큰 및 사용자 정보 저장
      localStorage.setItem('access_token', response.access_token);
      localStorage.setItem('user', JSON.stringify(response.user));
      authService.setToken(response.access_token);
      setUser(response.user);
      
      return response;
    } catch (err) {
      setError(err.message || '로그인 실패');
      throw err;
    }
  };

  const logout = async () => {
    try {
      await authService.logout();
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      // 로컬 상태 및 저장소 정리
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      authService.setToken(null);
      setUser(null);
    }
  };

  const refreshToken = async () => {
    try {
      const response = await authService.refreshToken();
      localStorage.setItem('access_token', response.access_token);
      authService.setToken(response.access_token);
      return response;
    } catch (err) {
      console.error('Token refresh failed:', err);
      await logout();
      throw err;
    }
  };

  const isAdmin = () => {
    return user?.role === 'admin';
  };

  const isOperator = () => {
    return user?.role === 'operator' || user?.role === 'admin';
  };

  const value = {
    user,
    loading,
    error,
    login,
    logout,
    refreshToken,
    isAuthenticated: !!user,
    isAdmin,
    isOperator
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
