FROM public.ecr.aws/docker/library/python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASK_APP=index.py

WORKDIR /app

# Create user first and set up directory permissions safely
RUN useradd --create-home --shell /bin/bash appuser && \
    mkdir -p /app/instance && \
    chown -R appuser:appuser /app

# Install dependencies with long timeouts and retries for slow connections
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir --default-timeout=120 --retries 5 -r requirements.txt

# Copy application files with correct non-root ownership
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

# Apply database migrations on start up, then boot the production server
CMD ["sh", "-c", "flask db upgrade && gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 60 index:app"]
