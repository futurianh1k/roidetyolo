"""
ROI 영역 선택 도구
마우스로 드래그하여 ROI 영역을 설정하고 config.json에 저장
"""

import cv2
import json
import numpy as np


class ROISelector:
    def __init__(self, video_source=0):
        """
        ROI 선택기 초기화
        
        Args:
            video_source: 비디오 소스 (카메라 번호 또는 파일 경로)
        """
        self.video_source = video_source
        self.cap = cv2.VideoCapture(video_source)
        
        # 첫 프레임 읽기
        ret, self.frame = self.cap.read()
        if not ret:
            raise ValueError("비디오 소스를 열 수 없습니다.")
        
        self.original_frame = self.frame.copy()
        self.roi_regions = []
        self.current_roi = None
        self.drawing = False
        self.start_point = None
        
        # 윈도우 설정
        cv2.namedWindow('ROI Selector')
        cv2.setMouseCallback('ROI Selector', self.mouse_callback)
        
        print("\n📐 ROI 선택 도구")
        print("=" * 50)
        print("사용 방법:")
        print("  - 마우스로 드래그하여 ROI 영역 선택")
        print("  - 's' 키: 현재 ROI 저장")
        print("  - 'd' 키: 마지막 ROI 삭제")
        print("  - 'c' 키: 모든 ROI 초기화")
        print("  - 'q' 키: 완료 및 config.json 저장")
        print("=" * 50 + "\n")
    
    def mouse_callback(self, event, x, y, flags, param):
        """마우스 이벤트 핸들러"""
        if event == cv2.EVENT_LBUTTONDOWN:
            # 드래그 시작
            self.drawing = True
            self.start_point = (x, y)
            self.current_roi = None
        
        elif event == cv2.EVENT_MOUSEMOVE:
            # 드래그 중
            if self.drawing:
                self.current_roi = {
                    'start': self.start_point,
                    'end': (x, y)
                }
        
        elif event == cv2.EVENT_LBUTTONUP:
            # 드래그 종료
            self.drawing = False
            if self.start_point and (x, y) != self.start_point:
                # 최소 크기 체크
                if abs(x - self.start_point[0]) > 20 and abs(y - self.start_point[1]) > 20:
                    self.current_roi = {
                        'start': self.start_point,
                        'end': (x, y)
                    }
                    print(f"✏️  ROI 생성됨: {self.start_point} -> {(x, y)}")
                    print(f"   's' 키를 눌러 저장하세요.")
    
    def draw_rois(self):
        """모든 ROI를 프레임에 그리기"""
        frame = self.original_frame.copy()
        
        # 저장된 ROI들 그리기
        for i, roi in enumerate(self.roi_regions):
            x, y = roi['start']
            x2, y2 = roi['end']
            
            # ROI 박스
            cv2.rectangle(frame, (x, y), (x2, y2), (0, 255, 0), 2)
            
            # ROI 번호
            label = f"ROI{i+1}"
            cv2.putText(frame, label, (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # 크기 정보
            width = abs(x2 - x)
            height = abs(y2 - y)
            size_text = f"{width}x{height}"
            cv2.putText(frame, size_text, (x, y2 + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        
        # 현재 그리는 중인 ROI
        if self.current_roi:
            x, y = self.current_roi['start']
            x2, y2 = self.current_roi['end']
            cv2.rectangle(frame, (x, y), (x2, y2), (0, 0, 255), 2)
            
            # 실시간 크기 표시
            width = abs(x2 - x)
            height = abs(y2 - y)
            size_text = f"{width}x{height}"
            cv2.putText(frame, size_text, (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        # 도움말 표시
        help_text = [
            "S: Save | D: Delete | C: Clear | Q: Quit",
            f"ROIs: {len(self.roi_regions)}"
        ]
        
        for i, text in enumerate(help_text):
            cv2.putText(frame, text, (10, 30 + i * 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, text, (10, 30 + i * 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
        
        return frame
    
    def save_current_roi(self):
        """현재 ROI를 목록에 저장"""
        if self.current_roi:
            self.roi_regions.append(self.current_roi.copy())
            print(f"✅ ROI{len(self.roi_regions)} 저장됨")
            self.current_roi = None
        else:
            print("⚠️  저장할 ROI가 없습니다. 먼저 ROI를 그려주세요.")
    
    def delete_last_roi(self):
        """마지막 ROI 삭제"""
        if self.roi_regions:
            deleted = self.roi_regions.pop()
            print(f"🗑️  마지막 ROI 삭제됨")
        else:
            print("⚠️  삭제할 ROI가 없습니다.")
    
    def clear_all_rois(self):
        """모든 ROI 초기화"""
        if self.roi_regions:
            self.roi_regions = []
            self.current_roi = None
            print("🧹 모든 ROI가 초기화되었습니다.")
        else:
            print("⚠️  초기화할 ROI가 없습니다.")
    
    def convert_to_config_format(self):
        """ROI 데이터를 config.json 형식으로 변환"""
        config_rois = []
        
        for i, roi in enumerate(self.roi_regions):
            x1, y1 = roi['start']
            x2, y2 = roi['end']
            
            # 좌상단 좌표와 너비/높이 계산
            x = min(x1, x2)
            y = min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            
            config_roi = {
                'id': f'ROI{i+1}',
                'x': x,
                'y': y,
                'width': width,
                'height': height,
                'description': f'영역 {i+1}'
            }
            
            config_rois.append(config_roi)
        
        return config_rois
    
    def save_to_config(self):
        """config.json에 ROI 정보 저장"""
        if not self.roi_regions:
            print("⚠️  저장할 ROI가 없습니다.")
            return False
        
        try:
            # 기존 config 읽기 (있는 경우)
            try:
                with open('config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except FileNotFoundError:
                # 기본 config 생성
                config = {
                    "yolo_model": "yolov8n.pt",
                    "camera_source": self.video_source,
                    "frame_width": int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    "frame_height": int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                    "confidence_threshold": 0.5,
                    "presence_threshold_seconds": 5,
                    "absence_threshold_seconds": 3,
                    "count_interval_seconds": 1,
                    "api_endpoint": "http://localhost:8080/api/emergency",
                    "watch_id": "watch_default",
                    "include_image_url": False
                }
            
            # ROI 정보 업데이트
            config['roi_regions'] = self.convert_to_config_format()
            
            # config.json 저장
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print("\n✅ config.json에 저장되었습니다!")
            print(f"   총 {len(self.roi_regions)}개의 ROI 영역이 저장되었습니다.")
            
            # 저장된 ROI 정보 출력
            print("\n저장된 ROI 정보:")
            for roi in config['roi_regions']:
                print(f"  - {roi['id']}: ({roi['x']}, {roi['y']}) {roi['width']}x{roi['height']}")
            
            return True
        
        except Exception as e:
            print(f"❌ 저장 실패: {e}")
            return False
    
    def run(self):
        """메인 루프 실행"""
        while True:
            # ROI가 그려진 프레임 표시
            frame = self.draw_rois()
            cv2.imshow('ROI Selector', frame)
            
            # 키 입력 처리
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('s'):
                # 현재 ROI 저장
                self.save_current_roi()
            
            elif key == ord('d'):
                # 마지막 ROI 삭제
                self.delete_last_roi()
            
            elif key == ord('c'):
                # 모든 ROI 초기화
                self.clear_all_rois()
            
            elif key == ord('q'):
                # 종료 및 저장
                if self.save_to_config():
                    break
                else:
                    print("⚠️  저장할 ROI가 없어 종료할 수 없습니다.")
                    print("   ROI를 추가하거나 'Ctrl+C'로 강제 종료하세요.")
        
        # 정리
        self.cap.release()
        cv2.destroyAllWindows()
        print("\n✅ ROI 선택 완료!")


def main():
    """메인 함수"""
    import sys
    
    # 비디오 소스 지정 (기본값: 0 - 웹캠)
    video_source = 0
    if len(sys.argv) > 1:
        try:
            video_source = int(sys.argv[1])
        except ValueError:
            video_source = sys.argv[1]  # 파일 경로
    
    try:
        selector = ROISelector(video_source)
        selector.run()
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
