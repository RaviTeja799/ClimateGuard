# ClimateGuard Multi-Agent System
# Dockerfile for Cloud Run Deployment
# Google AI Agents Intensive Capstone - Agents for Good Track

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8080

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Run the application
# Using gunicorn for production-ready serving
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app

# Alternative: Run as ADK A2A server
# CMD ["python", "-m", "google.adk.cli", "a2a_server", "--host", "0.0.0.0", "--port", "8080", "agents.supervisor"]
