# Multi-stage build for Breakout Bot Trading System
FROM python:3.12-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY breakout_bot/ ./breakout_bot/
COPY pyproject.toml .
COPY pytest.ini .

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/reports /app/pids

# Set ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/health', timeout=5)"

# Expose port (Railway will set PORT env variable)
EXPOSE 8000

# Default command - use PORT env variable if set, otherwise 8000
CMD ["sh", "-c", "python -m uvicorn breakout_bot.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
