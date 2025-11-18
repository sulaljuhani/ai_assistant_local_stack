#!/bin/bash
# AI Stack - MCP Server Build Script

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
IMAGE_NAME="mcp-server-ai-stack"
TAG="latest"

echo "════════════════════════════════════════════════════════════"
echo "  Building MCP Server Docker Image"
echo "════════════════════════════════════════════════════════════"
echo ""

cd "$SCRIPT_DIR"

echo "Building image: ${IMAGE_NAME}:${TAG}"
docker build -t "${IMAGE_NAME}:${TAG}" .

echo ""
echo "✓ Image built successfully!"
echo ""
echo "Image size:"
docker images "${IMAGE_NAME}:${TAG}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
echo ""
echo "Next steps:"
echo "  1. Install via unRAID template (my-mcp-server.xml)"
echo "  2. Or run manually: ./run.sh"
echo ""
