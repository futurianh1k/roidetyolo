"""
YOLO ROI 사람 검출 시스템 - PyQt5 버전
Streamlit UI를 PyQt5로 변환한 데스크톱 애플리케이션
"""

import sys
import cv2
import numpy as np
import json
import time
from pathlib import Path
from datetime import datetime
from collections import deque

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QSpinBox, QDoubleSpinBox,
    QComboBox, QCheckBox, QLineEdit, QTextEdit, QGroupBox,
    QFormLayout, QScrollArea, QSplitter, QMessageBox, QFileDialog,
    QListWidget, QTableWidget, QTableWidgetItem, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QPoint
from PyQt5.QtGui import QImage, QPixmap, QFont, QPainter, QPen, QColor, QPolygon

from realtime_detector import RealtimeDetector
from roi_utils import create_quadrant_rois, create_left_right_rois
from camera_utils import detect_available_cameras


class ClickableLabel(QLabel):
    """마우스 클릭 가능한 라벨 (ROI 편집용)"""
    clicked = pyqtSignal(int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(event.x(), event.y())
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    """메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YOLO ROI 사람 검출 시스템 (PyQt5)")
        self.setGeometry(100, 100, 1600, 900)
        
        # 상태 변수
        self.config = self.load_config()
        self.roi_regions = self.config.get('roi_regions', [])
        self.current_points = []
        self.selected_roi_idx = None
        self.detector = None
        self.detection_running = False
        self.event_log = deque(maxlen=50)
        self.detection_stats = {}
        self.face_analysis_stats = {
            'total_faces_detected': 0,
            'expressions': {'neutral': 0, 'happy': 0, 'sad': 0, 'surprised': 0, 'pain': 0, 'angry': 0},
            'eyes_open_count': 0,
            'eyes_closed_count': 0,
            'mouth_closed_count': 0,
            'mouth_speaking_count': 0,
            'mouth_wide_open_count': 0,
            'mask_detected_count': 0,
            'last_expression': None,
            'last_update': None
        }
        
        # ROI 편집 모드
        self.roi_editing_mode = False
        self.roi_edit_frame = None
        
        # 카메라 관련
        self.camera_cap = None
        
        # UI 초기화
        self.init_ui()
        
        # 타이머 설정 (실시간 업데이트용)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_detection_display)
        self.update_timer.setInterval(33)  # 30 FPS
    
    def load_config(self):
        """설정 파일 로드"""
        config_path = Path('config.json')
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # ROI 정규화
                if 'roi_regions' in config:
                    for roi in config['roi_regions']:
                        if 'type' not in roi and 'points' not in roi:
                            # Rectangle to polygon conversion
                            x, y, w, h = roi['x'], roi['y'], roi['width'], roi['height']
                            roi['points'] = [
                                [x, y], [x + w, y], [x + w, y + h], [x, y + h]
                            ]
                            roi['type'] = 'polygon'
                return config
        else:
            return {
                'yolo_model': 'yolov8n.pt',
                'camera_source': 0,
                'frame_width': 1280,
                'frame_height': 720,
                'confidence_threshold': 0.5,
                'detection_interval_seconds': 1.0,
                'presence_threshold_seconds': 5,
                'absence_threshold_seconds': 3,
                'enable_face_analysis': True,
                'face_analysis_roi_only': False,
                'api_endpoint': 'http://10.10.11.23:10008/api/emergency/quick/watch_1764653561585_7956',
                'watch_id': 'watch_1764653561585_7956',
                'roi_regions': []
            }
    
    def save_config(self):
        """설정 파일 저장"""
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def init_ui(self):
        """UI 초기화"""
        # 스타일시트 적용
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                padding: 8px 15px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                opacity: 0.8;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
            QTabBar::tab {
                padding: 10px 20px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #2196F3;
                color: white;
            }
            QTextEdit, QListWidget {
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃 (수평 분할)
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 왼쪽: 설정 패널
        settings_panel = self.create_settings_panel()
        main_layout.addWidget(settings_panel, 1)
        
        # 오른쪽: 탭 위젯
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs, 3)
        
        # 탭 추가
        self.tabs.addTab(self.create_roi_edit_tab(), "📐 ROI 편집")
        self.tabs.addTab(self.create_detection_tab(), "🎥 실시간 검출")
        self.tabs.addTab(self.create_stats_tab(), "📊 통계 & 로그")
        self.tabs.addTab(self.create_api_test_tab(), "🔗 API 테스트")
    
    def create_settings_panel(self):
        """설정 패널 생성"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(350)
        scroll.setMaximumWidth(450)
        
        settings_widget = QWidget()
        layout = QVBoxLayout()
        settings_widget.setLayout(layout)
        
        # 제목
        title = QLabel("⚙️ 설정")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)
        
        # YOLO 모델 설정
        yolo_group = QGroupBox("🤖 YOLO 모델")
        yolo_layout = QFormLayout()
        self.model_combo = QComboBox()
        self.model_combo.addItems(['yolov8n.pt', 'yolov8s.pt', 'yolov8m.pt', 'yolov8l.pt'])
        self.model_combo.setCurrentText(self.config.get('yolo_model', 'yolov8n.pt'))
        yolo_layout.addRow("모델 선택:", self.model_combo)
        yolo_group.setLayout(yolo_layout)
        layout.addWidget(yolo_group)
        
        # 카메라 설정
        camera_group = QGroupBox("📹 카메라")
        camera_layout = QFormLayout()
        self.camera_source_spin = QSpinBox()
        self.camera_source_spin.setRange(0, 10)
        self.camera_source_spin.setValue(int(self.config.get('camera_source', 0)))
        camera_layout.addRow("카메라 번호:", self.camera_source_spin)
        camera_group.setLayout(camera_layout)
        layout.addWidget(camera_group)
        
        # 검출 설정
        detection_group = QGroupBox("🎯 검출 설정")
        detection_layout = QFormLayout()
        
        self.detection_interval_spin = QDoubleSpinBox()
        self.detection_interval_spin.setRange(0.5, 5.0)
        self.detection_interval_spin.setSingleStep(0.5)
        self.detection_interval_spin.setValue(float(self.config.get('detection_interval_seconds', 1.0)))
        detection_layout.addRow("YOLO 검출 간격 (초):", self.detection_interval_spin)
        
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.0, 1.0)
        self.confidence_spin.setSingleStep(0.05)
        self.confidence_spin.setValue(float(self.config.get('confidence_threshold', 0.5)))
        detection_layout.addRow("신뢰도 임계값:", self.confidence_spin)
        
        self.presence_spin = QSpinBox()
        self.presence_spin.setRange(1, 60)
        self.presence_spin.setValue(int(self.config.get('presence_threshold_seconds', 5)))
        detection_layout.addRow("존재 확인 시간 (초):", self.presence_spin)
        
        self.absence_spin = QSpinBox()
        self.absence_spin.setRange(1, 60)
        self.absence_spin.setValue(int(self.config.get('absence_threshold_seconds', 3)))
        detection_layout.addRow("부재 확인 시간 (초):", self.absence_spin)
        
        detection_group.setLayout(detection_layout)
        layout.addWidget(detection_group)
        
        # 얼굴 분석 설정
        face_group = QGroupBox("😊 얼굴 분석")
        face_layout = QVBoxLayout()
        
        self.face_analysis_check = QCheckBox("얼굴 분석 활성화")
        self.face_analysis_check.setChecked(self.config.get('enable_face_analysis', False))
        face_layout.addWidget(self.face_analysis_check)
        
        self.face_roi_only_check = QCheckBox("ROI 내부만 분석")
        self.face_roi_only_check.setChecked(self.config.get('face_analysis_roi_only', True))
        face_layout.addWidget(self.face_roi_only_check)
        
        info_label = QLabel("📊 분석 항목:\n- 👁️ 눈 개폐 (EAR)\n- 👄 입 상태 (MAR)\n- 😊 표정 분석\n- 😷 호흡기 검출")
        info_label.setStyleSheet("color: #666; padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        face_layout.addWidget(info_label)
        
        face_group.setLayout(face_layout)
        layout.addWidget(face_group)
        
        # API 설정
        api_group = QGroupBox("🌐 API 설정")
        api_layout = QFormLayout()
        
        self.watch_id_edit = QLineEdit(self.config.get('watch_id', ''))
        api_layout.addRow("Watch ID:", self.watch_id_edit)
        
        self.sender_id_edit = QLineEdit(self.config.get('sender_id', 'yolo_detector'))
        api_layout.addRow("Sender ID:", self.sender_id_edit)
        
        self.api_endpoint_edit = QLineEdit(self.config.get('api_endpoint', ''))
        api_layout.addRow("API 엔드포인트:", self.api_endpoint_edit)
        
        self.note_edit = QLineEdit(self.config.get('note', ''))
        api_layout.addRow("Note (선택):", self.note_edit)
        
        self.method_edit = QLineEdit(self.config.get('method', 'realtime_detection'))
        api_layout.addRow("Method (선택):", self.method_edit)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        # 설정 저장 버튼
        save_btn = QPushButton("💾 설정 저장")
        save_btn.clicked.connect(self.on_save_settings)
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-weight: bold;")
        layout.addWidget(save_btn)
        
        layout.addStretch()
        scroll.setWidget(settings_widget)
        return scroll
    
    def create_roi_edit_tab(self):
        """ROI 편집 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # 상단: 비디오 표시 영역 (클릭 가능)
        self.roi_video_label = ClickableLabel("카메라 프레임이 여기에 표시됩니다")
        self.roi_video_label.setAlignment(Qt.AlignCenter)
        self.roi_video_label.setMinimumHeight(400)
        self.roi_video_label.setStyleSheet("border: 2px solid #ccc; background-color: #000;")
        self.roi_video_label.clicked.connect(self.on_roi_canvas_click)
        layout.addWidget(self.roi_video_label)
        
        # ROI 편집 시작 버튼
        edit_control_layout = QHBoxLayout()
        
        self.start_roi_edit_btn = QPushButton("✏️ ROI 편집 시작 (카메라 켜기)")
        self.start_roi_edit_btn.clicked.connect(self.on_start_roi_edit)
        self.start_roi_edit_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 10px;")
        edit_control_layout.addWidget(self.start_roi_edit_btn)
        
        self.stop_roi_edit_btn = QPushButton("⏹️ ROI 편집 중지 (카메라 끄기)")
        self.stop_roi_edit_btn.clicked.connect(self.on_stop_roi_edit)
        self.stop_roi_edit_btn.setEnabled(False)
        self.stop_roi_edit_btn.setStyleSheet("background-color: #f44336; color: white; padding: 10px;")
        edit_control_layout.addWidget(self.stop_roi_edit_btn)
        
        layout.addLayout(edit_control_layout)
        
        # 중단: 수동 ROI 편집
        manual_edit_layout = QHBoxLayout()
        
        add_point_btn = QPushButton("➕ 현재 점 추가")
        add_point_btn.clicked.connect(self.on_add_current_point)
        manual_edit_layout.addWidget(add_point_btn)
        
        complete_roi_btn = QPushButton("✅ ROI 완성")
        complete_roi_btn.clicked.connect(self.on_complete_roi)
        complete_roi_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        manual_edit_layout.addWidget(complete_roi_btn)
        
        undo_btn = QPushButton("⬅️ 마지막 점 취소")
        undo_btn.clicked.connect(self.on_undo_last_point)
        manual_edit_layout.addWidget(undo_btn)
        
        layout.addLayout(manual_edit_layout)
        
        # 하단: ROI 제어 버튼들
        controls_layout = QHBoxLayout()
        
        # 자동 생성 버튼
        lr_btn = QPushButton("⬅️➡️ 좌/우 2분할")
        lr_btn.clicked.connect(self.on_create_lr_rois)
        controls_layout.addWidget(lr_btn)
        
        quad_btn = QPushButton("🎯 4사분면")
        quad_btn.clicked.connect(self.on_create_quad_rois)
        controls_layout.addWidget(quad_btn)
        
        clear_btn = QPushButton("🗑️ 모두 삭제")
        clear_btn.clicked.connect(self.on_clear_rois)
        clear_btn.setStyleSheet("background-color: #f44336; color: white;")
        controls_layout.addWidget(clear_btn)
        
        layout.addLayout(controls_layout)
        
        # ROI 목록
        roi_list_group = QGroupBox("저장된 ROI")
        roi_list_layout = QVBoxLayout()
        
        self.roi_list_widget = QListWidget()
        self.update_roi_list()
        roi_list_layout.addWidget(self.roi_list_widget)
        
        roi_list_group.setLayout(roi_list_layout)
        layout.addWidget(roi_list_group)
        
        return widget
    
    def create_detection_tab(self):
        """실시간 검출 탭 생성"""
        widget = QWidget()
        layout = QHBoxLayout()
        widget.setLayout(layout)
        
        # 왼쪽: 비디오 표시
        left_layout = QVBoxLayout()
        
        self.detection_video_label = QLabel("실시간 검출 화면")
        self.detection_video_label.setAlignment(Qt.AlignCenter)
        self.detection_video_label.setMinimumSize(800, 600)
        self.detection_video_label.setStyleSheet("border: 2px solid #ccc; background-color: #000;")
        left_layout.addWidget(self.detection_video_label)
        
        # FPS 표시
        self.fps_label = QLabel("FPS: 0.0")
        self.fps_label.setStyleSheet("font-size: 14px; padding: 5px;")
        left_layout.addWidget(self.fps_label)
        
        # 검출 제어 버튼
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶️ 실시간 검출 시작")
        self.start_btn.clicked.connect(self.on_start_detection)
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 15px; font-size: 16px; font-weight: bold;")
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ 검출 중지")
        self.stop_btn.clicked.connect(self.on_stop_detection)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; padding: 15px; font-size: 16px; font-weight: bold;")
        control_layout.addWidget(self.stop_btn)
        
        left_layout.addLayout(control_layout)
        layout.addLayout(left_layout, 3)
        
        # 오른쪽: 실시간 상태
        right_layout = QVBoxLayout()
        
        status_label = QLabel("📊 실시간 상태")
        status_label.setFont(QFont("Arial", 14, QFont.Bold))
        right_layout.addWidget(status_label)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumWidth(300)
        right_layout.addWidget(self.status_text)
        
        layout.addLayout(right_layout, 1)
        
        return widget
    
    def create_stats_tab(self):
        """통계 & 로그 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # 얼굴 분석 통계
        face_stats_group = QGroupBox("😊 얼굴 분석 통계")
        face_stats_layout = QHBoxLayout()
        
        # 열 1: 총 검출 및 표정
        col1 = QVBoxLayout()
        self.total_faces_label = QLabel("🎭 총 검출 얼굴: 0")
        self.total_faces_label.setFont(QFont("Arial", 12, QFont.Bold))
        col1.addWidget(self.total_faces_label)
        
        self.expression_text = QTextEdit()
        self.expression_text.setReadOnly(True)
        self.expression_text.setMaximumHeight(150)
        col1.addWidget(QLabel("표정 분포:"))
        col1.addWidget(self.expression_text)
        
        face_stats_layout.addLayout(col1)
        
        # 열 2: 눈 상태
        col2 = QVBoxLayout()
        col2.addWidget(QLabel("👁️ 눈 상태"))
        self.eyes_open_label = QLabel("눈 뜸: 0")
        self.eyes_closed_label = QLabel("눈 감음: 0")
        col2.addWidget(self.eyes_open_label)
        col2.addWidget(self.eyes_closed_label)
        
        self.eye_progress = QProgressBar()
        self.eye_progress.setRange(0, 100)
        col2.addWidget(QLabel("개안율:"))
        col2.addWidget(self.eye_progress)
        
        face_stats_layout.addLayout(col2)
        
        # 열 3: 입 상태
        col3 = QVBoxLayout()
        col3.addWidget(QLabel("👄 입 상태"))
        self.mouth_closed_label = QLabel("닫힘: 0")
        self.mouth_speaking_label = QLabel("말하기: 0")
        self.mouth_open_label = QLabel("크게 열림: 0")
        col3.addWidget(self.mouth_closed_label)
        col3.addWidget(self.mouth_speaking_label)
        col3.addWidget(self.mouth_open_label)
        
        col3.addWidget(QLabel("😷 마스크/호흡기"))
        self.mask_label = QLabel("착용 검출: 0")
        col3.addWidget(self.mask_label)
        
        face_stats_layout.addLayout(col3)
        
        face_stats_group.setLayout(face_stats_layout)
        layout.addWidget(face_stats_group)
        
        # 통계 초기화 버튼
        reset_stats_btn = QPushButton("🔄 얼굴 분석 통계 초기화")
        reset_stats_btn.clicked.connect(self.on_reset_face_stats)
        layout.addWidget(reset_stats_btn)
        
        # YOLO 검출 통계
        yolo_stats_group = QGroupBox("📊 YOLO 검출 통계")
        self.yolo_stats_text = QTextEdit()
        self.yolo_stats_text.setReadOnly(True)
        self.yolo_stats_text.setMaximumHeight(150)
        yolo_stats_layout = QVBoxLayout()
        yolo_stats_layout.addWidget(self.yolo_stats_text)
        yolo_stats_group.setLayout(yolo_stats_layout)
        layout.addWidget(yolo_stats_group)
        
        # 이벤트 로그
        log_group = QGroupBox("📝 이벤트 로그")
        self.event_log_text = QTextEdit()
        self.event_log_text.setReadOnly(True)
        log_layout = QVBoxLayout()
        log_layout.addWidget(self.event_log_text)
        
        clear_log_btn = QPushButton("🧹 로그 초기화")
        clear_log_btn.clicked.connect(self.on_clear_log)
        log_layout.addWidget(clear_log_btn)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        return widget
    
    def create_api_test_tab(self):
        """API 테스트 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        test_group = QGroupBox("🔗 API 테스트")
        test_layout = QFormLayout()
        
        self.api_test_watch_id = QLineEdit(self.config.get('watch_id', ''))
        test_layout.addRow("Watch ID:", self.api_test_watch_id)
        
        self.api_test_sender_id = QLineEdit("test-user")
        test_layout.addRow("Sender ID:", self.api_test_sender_id)
        
        self.api_test_note = QLineEdit("Test event from PyQt UI")
        test_layout.addRow("Note:", self.api_test_note)
        
        test_btn = QPushButton("📤 API 테스트 실행")
        test_btn.clicked.connect(self.on_test_api)
        test_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 10px;")
        test_layout.addRow(test_btn)
        
        test_group.setLayout(test_layout)
        layout.addWidget(test_group)
        
        # 결과 표시
        result_group = QGroupBox("📊 테스트 결과")
        result_layout = QVBoxLayout()
        
        self.api_result_text = QTextEdit()
        self.api_result_text.setReadOnly(True)
        result_layout.addWidget(self.api_result_text)
        
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)
        
        layout.addStretch()
        
        return widget
    
    def on_save_settings(self):
        """설정 저장"""
        self.config['yolo_model'] = self.model_combo.currentText()
        self.config['camera_source'] = self.camera_source_spin.value()
        self.config['detection_interval_seconds'] = self.detection_interval_spin.value()
        self.config['confidence_threshold'] = self.confidence_spin.value()
        self.config['presence_threshold_seconds'] = self.presence_spin.value()
        self.config['absence_threshold_seconds'] = self.absence_spin.value()
        self.config['enable_face_analysis'] = self.face_analysis_check.isChecked()
        self.config['face_analysis_roi_only'] = self.face_roi_only_check.isChecked()
        self.config['watch_id'] = self.watch_id_edit.text()
        self.config['sender_id'] = self.sender_id_edit.text()
        self.config['api_endpoint'] = self.api_endpoint_edit.text()
        self.config['note'] = self.note_edit.text()
        self.config['method'] = self.method_edit.text()
        self.config['roi_regions'] = self.roi_regions
        
        self.save_config()
        QMessageBox.information(self, "설정 저장", "✅ 설정이 저장되었습니다!")
    
    def on_start_roi_edit(self):
        """ROI 편집 모드 시작 - 카메라 켜기"""
        if self.detector and self.detection_running:
            QMessageBox.warning(self, "ROI 편집", "❌ 실시간 검출을 중지하고 ROI 편집을 시작하세요!")
            return
        
        camera_source = self.config.get('camera_source', 0)
        self.camera_cap = cv2.VideoCapture(camera_source)
        
        if not self.camera_cap.isOpened():
            QMessageBox.critical(self, "카메라 오류", f"❌ 카메라 {camera_source}를 열 수 없습니다!")
            return
        
        self.roi_editing_mode = True
        self.start_roi_edit_btn.setEnabled(False)
        self.stop_roi_edit_btn.setEnabled(True)
        
        # ROI 편집용 타이머 시작
        self.roi_edit_timer = QTimer()
        self.roi_edit_timer.timeout.connect(self.update_roi_edit_display)
        self.roi_edit_timer.start(33)  # 30 FPS
        
        QMessageBox.information(self, "ROI 편집", "✅ ROI 편집 모드 시작! 화면을 클릭하여 ROI 점을 추가하세요.")
    
    def on_stop_roi_edit(self):
        """ROI 편집 모드 중지 - 카메라 끄기"""
        if hasattr(self, 'roi_edit_timer'):
            self.roi_edit_timer.stop()
        
        if self.camera_cap:
            self.camera_cap.release()
            self.camera_cap = None
        
        self.roi_editing_mode = False
        self.start_roi_edit_btn.setEnabled(True)
        self.stop_roi_edit_btn.setEnabled(False)
        self.roi_video_label.setText("카메라 프레임이 여기에 표시됩니다")
    
    def update_roi_edit_display(self):
        """ROI 편집 화면 업데이트"""
        if not self.camera_cap or not self.roi_editing_mode:
            return
        
        ret, frame = self.camera_cap.read()
        if not ret:
            return
        
        self.roi_edit_frame = frame.copy()
        display_frame = frame.copy()
        
        # 기존 ROI 그리기
        for roi in self.roi_regions:
            points = roi.get('points', [])
            if len(points) >= 3:
                pts = np.array(points, dtype=np.int32)
                cv2.polylines(display_frame, [pts], True, (0, 255, 0), 2)
                cv2.fillPoly(display_frame, [pts], (0, 255, 0, 50))
                
                # ROI ID 표시
                center_x = int(np.mean([p[0] for p in points]))
                center_y = int(np.mean([p[1] for p in points]))
                cv2.putText(display_frame, roi.get('id', ''), (center_x, center_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # 현재 편집 중인 점들 그리기
        for point in self.current_points:
            cv2.circle(display_frame, tuple(point), 5, (0, 0, 255), -1)
        
        # 현재 점들을 선으로 연결
        if len(self.current_points) >= 2:
            pts = np.array(self.current_points, dtype=np.int32)
            cv2.polylines(display_frame, [pts], False, (255, 0, 0), 2)
        
        # BGR to RGB
        frame_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        
        # 비디오 라벨 크기에 맞게 조정
        scaled_pixmap = pixmap.scaled(self.roi_video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.roi_video_label.setPixmap(scaled_pixmap)
    
    def on_roi_canvas_click(self, x, y):
        """ROI 캔버스 클릭 이벤트"""
        if not self.roi_editing_mode or self.roi_edit_frame is None:
            return
        
        # 라벨 크기 대비 실제 프레임 크기 비율 계산
        label_w = self.roi_video_label.width()
        label_h = self.roi_video_label.height()
        frame_h, frame_w = self.roi_edit_frame.shape[:2]
        
        # 스케일 비율 계산
        scale_x = frame_w / label_w
        scale_y = frame_h / label_h
        
        # 클릭 좌표를 실제 프레임 좌표로 변환
        real_x = int(x * scale_x)
        real_y = int(y * scale_y)
        
        # 프레임 경계 체크
        real_x = max(0, min(real_x, frame_w - 1))
        real_y = max(0, min(real_y, frame_h - 1))
        
        self.current_points.append([real_x, real_y])
        print(f"✅ 점 추가: ({real_x}, {real_y}) - 총 {len(self.current_points)}개 점")
    
    def on_add_current_point(self):
        """수동으로 현재 점 추가 (콘솔 입력)"""
        if not self.roi_editing_mode:
            QMessageBox.warning(self, "점 추가", "❌ ROI 편집 모드를 먼저 시작하세요!")
            return
        
        QMessageBox.information(self, "점 추가", "화면을 직접 클릭하여 점을 추가하세요!")
    
    def on_undo_last_point(self):
        """마지막 점 취소"""
        if self.current_points:
            removed = self.current_points.pop()
            QMessageBox.information(self, "점 취소", f"✅ 마지막 점이 취소되었습니다: {removed}")
        else:
            QMessageBox.warning(self, "점 취소", "❌ 취소할 점이 없습니다!")
    
    def on_complete_roi(self):
        """ROI 완성"""
        if len(self.current_points) < 3:
            QMessageBox.warning(self, "ROI 완성", "❌ ROI를 완성하려면 최소 3개 이상의 점이 필요합니다!")
            return
        
        # 새 ROI 생성
        new_roi = {
            'id': f'ROI_{len(self.roi_regions) + 1}',
            'description': f'사용자 정의 ROI {len(self.roi_regions) + 1}',
            'type': 'polygon',
            'points': self.current_points.copy()
        }
        
        self.roi_regions.append(new_roi)
        self.current_points = []
        self.update_roi_list()
        
        QMessageBox.information(self, "ROI 완성", f"✅ {new_roi['id']}가 생성되었습니다!")
    
    def on_create_lr_rois(self):
        """좌/우 2분할 ROI 생성"""
        # 카메라에서 프레임 크기 가져오기
        camera_source = self.config.get('camera_source', 0)
        cap = cv2.VideoCapture(camera_source)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                h, w = frame.shape[:2]
                self.roi_regions = create_left_right_rois(w, h)
                self.update_roi_list()
                QMessageBox.information(self, "ROI 생성", "✅ 좌/우 2분할 ROI가 생성되었습니다!")
            cap.release()
        else:
            QMessageBox.warning(self, "ROI 생성", "❌ 카메라를 열 수 없습니다!")
    
    def on_create_quad_rois(self):
        """4사분면 ROI 생성"""
        camera_source = self.config.get('camera_source', 0)
        cap = cv2.VideoCapture(camera_source)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                h, w = frame.shape[:2]
                self.roi_regions = create_quadrant_rois(w, h)
                self.update_roi_list()
                QMessageBox.information(self, "ROI 생성", "✅ 4사분면 ROI가 생성되었습니다!")
            cap.release()
        else:
            QMessageBox.warning(self, "ROI 생성", "❌ 카메라를 열 수 없습니다!")
    
    def on_clear_rois(self):
        """ROI 모두 삭제"""
        reply = QMessageBox.question(self, "ROI 삭제", 
                                     "모든 ROI를 삭제하시겠습니까?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.roi_regions = []
            self.update_roi_list()
    
    def update_roi_list(self):
        """ROI 목록 업데이트"""
        self.roi_list_widget.clear()
        for roi in self.roi_regions:
            self.roi_list_widget.addItem(f"{roi['id']} - {roi.get('description', 'No description')}")
    
    def on_start_detection(self):
        """실시간 검출 시작"""
        if not self.roi_regions:
            QMessageBox.warning(self, "검출 시작", "❌ ROI 영역을 먼저 설정해주세요!")
            return
        
        try:
            self.detector = RealtimeDetector(self.config, self.roi_regions)
            self.detector.start()
            self.detection_running = True
            
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            
            self.update_timer.start()
            
            QMessageBox.information(self, "검출 시작", "✅ 실시간 검출이 시작되었습니다!")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"❌ 검출 시작 실패:\n{str(e)}")
    
    def on_stop_detection(self):
        """실시간 검출 중지"""
        if self.detector:
            self.detector.stop()
            self.detector = None
        
        self.detection_running = False
        self.update_timer.stop()
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        QMessageBox.information(self, "검출 중지", "⏹️ 실시간 검출이 중지되었습니다!")
    
    def update_detection_display(self):
        """실시간 검출 화면 업데이트"""
        if not self.detector or not self.detection_running:
            return
        
        # 최신 프레임 가져오기
        frame = self.detector.get_latest_frame()
        if frame is not None:
            # BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            
            # 비디오 라벨 크기에 맞게 조정
            scaled_pixmap = pixmap.scaled(self.detection_video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.detection_video_label.setPixmap(scaled_pixmap)
            
            # FPS 업데이트
            self.fps_label.setText(f"FPS: {self.detector.fps:.1f}")
        
        # 통계 업데이트
        stats_updates = self.detector.get_latest_stats()
        for stat in stats_updates:
            roi_id = stat['roi_id']
            self.detection_stats[roi_id] = {
                'status': stat['status'],
                'count': stat['count']
            }
        
        # 상태 텍스트 업데이트
        status_text = ""
        for roi_id, stats in self.detection_stats.items():
            status_emoji = "🟢" if stats['status'] == 'present' else "🔴"
            status_text += f"{status_emoji} {roi_id}: {stats['status']} (카운트: {stats['count']})\n"
        self.status_text.setPlainText(status_text)
        
        # 얼굴 분석 통계 업데이트 (YOLO 검출 주기와 동기화)
        # last_face_results는 YOLO 검출 주기마다 한 번만 업데이트됨
        if hasattr(self.detector, 'last_face_results') and self.detector.last_face_results:
            # 이전에 처리한 프레임 타임스탬프 추적
            current_timestamp = time.time()
            if not hasattr(self, '_last_face_stats_update'):
                self._last_face_stats_update = 0
            
            # YOLO 검출 간격보다 짧은 간격으로 중복 집계 방지
            detection_interval = self.config.get('detection_interval_seconds', 1.0)
            if current_timestamp - self._last_face_stats_update >= detection_interval * 0.9:
                for bbox, face_result in self.detector.last_face_results.items():
                    if face_result and face_result.get('face_detected'):
                        self.face_analysis_stats['total_faces_detected'] += 1
                        
                        if face_result.get('eyes_open'):
                            self.face_analysis_stats['eyes_open_count'] += 1
                        else:
                            self.face_analysis_stats['eyes_closed_count'] += 1
                        
                        mouth_state = face_result.get('mouth_state', 'closed')
                        if mouth_state == 'closed':
                            self.face_analysis_stats['mouth_closed_count'] += 1
                        elif mouth_state == 'speaking':
                            self.face_analysis_stats['mouth_speaking_count'] += 1
                        elif mouth_state == 'wide_open':
                            self.face_analysis_stats['mouth_wide_open_count'] += 1
                        
                        expr_info = face_result.get('expression', {})
                        if isinstance(expr_info, dict):
                            expression = expr_info.get('expression', 'neutral')
                            if expression in self.face_analysis_stats['expressions']:
                                self.face_analysis_stats['expressions'][expression] += 1
                            self.face_analysis_stats['last_expression'] = expression
                        
                        if face_result.get('has_mask_or_ventilator'):
                            self.face_analysis_stats['mask_detected_count'] += 1
                
                self._last_face_stats_update = current_timestamp
        
        self.update_face_stats_display()
        
        # 이벤트 로그 업데이트
        events = self.detector.get_latest_events()
        for event in events:
            self.event_log.append(event)
        
        self.update_event_log_display()
        self.update_yolo_stats_display()
    
    def update_face_stats_display(self):
        """얼굴 분석 통계 표시 업데이트"""
        stats = self.face_analysis_stats
        
        # 총 검출 얼굴
        self.total_faces_label.setText(f"🎭 총 검출 얼굴: {stats['total_faces_detected']}")
        
        # 표정 분포
        expr_text = ""
        total_expr = sum(stats['expressions'].values())
        if total_expr > 0:
            emoji_map = {'neutral': '😐', 'happy': '😊', 'sad': '😢', 
                        'surprised': '😲', 'pain': '😖', 'angry': '😠'}
            for expr, count in stats['expressions'].items():
                if count > 0:
                    percentage = (count / total_expr) * 100
                    expr_text += f"{emoji_map.get(expr, '😐')} {expr.capitalize()}: {count} ({percentage:.1f}%)\n"
        self.expression_text.setPlainText(expr_text)
        
        # 눈 상태
        self.eyes_open_label.setText(f"눈 뜸: {stats['eyes_open_count']}")
        self.eyes_closed_label.setText(f"눈 감음: {stats['eyes_closed_count']}")
        
        total_eyes = stats['eyes_open_count'] + stats['eyes_closed_count']
        if total_eyes > 0:
            open_rate = int((stats['eyes_open_count'] / total_eyes) * 100)
            self.eye_progress.setValue(open_rate)
        
        # 입 상태
        self.mouth_closed_label.setText(f"닫힘: {stats['mouth_closed_count']}")
        self.mouth_speaking_label.setText(f"말하기: {stats['mouth_speaking_count']}")
        self.mouth_open_label.setText(f"크게 열림: {stats['mouth_wide_open_count']}")
        
        # 마스크
        self.mask_label.setText(f"착용 검출: {stats['mask_detected_count']}")
    
    def update_yolo_stats_display(self):
        """YOLO 통계 표시 업데이트"""
        stats_text = ""
        for roi_id, stats in self.detection_stats.items():
            stats_text += f"{roi_id}: {stats['status']} (카운트: {stats['count']})\n"
        self.yolo_stats_text.setPlainText(stats_text)
    
    def update_event_log_display(self):
        """이벤트 로그 표시 업데이트"""
        log_text = ""
        for event in reversed(list(self.event_log)):
            timestamp = event.get('timestamp', 'N/A')
            roi_id = event.get('roi_id', 'N/A')
            status = event.get('status', 'N/A')
            status_emoji = '🟢' if status == 'present' else '🔴'
            log_text += f"{status_emoji} [{timestamp}] {roi_id}: {status}\n"
        self.event_log_text.setPlainText(log_text)
    
    def on_reset_face_stats(self):
        """얼굴 분석 통계 초기화"""
        self.face_analysis_stats = {
            'total_faces_detected': 0,
            'expressions': {'neutral': 0, 'happy': 0, 'sad': 0, 'surprised': 0, 'pain': 0, 'angry': 0},
            'eyes_open_count': 0,
            'eyes_closed_count': 0,
            'mouth_closed_count': 0,
            'mouth_speaking_count': 0,
            'mouth_wide_open_count': 0,
            'mask_detected_count': 0,
            'last_expression': None,
            'last_update': None
        }
        self.update_face_stats_display()
        QMessageBox.information(self, "통계 초기화", "✅ 얼굴 분석 통계가 초기화되었습니다!")
    
    def on_clear_log(self):
        """이벤트 로그 초기화"""
        self.event_log.clear()
        self.update_event_log_display()
    
    def on_test_api(self):
        """API 테스트 실행"""
        import requests
        
        try:
            payload = {
                'eventId': f"test_{int(datetime.now().timestamp())}",
                'watch_id': self.api_test_watch_id.text(),
                'senderId': self.api_test_sender_id.text(),
                'note': self.api_test_note.text(),
                'timestamp': datetime.now().isoformat()
            }
            
            response = requests.post(
                self.config.get('api_endpoint', ''),
                json=payload,
                timeout=5
            )
            
            result_text = f"📤 요청:\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n\n"
            result_text += f"📥 응답:\n상태 코드: {response.status_code}\n"
            result_text += f"응답 본문:\n{response.text}"
            
            self.api_result_text.setPlainText(result_text)
            
            if response.status_code in [200, 201]:
                QMessageBox.information(self, "API 테스트", "✅ API 전송 성공!")
            else:
                QMessageBox.warning(self, "API 테스트", f"⚠️ API 응답 오류: {response.status_code}")
                
        except Exception as e:
            error_text = f"❌ API 테스트 실패:\n{str(e)}"
            self.api_result_text.setPlainText(error_text)
            QMessageBox.critical(self, "API 테스트", error_text)
    
    def closeEvent(self, event):
        """윈도우 닫기 이벤트"""
        # 검출 중지
        if self.detector:
            self.detector.stop()
        
        # ROI 편집 중지
        if hasattr(self, 'roi_edit_timer'):
            self.roi_edit_timer.stop()
        
        # 카메라 해제
        if self.camera_cap:
            self.camera_cap.release()
        
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
