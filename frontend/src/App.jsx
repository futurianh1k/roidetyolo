import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom'
import './App.css'
import { AuthProvider, useAuth } from './context/AuthContext'
import HomePage from './pages/HomePage'
import DetectionPage from './pages/DetectionPage'
import StatsPage from './pages/StatsPage'
import DevicesPage from './pages/DevicesPage'
import LoginPage from './pages/LoginPage'
import { FaHome, FaVideo, FaChartBar, FaServer, FaSignOutAlt, FaUser } from 'react-icons/fa'

// 인증이 필요한 라우트 보호
function PrivateRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return <div className="loading">로딩 중...</div>;
  }
  
  return isAuthenticated ? children : <Navigate to="/login" />;
}

// 메인 내비게이션 컴포넌트
function MainNav() {
  const { user, logout, isAuthenticated } = useAuth();
  
  if (!isAuthenticated) return null;
  
  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <h1>🎯 YOLO ROI 검출 시스템</h1>
      </div>
      <div className="navbar-menu">
        <Link to="/" className="nav-link">
          <FaHome /> 홈
        </Link>
        <Link to="/devices" className="nav-link">
          <FaServer /> 장비 관리
        </Link>
        <Link to="/detection" className="nav-link">
          <FaVideo /> 실시간 검출
        </Link>
        <Link to="/stats" className="nav-link">
          <FaChartBar /> 통계
        </Link>
      </div>
      <div className="navbar-user">
        <div className="user-info">
          <FaUser /> {user?.username} ({user?.role})
        </div>
        <button onClick={logout} className="btn-logout">
          <FaSignOutAlt /> 로그아웃
        </button>
      </div>
    </nav>
  );
}

function AppContent() {
  return (
    <div className="app">
      <MainNav />
      <main className="main-content">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={
            <PrivateRoute>
              <HomePage />
            </PrivateRoute>
          } />
          <Route path="/devices" element={
            <PrivateRoute>
              <DevicesPage />
            </PrivateRoute>
          } />
          <Route path="/detection" element={
            <PrivateRoute>
              <DetectionPage />
            </PrivateRoute>
          } />
          <Route path="/stats" element={
            <PrivateRoute>
              <StatsPage />
            </PrivateRoute>
          } />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <AppContent />
      </Router>
    </AuthProvider>
  )
}

export default App
