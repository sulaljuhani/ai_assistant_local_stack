#!/bin/bash
# AI Stack - MCP Server Run Script (for manual testing)

set -e

IMAGE_NAME="mcp-server-ai-stack"
CONTAINER_NAME="mcp-server-ai-stack"
NETWORK="ai-stack-network"

# Load environment variables (or use defaults)
POSTGRES_HOST="${POSTGRES_HOST:-postgres-ai-stack}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-aistack}"
POSTGRES_USER="${POSTGRES_USER:-aistack_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-changeme}"

QDRANT_HOST="${QDRANT_HOST:-qdrant-ai-stack}"
QDRANT_PORT="${QDRANT_PORT:-6333}"

OLLAMA_HOST="${OLLAMA_HOST:-ollama-ai-stack}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"

DEFAULT_USER_ID="${DEFAULT_USER_ID:-00000000-0000-0000-0000-000000000001}"

echo "════════════════════════════════════════════════════════════"
echo "  Starting MCP Server Container"
echo "════════════════════════════════════════════════════════════"
echo ""

# Check if container already exists
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Stopping and removing existing container..."
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
fi

# Check if network exists
if ! docker network ls | grep -q "$NETWORK"; then
    echo "Error: Docker network '$NETWORK' not found."
    echo "Please run: docker network create $NETWORK"
    exit 1
fi

# Check if image exists
if ! docker images | grep -q "$IMAGE_NAME"; then
    echo "Error: Docker image '$IMAGE_NAME' not found."
    echo "Please run: ./build.sh"
    exit 1
fi

echo "Starting container..."
docker run -d \
  --name "$CONTAINER_NAME" \
  --network "$NETWORK" \
  -p 8081:8081 \
  -e POSTGRES_HOST="$POSTGRES_HOST" \
  -e POSTGRES_PORT="$POSTGRES_PORT" \
  -e POSTGRES_DB="$POSTGRES_DB" \
  -e POSTGRES_USER="$POSTGRES_USER" \
  -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  -e QDRANT_HOST="$QDRANT_HOST" \
  -e QDRANT_PORT="$QDRANT_PORT" \
  -e OLLAMA_HOST="$OLLAMA_HOST" \
  -e OLLAMA_PORT="$OLLAMA_PORT" \
  -e DEFAULT_USER_ID="$DEFAULT_USER_ID" \
  --restart unless-stopped \
  "$IMAGE_NAME:latest"

echo ""
echo "✓ Container started successfully!"
echo ""
echo "Container: $CONTAINER_NAME"
echo "Network: $NETWORK"
echo "Port: 8081"
echo ""
echo "View logs: docker logs -f $CONTAINER_NAME"
echo "Stop: docker stop $CONTAINER_NAME"
echo ""
