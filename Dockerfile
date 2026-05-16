# ────────────────────────────────────────────────────────────────────────────
# OkChat — Production-Optimized Multi-Stage Dockerfile
# ────────────────────────────────────────────────────────────────────────────
# Stage 1: builder — installs dependencies in a venv
# Stage 2: runtime — minimal image, non-root user, no dev tools
# ────────────────────────────────────────────────────────────────────────────

# ── Builder ──────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system build deps (only in builder, not in runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment to isolate deps
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy only dependency files first — maximizes Docker layer cache
COPY pyproject.toml ./

# Install production dependencies
RUN pip install --upgrade pip --no-cache-dir && \
    pip install --no-cache-dir .

# ── Runtime ───────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Labels for container registry
LABEL maintainer="carlos@okchat.io"
LABEL org.opencontainers.image.title="OkChat API"
LABEL org.opencontainers.image.description="Multi-channel conversational AI API"

WORKDIR /app

# Install only runtime system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy venv from builder — no pip in runtime image
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source
COPY src/ ./src/

# ── Security: non-root user ───────────────────────────────────────────────────
RUN groupadd --gid 1001 okchat && \
    useradd --uid 1001 --gid okchat --shell /bin/bash --create-home okchat && \
    chown -R okchat:okchat /app

USER okchat

# ── Config ────────────────────────────────────────────────────────────────────
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# ── Health check for Docker (Kubernetes uses its own probes) ─────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# ── Entrypoint ────────────────────────────────────────────────────────────────
# gunicorn manages worker processes; uvicorn workers handle async I/O
# --workers: typically 2 × CPU cores + 1
# --worker-class: uvicorn.workers.UvicornWorker for async FastAPI
CMD ["gunicorn", \
     "okchat.main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--keep-alive", "5", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "warning"]
