#!/bin/bash
# AI Stack - Qdrant Collections Verification
# Verifies that collections are set up correctly with correct dimensions

set -e

# Configuration
QDRANT_HOST="${QDRANT_HOST:-localhost}"
QDRANT_PORT="${QDRANT_PORT:-6333}"
QDRANT_URL="http://${QDRANT_HOST}:${QDRANT_PORT}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "════════════════════════════════════════════════════════════"
echo "  AI Stack - Qdrant Collections Verification"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Target: ${QDRANT_URL}"
echo ""

# Check if Qdrant is accessible
echo -n "Checking Qdrant connection... "
if curl -sf "${QDRANT_URL}/collections" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Connected${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
    exit 1
fi

echo ""
echo "Verifying collections..."
echo ""

# Expected collections
EXPECTED_COLLECTIONS=("knowledge_base" "memories")
EXPECTED_DIMENSIONS=768
EXPECTED_DISTANCE="Cosine"

ALL_GOOD=true

for COLLECTION in "${EXPECTED_COLLECTIONS[@]}"; do
    echo -e "${BLUE}Checking collection: $COLLECTION${NC}"

    # Check if collection exists
    COLLECTION_INFO=$(curl -s "${QDRANT_URL}/collections/${COLLECTION}")

    if echo "$COLLECTION_INFO" | grep -q '"status":"ok"'; then
        echo -e "  ${GREEN}✓${NC} Collection exists"

        # Extract and verify vector size
        VECTOR_SIZE=$(echo "$COLLECTION_INFO" | grep -o '"size":[0-9]*' | head -1 | cut -d':' -f2)
        if [ "$VECTOR_SIZE" = "$EXPECTED_DIMENSIONS" ]; then
            echo -e "  ${GREEN}✓${NC} Vector size: $VECTOR_SIZE (correct)"
        else
            echo -e "  ${RED}✗${NC} Vector size: $VECTOR_SIZE (expected $EXPECTED_DIMENSIONS)"
            ALL_GOOD=false
        fi

        # Extract and verify distance metric
        DISTANCE=$(echo "$COLLECTION_INFO" | grep -o '"distance":"[^"]*"' | head -1 | cut -d'"' -f4)
        if [ "$DISTANCE" = "$EXPECTED_DISTANCE" ]; then
            echo -e "  ${GREEN}✓${NC} Distance metric: $DISTANCE (correct)"
        else
            echo -e "  ${YELLOW}⚠${NC} Distance metric: $DISTANCE (expected $EXPECTED_DISTANCE)"
        fi

        # Get points count
        POINTS_COUNT=$(echo "$COLLECTION_INFO" | grep -o '"points_count":[0-9]*' | cut -d':' -f2)
        echo -e "  ${BLUE}ℹ${NC} Points count: ${POINTS_COUNT:-0}"

        # Get indexed fields count
        INDEXED_FIELDS=$(echo "$COLLECTION_INFO" | grep -o '"payload_schema":{[^}]*}' | grep -o '":"' | wc -l)
        echo -e "  ${BLUE}ℹ${NC} Indexed fields: ${INDEXED_FIELDS:-0}"

    else
        echo -e "  ${RED}✗${NC} Collection does not exist"
        ALL_GOOD=false
    fi

    echo ""
done

# Check Ollama model
echo -e "${BLUE}Checking Ollama embedding model${NC}"
OLLAMA_HOST="${OLLAMA_HOST:-localhost}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
OLLAMA_URL="http://${OLLAMA_HOST}:${OLLAMA_PORT}"

if curl -sf "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; then
    MODELS=$(curl -s "${OLLAMA_URL}/api/tags")
    if echo "$MODELS" | grep -q "nomic-embed-text"; then
        echo -e "  ${GREEN}✓${NC} nomic-embed-text model is available"

        # Test embedding generation
        echo -n "  Testing embedding generation... "
        TEST_RESPONSE=$(curl -s -X POST "${OLLAMA_URL}/api/embeddings" \
            -H "Content-Type: application/json" \
            -d '{"model": "nomic-embed-text", "prompt": "test"}')

        if echo "$TEST_RESPONSE" | grep -q '"embedding"'; then
            EMBEDDING_DIM=$(echo "$TEST_RESPONSE" | grep -o '"embedding":\[[^]]*' | grep -o ',' | wc -l)
            EMBEDDING_DIM=$((EMBEDDING_DIM + 1))  # Add 1 because commas are between elements

            if [ "$EMBEDDING_DIM" = "$EXPECTED_DIMENSIONS" ]; then
                echo -e "${GREEN}✓ ${EMBEDDING_DIM} dimensions (correct)${NC}"
            else
                echo -e "${RED}✗ ${EMBEDDING_DIM} dimensions (expected $EXPECTED_DIMENSIONS)${NC}"
                ALL_GOOD=false
            fi
        else
            echo -e "${RED}✗ Failed${NC}"
            ALL_GOOD=false
        fi
    else
        echo -e "  ${RED}✗${NC} nomic-embed-text model not found"
        echo -e "  ${YELLOW}Run: docker exec ollama-ai-stack ollama pull nomic-embed-text${NC}"
        ALL_GOOD=false
    fi
else
    echo -e "  ${YELLOW}⚠${NC} Cannot connect to Ollama at ${OLLAMA_URL}"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
if [ "$ALL_GOOD" = true ]; then
    echo -e "  ${GREEN}All checks passed!${NC}"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "Your Qdrant setup is ready for use with nomic-embed-text (768 dims)."
    exit 0
else
    echo -e "  ${RED}Some checks failed!${NC}"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "Please review the errors above and fix them before proceeding."
    exit 1
fi
