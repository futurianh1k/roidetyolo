"""
ResultStorage - 검출 결과 저장 및 관리

저장 경로 구조:
  {base_path}/{날짜 YYYYMMDD}/{소스타입}/{세션시작시간 HHMMSS}/
    ├── frame_0001.jpg
    ├── frame_0002.jpg
    └── metadata.json

용량 관리:
  - 최대 용량 초과 시 가장 오래된 세션부터 삭제
  - 세션 단위로 삭제

참고자료:
- Python pathlib: https://docs.python.org/3/library/pathlib.html
- shutil: https://docs.python.org/3/library/shutil.html
"""

import os
import json
import shutil
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from threading import Lock
import time


@dataclass
class FrameMetadata:
    """프레임 메타데이터"""

    filename: str
    captured_at: str  # ISO 형식
    detections_count: int
    detections: List[Dict[str, Any]]
    face_results: List[Dict[str, Any]]


@dataclass
class SessionMetadata:
    """세션 메타데이터"""

    session_id: str
    source_type: str
    source: str
    start_time: str  # ISO 형식
    frames: List[Dict[str, Any]]
    total_frames: int
    last_updated: str  # ISO 형식


class ResultStorage:
    """
    검출 결과 저장 관리자

    사용법:
        storage = ResultStorage(base_path="./detection_results", max_size_mb=100)
        storage.start_session("http_post", "CoreS3 장비")

        # 검출 결과 저장
        filepath = storage.save_detection(annotated_frame, detections, face_results)

        # 세션 목록 조회
        sessions = storage.list_sessions()

        # 세션 내 프레임 조회
        frames = storage.list_frames(session_path)
    """

    def __init__(self, base_path: str = "./detection_results", max_size_mb: int = 100):
        """
        Args:
            base_path: 기본 저장 경로
            max_size_mb: 최대 저장 용량 (MB)
        """
        self.base_path = Path(base_path)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_size_mb = max_size_mb

        # 세션 정보
        self.session_id: Optional[str] = None
        self.session_path: Optional[Path] = None
        self.source_type: Optional[str] = None
        self.source_name: Optional[str] = None
        self.session_start_time: Optional[datetime] = None

        # 프레임 카운터
        self.frame_counter = 0

        # 스레드 안전
        self._lock = Lock()

        # 메타데이터 캐시
        self._metadata: Optional[SessionMetadata] = None

        # 기본 경로 생성
        self.base_path.mkdir(parents=True, exist_ok=True)

        print(
            f"[ResultStorage] 초기화 완료 - 경로: {self.base_path}, 최대: {max_size_mb}MB"
        )

    def start_session(self, source_type: str, source_name: str = "") -> str:
        """
        새 세션 시작 (소스 변경 시 호출)

        Args:
            source_type: 소스 타입 (usb, http_post, rtsp, http 등)
            source_name: 소스 이름 (옵션)

        Returns:
            세션 경로
        """
        with self._lock:
            now = datetime.now()

            # 세션 ID (시간 기반)
            self.session_id = now.strftime("%H%M%S")
            self.session_start_time = now
            self.source_type = self._sanitize_path(source_type)
            self.source_name = source_name or source_type

            # 경로 생성: base_path/날짜/소스타입/세션시간
            date_str = now.strftime("%Y%m%d")
            self.session_path = (
                self.base_path / date_str / self.source_type / self.session_id
            )
            self.session_path.mkdir(parents=True, exist_ok=True)

            # 프레임 카운터 초기화
            self.frame_counter = 0

            # 메타데이터 초기화
            self._metadata = SessionMetadata(
                session_id=self.session_id,
                source_type=source_type,
                source=self.source_name,
                start_time=now.isoformat(),
                frames=[],
                total_frames=0,
                last_updated=now.isoformat(),
            )
            self._save_metadata()

            print(f"[ResultStorage] 새 세션 시작: {self.session_path}")
            return str(self.session_path)

    def end_session(self):
        """
        현재 세션 종료

        세션 정보를 초기화하고 메타데이터를 최종 저장합니다.
        """
        with self._lock:
            if self.session_path is None:
                return

            # 최종 메타데이터 저장
            if self._metadata:
                self._metadata.last_updated = datetime.now().isoformat()
                self._save_metadata()

            session_info = (
                f"{self.source_type}/{self.session_id}"
                if self.source_type
                else "unknown"
            )
            total_frames = self.frame_counter

            # 세션 정보 초기화
            self.session_id = None
            self.session_path = None
            self.source_type = None
            self.source_name = None
            self.session_start_time = None
            self.frame_counter = 0
            self._metadata = None

            print(f"[ResultStorage] 세션 종료: {session_info} (총 {total_frames}장)")

    def is_session_active(self) -> bool:
        """세션 활성 상태 확인"""
        return self.session_path is not None

    def save_detection(
        self,
        annotated_frame: np.ndarray,
        detections: List[Dict[str, Any]],
        face_results: Dict[Any, Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        검출 결과 저장 (bbox가 그려진 이미지)

        Args:
            annotated_frame: bbox가 그려진 프레임
            detections: 검출 결과 리스트
            face_results: 얼굴 분석 결과 (bbox 튜플 -> 결과)

        Returns:
            저장된 파일 경로 또는 None
        """
        if self.session_path is None:
            print("[ResultStorage] ⚠️ 세션이 시작되지 않음")
            return None

        with self._lock:
            # 용량 체크 및 정리
            self._ensure_storage_space()

            # 파일명 생성
            self.frame_counter += 1
            filename = f"frame_{self.frame_counter:04d}.jpg"
            filepath = self.session_path / filename

            # 이미지 저장 (JPEG 품질 85)
            success = cv2.imwrite(
                str(filepath), annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 85]
            )

            if not success:
                print(f"[ResultStorage] ❌ 이미지 저장 실패: {filepath}")
                return None

            # 얼굴 분석 결과 변환
            face_list = []
            if face_results:
                for bbox_tuple, result in face_results.items():
                    if isinstance(bbox_tuple, tuple):
                        bbox = list(bbox_tuple)
                    else:
                        bbox = bbox_tuple

                    expr_info = result.get("expression", {})
                    if isinstance(expr_info, dict):
                        face_list.append(
                            {
                                "bbox": bbox,
                                "expression": expr_info.get("expression", "unknown"),
                                "expression_confidence": expr_info.get("confidence", 0),
                            }
                        )

            # 프레임 메타데이터
            now = datetime.now()
            frame_meta = {
                "filename": filename,
                "captured_at": now.isoformat(),
                "detections_count": len(detections),
                "detections": [
                    {
                        "bbox": det.get("bbox", []),
                        "confidence": round(det.get("confidence", 0), 3),
                        "class": (
                            "person"
                            if det.get("class", 0) == 0
                            else str(det.get("class", "unknown"))
                        ),
                    }
                    for det in detections
                ],
                "face_results": face_list,
            }

            # 메타데이터 업데이트
            if self._metadata:
                self._metadata.frames.append(frame_meta)
                self._metadata.total_frames = len(self._metadata.frames)
                self._metadata.last_updated = now.isoformat()
                self._save_metadata()

            print(f"[ResultStorage] 💾 저장: {filename} (검출: {len(detections)}명)")
            return str(filepath)

    def _save_metadata(self):
        """메타데이터 저장"""
        if self.session_path is None or self._metadata is None:
            return

        metadata_path = self.session_path / "metadata.json"
        try:
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(asdict(self._metadata), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ResultStorage] ❌ 메타데이터 저장 실패: {e}")

    def _ensure_storage_space(self):
        """저장 공간 확보 (용량 초과 시 정리)"""
        current_size = self.get_total_size()

        if current_size < self.max_size_bytes:
            return

        print(
            f"[ResultStorage] ⚠️ 용량 초과 ({current_size / 1024 / 1024:.1f}MB), 정리 시작..."
        )

        # 가장 오래된 세션부터 삭제
        sessions = self.list_sessions()
        sessions.sort(key=lambda x: x.get("start_time", ""))

        for session in sessions:
            if current_size < self.max_size_bytes * 0.8:  # 80%까지 정리
                break

            session_path = session.get("path")
            if session_path and Path(session_path).exists():
                # 현재 세션은 삭제하지 않음
                if self.session_path and str(self.session_path) == session_path:
                    continue

                session_size = self._get_folder_size(Path(session_path))
                try:
                    shutil.rmtree(session_path)
                    current_size -= session_size
                    print(f"[ResultStorage] 🗑️ 삭제됨: {session_path}")
                except Exception as e:
                    print(f"[ResultStorage] ❌ 삭제 실패: {e}")

        # 빈 날짜 폴더 정리
        self._cleanup_empty_folders()

    def _cleanup_empty_folders(self):
        """빈 폴더 정리"""
        for date_folder in self.base_path.iterdir():
            if date_folder.is_dir():
                for source_folder in date_folder.iterdir():
                    if source_folder.is_dir() and not any(source_folder.iterdir()):
                        source_folder.rmdir()

                if not any(date_folder.iterdir()):
                    date_folder.rmdir()

    def get_total_size(self) -> int:
        """전체 저장 용량 (bytes)"""
        return self._get_folder_size(self.base_path)

    def get_total_size_mb(self) -> float:
        """전체 저장 용량 (MB)"""
        return self.get_total_size() / 1024 / 1024

    def _get_folder_size(self, folder: Path) -> int:
        """폴더 크기 계산"""
        total = 0
        try:
            for item in folder.rglob("*"):
                if item.is_file():
                    total += item.stat().st_size
        except Exception:
            pass
        return total

    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        저장된 세션 목록 조회

        Returns:
            세션 정보 리스트 (날짜, 소스타입, 세션ID, 프레임 수 등)
        """
        sessions = []

        try:
            for date_folder in sorted(self.base_path.iterdir(), reverse=True):
                if not date_folder.is_dir():
                    continue

                date_str = date_folder.name

                for source_folder in sorted(date_folder.iterdir()):
                    if not source_folder.is_dir():
                        continue

                    source_type = source_folder.name

                    for session_folder in sorted(source_folder.iterdir(), reverse=True):
                        if not session_folder.is_dir():
                            continue

                        session_id = session_folder.name

                        # 메타데이터 읽기
                        metadata_path = session_folder / "metadata.json"
                        metadata = {}
                        if metadata_path.exists():
                            try:
                                with open(metadata_path, "r", encoding="utf-8") as f:
                                    metadata = json.load(f)
                            except Exception:
                                pass

                        # 이미지 파일 수 계산
                        image_count = len(list(session_folder.glob("*.jpg")))

                        # 폴더 크기
                        folder_size = self._get_folder_size(session_folder)

                        sessions.append(
                            {
                                "date": date_str,
                                "source_type": source_type,
                                "session_id": session_id,
                                "path": str(session_folder),
                                "start_time": metadata.get("start_time", ""),
                                "source_name": metadata.get("source", source_type),
                                "total_frames": metadata.get(
                                    "total_frames", image_count
                                ),
                                "last_updated": metadata.get("last_updated", ""),
                                "size_mb": round(folder_size / 1024 / 1024, 2),
                            }
                        )
        except Exception as e:
            print(f"[ResultStorage] ❌ 세션 목록 조회 실패: {e}")

        return sessions

    def list_dates(self) -> List[str]:
        """저장된 날짜 목록"""
        dates = []
        try:
            for folder in sorted(self.base_path.iterdir(), reverse=True):
                if folder.is_dir() and len(folder.name) == 8:  # YYYYMMDD
                    dates.append(folder.name)
        except Exception:
            pass
        return dates

    def list_sources_by_date(self, date: str) -> List[str]:
        """특정 날짜의 소스 타입 목록"""
        sources = []
        date_path = self.base_path / date
        try:
            if date_path.exists():
                for folder in sorted(date_path.iterdir()):
                    if folder.is_dir():
                        sources.append(folder.name)
        except Exception:
            pass
        return sources

    def list_sessions_by_date_source(
        self, date: str, source_type: str
    ) -> List[Dict[str, Any]]:
        """특정 날짜/소스의 세션 목록"""
        sessions = []
        source_path = self.base_path / date / source_type

        try:
            if source_path.exists():
                for session_folder in sorted(source_path.iterdir(), reverse=True):
                    if session_folder.is_dir():
                        metadata_path = session_folder / "metadata.json"
                        metadata = {}
                        if metadata_path.exists():
                            try:
                                with open(metadata_path, "r", encoding="utf-8") as f:
                                    metadata = json.load(f)
                            except Exception:
                                pass

                        sessions.append(
                            {
                                "session_id": session_folder.name,
                                "path": str(session_folder),
                                "start_time": metadata.get("start_time", ""),
                                "total_frames": metadata.get("total_frames", 0),
                                "size_mb": round(
                                    self._get_folder_size(session_folder) / 1024 / 1024,
                                    2,
                                ),
                            }
                        )
        except Exception:
            pass

        return sessions

    def list_frames(self, session_path: str) -> List[Dict[str, Any]]:
        """
        세션 내 프레임 목록 조회

        Args:
            session_path: 세션 폴더 경로

        Returns:
            프레임 정보 리스트
        """
        frames = []
        session_folder = Path(session_path)

        if not session_folder.exists():
            return frames

        # 메타데이터 읽기
        metadata_path = session_folder / "metadata.json"
        metadata = {}
        if metadata_path.exists():
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
            except Exception:
                pass

        # 메타데이터에서 프레임 정보 가져오기
        if "frames" in metadata:
            for frame_info in metadata["frames"]:
                frame_path = session_folder / frame_info["filename"]
                if frame_path.exists():
                    frames.append({**frame_info, "path": str(frame_path)})
        else:
            # 메타데이터 없으면 파일 목록에서 생성
            for img_path in sorted(session_folder.glob("*.jpg")):
                frames.append(
                    {
                        "filename": img_path.name,
                        "path": str(img_path),
                        "captured_at": datetime.fromtimestamp(
                            img_path.stat().st_mtime
                        ).isoformat(),
                        "detections_count": 0,
                        "detections": [],
                        "face_results": [],
                    }
                )

        return frames

    def load_frame_image(self, frame_path: str) -> Optional[np.ndarray]:
        """프레임 이미지 로드"""
        try:
            return cv2.imread(frame_path)
        except Exception:
            return None

    def delete_session(self, session_path: str) -> bool:
        """세션 삭제"""
        try:
            if Path(session_path).exists():
                shutil.rmtree(session_path)
                self._cleanup_empty_folders()
                print(f"[ResultStorage] 🗑️ 세션 삭제됨: {session_path}")
                return True
        except Exception as e:
            print(f"[ResultStorage] ❌ 세션 삭제 실패: {e}")
        return False

    def get_storage_info(self) -> Dict[str, Any]:
        """저장소 정보"""
        total_size = self.get_total_size()
        return {
            "base_path": str(self.base_path),
            "used_mb": round(total_size / 1024 / 1024, 2),
            "max_mb": self.max_size_mb,
            "usage_percent": (
                round(total_size / self.max_size_bytes * 100, 1)
                if self.max_size_bytes > 0
                else 0
            ),
            "current_session": str(self.session_path) if self.session_path else None,
        }

    def _sanitize_path(self, name: str) -> str:
        """경로에 사용할 수 없는 문자 제거"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, "_")
        return name


# 전역 인스턴스
_storage_instance: Optional[ResultStorage] = None


def get_storage(
    base_path: str = "./detection_results", max_size_mb: int = 100
) -> ResultStorage:
    """전역 스토리지 인스턴스 가져오기"""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = ResultStorage(base_path, max_size_mb)
    return _storage_instance


def reset_storage():
    """전역 스토리지 인스턴스 초기화"""
    global _storage_instance
    _storage_instance = None
