# syntax=docker/dockerfile:1.7    # <-- enables cache mounts
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps (with apt cache)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---- deps layer (cacheable) ----
# Keep requirements stable to leverage cache
COPY requirements.txt ./requirements.txt

# Use pip cache between builds
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip && \
    # Install CPU wheel for torch first (fast; no CUDA)
    pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch && \
    # Then the rest
    pip install --no-cache-dir --prefer-binary -r requirements.txt

# ---- app layer ----
COPY . .

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["uvicorn", "app.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
# If your code is under chatbi/app/, use:
# CMD ["uvicorn", "chatbi.app.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
