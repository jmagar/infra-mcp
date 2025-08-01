# Infrastructure Management MCP Server Dockerfile
# 
# NOTE: This Dockerfile is prepared for future containerized deployment but is not 
# currently used in development. We are deploying only PostgreSQL via Docker while 
# the MCP server runs locally for development until fully operational.
# 
# Current deployment approach:
# - PostgreSQL + TimescaleDB: Docker container (port 9100)
# - FastAPI + MCP Server: Local development environment
# 
# Future deployment will containerize the full application.

FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # SSH client for device communication
    openssh-client \
    # System monitoring tools
    curl \
    htop \
    # Build tools (may be needed for some Python packages)
    gcc \
    g++ \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install UV (modern Python package manager)
RUN pip install uv

# Create application directory
WORKDIR /app

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python dependencies using UV
RUN uv sync --frozen --no-dev

# Copy application source
COPY apps/backend/src/ ./src/
COPY init-scripts/ ./init-scripts/

# Create directories for logs and SSH keys
RUN mkdir -p /app/logs /app/.ssh \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose ports
# 8000: FastAPI REST API
# 8001: WebSocket connections  
# 8080: MCP Server (when separated)
EXPOSE 8000 8001 8080

# Default command (will be overridden in production)
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production command (uncomment when ready for containerized deployment):
# CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# Labels for container metadata
LABEL maintainer="Infrastructure Team" \
      description="Infrastructure Management MCP Server" \
      version="1.0.0-dev" \
      deployment.status="development-ready" \
      deployment.note="Currently using local development with Docker PostgreSQL only"