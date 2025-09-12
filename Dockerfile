# syntax=docker/dockerfile:1.7
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---- deps (cacheable) ----
COPY requirements.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip && \
    # optional but nice for reranker CPU
    pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch && \
    pip install --no-cache-dir --prefer-binary -r requirements.txt

# ---- app ----
COPY . .
ENV PYTHONPATH=/app
EXPOSE 8000

# Force single worker (Prometheus-safe)
CMD ["uvicorn", "app.api.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
