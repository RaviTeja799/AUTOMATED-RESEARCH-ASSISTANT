FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only torch first (largest dep, benefits from layer caching)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        "torch>=2.6.0"

# Install remaining dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/
COPY main.py .
COPY frontend/ ./frontend/
COPY scripts/ ./scripts/

# Create writable directories
RUN mkdir -p data/uploads data/processed logs

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/live || exit 1

# Railway injects $PORT
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
