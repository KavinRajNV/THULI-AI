# =============================================================================
# Stage 1: Build & Dependency Wheel Cache
# =============================================================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Install system build dependencies required for C extensions and postgres client
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create isolated Python virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies into /opt/venv
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r ./requirements.txt

# =============================================================================
# Stage 2: Final Minimal Runtime Image
# =============================================================================
FROM python:3.11-slim AS runner

# Labels for OCI image compliance
LABEL maintainer="Thuli AI Team"
LABEL description="Thuli AI - Voice-First Multilingual Agricultural Intelligence"

# Runtime system dependencies only (libpq for PostgreSQL connection)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Create non-root user and group (security best practice)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/sh -m appuser

WORKDIR /app

# Copy application source code (backend, Exotel webhook module, and app wrapper)
COPY --chown=appuser:appgroup backend ./backend
COPY --chown=appuser:appgroup Exotel ./Exotel
COPY --chown=appuser:appgroup app ./app

# Create writable runtime directories for TTS audio cache, logs, and downloaded models
RUN mkdir -p /app/backend/static/calls \
             /app/backend/logs \
             /app/backend/models \
             /app/backend/data \
             /app/backend/Dataset && \
    chown -R appuser:appgroup /app

# Run as non-root user
USER appuser

WORKDIR /app/backend

EXPOSE 8000

# Health check using Python's standard library (no curl required)
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

# Production command: runs uvicorn on port 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
