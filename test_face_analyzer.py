"""
얼굴 분석기 테스트 스크립트
MediaPipe 기반 얼굴 분석 기능 테스트
"""

import cv2
import sys
from face_analyzer import FaceAnalyzer, MEDIAPIPE_AVAILABLE

def test_face_analyzer_camera():
    """웹캠으로 얼굴 분석 테스트"""
    
    if not MEDIAPIPE_AVAILABLE:
        print("❌ MediaPipe가 설치되지 않았습니다.")
        print("   설치: pip install mediapipe")
        return
    
    print("🎥 웹캠 얼굴 분석 테스트")
    print("=" * 50)
    
    # 얼굴 분석기 초기화
    config = {
        'ear_threshold': 0.21,
        'mar_speak_threshold': 0.3,
        'mar_open_threshold': 0.5,
        'ventilator_detection_threshold': 0.3
    }
    
    try:
        analyzer = FaceAnalyzer(config)
    except Exception as e:
        print(f"❌ FaceAnalyzer 초기화 실패: {e}")
        return
    
    # 카메라 열기
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ 카메라를 열 수 없습니다.")
        return
    
    print("✅ 카메라 열림")
    print()
    print("📖 사용법:")
    print("  - ESC: 종료")
    print("  - 스페이스: 분석 결과 출력")
    print()
    
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        
        if not ret:
            print("❌ 프레임 읽기 실패")
            break
        
        frame_count += 1
        
        # 얼굴 분석 (전체 프레임)
        face_result = analyzer.analyze_face(frame)
        
        # 결과 시각화
        if face_result:
            frame = analyzer.draw_face_analysis(frame, face_result)
            
            # 프레임 카운트에 정보 추가
            if frame_count % 30 == 0:  # 1초마다 출력
                print(f"\n[Frame {frame_count}]")
                print(f"  Eyes: {'Open' if face_result['eyes_open'] else 'Closed'} (EAR: {face_result['ear']:.3f})")
                print(f"  Mouth: {face_result['mouth_state']} (MAR: {face_result['mar']:.3f})")
                print(f"  Expression: {face_result['expression']}")
                
                if face_result['has_mask_or_ventilator']:
                    print(f"  🎭 Mask/Ventilator: Detected ({face_result['device_confidence']:.2f})")
        else:
            # 얼굴 미검출
            cv2.putText(
                frame, "No face detected",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1, (0, 0, 255), 2
            )
        
        # FPS 표시
        cv2.putText(
            frame, f"Frame: {frame_count}",
            (10, frame.shape[0] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5, (255, 255, 255), 1
        )
        
        # 화면 표시
        cv2.imshow('Face Analyzer Test', frame)
        
        # 키 입력
        key = cv2.waitKey(1) & 0xFF
        
        if key == 27:  # ESC
            print("\n👋 종료")
            break
        elif key == 32:  # Space
            if face_result:
                print("\n" + "="*50)
                print("📊 상세 분석 결과:")
                print("="*50)
                for k, v in face_result.items():
                    if k != 'landmarks':  # 랜드마크는 너무 길어서 제외
                        print(f"  {k}: {v}")
                print("="*50)
    
    # 자원 해제
    cap.release()
    cv2.destroyAllWindows()
    
    print(f"\n✅ 총 {frame_count} 프레임 처리 완료")


def test_face_analyzer_image(image_path):
    """이미지 파일로 얼굴 분석 테스트"""
    
    if not MEDIAPIPE_AVAILABLE:
        print("❌ MediaPipe가 설치되지 않았습니다.")
        print("   설치: pip install mediapipe")
        return
    
    print(f"🖼️  이미지 얼굴 분석 테스트: {image_path}")
    print("=" * 50)
    
    # 이미지 읽기
    frame = cv2.imread(image_path)
    
    if frame is None:
        print(f"❌ 이미지를 읽을 수 없습니다: {image_path}")
        return
    
    # 얼굴 분석기 초기화
    analyzer = FaceAnalyzer()
    
    # 얼굴 분석
    print("🔍 얼굴 분석 중...")
    face_result = analyzer.analyze_face(frame)
    
    if face_result:
        print("\n✅ 얼굴 검출 성공!")
        print("\n📊 분석 결과:")
        print("-" * 50)
        print(f"  Eyes: {'Open' if face_result['eyes_open'] else 'Closed'} (EAR: {face_result['ear']:.3f})")
        print(f"  Mouth: {face_result['mouth_state']} (MAR: {face_result['mar']:.3f})")
        print(f"  Expression: {face_result['expression']}")
        
        if face_result['has_mask_or_ventilator']:
            print(f"  🎭 Mask/Ventilator: Detected ({face_result['device_confidence']:.2f})")
        else:
            print(f"  🎭 Mask/Ventilator: Not detected")
        
        print("-" * 50)
        
        # 결과 시각화
        result_frame = analyzer.draw_face_analysis(frame, face_result)
        
        # 화면 표시
        cv2.imshow('Face Analysis Result', result_frame)
        print("\n💡 아무 키나 눌러서 종료...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        
    else:
        print("❌ 얼굴을 검출하지 못했습니다.")


def main():
    """메인 함수"""
    
    print("🔬 FaceAnalyzer 테스트 도구")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        # 이미지 파일 테스트
        image_path = sys.argv[1]
        test_face_analyzer_image(image_path)
    else:
        # 웹캠 테스트
        test_face_analyzer_camera()


if __name__ == '__main__':
    main()
