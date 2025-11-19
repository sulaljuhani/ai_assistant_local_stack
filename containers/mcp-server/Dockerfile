# AI Stack - MCP Server Dockerfile
# Multi-stage build with non-root user for security

# ============================================================================
# Stage 1: Builder
# ============================================================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies to user site-packages
RUN pip install --user --no-cache-dir -r requirements.txt

# ============================================================================
# Stage 2: Runtime
# ============================================================================
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only (libpq for PostgreSQL client)
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# FIX: Create non-root user for security
RUN useradd -m -u 1000 mcp && \
    chown -R mcp:mcp /app

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/mcp/.local

# Copy server code
COPY --chown=mcp:mcp server.py .

# FIX: Switch to non-root user
USER mcp

# Add user site-packages to PATH
ENV PATH=/home/mcp/.local/bin:$PATH

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run server as non-root user
CMD ["python", "server.py"]
