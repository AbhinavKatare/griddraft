# ==============================================================================
# Stage 1: Build Frontend Assets (Node.js Alpine)
# ==============================================================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Install frontend dependencies
COPY frontend/package*.json ./
RUN npm ci --legacy-peer-deps

# Copy frontend source and compile production bundle
COPY frontend/ ./
RUN npm run build

# ==============================================================================
# Stage 2: Install Python Dependencies (Python 3.11 Slim)
# ==============================================================================
FROM python:3.11-slim AS python-builder
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ==============================================================================
# Stage 3: Final Production Runner (Python 3.11 Slim, Non-Root, Healthcheck)
# ==============================================================================
FROM python:3.11-slim AS runner
WORKDIR /app

# Install curl for HEALTHCHECK and runtime utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root system group and user
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Copy installed Python packages from python-builder
COPY --from=python-builder /install /usr/local

# Copy backend application code
COPY backend/app/ ./app/

# Bundle canonical Parquet cache directly inside the image
COPY backend/data/ ./data/

# Copy compiled frontend assets from frontend-builder into static serving directory
COPY --from=frontend-builder /app/frontend/dist/ ./static/

# Environment configuration
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    STATIC_DIR=/app/static \
    CACHE_DIR=/app/data/cache

# Enforce non-root ownership
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

# Docker Healthcheck targeting /health endpoint
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Start Uvicorn ASGI server with dynamic Heroku $PORT support
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
