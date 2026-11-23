import os
import threading
import time

os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")


class Stream:
    """Background thread keeps the newest frame; read() returns it once, or None."""

    def __init__(self, url):
        self.url = url
        self._frame = None
        self._lock = threading.Lock()
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        import cv2
        backoff = 1
        while True:
            cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
            while cap.isOpened():
                ok, frame = cap.read()
                if not ok:
                    break
                backoff = 1
                with self._lock:
                    self._frame = frame
            cap.release()
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)

    def read(self):
        with self._lock:
            f, self._frame = self._frame, None
        return f
