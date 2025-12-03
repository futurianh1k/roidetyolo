import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { sessionAPI } from '../services/api';
import './HomePage.css';

function HomePage() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const data = await sessionAPI.listSessions();
      setSessions(data);
    } catch (error) {
      console.error('Failed to load sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  const createNewSession = async () => {
    try {
      const session = await sessionAPI.createSession();
      navigate(`/detection?session=${session.session_id}`);
    } catch (error) {
      console.error('Failed to create session:', error);
      alert('세션 생성 실패');
    }
  };

  const deleteSession = async (sessionId) => {
    if (!window.confirm('세션을 삭제하시겠습니까?')) return;
    
    try {
      await sessionAPI.deleteSession(sessionId);
      loadSessions();
    } catch (error) {
      console.error('Failed to delete session:', error);
      alert('세션 삭제 실패');
    }
  };

  const openSession = (sessionId) => {
    navigate(`/detection?session=${sessionId}`);
  };

  return (
    <div className="home-page">
      <div className="hero">
        <h1>🎯 YOLO ROI 사람 검출 시스템</h1>
        <p>실시간 비디오 스트림에서 지정된 ROI 영역 내 사람을 검출하고 얼굴 분석을 수행합니다</p>
        <button className="btn btn-primary btn-large" onClick={createNewSession}>
          ✨ 새 세션 시작하기
        </button>
      </div>

      <div className="features">
        <div className="feature-card">
          <div className="feature-icon">🎥</div>
          <h3>실시간 검출</h3>
          <p>YOLO를 사용한 실시간 사람 검출</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon">📐</div>
          <h3>ROI 편집</h3>
          <p>마우스 클릭으로 쉽게 ROI 영역 설정</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon">😊</div>
          <h3>얼굴 분석</h3>
          <p>표정, 눈/입 상태, 마스크 검출</p>
        </div>
        <div className="feature-card">
          <div className="feature-icon">📊</div>
          <h3>통계 대시보드</h3>
          <p>실시간 통계 및 검출 결과 분석</p>
        </div>
      </div>

      {sessions.length > 0 && (
        <div className="sessions-section">
          <h2>📋 최근 세션</h2>
          <div className="sessions-list">
            {sessions.map((session) => (
              <div key={session.session_id} className="session-card">
                <div className="session-info">
                  <h4>{session.session_id.slice(0, 8)}...</h4>
                  <div className="session-meta">
                    <span className={`status-badge status-${session.status}`}>
                      {session.status}
                    </span>
                    <span className="session-date">
                      {new Date(session.created_at).toLocaleString('ko-KR')}
                    </span>
                  </div>
                  <div className="session-stats">
                    <span>🎯 ROI: {session.roi_regions.length}</span>
                    <span>📊 검출: {session.statistics.total_detections}</span>
                  </div>
                </div>
                <div className="session-actions">
                  <button 
                    className="btn btn-primary"
                    onClick={() => openSession(session.session_id)}
                  >
                    열기
                  </button>
                  <button 
                    className="btn btn-danger"
                    onClick={() => deleteSession(session.session_id)}
                  >
                    삭제
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {loading && (
        <div className="loading">
          <div className="spinner"></div>
        </div>
      )}
    </div>
  );
}

export default HomePage;
