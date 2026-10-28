# =============================================================================
# Stage 1: Builder - Install dependencies & pre-bake HuggingFace ML models
# =============================================================================
FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/models_cache

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --upgrade pip && \
    pip install --prefix=/install -r ./backend/requirements.txt

COPY backend/ ./backend/
RUN PYTHONPATH=/install/lib/python3.10/site-packages:/app python -m backend.scripts.download_models

# =============================================================================
# Stage 2: Runtime - Lean production image with pre-baked models & seed script
# =============================================================================
FROM python:3.10-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    HF_HOME=/app/models_cache \
    HOST=0.0.0.0 \
    PORT=8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY --from=builder /app/models_cache /app/models_cache

COPY backend/ ./backend/
COPY data/ ./data/

RUN mkdir -p /app/data/papers /app/data/chromadb /app/data/sqlite

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["sh", "-c", "python -m backend.scripts.seed_database && uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
