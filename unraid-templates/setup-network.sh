#!/bin/bash
# AI Stack - Docker Network Setup Script
# Run this before installing any containers

set -e

NETWORK_NAME="ai-stack-network"

echo "════════════════════════════════════════════════════════════"
echo "  AI Stack - Docker Network Setup"
echo "════════════════════════════════════════════════════════════"
echo ""

# Check if network already exists
if docker network ls | grep -q "$NETWORK_NAME"; then
    echo "✓ Network '$NETWORK_NAME' already exists"
    echo ""
    echo "Network details:"
    docker network inspect "$NETWORK_NAME" --format '  Subnet: {{range .IPAM.Config}}{{.Subnet}}{{end}}'
    docker network inspect "$NETWORK_NAME" --format '  Gateway: {{range .IPAM.Config}}{{.Gateway}}{{end}}'
    docker network inspect "$NETWORK_NAME" --format '  Driver: {{.Driver}}'
    echo ""

    # List connected containers
    CONTAINERS=$(docker network inspect "$NETWORK_NAME" --format '{{range $k, $v := .Containers}}{{$v.Name}} {{end}}')
    if [ -n "$CONTAINERS" ]; then
        echo "Connected containers:"
        for container in $CONTAINERS; do
            echo "  - $container"
        done
    else
        echo "No containers connected yet"
    fi
else
    echo "Creating Docker bridge network: $NETWORK_NAME"
    docker network create "$NETWORK_NAME" --driver bridge
    echo "✓ Network created successfully"
    echo ""
    echo "Network details:"
    docker network inspect "$NETWORK_NAME" --format '  Subnet: {{range .IPAM.Config}}{{.Subnet}}{{end}}'
    docker network inspect "$NETWORK_NAME" --format '  Gateway: {{range .IPAM.Config}}{{.Gateway}}{{end}}'
    docker network inspect "$NETWORK_NAME" --format '  Driver: {{.Driver}}'
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Network setup complete!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. Install containers using unRAID templates"
echo "  2. Ensure all templates have --network=ai-stack-network"
echo "  3. Containers can communicate using container names"
echo ""
echo "Example: From n8n container, connect to:"
echo "  - PostgreSQL: postgres-ai-stack:5432"
echo "  - Qdrant: qdrant-ai-stack:6333"
echo "  - Ollama: ollama-ai-stack:11434"
echo ""
