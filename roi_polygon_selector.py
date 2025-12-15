"""
Polygon 기반 ROI 영역 선택 도구
마우스 클릭으로 다각형 ROI 영역을 설정하고 config.json에 저장
"""

import cv2
import json
import numpy as np


class PolygonROISelector:
    def __init__(self, video_source=0):
        """
        Polygon ROI 선택기 초기화
        
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
        self.roi_regions = []  # 완성된 ROI 목록
        self.current_points = []  # 현재 그리는 중인 polygon 점들
        self.drawing = False
        
        # 윈도우 설정
        cv2.namedWindow('Polygon ROI Selector')
        cv2.setMouseCallback('Polygon ROI Selector', self.mouse_callback)
        
        print("\n📐 Polygon ROI 선택 도구")
        print("=" * 60)
        print("사용 방법:")
        print("  - 마우스 좌클릭: 다각형 꼭지점 추가")
        print("  - 마우스 우클릭 또는 'Enter' 키: 현재 다각형 완성")
        print("  - 's' 키: 완성된 다각형 저장")
        print("  - 'd' 키: 마지막 ROI 삭제")
        print("  - 'u' 키: 현재 그리는 중인 다각형의 마지막 점 삭제")
        print("  - 'c' 키: 모든 ROI 초기화")
        print("  - 'q' 키: 완료 및 config.json 저장")
        print("=" * 60)
        print("\n💡 팁: 복잡한 형태의 영역도 자유롭게 그릴 수 있습니다!")
        print("=" * 60 + "\n")
    
    def mouse_callback(self, event, x, y, flags, param):
        """마우스 이벤트 핸들러"""
        if event == cv2.EVENT_LBUTTONDOWN:
            # 좌클릭: 점 추가
            self.current_points.append((x, y))
            print(f"✏️  점 추가: ({x}, {y}) - 총 {len(self.current_points)}개 점")
            
            if len(self.current_points) == 1:
                print(f"   계속 클릭하여 다각형을 그리세요. (최소 3개 점 필요)")
            elif len(self.current_points) >= 3:
                print(f"   우클릭 또는 Enter 키로 다각형 완성")
        
        elif event == cv2.EVENT_RBUTTONDOWN:
            # 우클릭: 다각형 완성
            if len(self.current_points) >= 3:
                self.complete_current_polygon()
            else:
                print("⚠️  다각형을 완성하려면 최소 3개의 점이 필요합니다.")
    
    def complete_current_polygon(self):
        """현재 그리는 중인 다각형 완성"""
        if len(self.current_points) >= 3:
            # numpy array로 변환
            points_array = np.array(self.current_points, dtype=np.int32)
            
            # 면적 계산 (너무 작은 polygon 필터링)
            area = cv2.contourArea(points_array)
            
            if area > 100:  # 최소 면적
                roi_data = {
                    'points': self.current_points.copy(),
                    'type': 'polygon'
                }
                
                # 임시 저장 (아직 roi_regions에 추가하지 않음)
                self.current_polygon = roi_data
                
                print(f"✅ 다각형 완성! 점 개수: {len(self.current_points)}, 면적: {area:.1f}")
                print(f"   's' 키를 눌러 저장하세요.")
            else:
                print(f"⚠️  다각형이 너무 작습니다. (면적: {area:.1f})")
                self.current_points = []
        else:
            print("⚠️  다각형을 완성하려면 최소 3개의 점이 필요합니다.")
    
    def save_current_polygon(self):
        """완성된 다각형을 ROI 목록에 저장"""
        if hasattr(self, 'current_polygon') and self.current_polygon:
            self.roi_regions.append(self.current_polygon.copy())
            print(f"💾 ROI{len(self.roi_regions)} 저장 완료!")
            
            # 초기화
            self.current_points = []
            self.current_polygon = None
        else:
            print("⚠️  저장할 다각형이 없습니다. 먼저 다각형을 완성하세요.")
    
    def undo_last_point(self):
        """현재 그리는 중인 다각형의 마지막 점 삭제"""
        if self.current_points:
            removed = self.current_points.pop()
            print(f"↩️  마지막 점 삭제: {removed} - 남은 점: {len(self.current_points)}개")
        else:
            print("⚠️  삭제할 점이 없습니다.")
    
    def draw_rois(self):
        """모든 ROI를 프레임에 그리기"""
        frame = self.original_frame.copy()
        
        # 저장된 ROI들 그리기 (초록색)
        for i, roi in enumerate(self.roi_regions):
            points = np.array(roi['points'], dtype=np.int32)
            
            # 다각형 채우기 (반투명)
            overlay = frame.copy()
            cv2.fillPoly(overlay, [points], (0, 255, 0))
            cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
            
            # 다각형 테두리
            cv2.polylines(frame, [points], True, (0, 255, 0), 2)
            
            # 꼭지점 표시
            for point in roi['points']:
                cv2.circle(frame, point, 5, (0, 255, 0), -1)
            
            # ROI 번호 (중심점에 표시)
            M = cv2.moments(points)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                label = f"ROI{i+1}"
                cv2.putText(frame, label, (cx - 30, cy),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 3)
                cv2.putText(frame, label, (cx - 30, cy),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        # 현재 그리는 중인 다각형 (빨간색)
        if self.current_points:
            points_array = np.array(self.current_points, dtype=np.int32)
            
            # 현재까지 그린 선 그리기
            if len(self.current_points) >= 2:
                cv2.polylines(frame, [points_array], False, (0, 0, 255), 2)
            
            # 꼭지점 표시
            for i, point in enumerate(self.current_points):
                cv2.circle(frame, point, 6, (0, 0, 255), -1)
                # 점 번호 표시
                cv2.putText(frame, str(i+1), (point[0] + 10, point[1] - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
            # 첫 점과 마지막 점을 연결하는 임시 선 (점선 효과)
            if len(self.current_points) >= 3:
                cv2.line(frame, self.current_points[-1], self.current_points[0], 
                        (255, 0, 0), 1, cv2.LINE_AA)
        
        # 완성되었지만 아직 저장하지 않은 다각형 (노란색)
        if hasattr(self, 'current_polygon') and self.current_polygon and not self.current_points:
            points = np.array(self.current_polygon['points'], dtype=np.int32)
            
            # 다각형 채우기 (반투명)
            overlay = frame.copy()
            cv2.fillPoly(overlay, [points], (0, 255, 255))
            cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
            
            # 다각형 테두리
            cv2.polylines(frame, [points], True, (0, 255, 255), 3)
            
            # 꼭지점 표시
            for point in self.current_polygon['points']:
                cv2.circle(frame, point, 5, (0, 255, 255), -1)
            
            # "Press 'S' to Save" 메시지
            M = cv2.moments(points)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                cv2.putText(frame, "Press 'S' to Save", (cx - 80, cy),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 3)
                cv2.putText(frame, "Press 'S' to Save", (cx - 80, cy),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # 도움말 표시
        help_text = [
            "Click: Add Point | RightClick/Enter: Complete",
            "S: Save | D: Delete | U: Undo | C: Clear | Q: Quit",
            f"Current Points: {len(self.current_points)} | Saved ROIs: {len(self.roi_regions)}"
        ]
        
        y_offset = 30
        for text in help_text:
            # 배경 (가독성 향상)
            (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(frame, (5, y_offset - 20), (w + 15, y_offset + 5), (0, 0, 0), -1)
            
            # 텍스트
            cv2.putText(frame, text, (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y_offset += 30
        
        return frame
    
    def delete_last_roi(self):
        """마지막으로 저장된 ROI 삭제"""
        if self.roi_regions:
            deleted = self.roi_regions.pop()
            print(f"🗑️  ROI{len(self.roi_regions) + 1} 삭제됨")
        else:
            print("⚠️  삭제할 ROI가 없습니다.")
    
    def clear_all_rois(self):
        """모든 ROI 초기화"""
        if self.roi_regions or self.current_points:
            self.roi_regions = []
            self.current_points = []
            if hasattr(self, 'current_polygon'):
                self.current_polygon = None
            print("🧹 모든 ROI가 초기화되었습니다.")
        else:
            print("⚠️  초기화할 ROI가 없습니다.")
    
    def convert_to_config_format(self):
        """ROI 데이터를 config.json 형식으로 변환"""
        config_rois = []
        
        for i, roi in enumerate(self.roi_regions):
            config_roi = {
                'id': f'ROI{i+1}',
                'type': 'polygon',
                'points': roi['points'],
                'description': f'다각형 영역 {i+1}'
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
            print(f"   총 {len(self.roi_regions)}개의 Polygon ROI 영역이 저장되었습니다.")
            
            # 저장된 ROI 정보 출력
            print("\n저장된 ROI 정보:")
            for roi in config['roi_regions']:
                print(f"  - {roi['id']}: {len(roi['points'])}개 점, 타입: {roi['type']}")
            
            return True
        
        except Exception as e:
            print(f"❌ 저장 실패: {e}")
            return False
    
    def run(self):
        """메인 루프 실행"""
        while True:
            # ROI가 그려진 프레임 표시
            frame = self.draw_rois()
            cv2.imshow('Polygon ROI Selector', frame)
            
            # 키 입력 처리
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('s'):
                # 현재 다각형 저장
                self.save_current_polygon()
            
            elif key == ord('d'):
                # 마지막 ROI 삭제
                self.delete_last_roi()
            
            elif key == ord('u'):
                # 현재 다각형의 마지막 점 삭제
                self.undo_last_point()
            
            elif key == ord('c'):
                # 모든 ROI 초기화
                self.clear_all_rois()
            
            elif key == 13 or key == 10:  # Enter 키
                # 현재 다각형 완성
                if len(self.current_points) >= 3:
                    self.complete_current_polygon()
            
            elif key == ord('q'):
                # 종료 및 저장
                if self.roi_regions:
                    if self.save_to_config():
                        break
                else:
                    print("⚠️  저장할 ROI가 없어 종료할 수 없습니다.")
                    print("   ROI를 추가하거나 'Ctrl+C'로 강제 종료하세요.")
        
        # 정리
        self.cap.release()
        cv2.destroyAllWindows()
        print("\n✅ Polygon ROI 선택 완료!")


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
        selector = PolygonROISelector(video_source)
        selector.run()
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
