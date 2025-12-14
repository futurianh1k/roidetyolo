"""
이미지 수신 서버 (FastAPI)
- CoreS3 장비에서 주기적으로 POST하는 이미지를 수신
- 수신된 이미지를 공유 큐에 저장하여 검출기에서 사용

사용법:
    python image_receiver.py --port 8502

또는 Streamlit과 함께 백그라운드로 실행됨

참고자료:
- FastAPI: https://fastapi.tiangolo.com/
- OpenCV 이미지 디코딩: https://docs.opencv.org/4.x/d4/da8/group__imgcodecs.html
"""

import asyncio
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any
from queue import Queue, Full
import numpy as np
import cv2

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn


# 전역 이미지 큐 (검출기와 공유)
_image_queue: Optional[Queue] = None
_last_image: Optional[np.ndarray] = None
_last_image_time: Optional[float] = None
_stats = {
    "received_count": 0,
    "last_received_at": None,
    "last_device_id": None,
    "last_image_size": None,
    "errors_count": 0,
}


def get_image_queue() -> Queue:
    """이미지 큐 가져오기 (없으면 생성)"""
    global _image_queue
    if _image_queue is None:
        _image_queue = Queue(maxsize=10)
    return _image_queue


def set_image_queue(queue: Queue):
    """외부에서 큐 설정 (검출기와 공유용)"""
    global _image_queue
    _image_queue = queue


def get_last_image() -> Optional[np.ndarray]:
    """마지막으로 수신된 이미지 가져오기"""
    return _last_image


def get_last_image_time() -> Optional[float]:
    """마지막 이미지 수신 시간"""
    return _last_image_time


def get_stats() -> Dict[str, Any]:
    """수신 통계"""
    return _stats.copy()


# FastAPI 앱 생성
app = FastAPI(
    title="Image Receiver Server",
    description="CoreS3 장비에서 전송하는 이미지를 수신하는 서버",
    version="1.0.0",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """서버 상태 확인"""
    return {
        "status": "running",
        "service": "Image Receiver Server",
        "stats": get_stats(),
    }


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/upload/image")
async def upload_image(
    file: UploadFile = File(...), device_id: Optional[str] = Form(None)
):
    """
    이미지 업로드 엔드포인트

    CoreS3에서 JPEG 이미지를 POST로 전송

    Args:
        file: JPEG 이미지 파일
        device_id: 장비 ID (선택)

    Returns:
        JSONResponse: 처리 결과
    """
    global _last_image, _last_image_time, _stats

    try:
        # 파일 읽기
        contents = await file.read()

        if len(contents) == 0:
            _stats["errors_count"] += 1
            raise HTTPException(status_code=400, detail="Empty file")

        # JPEG 디코딩
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            _stats["errors_count"] += 1
            raise HTTPException(status_code=400, detail="Failed to decode image")

        # 통계 업데이트
        current_time = time.time()
        _stats["received_count"] += 1
        _stats["last_received_at"] = datetime.now().isoformat()
        _stats["last_device_id"] = device_id
        _stats["last_image_size"] = f"{image.shape[1]}x{image.shape[0]}"

        # 마지막 이미지 저장
        _last_image = image
        _last_image_time = current_time

        # 큐에 이미지 추가
        queue = get_image_queue()
        try:
            # 큐가 가득 차면 오래된 이미지 제거
            if queue.full():
                try:
                    queue.get_nowait()
                except:
                    pass
            queue.put_nowait(image)
        except Full:
            pass  # 무시

        print(
            f"[ImageReceiver] 📷 이미지 수신: {image.shape[1]}x{image.shape[0]}, device={device_id}, total={_stats['received_count']}"
        )

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Image received",
                "size": f"{image.shape[1]}x{image.shape[0]}",
                "received_count": _stats["received_count"],
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        _stats["errors_count"] += 1
        print(f"[ImageReceiver] ❌ 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload/frame")
async def upload_frame_raw(file: UploadFile = File(...)):
    """
    간단한 이미지 업로드 (Form 없이 JPEG만)

    CoreS3에서 단순히 JPEG 바이너리만 POST하는 경우
    """
    return await upload_image(file=file, device_id=None)


@app.get("/stats")
async def get_statistics():
    """수신 통계 조회"""
    stats = get_stats()

    # 마지막 이미지 시간 계산
    if _last_image_time:
        stats["seconds_since_last_image"] = time.time() - _last_image_time
    else:
        stats["seconds_since_last_image"] = None

    return stats


@app.get("/last-image/info")
async def get_last_image_info():
    """마지막 수신 이미지 정보"""
    if _last_image is None:
        return {"available": False}

    return {
        "available": True,
        "width": _last_image.shape[1],
        "height": _last_image.shape[0],
        "channels": _last_image.shape[2] if len(_last_image.shape) > 2 else 1,
        "received_at": _stats.get("last_received_at"),
        "device_id": _stats.get("last_device_id"),
    }


class ImageReceiverServer:
    """
    이미지 수신 서버 관리 클래스
    백그라운드 스레드에서 실행
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8502):
        self.host = host
        self.port = port
        self.server = None
        self.thread = None
        self.running = False

    def start(self):
        """서버 시작 (백그라운드 스레드)"""
        if self.running:
            print("[ImageReceiverServer] 이미 실행 중")
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        print(f"[ImageReceiverServer] ✅ 시작됨 - http://{self.host}:{self.port}")

    def _run_server(self):
        """서버 실행 (스레드에서 호출)"""
        try:
            config = uvicorn.Config(
                app=app,
                host=self.host,
                port=self.port,
                log_level="warning",  # 로그 최소화
                access_log=False,
            )
            self.server = uvicorn.Server(config)

            # 새 이벤트 루프에서 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.server.serve())
        except Exception as e:
            print(f"[ImageReceiverServer] ❌ 오류: {e}")
            self.running = False

    def stop(self):
        """서버 중지"""
        if self.server:
            self.server.should_exit = True
        self.running = False
        print("[ImageReceiverServer] 중지됨")

    def is_running(self) -> bool:
        """실행 상태 확인"""
        return self.running


# 전역 서버 인스턴스
_server_instance: Optional[ImageReceiverServer] = None


def get_server() -> ImageReceiverServer:
    """전역 서버 인스턴스 가져오기"""
    global _server_instance
    if _server_instance is None:
        _server_instance = ImageReceiverServer()
    return _server_instance


def start_receiver_server(host: str = "0.0.0.0", port: int = 8502):
    """서버 시작 (편의 함수)"""
    server = get_server()
    server.host = host
    server.port = port
    server.start()
    return server


def stop_receiver_server():
    """서버 중지 (편의 함수)"""
    global _server_instance
    if _server_instance:
        _server_instance.stop()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Image Receiver Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8502, help="Port to listen")
    args = parser.parse_args()

    print(f"[ImageReceiver] 서버 시작: http://{args.host}:{args.port}")
    print(
        f"[ImageReceiver] 이미지 업로드 URL: http://{args.host}:{args.port}/upload/image"
    )
    print(f"[ImageReceiver] Ctrl+C로 종료")

    uvicorn.run(app, host=args.host, port=args.port)
