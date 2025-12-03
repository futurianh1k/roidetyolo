import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { sessionAPI } from '../services/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './StatsPage.css';

function StatsPage() {
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get('session');
  
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (sessionId) {
      loadStatistics();
      const interval = setInterval(loadStatistics, 5000); // 5초마다 업데이트
      return () => clearInterval(interval);
    }
  }, [sessionId]);

  const loadStatistics = async () => {
    try {
      const data = await sessionAPI.getSession(sessionId);
      setSession(data);
    } catch (error) {
      console.error('Failed to load statistics:', error);
    } finally {
      setLoading(false);
    }
  };

  const resetStatistics = async () => {
    if (!window.confirm('통계를 초기화하시겠습니까?')) return;
    
    try {
      await sessionAPI.resetStatistics(sessionId);
      loadStatistics();
    } catch (error) {
      console.error('Failed to reset statistics:', error);
      alert('통계 초기화 실패');
    }
  };

  if (loading || !session) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>통계 로딩 중...</p>
      </div>
    );
  }

  const { statistics } = session;
  const faceStats = statistics.face_stats || {};
  
  // 표정 분포 데이터
  const expressionData = [
    { name: '중립', value: faceStats.neutral || 0, emoji: '😐' },
    { name: '행복', value: faceStats.happy || 0, emoji: '😊' },
    { name: '슬픔', value: faceStats.sad || 0, emoji: '😢' },
    { name: '놀람', value: faceStats.surprised || 0, emoji: '😲' },
    { name: '고통', value: faceStats.pain || 0, emoji: '😖' },
    { name: '화남', value: faceStats.angry || 0, emoji: '😠' },
  ];

  // 눈/입 상태 데이터
  const eyesTotal = (faceStats.eyes_open || 0) + (faceStats.eyes_closed || 0);
  const eyeOpenRate = eyesTotal > 0 ? ((faceStats.eyes_open || 0) / eyesTotal * 100).toFixed(1) : 0;

  return (
    <div className="stats-page">
      <div className="stats-header">
        <h2>📊 통계 대시보드</h2>
        <button className="btn btn-warning" onClick={resetStatistics}>
          🔄 통계 초기화
        </button>
      </div>

      <div className="stats-overview">
        <div className="overview-card">
          <div className="overview-icon">🎯</div>
          <div className="overview-content">
            <div className="overview-value">{statistics.total_detections}</div>
            <div className="overview-label">총 검출 횟수</div>
          </div>
        </div>

        <div className="overview-card">
          <div className="overview-icon">😊</div>
          <div className="overview-content">
            <div className="overview-value">{faceStats.total_faces || 0}</div>
            <div className="overview-label">얼굴 분석</div>
          </div>
        </div>

        <div className="overview-card">
          <div className="overview-icon">👁️</div>
          <div className="overview-content">
            <div className="overview-value">{eyeOpenRate}%</div>
            <div className="overview-label">개안율</div>
          </div>
        </div>

        <div className="overview-card">
          <div className="overview-icon">😷</div>
          <div className="overview-content">
            <div className="overview-value">{faceStats.mask_detected || 0}</div>
            <div className="overview-label">마스크 검출</div>
          </div>
        </div>
      </div>

      <div className="stats-grid">
        <div className="card">
          <h3>😊 표정 분포</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={expressionData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="value" fill="#2196F3" />
            </BarChart>
          </ResponsiveContainer>
          <div className="expression-list">
            {expressionData.map(({ name, value, emoji }) => (
              value > 0 && (
                <div key={name} className="expression-item">
                  <span className="expression-emoji">{emoji}</span>
                  <span className="expression-name">{name}</span>
                  <span className="expression-value">{value}</span>
                </div>
              )
            ))}
          </div>
        </div>

        <div className="card">
          <h3>👁️ 눈 상태</h3>
          <div className="eye-stats">
            <div className="eye-stat-item">
              <div className="eye-stat-label">눈 뜸</div>
              <div className="eye-stat-value">{faceStats.eyes_open || 0}</div>
            </div>
            <div className="eye-stat-item">
              <div className="eye-stat-label">눈 감음</div>
              <div className="eye-stat-value">{faceStats.eyes_closed || 0}</div>
            </div>
          </div>
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${eyeOpenRate}%` }}
            ></div>
          </div>
          <div className="progress-label">개안율: {eyeOpenRate}%</div>
        </div>

        <div className="card">
          <h3>👄 입 상태</h3>
          <div className="mouth-stats">
            <div className="mouth-stat-item">
              <div className="mouth-stat-icon">🤐</div>
              <div className="mouth-stat-content">
                <div className="mouth-stat-label">닫힘</div>
                <div className="mouth-stat-value">{faceStats.mouth_closed || 0}</div>
              </div>
            </div>
            <div className="mouth-stat-item">
              <div className="mouth-stat-icon">🗣️</div>
              <div className="mouth-stat-content">
                <div className="mouth-stat-label">말하기</div>
                <div className="mouth-stat-value">{faceStats.mouth_speaking || 0}</div>
              </div>
            </div>
            <div className="mouth-stat-item">
              <div className="mouth-stat-icon">😮</div>
              <div className="mouth-stat-content">
                <div className="mouth-stat-label">크게 열림</div>
                <div className="mouth-stat-value">{faceStats.mouth_wide_open || 0}</div>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <h3>🎯 ROI 통계</h3>
          {Object.keys(statistics.roi_stats || {}).length > 0 ? (
            <div className="roi-stats">
              {Object.entries(statistics.roi_stats).map(([roiId, stats]) => (
                <div key={roiId} className="roi-stat-item">
                  <div className="roi-stat-header">{roiId}</div>
                  <div className="roi-stat-content">
                    <span className="roi-stat-present">
                      🟢 Present: {stats.present || 0}
                    </span>
                    <span className="roi-stat-absent">
                      🔴 Absent: {stats.absent || 0}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="no-data">ROI 통계 없음</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default StatsPage;
