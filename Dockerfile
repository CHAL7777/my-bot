# Telegram Quiz Bot - Dockerfile for Koyeb + Supabase Deployment
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/data /app/logs && chmod 777 /app/data /app/logs

# Make scripts executable
RUN chmod +x /app/koyeb_start.sh /app/scripts/init_db.py

# Expose the port (Koyeb uses 8000 by default)
EXPOSE 8000

# Health check - Koyeb will check this endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --spider --tries=1 http://localhost:${PORT:-8000}/ping -q || exit 1

# Default command - uses the koyeb_start.sh script
CMD ["bash", "/app/koyeb_start.sh"]

