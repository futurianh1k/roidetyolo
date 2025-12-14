#!/bin/bash
# 카메라 권한 및 설정 체크 스크립트 (RK3588 Linux)

echo "============================================="
echo "  카메라 권한 및 설정 체크 (RK3588 Linux)"
echo "============================================="
echo ""

echo "1️⃣  USB 카메라 연결 확인 (lsusb)"
echo "---------------------------------------------"
lsusb | grep -i "camera\|webcam\|lifecam\|video" || echo "카메라 관련 USB 장치를 찾지 못했습니다."
echo ""

echo "2️⃣  비디오 장치 확인 (/dev/video*)"
echo "---------------------------------------------"
ls -la /dev/video* 2>/dev/null || echo "❌ /dev/video* 장치를 찾지 못했습니다."
echo ""

echo "3️⃣  현재 사용자 그룹 확인"
echo "---------------------------------------------"
groups $USER
if groups $USER | grep -q "video"; then
    echo "✅ 사용자가 'video' 그룹에 속해 있습니다."
else
    echo "❌ 사용자가 'video' 그룹에 속해 있지 않습니다."
    echo "   권한 추가 방법: sudo usermod -aG video $USER"
    echo "   (로그아웃 후 다시 로그인 필요)"
fi
echo ""

echo "4️⃣  v4l-utils 설치 확인"
echo "---------------------------------------------"
if command -v v4l2-ctl &> /dev/null; then
    echo "✅ v4l2-ctl 설치됨"
    echo ""
    echo "카메라 장치 목록:"
    v4l2-ctl --list-devices 2>/dev/null || echo "장치 목록을 가져올 수 없습니다."
else
    echo "❌ v4l2-ctl이 설치되지 않았습니다."
    echo "   설치 방법: sudo apt-get install v4l-utils"
fi
echo ""

echo "5️⃣  OpenCV 카메라 테스트 (Python)"
echo "---------------------------------------------"
python3 << 'EOF'
import cv2
import platform

print(f"Python OpenCV 버전: {cv2.__version__}")
print(f"플랫폼: {platform.system()}")

# 카메라 검색
found_cameras = []
for i in range(5):
    cap = cv2.VideoCapture(i, cv2.CAP_V4L2)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            backend = cap.getBackendName()
            print(f"✅ Camera {i}: {width}x{height} @ {fps:.1f}fps (Backend: {backend})")
            found_cameras.append(i)
        cap.release()

if not found_cameras:
    print("❌ OpenCV에서 사용 가능한 카메라를 찾지 못했습니다.")
else:
    print(f"✅ 총 {len(found_cameras)}개의 카메라 발견: {found_cameras}")
EOF
echo ""

echo "============================================="
echo "  체크 완료"
echo "============================================="
echo ""
echo "문제 해결 방법:"
echo "  1. 카메라가 연결되지 않은 경우:"
echo "     - USB 케이블 확인"
echo "     - 다른 USB 포트 사용"
echo ""
echo "  2. /dev/video* 장치가 없는 경우:"
echo "     - 카메라 드라이버 설치 확인"
echo "     - dmesg | grep video 로 커널 로그 확인"
echo ""
echo "  3. 권한 문제:"
echo "     - sudo usermod -aG video $USER"
echo "     - 로그아웃 후 재로그인"
echo ""
echo "  4. v4l-utils 설치:"
echo "     - sudo apt-get update"
echo "     - sudo apt-get install v4l-utils"
echo ""
