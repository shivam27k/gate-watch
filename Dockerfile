FROM python:3.12-slim
WORKDIR /app
ENV PIP_DEFAULT_TIMEOUT=100 PIP_RETRIES=10
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir ultralytics opencv-python-headless requests
COPY gatewatch ./gatewatch
COPY scripts ./scripts
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
CMD ["python", "-m", "gatewatch.main"]
