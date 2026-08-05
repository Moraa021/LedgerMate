# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

# Prevents Python from writing .pyc files / buffering stdout (good for logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASK_APP=index.py

WORKDIR /app

# System deps needed to build psycopg2-binary / pillow wheels on slim images
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libpq-dev \
       gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first so this layer is cached unless requirements change
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the app
COPY . .

# Run as a non-root user
RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /app/instance \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Apply any pending DB migrations, then start gunicorn against the
# production app factory (index.py -> app)
CMD ["sh", "-c", "flask db upgrade && gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 60 index:app"]
