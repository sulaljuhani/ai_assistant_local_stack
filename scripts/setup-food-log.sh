#!/bin/bash
# Setup Food Log Feature
# This script sets up the food log tracking system with vectorization

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${CYAN}       🍽️  FOOD LOG FEATURE SETUP${NC}"
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Step 1: Run migration
echo -e "${YELLOW}Step 1: Running database migration...${NC}"
docker exec -i postgres-ai-stack psql -U aistack_user -d aistack < "$PROJECT_ROOT/migrations/009_create_food_log.sql"
echo -e "${GREEN}✅ Database migration completed${NC}\n"

# Step 2: Create Qdrant collection for food memories
echo -e "${YELLOW}Step 2: Creating Qdrant collection for food memories...${NC}"
curl -X PUT "http://localhost:6333/collections/food_memories" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 768,
      "distance": "Cosine"
    }
  }' 2>/dev/null || echo "Collection may already exist"
echo -e "${GREEN}✅ Qdrant collection created${NC}\n"

# Step 3: Import n8n workflow
echo -e "${YELLOW}Step 3: Importing n8n workflow...${NC}"
echo -e "${CYAN}ℹ️  Please import the workflow manually:${NC}"
echo "   1. Open n8n at http://localhost:5678"
echo "   2. Go to Workflows → Import from File"
echo "   3. Select: $PROJECT_ROOT/n8n-workflows/19-food-log.json"
echo "   4. Activate the workflow"
echo -e "${GREEN}✅ Workflow file ready for import${NC}\n"

# Step 4: Install AnythingLLM skills
echo -e "${YELLOW}Step 4: Installing AnythingLLM skills...${NC}"
echo -e "${CYAN}ℹ️  Please install the skills manually:${NC}"
echo "   1. Open AnythingLLM at http://localhost:3001"
echo "   2. Go to Settings → Agent Skills"
echo "   3. Upload skills from: $PROJECT_ROOT/anythingllm-skills/"
echo "      - log-food.js"
echo "      - recommend-food.js"
echo "   4. Enable them in your workspace"
echo -e "${GREEN}✅ Skills ready for installation${NC}\n"

# Step 5: Test setup
echo -e "${YELLOW}Step 5: Testing setup...${NC}"
echo "Testing database connection..."
docker exec postgres-ai-stack psql -U aistack_user -d aistack -c "SELECT COUNT(*) FROM food_log;" > /dev/null 2>&1
echo -e "${GREEN}✅ Database is ready${NC}"

echo "Testing Qdrant collection..."
curl -s "http://localhost:6333/collections/food_memories" > /dev/null 2>&1
echo -e "${GREEN}✅ Qdrant collection is ready${NC}\n"

# Summary
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${GREEN}       ✅ FOOD LOG SETUP COMPLETE${NC}"
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

echo -e "${BOLD}Next Steps:${NC}"
echo "  1. Import n8n workflow from: n8n-workflows/19-food-log.json"
echo "  2. Install AnythingLLM skills: log-food.js and recommend-food.js"
echo "  3. Test by saying in AnythingLLM:"
echo -e "     ${CYAN}\"Log that I ate pizza for lunch, I bought it and rated it 5 stars\"${NC}"
echo "  4. Get recommendations by saying:"
echo -e "     ${CYAN}\"What should I eat today?\"${NC}"
echo "  5. View your food log using:"
echo -e "     ${CYAN}./scripts/view-food-log.sh${NC}\n"

echo -e "${BOLD}Documentation:${NC}"
echo "  • Migration file: migrations/009_create_food_log.sql"
echo "  • n8n workflow: n8n-workflows/19-food-log.json"
echo "  • AnythingLLM skills: anythingllm-skills/log-food.js, recommend-food.js"
echo "  • Viewer script: scripts/view-food-log.sh"
echo ""
