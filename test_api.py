"""
API 엔드포인트 테스트 스크립트
실제 서버 연결 없이 API 전송 기능을 테스트합니다.
"""

import requests
import json
import uuid
from datetime import datetime

# API 전송 유틸리티 (통합 + 재시도 + 비동기)
from api_utils import send_api_event


def test_api_endpoint(api_url):
    """
    API 엔드포인트 테스트
    
    Args:
        api_url: API 엔드포인트 URL
    """
    print(f"\n🧪 API 엔드포인트 테스트")
    print(f"URL: {api_url}")
    print("=" * 60)
    
    # 테스트 데이터 1: Present (사람 검출됨)
    test_data_present = {
        "eventId": str(uuid.uuid4()),
        "roiId": "ROI1",
        "objectType": "human",
        "status": 1,
        "createdAt": datetime.now().isoformat(),
        "watchId": "watch_1760663070591_8022"
    }
    
    # 테스트 데이터 2: Absent (사람 검출 안됨)
    test_data_absent = {
        "eventId": str(uuid.uuid4()),
        "roiId": "ROI1",
        "objectType": "human",
        "status": 0,
        "createdAt": datetime.now().isoformat(),
        "watchId": "watch_1760663070591_8022"
    }
    
    # 테스트 1: Present 이벤트 전송
    print("\n📤 테스트 1: Present 이벤트 (status: 1)")
    print(f"데이터: {json.dumps(test_data_present, indent=2, ensure_ascii=False)}")

    # 🚀 통합 API 전송 함수 사용 (재시도 로직 포함)
    result = send_api_event(
        url=api_url,
        event_data=test_data_present,
        timeout=10,
        retry_count=3,
    )

    print(f"\n응답 결과:")
    print(f"  성공 여부: {result.get('success')}")
    print(f"  상태 코드: {result.get('status_code')}")
    print(f"  응답 내용: {result.get('response_text', '')[:200]}")

    if result.get("success"):
        print("✅ Present 이벤트 전송 성공!")
    else:
        error = result.get("error", "Unknown")
        print(f"⚠️ Present 이벤트 전송 실패: {error}")
    
    # 테스트 2: Absent 이벤트 전송
    print("\n" + "=" * 60)
    print("\n📤 테스트 2: Absent 이벤트 (status: 0)")
    print(f"데이터: {json.dumps(test_data_absent, indent=2, ensure_ascii=False)}")

    # 🚀 통합 API 전송 함수 사용 (재시도 로직 포함)
    result = send_api_event(
        url=api_url,
        event_data=test_data_absent,
        timeout=10,
        retry_count=3,
    )

    print(f"\n응답 결과:")
    print(f"  성공 여부: {result.get('success')}")
    print(f"  상태 코드: {result.get('status_code')}")
    print(f"  응답 내용: {result.get('response_text', '')[:200]}")

    if result.get("success"):
        print("✅ Absent 이벤트 전송 성공!")
    else:
        error = result.get("error", "Unknown")
        print(f"⚠️ Absent 이벤트 전송 실패: {error}")
    
    print("\n" + "=" * 60)
    print("\n💡 참고사항:")
    print("  - 실제 서버가 실행 중이 아니면 연결 오류가 발생합니다.")
    print("  - config.json에서 api_endpoint를 올바르게 설정하세요.")
    print("  - 서버의 API 명세에 맞게 데이터 형식을 조정하세요.")


def test_mock_server():
    """
    Mock 서버 테스트 (로컬 Flask 서버가 있는 경우)
    """
    print("\n🔧 Mock 서버 테스트")
    print("=" * 60)
    print("\nMock 서버를 사용하려면 다음 명령으로 간단한 서버를 실행하세요:")
    print("\n```python")
    print("# mock_server.py")
    print("from flask import Flask, request, jsonify")
    print("")
    print("app = Flask(__name__)")
    print("")
    print("@app.route('/api/emergency', methods=['POST'])")
    print("def emergency_alert():")
    print("    data = request.json")
    print("    print(f'받은 이벤트: {data}')")
    print("    return jsonify({'status': 'success', 'message': 'Event received'}), 200")
    print("")
    print("if __name__ == '__main__':")
    print("    app.run(host='0.0.0.0', port=8080)")
    print("```")
    print("\n실행: python mock_server.py")
    print("테스트: python test_api.py http://localhost:8080/api/emergency")


def main():
    """메인 함수"""
    import sys
    
    # API URL 가져오기
    if len(sys.argv) > 1:
        api_url = sys.argv[1]
    else:
        # config.json에서 읽기
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                api_url = config.get('api_endpoint', 'http://localhost:8080/api/emergency')
        except FileNotFoundError:
            api_url = 'http://localhost:8080/api/emergency'
            print("⚠️  config.json을 찾을 수 없습니다. 기본 URL을 사용합니다.")
    
    print("\n" + "=" * 60)
    print("API 엔드포인트 테스트 도구")
    print("=" * 60)
    
    # API 테스트 실행
    test_api_endpoint(api_url)
    
    # Mock 서버 안내
    print("\n")
    test_mock_server()


if __name__ == '__main__':
    main()
