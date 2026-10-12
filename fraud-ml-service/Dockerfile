# Build context: the fraud-ml-service/ directory
#   docker build -t fraud-ml-service:dev .
# The model is NOT baked in: mount artifacts/models at /srv/artifacts/models (see infra/docker-compose.yml).

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MODEL_DIR=/srv/artifacts/models

# libgomp1: OpenMP runtime required by LightGBM. curl: used by the container health check.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

# Install dependencies first so this layer is cached until requirements change
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app ./app
COPY config ./config

# Run as a non-root user
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /srv/artifacts/models \
    && chown -R appuser /srv
USER appuser

EXPOSE 8000

# Liveness only: the container is not restarted just because the model is missing.
# Use /health/ready for traffic routing.
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
  CMD curl -fs http://localhost:8000/health/live || exit 1

# Worker count can be set with the WEB_CONCURRENCY environment variable
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
