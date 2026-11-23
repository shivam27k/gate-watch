"""Save one frame per channel to /data/frame_ch<N>.jpg: python scripts/grab_frame.py 1 2"""
import os
import sys

os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")
import cv2

from gatewatch.logic import rtsp_url

for ch in sys.argv[1:] or ["1", "2"]:
    url = rtsp_url(os.environ["NVR_HOST"], os.environ["NVR_USER"], os.environ["NVR_PASS"], int(ch), subtype=0)
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    ok, frame = cap.read()
    cap.release()
    if ok:
        cv2.imwrite(f"/data/frame_ch{ch}.jpg", frame)
        print(f"channel {ch}: saved {frame.shape[1]}x{frame.shape[0]}")
    else:
        print(f"channel {ch}: no frame")
