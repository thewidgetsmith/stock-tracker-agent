# Multi-stage build for development and production

# Base stage with common dependencies
FROM python:3.12-slim-bookworm as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Development stage
FROM base as development

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    black \
    flake8 \
    mypy \
    ipython

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p resources logs

# Expose the port
EXPOSE 8000

# Development command (can be overridden in docker-compose)
CMD ["python", "src/main.py", "-test"]

# Production stage
FROM base as production

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p resources logs \
    && useradd -m -u 1000 appuser \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose the port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command
CMD ["python", "src/main.py"]
