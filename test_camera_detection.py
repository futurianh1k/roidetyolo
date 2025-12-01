"""
카메라 자동 검출 테스트 스크립트
"""

from camera_utils import detect_available_cameras, format_camera_list_for_ui, test_camera
from roi_utils import create_quadrant_rois, validate_roi, calculate_roi_area

print("=" * 70)
print("🎥 카메라 자동 검출 및 ROI 생성 테스트")
print("=" * 70)

# 1. 카메라 자동 검출
print("\n📹 1단계: 카메라 자동 검출")
print("-" * 70)

cameras = detect_available_cameras(max_cameras=5)

if cameras:
    print(f"\n✅ {len(cameras)}개의 카메라를 찾았습니다:\n")
    
    camera_list = format_camera_list_for_ui(cameras)
    for i, cam_str in enumerate(camera_list):
        print(f"  {i+1}. {cam_str}")
    
    # 첫 번째 카메라 선택
    selected_camera = cameras[0]
    print(f"\n🎯 선택된 카메라: Camera {selected_camera['index']}")
    print(f"   해상도: {selected_camera['resolution'][0]}x{selected_camera['resolution'][1]}")
    print(f"   FPS: {selected_camera['fps']:.1f}")
    
    # 2. 카메라 테스트
    print(f"\n📹 2단계: Camera {selected_camera['index']} 테스트")
    print("-" * 70)
    
    test_result = test_camera(selected_camera['index'], duration=2)
    
    if test_result:
        # 3. 4사분면 ROI 생성
        print("\n📐 3단계: 4사분면 ROI 생성")
        print("-" * 70)
        
        frame_width, frame_height = selected_camera['resolution']
        quadrant_rois = create_quadrant_rois(frame_width, frame_height, margin=20)
        
        print(f"\n✅ 4사분면 ROI 생성 완료 ({frame_width}x{frame_height})\n")
        
        for roi in quadrant_rois:
            # ROI 검증
            valid, message = validate_roi(roi, frame_width, frame_height)
            
            # ROI 면적 계산
            area = calculate_roi_area(roi)
            
            print(f"📍 {roi['id']}: {roi['description']}")
            print(f"   타입: {roi['type']}")
            print(f"   점 개수: {len(roi['points'])}")
            print(f"   면적: {area:,.0f} 픽셀²")
            print(f"   유효성: {'✅ ' + message if valid else '❌ ' + message}")
            print()
        
        # 4. 설정 파일 저장 예시
        print("=" * 70)
        print("💾 4단계: 설정 파일 예시")
        print("-" * 70)
        
        config_example = {
            "camera_source": selected_camera['index'],
            "frame_width": frame_width,
            "frame_height": frame_height,
            "roi_regions": quadrant_rois
        }
        
        import json
        print("\n설정 파일 (config.json) 예시:")
        print(json.dumps(config_example, indent=2, ensure_ascii=False))
        
        print("\n" + "=" * 70)
        print("✅ 모든 테스트 완료!")
        print("=" * 70)
        print("\n다음 단계:")
        print("  1. streamlit run streamlit_app.py")
        print("  2. '🔍 카메라 자동 검색' 버튼 클릭")
        print("  3. '🎯 4사분면 ROI 자동 생성' 버튼 클릭")
        print("  4. 실시간 검출 시작!")
    
    else:
        print("\n❌ 카메라 테스트 실패")

else:
    print("\n❌ 사용 가능한 카메라를 찾지 못했습니다.")
    print("\n문제 해결:")
    print("  1. 카메라가 컴퓨터에 연결되어 있는지 확인")
    print("  2. 다른 프로그램이 카메라를 사용 중인지 확인")
    print("  3. 카메라 드라이버가 설치되어 있는지 확인")
    print("  4. 카메라 권한 설정 확인")

print()
