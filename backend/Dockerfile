# Santhra backend — FastAPI + CPU PyTorch. Build context = repo root.
FROM python:3.11-slim

# opencv-headless needs libglib; torch needs libgomp
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libgomp1 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# CPU torch first (large wheels), then the rest. Generous timeout/retries so a
# slow mirror does not stall the build.
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --timeout 180 --retries 6 \
      torch==2.6.0 torchvision==0.21.0 \
      --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir --timeout 180 --retries 6 -r requirements.txt

# app code + committed model checkpoints (REPO_ROOT resolves to /app)
COPY backend/ ./backend/
COPY ml/checkpoints/ ./ml/checkpoints/
RUN mkdir -p /app/data /app/media

ENV SANTHRA_DEVICE=cpu \
    LOG_LEVEL=INFO \
    DATABASE_URL=sqlite:////app/data/santhra.db \
    PYTHONUNBUFFERED=1

WORKDIR /app/backend
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --retries=5 --start-period=40s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
