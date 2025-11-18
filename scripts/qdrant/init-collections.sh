#!/bin/bash
# AI Stack - Qdrant Collections Initialization
# Creates vector database collections with 768 dimensions (nomic-embed-text)

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
echo "  AI Stack - Qdrant Collections Setup"
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
    echo ""
    echo "Error: Cannot connect to Qdrant at ${QDRANT_URL}"
    echo "Please ensure:"
    echo "  1. Qdrant container is running"
    echo "  2. Port ${QDRANT_PORT} is accessible"
    echo "  3. QDRANT_HOST and QDRANT_PORT are correct"
    exit 1
fi

echo ""
echo "Creating collections with 768 dimensions (nomic-embed-text)..."
echo ""

# ============================================================================
# Collection 1: knowledge_base
# ============================================================================

echo -n "Creating collection: knowledge_base... "

RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${QDRANT_URL}/collections/knowledge_base" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 768,
      "distance": "Cosine"
    },
    "optimizers_config": {
      "indexing_threshold": 10000
    }
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 201 ]; then
    echo -e "${GREEN}✓ Created${NC}"
elif echo "$BODY" | grep -q "already exists"; then
    echo -e "${YELLOW}⚠ Already exists${NC}"
else
    echo -e "${RED}✗ Failed (HTTP $HTTP_CODE)${NC}"
    echo "Response: $BODY"
    exit 1
fi

# Create indexes for knowledge_base
echo -n "  Creating payload indexes... "

# Index: user_id (for filtering by user)
curl -s -X PUT "${QDRANT_URL}/collections/knowledge_base/index" \
  -H "Content-Type: application/json" \
  -d '{
    "field_name": "user_id",
    "field_schema": "keyword"
  }' > /dev/null

# Index: content_type (note, document_chunk, task, reminder, event)
curl -s -X PUT "${QDRANT_URL}/collections/knowledge_base/index" \
  -H "Content-Type: application/json" \
  -d '{
    "field_name": "content_type",
    "field_schema": "keyword"
  }' > /dev/null

# Index: created_at (for temporal filtering)
curl -s -X PUT "${QDRANT_URL}/collections/knowledge_base/index" \
  -H "Content-Type: application/json" \
  -d '{
    "field_name": "created_at",
    "field_schema": "datetime"
  }' > /dev/null

echo -e "${GREEN}✓ Done${NC}"

# ============================================================================
# Collection 2: memories (OpenMemory)
# ============================================================================

echo -n "Creating collection: memories... "

RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${QDRANT_URL}/collections/memories" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 768,
      "distance": "Cosine"
    },
    "optimizers_config": {
      "indexing_threshold": 10000,
      "default_segment_number": 2
    },
    "hnsw_config": {
      "m": 16,
      "ef_construct": 100
    }
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 201 ]; then
    echo -e "${GREEN}✓ Created${NC}"
elif echo "$BODY" | grep -q "already exists"; then
    echo -e "${YELLOW}⚠ Already exists${NC}"
else
    echo -e "${RED}✗ Failed (HTTP $HTTP_CODE)${NC}"
    echo "Response: $BODY"
    exit 1
fi

# Create indexes for memories
echo -n "  Creating payload indexes... "

# Index: user_id
curl -s -X PUT "${QDRANT_URL}/collections/memories/index" \
  -H "Content-Type: application/json" \
  -d '{
    "field_name": "user_id",
    "field_schema": "keyword"
  }' > /dev/null

# Index: memory_id
curl -s -X PUT "${QDRANT_URL}/collections/memories/index" \
  -H "Content-Type: application/json" \
  -d '{
    "field_name": "memory_id",
    "field_schema": "keyword"
  }' > /dev/null

# Index: sector (semantic, episodic, procedural, emotional, reflective)
curl -s -X PUT "${QDRANT_URL}/collections/memories/index" \
  -H "Content-Type: application/json" \
  -d '{
    "field_name": "sector",
    "field_schema": "keyword"
  }' > /dev/null

# Index: source (anythingllm, chatgpt, claude, gemini)
curl -s -X PUT "${QDRANT_URL}/collections/memories/index" \
  -H "Content-Type: application/json" \
  -d '{
    "field_name": "source",
    "field_schema": "keyword"
  }' > /dev/null

# Index: salience_score (for filtering high-importance memories)
curl -s -X PUT "${QDRANT_URL}/collections/memories/index" \
  -H "Content-Type: application/json" \
  -d '{
    "field_name": "salience_score",
    "field_schema": "float"
  }' > /dev/null

# Index: created_at
curl -s -X PUT "${QDRANT_URL}/collections/memories/index" \
  -H "Content-Type: application/json" \
  -d '{
    "field_name": "created_at",
    "field_schema": "datetime"
  }' > /dev/null

echo -e "${GREEN}✓ Done${NC}"

# ============================================================================
# Verification
# ============================================================================

echo ""
echo "Verifying collections..."
echo ""

COLLECTIONS=$(curl -s "${QDRANT_URL}/collections" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for collection in data.get('result', {}).get('collections', []):
    print(f\"{collection['name']}: {collection.get('points_count', 0)} points\")
" 2>/dev/null)

if [ -n "$COLLECTIONS" ]; then
    echo "$COLLECTIONS"
else
    # Fallback if python not available
    curl -s "${QDRANT_URL}/collections" | grep -o '"name":"[^"]*"' | cut -d'"' -f4
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Collection Details"
echo "════════════════════════════════════════════════════════════"
echo ""

# Get knowledge_base details
echo -e "${BLUE}Collection: knowledge_base${NC}"
KB_INFO=$(curl -s "${QDRANT_URL}/collections/knowledge_base")
echo "$KB_INFO" | python3 -c "
import sys, json
data = json.load(sys.stdin)
result = data.get('result', {})
print(f\"  Vector size: {result.get('config', {}).get('params', {}).get('vectors', {}).get('size', 'N/A')}\")
print(f\"  Distance: {result.get('config', {}).get('params', {}).get('vectors', {}).get('distance', 'N/A')}\")
print(f\"  Points count: {result.get('points_count', 0)}\")
print(f\"  Indexed fields: {len(result.get('payload_schema', {}))}\")
" 2>/dev/null || echo "  (Details not available)"

echo ""

# Get memories details
echo -e "${BLUE}Collection: memories${NC}"
MEM_INFO=$(curl -s "${QDRANT_URL}/collections/memories")
echo "$MEM_INFO" | python3 -c "
import sys, json
data = json.load(sys.stdin)
result = data.get('result', {})
print(f\"  Vector size: {result.get('config', {}).get('params', {}).get('vectors', {}).get('size', 'N/A')}\")
print(f\"  Distance: {result.get('config', {}).get('params', {}).get('vectors', {}).get('distance', 'N/A')}\")
print(f\"  Points count: {result.get('points_count', 0)}\")
print(f\"  Indexed fields: {len(result.get('payload_schema', {}))}\")
" 2>/dev/null || echo "  (Details not available)"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Setup Complete!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. Pull Ollama model: docker exec ollama-ai-stack ollama pull nomic-embed-text"
echo "  2. Verify embedding dimensions: 768"
echo "  3. Start importing data or begin using AnythingLLM"
echo ""
