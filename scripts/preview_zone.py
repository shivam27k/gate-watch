"""Draw each camera's zone on a saved frame so you can check it.

    python scripts/preview_zone.py data/cameras.json car data/frame_ch1.jpg data/preview_car.jpg
"""
import json
import sys

import cv2
import numpy as np

cameras_file, name, frame_path, out_path = sys.argv[1:5]
cam = next(c for c in json.load(open(cameras_file)) if c["name"] == name)
img = cv2.imread(frame_path)
h, w = img.shape[:2]
poly = np.array([[x * w, y * h] for x, y in cam["zone"]], dtype=np.int32)
overlay = img.copy()
cv2.fillPoly(overlay, [poly], (0, 255, 255))
img = cv2.addWeighted(overlay, 0.25, img, 0.75, 0)
cv2.polylines(img, [poly], True, (0, 255, 255), 2)
cv2.imwrite(out_path, img)
print(f"wrote {out_path}")
