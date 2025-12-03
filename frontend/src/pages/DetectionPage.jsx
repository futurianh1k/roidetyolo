import { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { sessionAPI } from '../services/api';
import WebSocketClient from '../services/websocket';
import './DetectionPage.css';

function DetectionPage() {
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get('session');
  
  const [session, setSession] = useState(null);
  const [isDetecting, setIsDetecting] = useState(false);
  const [fps, setFps] = useState(0);
  const [currentFrame, setCurrentFrame] = useState(null);
  
  const wsRef = useRef(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    if (sessionId) {
      loadSession();
      connectWebSocket();
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect();
      }
    };
  }, [sessionId]);

  const loadSession = async () => {
    try {
      const data = await sessionAPI.getSession(sessionId);
      setSession(data);
      setIsDetecting(data.status === 'detecting');
    } catch (error) {
      console.error('Failed to load session:', error);
    }
  };

  const connectWebSocket = () => {
    wsRef.current = new WebSocketClient(sessionId);
    
    wsRef.current.on('frame', ({ data, fps: frameFps }) => {
      setCurrentFrame(data);
      setFps(frameFps);
      renderFrame(data);
    });

    wsRef.current.on('stats', (stats) => {
      console.log('Stats updated:', stats);
    });

    wsRef.current.connect();
  };

  const renderFrame = (base64Data) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const img = new Image();
    
    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.drawImage(img, 0, 0);
    };
    
    img.src = `data:image/jpeg;base64,${base64Data}`;
  };

  const startDetection = async () => {
    try {
      await sessionAPI.startDetection(sessionId);
      setIsDetecting(true);
      loadSession();
    } catch (error) {
      console.error('Failed to start detection:', error);
      alert('검출 시작 실패: ' + error.message);
    }
  };

  const stopDetection = async () => {
    try {
      await sessionAPI.stopDetection(sessionId);
      setIsDetecting(false);
      loadSession();
    } catch (error) {
      console.error('Failed to stop detection:', error);
    }
  };

  if (!session) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>세션 로딩 중...</p>
      </div>
    );
  }

  return (
    <div className="detection-page">
      <div className="detection-header">
        <h2>🎥 실시간 검출</h2>
        <div className="detection-controls">
          {!isDetecting ? (
            <button className="btn btn-success" onClick={startDetection}>
              ▶️ 검출 시작
            </button>
          ) : (
            <button className="btn btn-danger" onClick={stopDetection}>
              ⏹️ 검출 중지
            </button>
          )}
          <span className="fps-badge">FPS: {fps.toFixed(1)}</span>
        </div>
      </div>

      <div className="detection-content">
        <div className="video-section card">
          <canvas ref={canvasRef} className="video-canvas" />
          {!currentFrame && (
            <div className="no-video">
              <p>📹 비디오 스트림 대기 중...</p>
              <p className="hint">검출을 시작하면 여기에 실시간 영상이 표시됩니다</p>
            </div>
          )}
        </div>

        <div className="stats-sidebar">
          <div className="card">
            <h3>📊 세션 정보</h3>
            <div className="info-item">
              <span className="info-label">세션 ID:</span>
              <span className="info-value">{session.session_id.slice(0, 12)}...</span>
            </div>
            <div className="info-item">
              <span className="info-label">상태:</span>
              <span className={`status-badge status-${session.status}`}>
                {session.status}
              </span>
            </div>
            <div className="info-item">
              <span className="info-label">ROI 영역:</span>
              <span className="info-value">{session.roi_regions.length}개</span>
            </div>
          </div>

          <div className="card">
            <h3>📈 통계</h3>
            <div className="stats-grid">
              <div className="stat-item">
                <div className="stat-value">{session.statistics.total_detections}</div>
                <div className="stat-label">총 검출</div>
              </div>
              <div className="stat-item">
                <div className="stat-value">{session.statistics.face_stats.total_faces}</div>
                <div className="stat-label">얼굴 분석</div>
              </div>
            </div>
          </div>

          {session.roi_regions.length > 0 && (
            <div className="card">
              <h3>🎯 ROI 상태</h3>
              <div className="roi-list">
                {session.roi_regions.map((roi) => (
                  <div key={roi.id} className="roi-item">
                    <span className="roi-id">{roi.id}</span>
                    <span className="roi-description">{roi.description}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default DetectionPage;
