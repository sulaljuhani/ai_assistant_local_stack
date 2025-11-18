#!/bin/bash
# Migration Script: Add metadata column to memories table
# This script safely adds the metadata JSONB column if it doesn't exist

set -e  # Exit on error

# Configuration
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5434}"
POSTGRES_DB="${POSTGRES_DB:-aistack}"
POSTGRES_USER="${POSTGRES_USER:-aistack_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-changeme}"

echo "=========================================="
echo " AI Stack - Database Migration"
echo " Adding metadata column to memories table"
echo "=========================================="
echo ""

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo "❌ Error: psql command not found"
    echo "   Install PostgreSQL client or run from Docker:"
    echo "   docker exec -it postgres-ai-stack bash"
    exit 1
fi

# Test connection
echo "📡 Testing database connection..."
export PGPASSWORD="$POSTGRES_PASSWORD"

if ! psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1;" > /dev/null 2>&1; then
    echo "❌ Error: Cannot connect to database"
    echo "   Host: $POSTGRES_HOST:$POSTGRES_PORT"
    echo "   Database: $POSTGRES_DB"
    echo "   User: $POSTGRES_USER"
    exit 1
fi

echo "✅ Connected to database"
echo ""

# Check if metadata column already exists
echo "🔍 Checking if metadata column exists..."
COLUMN_EXISTS=$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
    "SELECT COUNT(*) FROM information_schema.columns
     WHERE table_name = 'memories' AND column_name = 'metadata';")

if [ "$COLUMN_EXISTS" -gt 0 ]; then
    echo "✅ metadata column already exists, skipping migration"
    exit 0
fi

echo "📝 metadata column not found, adding it now..."
echo ""

# Add metadata column
echo "Running migration..."
psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<'SQL'
-- Add metadata column to memories table
ALTER TABLE memories ADD COLUMN IF NOT EXISTS metadata JSONB;

-- Create index on metadata for faster JSONB queries
CREATE INDEX IF NOT EXISTS idx_memories_metadata ON memories USING GIN(metadata);

-- Add comment
COMMENT ON COLUMN memories.metadata IS 'General metadata for various purposes (archiving, syncing, etc.)';

-- Verify the column was added
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'memories' AND column_name = 'metadata';
SQL

echo ""
echo "=========================================="
echo " ✅ Migration Complete!"
echo "=========================================="
echo ""
echo "The metadata column has been added to the memories table."
echo "You can now use it to store additional metadata like:"
echo "  - archived_reason"
echo "  - synced_to_vault: true/false"
echo "  - vault_file: filename"
echo "  - import_source: chatgpt/claude/etc"
echo ""
