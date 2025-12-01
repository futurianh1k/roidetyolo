# 문제 해결 가이드 (TROUBLESHOOTING)

## 🔧 RK3588 Debian Linaro 환경 문제 해결

### 1️⃣ KeyError: 'points' 오류 해결

**증상:**
```
KeyError: 'points'
at line 481 in streamlit_app.py
```

**원인:**
- 기존 `config.json`이 rectangle 형식 ROI 데이터를 사용
- Streamlit 앱이 polygon 형식 ROI를 기대함

**해결 방법:**
이제 자동으로 처리됩니다! 코드가 rectangle 형식을 자동으로 polygon 형식으로 변환합니다.

만약 여전히 오류가 발생하면:

```bash
# config.json 백업 후 삭제
mv config.json config.json.backup

# Streamlit 앱 재시작 (새로운 기본 설정 생성)
streamlit run streamlit_app.py
```

---

### 2️⃣ 카메라 미검출 문제 (RK3588 Linux)

**증상:**
```
[ WARN:0@3.619] global cap_v4l.cpp:1119 tryIoctl VIDEOIO(V4L2:/dev/video0): Unable to get camera FPS
[Camera] 총 0개의 카메라 발견
```

**원인:**
1. 카메라 드라이버 문제
2. 카메라 권한 문제
3. V4L2 설정 문제

**해결 방법:**

#### Step 1: 카메라 권한 체크 스크립트 실행

```bash
cd /home/user/yolo_roi_detector
./check_camera_permissions.sh
```

이 스크립트는 다음을 확인합니다:
- USB 카메라 연결 상태 (`lsusb`)
- 비디오 장치 존재 여부 (`/dev/video*`)
- 사용자 권한 (`video` 그룹)
- v4l-utils 설치 상태
- OpenCV 카메라 접근 테스트

#### Step 2: 카메라 장치 확인

```bash
# USB 카메라 확인
lsusb

# 비디오 장치 확인
ls -la /dev/video*

# 장치 정보 확인 (v4l-utils 필요)
v4l2-ctl --list-devices
```

#### Step 3: 권한 추가

```bash
# 현재 사용자를 video 그룹에 추가
sudo usermod -aG video $USER

# 변경사항 확인
groups $USER

# ⚠️ 로그아웃 후 다시 로그인 필요!
```

#### Step 4: v4l-utils 설치

```bash
sudo apt-get update
sudo apt-get install v4l-utils

# 카메라 정보 확인
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --all
```

#### Step 5: Python에서 카메라 테스트

```python
import cv2

# V4L2 백엔드로 카메라 열기
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

if cap.isOpened():
    ret, frame = cap.read()
    if ret:
        print(f"✅ 카메라 작동: {frame.shape}")
    else:
        print("❌ 프레임 읽기 실패")
else:
    print("❌ 카메라 열기 실패")

cap.release()
```

#### Step 6: 카메라 권한 직접 설정 (임시)

```bash
# 임시로 카메라 권한 부여 (재부팅 시 초기화)
sudo chmod 666 /dev/video0
sudo chmod 666 /dev/video1
```

---

### 3️⃣ 카메라 FPS 경고 무시하기

**증상:**
```
[ WARN:0@3.619] global cap_v4l.cpp:1119 tryIoctl VIDEOIO(V4L2:/dev/video0): Unable to get camera FPS
```

**해결:**
이 경고는 무시해도 됩니다. 카메라에서 FPS 정보를 가져올 수 없을 때 발생하며, 코드는 기본값(30fps)을 사용합니다.

FPS 경고를 완전히 제거하려면:

```python
# OpenCV 환경 변수 설정
import os
os.environ['OPENCV_VIDEOIO_DEBUG'] = '0'
os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'
```

---

### 4️⃣ LifeCam HD-3000 카메라 특정 이슈

**Microsoft LifeCam HD-3000** 사용 시:

```bash
# USB 장치 확인
lsusb | grep LifeCam
# 출력 예: Bus 001 Device 003: ID 045e:0779 Microsoft Corp. LifeCam HD-3000

# 비디오 장치 확인
ls -la /dev/video* | grep -E "video[0-1]"

# v4l2-ctl로 포맷 확인
v4l2-ctl -d /dev/video0 --list-formats-ext

# 해상도 설정 테스트
v4l2-ctl -d /dev/video0 --set-fmt-video=width=1280,height=720,pixelformat=MJPG
```

일부 LifeCam 모델은 특정 해상도에서만 작동합니다:
- 1280x720 (권장)
- 640x480
- 320x240

---

## 🚀 빠른 문제 해결 체크리스트

### ✅ 카메라 미검출 시

1. ☐ USB 케이블이 제대로 연결되었는지 확인
2. ☐ `lsusb` 명령으로 카메라가 인식되는지 확인
3. ☐ `/dev/video*` 장치가 존재하는지 확인
4. ☐ 사용자가 `video` 그룹에 속해있는지 확인
5. ☐ `v4l-utils` 설치 여부 확인
6. ☐ 다른 프로그램이 카메라를 사용 중인지 확인
7. ☐ 로그아웃 후 재로그인 (권한 변경 후)

### ✅ KeyError: 'points' 오류 시

1. ☐ 최신 버전 코드 사용 확인
2. ☐ `config.json` 백업 후 삭제
3. ☐ Streamlit 앱 재시작

---

## 📞 추가 지원

문제가 계속되면:

1. **로그 확인:**
   ```bash
   dmesg | grep video
   dmesg | grep usb
   ```

2. **커널 모듈 확인:**
   ```bash
   lsmod | grep -i video
   lsmod | grep -i usb
   ```

3. **카메라 드라이버 재로드:**
   ```bash
   sudo modprobe -r uvcvideo
   sudo modprobe uvcvideo
   ```

4. **OpenCV 빌드 정보:**
   ```python
   import cv2
   print(cv2.getBuildInformation())
   ```

---

## 📝 코드 변경 내역

### v1.1 - RK3588 호환성 개선

- ✅ V4L2 백엔드 명시적 사용 (Linux)
- ✅ Rectangle → Polygon 자동 변환
- ✅ 카메라 권한 체크 스크립트 추가
- ✅ 상세한 디버깅 메시지 추가
- ✅ FPS 경고 메시지 제거

---

**마지막 업데이트:** 2025-01-17
