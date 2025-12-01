"""
Mock API 서버
테스트용 간단한 Flask 서버
"""

try:
    from flask import Flask, request, jsonify
    from datetime import datetime
    
    app = Flask(__name__)
    
    # 수신된 이벤트 저장
    received_events = []
    
    
    @app.route('/api/emergency', methods=['POST'])
    def emergency_alert():
        """
        긴급 알림 엔드포인트
        """
        try:
            data = request.json
            
            # 이벤트 저장
            event = {
                'received_at': datetime.now().isoformat(),
                'data': data
            }
            received_events.append(event)
            
            # 콘솔 출력
            print("\n" + "=" * 60)
            print(f"📥 이벤트 수신: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"ROI ID: {data.get('roiId', 'N/A')}")
            print(f"객체 타입: {data.get('objectType', 'N/A')}")
            print(f"상태: {'검출됨 (Present)' if data.get('status') == 1 else '검출 안됨 (Absent)'}")
            print(f"이벤트 ID: {data.get('eventId', 'N/A')}")
            print(f"Watch ID: {data.get('watchId', 'N/A')}")
            print("=" * 60)
            
            # 성공 응답
            response = {
                'status': 'success',
                'message': 'Event received successfully',
                'eventId': data.get('eventId'),
                'timestamp': datetime.now().isoformat()
            }
            
            return jsonify(response), 200
        
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 400
    
    
    @app.route('/api/events', methods=['GET'])
    def get_events():
        """
        수신된 모든 이벤트 조회
        """
        return jsonify({
            'total': len(received_events),
            'events': received_events
        }), 200
    
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """
        서버 상태 체크
        """
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'total_events': len(received_events)
        }), 200
    
    
    @app.route('/', methods=['GET'])
    def index():
        """
        루트 경로
        """
        return jsonify({
            'message': 'Mock Emergency Alert Server',
            'endpoints': {
                '/api/emergency': 'POST - 긴급 알림 수신',
                '/api/events': 'GET - 수신된 이벤트 조회',
                '/api/health': 'GET - 서버 상태 체크'
            }
        }), 200
    
    
    def main():
        """메인 함수"""
        print("\n" + "=" * 60)
        print("🚀 Mock API 서버 시작")
        print("=" * 60)
        print("\n서버 정보:")
        print("  - 주소: http://0.0.0.0:8080")
        print("  - 로컬: http://localhost:8080")
        print("  - 긴급 알림: POST http://localhost:8080/api/emergency")
        print("  - 이벤트 조회: GET http://localhost:8080/api/events")
        print("  - 상태 체크: GET http://localhost:8080/api/health")
        print("\n종료하려면 Ctrl+C를 누르세요.")
        print("=" * 60 + "\n")
        
        app.run(host='0.0.0.0', port=8080, debug=False)
    
    
    if __name__ == '__main__':
        main()

except ImportError:
    print("\n❌ Flask가 설치되지 않았습니다.")
    print("\n설치 방법:")
    print("  pip install flask")
    print("\n또는 requirements.txt에 추가:")
    print("  echo 'flask>=2.0.0' >> requirements.txt")
    print("  pip install -r requirements.txt")
