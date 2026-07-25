FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8010
ENV HOST=0.0.0.0
ENV WEB_WORKERS=1

WORKDIR /app

# Install system dependencies (curl for Healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python requirements
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend app code
COPY app /app/app
COPY start.sh /app/

# Create data directory and non-root user
RUN mkdir -p /app/data && \
    useradd -u 10001 -U -d /app -s /bin/bash appuser && \
    chown -R appuser:appuser /app && \
    chmod +x /app/start.sh

USER appuser

EXPOSE 8010

# Add container health check using ready endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8010/api/ready || exit 1

ENTRYPOINT ["/app/start.sh"]
