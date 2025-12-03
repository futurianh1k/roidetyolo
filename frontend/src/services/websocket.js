class WebSocketClient {
  constructor(sessionId) {
    this.sessionId = sessionId;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 3000;
    this.handlers = {
      frame: [],
      stats: [],
      event: [],
      fps: [],
      connect: [],
      disconnect: [],
      error: [],
    };
  }

  connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/${this.sessionId}`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('✅ WebSocket connected');
      this.reconnectAttempts = 0;
      this._trigger('connect');
      this._startHeartbeat();
    };

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        this._handleMessage(message);
      } catch (error) {
        console.error('❌ WebSocket message parse error:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
      this._trigger('error', error);
    };

    this.ws.onclose = () => {
      console.log('❌ WebSocket disconnected');
      this._trigger('disconnect');
      this._stopHeartbeat();
      this._attemptReconnect();
    };
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this._stopHeartbeat();
  }

  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  on(event, handler) {
    if (this.handlers[event]) {
      this.handlers[event].push(handler);
    }
  }

  off(event, handler) {
    if (this.handlers[event]) {
      this.handlers[event] = this.handlers[event].filter(h => h !== handler);
    }
  }

  _handleMessage(message) {
    const { type, data, fps, timestamp } = message;

    switch (type) {
      case 'frame':
        this._trigger('frame', { data, fps, timestamp });
        break;
      case 'stats':
        this._trigger('stats', data);
        break;
      case 'event':
        this._trigger('event', data);
        break;
      case 'fps':
        this._trigger('fps', data);
        break;
      case 'pong':
        // Heartbeat response
        break;
      default:
        console.warn('Unknown message type:', type);
    }
  }

  _trigger(event, data) {
    if (this.handlers[event]) {
      this.handlers[event].forEach(handler => handler(data));
    }
  }

  _startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      this.send({ type: 'ping' });
    }, 30000); // 30초마다 ping
  }

  _stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  _attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`🔄 Reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
      setTimeout(() => {
        this.connect();
      }, this.reconnectDelay);
    } else {
      console.error('❌ Max reconnect attempts reached');
    }
  }
}

export default WebSocketClient;
