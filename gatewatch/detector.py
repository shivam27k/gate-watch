import threading


class Detector:
    """One shared model; calls from camera threads are serialised with a lock."""

    def __init__(self, model_path="yolov8n.pt", conf=0.5):
        from ultralytics import YOLO
        self.model = YOLO(model_path)
        self.conf = conf
        self._lock = threading.Lock()

    def person_boxes(self, frame):
        with self._lock:
            r = self.model(frame, classes=[0], conf=self.conf, imgsz=640, verbose=False)[0]
        return [tuple(b) for b in r.boxes.xyxy.tolist()]


def save_snapshot(frame, boxes, zone, path):
    import cv2
    import numpy as np
    img = frame.copy()
    cv2.polylines(img, [np.array(zone, dtype=np.int32)], True, (0, 255, 255), 2)
    for x1, y1, x2, y2 in boxes:
        cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)
    cv2.imwrite(path, img)
