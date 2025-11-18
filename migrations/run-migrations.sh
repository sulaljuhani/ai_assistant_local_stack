#!/bin/bash
# AI Stack - PostgreSQL Migration Runner
# Runs all SQL migrations in order

set -e

# Configuration
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5434}"
POSTGRES_DB="${POSTGRES_DB:-aistack}"
POSTGRES_USER="${POSTGRES_USER:-aistack_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-changeme_secure_password}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "════════════════════════════════════════════════════════════"
echo "  AI Stack - Database Migration Runner"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Target: ${POSTGRES_USER}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
echo ""

# Check if PostgreSQL is accessible
echo -n "Checking PostgreSQL connection... "
if PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; then
    echo -e "${GREEN}✓ Connected${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
    echo ""
    echo "Error: Cannot connect to PostgreSQL."
    echo "Please ensure:"
    echo "  1. PostgreSQL container is running"
    echo "  2. Environment variables are correct"
    echo "  3. Password matches the container configuration"
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

        # Run migration
        if PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$migration" > /tmp/migration_output.log 2>&1; then
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
    if PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='$table');" | grep -q 't'; then
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
    echo "  1. Initialize Qdrant collections (run init-qdrant.sh)"
    echo "  2. Pull Ollama models (llama3.2:3b, nomic-embed-text)"
    echo "  3. Start remaining containers (n8n, AnythingLLM)"
    exit 0
else
    echo -e "${RED}Warning: ${#MISSING_TABLES[@]} tables are missing!${NC}"
    echo "Missing: ${MISSING_TABLES[*]}"
    exit 1
fi
