import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { deviceService } from '../services/deviceService';
import { FaPlus, FaEdit, FaTrash, FaSync, FaServer } from 'react-icons/fa';
import '../styles/DevicesPage.css';

function DevicesPage() {
  const { isAdmin } = useAuth();
  const [devices, setDevices] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedDevice, setSelectedDevice] = useState(null);
  
  // 폼 상태
  const [formData, setFormData] = useState({
    device_id: '',
    name: '',
    ip_address: '',
    port: 8000,
    location: '',
    description: ''
  });

  useEffect(() => {
    loadDevices();
    loadSummary();
    
    // 10초마다 자동 갱신
    const interval = setInterval(() => {
      loadDevices();
      loadSummary();
    }, 10000);
    
    return () => clearInterval(interval);
  }, []);

  const loadDevices = async () => {
    try {
      const data = await deviceService.listDevices();
      setDevices(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadSummary = async () => {
    try {
      const data = await deviceService.getStatusSummary();
      setSummary(data);
    } catch (err) {
      console.error('Failed to load summary:', err);
    }
  };

  const handleAddDevice = async (e) => {
    e.preventDefault();
    try {
      await deviceService.registerDevice(formData);
      setShowAddModal(false);
      resetForm();
      loadDevices();
      loadSummary();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleDeleteDevice = async (deviceId) => {
    if (!window.confirm('정말 이 장비를 삭제하시겠습니까?')) return;
    
    try {
      await deviceService.deleteDevice(deviceId);
      loadDevices();
      loadSummary();
    } catch (err) {
      alert(err.message);
    }
  };

  const resetForm = () => {
    setFormData({
      device_id: '',
      name: '',
      ip_address: '',
      port: 8000,
      location: '',
      description: ''
    });
    setSelectedDevice(null);
  };

  const getStatusColor = (status) => {
    const colors = {
      online: '#4caf50',
      offline: '#9e9e9e',
      busy: '#ff9800',
      error: '#f44336',
      maintenance: '#2196f3'
    };
    return colors[status] || '#9e9e9e';
  };

  const getStatusText = (status) => {
    const texts = {
      online: '온라인',
      offline: '오프라인',
      busy: '사용 중',
      error: '오류',
      maintenance: '점검 중'
    };
    return texts[status] || status;
  };

  if (loading) {
    return <div className="loading">장비 정보 로딩 중...</div>;
  }

  return (
    <div className="devices-page">
      <div className="page-header">
        <h1><FaServer /> 장비 관리</h1>
        <div className="header-actions">
          <button onClick={loadDevices} className="btn-refresh">
            <FaSync /> 새로고침
          </button>
          {isAdmin() && (
            <button
              onClick={() => setShowAddModal(true)}
              className="btn-add"
            >
              <FaPlus /> 장비 추가
            </button>
          )}
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {/* 상태 요약 */}
      {summary && (
        <div className="status-summary">
          <div className="summary-card">
            <h3>전체 장비</h3>
            <p className="summary-value">{summary.total}</p>
          </div>
          <div className="summary-card online">
            <h3>온라인</h3>
            <p className="summary-value">{summary.online}</p>
          </div>
          <div className="summary-card busy">
            <h3>사용 중</h3>
            <p className="summary-value">{summary.busy}</p>
          </div>
          <div className="summary-card offline">
            <h3>오프라인</h3>
            <p className="summary-value">{summary.offline}</p>
          </div>
          <div className="summary-card error">
            <h3>오류</h3>
            <p className="summary-value">{summary.error}</p>
          </div>
        </div>
      )}

      {/* 장비 목록 */}
      <div className="devices-grid">
        {devices.map((device) => (
          <div key={device.device_id} className="device-card">
            <div className="device-header">
              <h3>{device.name}</h3>
              <span
                className="status-badge"
                style={{ background: getStatusColor(device.status) }}
              >
                {getStatusText(device.status)}
              </span>
            </div>
            
            <div className="device-info">
              <p><strong>장비 ID:</strong> {device.device_id}</p>
              <p><strong>IP 주소:</strong> {device.ip_address}:{device.port}</p>
              <p><strong>위치:</strong> {device.location || 'N/A'}</p>
              <p><strong>설명:</strong> {device.description || 'N/A'}</p>
              <p><strong>등록일:</strong> {new Date(device.created_at).toLocaleString('ko-KR')}</p>
              {device.last_heartbeat && (
                <p><strong>마지막 연결:</strong> {new Date(device.last_heartbeat).toLocaleString('ko-KR')}</p>
              )}
            </div>

            {isAdmin() && (
              <div className="device-actions">
                <button
                  onClick={() => alert('수정 기능 구현 예정')}
                  className="btn-edit"
                  title="수정"
                >
                  <FaEdit />
                </button>
                <button
                  onClick={() => handleDeleteDevice(device.device_id)}
                  className="btn-delete"
                  title="삭제"
                >
                  <FaTrash />
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {devices.length === 0 && (
        <div className="empty-state">
          <FaServer size={60} />
          <p>등록된 장비가 없습니다.</p>
          {isAdmin() && (
            <button onClick={() => setShowAddModal(true)} className="btn-add">
              첫 장비 추가하기
            </button>
          )}
        </div>
      )}

      {/* 장비 추가 모달 */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>새 장비 추가</h2>
            <form onSubmit={handleAddDevice}>
              <div className="form-group">
                <label>장비 ID *</label>
                <input
                  type="text"
                  value={formData.device_id}
                  onChange={(e) => setFormData({...formData, device_id: e.target.value})}
                  placeholder="jetson-01"
                  required
                />
              </div>
              
              <div className="form-group">
                <label>장비 이름 *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  placeholder="Jetson Orin 1번기"
                  required
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>IP 주소 *</label>
                  <input
                    type="text"
                    value={formData.ip_address}
                    onChange={(e) => setFormData({...formData, ip_address: e.target.value})}
                    placeholder="10.10.11.99"
                    required
                  />
                </div>
                
                <div className="form-group">
                  <label>포트 *</label>
                  <input
                    type="number"
                    value={formData.port}
                    onChange={(e) => setFormData({...formData, port: parseInt(e.target.value)})}
                    placeholder="8000"
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label>위치</label>
                <input
                  type="text"
                  value={formData.location}
                  onChange={(e) => setFormData({...formData, location: e.target.value})}
                  placeholder="1층 출입구"
                />
              </div>

              <div className="form-group">
                <label>설명</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  placeholder="장비 설명을 입력하세요"
                  rows="3"
                />
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  onClick={() => {
                    setShowAddModal(false);
                    resetForm();
                  }}
                  className="btn-cancel"
                >
                  취소
                </button>
                <button type="submit" className="btn-submit">
                  추가
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default DevicesPage;
