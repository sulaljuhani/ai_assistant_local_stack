#!/bin/bash
# AI Stack - PostgreSQL Migration Runner (Docker Edition)
# Runs all SQL migrations through the PostgreSQL container

set -e

# Configuration
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-aistack}"
POSTGRES_USER="${POSTGRES_USER:-aistack_user}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "════════════════════════════════════════════════════════════"
echo "  AI Stack - Database Migration Runner (Docker)"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Container: ${POSTGRES_CONTAINER}"
echo "Database: ${POSTGRES_DB}"
echo "User: ${POSTGRES_USER}"
echo ""

# Check if PostgreSQL container is running
echo -n "Checking PostgreSQL container... "
if docker ps --format '{{.Names}}' | grep -q "^${POSTGRES_CONTAINER}$"; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not running${NC}"
    echo ""
    echo "Error: PostgreSQL container '${POSTGRES_CONTAINER}' is not running."
    echo "Start it with: docker start ${POSTGRES_CONTAINER}"
    exit 1
fi

# Check database connection
echo -n "Checking database connection... "
if docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; then
    echo -e "${GREEN}✓ Connected${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
    echo ""
    echo "Error: Cannot connect to database."
    echo "Please verify user '${POSTGRES_USER}' has access to database '${POSTGRES_DB}'"
    exit 1
fi

echo ""
echo "Running migrations..."
echo ""

# Get directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Track migration status
TOTAL=0
SUCCESS=0
FAILED=0

# Run each migration file in order
for migration in "$SCRIPT_DIR"/*.sql; do
    if [ -f "$migration" ]; then
        FILENAME=$(basename "$migration")
        TOTAL=$((TOTAL + 1))

        echo -n "[$TOTAL] Running $FILENAME... "

        # Copy migration file to container and run it
        if docker exec -i "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$migration" > /tmp/migration_output.log 2>&1; then
            echo -e "${GREEN}✓ Success${NC}"
            SUCCESS=$((SUCCESS + 1))
        else
            echo -e "${RED}✗ Failed${NC}"
            FAILED=$((FAILED + 1))
            echo ""
            echo "Error output:"
            cat /tmp/migration_output.log
            echo ""

            # Ask if we should continue
            read -p "Continue with remaining migrations? (y/n) " -n 1 -r
            echo ""
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "Aborting migrations."
                exit 1
            fi
        fi
    fi
done

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Migration Summary"
echo "════════════════════════════════════════════════════════════"
echo "Total migrations: $TOTAL"
echo -e "Successful: ${GREEN}$SUCCESS${NC}"
if [ $FAILED -gt 0 ]; then
    echo -e "Failed: ${RED}$FAILED${NC}"
fi
echo ""

# Verify key tables exist
echo "Verifying tables..."
EXPECTED_TABLES=(
    "users"
    "categories"
    "reminders"
    "tasks"
    "events"
    "notes"
    "documents"
    "memories"
    "memory_sectors"
    "conversations"
    "memory_links"
    "imported_chats"
)

MISSING_TABLES=()
for table in "${EXPECTED_TABLES[@]}"; do
    if docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='$table');" | grep -q 't'; then
        echo -e "  ✓ $table"
    else
        echo -e "  ${RED}✗ $table (missing)${NC}"
        MISSING_TABLES+=("$table")
    fi
done

echo ""

if [ ${#MISSING_TABLES[@]} -eq 0 ]; then
    echo -e "${GREEN}All tables created successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Initialize Qdrant collections (run scripts/init-qdrant.sh)"
    echo "  2. Pull Ollama models (llama3.2:3b, nomic-embed-text)"
    echo "  3. Restart LangGraph container to pick up new schema"
    exit 0
else
    echo -e "${RED}Warning: ${#MISSING_TABLES[@]} tables are missing!${NC}"
    echo "Missing: ${MISSING_TABLES[*]}"
    exit 1
fi
