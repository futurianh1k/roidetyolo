import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import './App.css'
import HomePage from './pages/HomePage'
import DetectionPage from './pages/DetectionPage'
import StatsPage from './pages/StatsPage'
import { FaHome, FaVideo, FaChartBar } from 'react-icons/fa'

function App() {
  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <div className="navbar-brand">
            <h1>🎯 YOLO ROI 검출 시스템</h1>
          </div>
          <div className="navbar-menu">
            <Link to="/" className="nav-link">
              <FaHome /> 홈
            </Link>
            <Link to="/detection" className="nav-link">
              <FaVideo /> 실시간 검출
            </Link>
            <Link to="/stats" className="nav-link">
              <FaChartBar /> 통계
            </Link>
          </div>
        </nav>

        <main className="main-content">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/detection" element={<DetectionPage />} />
            <Route path="/stats" element={<StatsPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
