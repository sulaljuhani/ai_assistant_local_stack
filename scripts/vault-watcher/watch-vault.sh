#!/bin/bash
# AI Stack - Vault File Watcher (Bash/Linux)
# Monitors vault directory for changes and triggers re-embedding

set -e

# Configuration
VAULT_DIR="${VAULT_DIR:-/mnt/user/appdata/ai_stack/vault}"
LANGGRAPH_API_URL="${LANGGRAPH_API_URL:-http://langgraph-agents:8080}"
API_ENDPOINT="${LANGGRAPH_API_URL}/api/vault/reembed"
POSTGRES_HOST="${POSTGRES_HOST:-postgres-ai-stack}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-aistack}"
POSTGRES_USER="${POSTGRES_USER:-aistack_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD}"
DEBOUNCE_SECONDS="${DEBOUNCE_SECONDS:-5}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "════════════════════════════════════════════════════════════"
echo "  AI Stack - Vault File Watcher"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Watching: $VAULT_DIR"
echo "API Endpoint: $API_ENDPOINT"
echo "Debounce: ${DEBOUNCE_SECONDS}s"
echo ""

# Check if inotify-tools is installed
if ! command -v inotifywait &> /dev/null; then
    echo "Error: inotify-tools not installed"
    echo "Install with: apt-get install inotify-tools (Debian/Ubuntu)"
    echo "           or: yum install inotify-tools (RHEL/CentOS)"
    exit 1
fi

# Check if vault directory exists
if [ ! -d "$VAULT_DIR" ]; then
    echo "Error: Vault directory not found: $VAULT_DIR"
    exit 1
fi

# Track last processed time for debouncing
declare -A last_processed

calculate_file_hash() {
    local file="$1"
    if [ -f "$file" ]; then
        sha256sum "$file" | awk '{print $1}'
    else
        echo ""
    fi
}

check_if_changed() {
    local file="$1"
    local current_hash=$(calculate_file_hash "$file")

    # Query database for existing hash
    EXISTING_HASH=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "
        SELECT file_hash FROM file_sync
        WHERE file_path = '${file#$VAULT_DIR/}'
        LIMIT 1
    " 2>/dev/null)

    if [ "$current_hash" != "$EXISTING_HASH" ]; then
        return 0  # Changed
    else
        return 1  # Not changed
    fi
}

process_file() {
    local file="$1"
    local event="$2"
    local relative_path="${file#$VAULT_DIR/}"

    # Skip hidden files and temp files
    if [[ "$(basename "$file")" == .* ]] || [[ "$(basename "$file")" == *~ ]]; then
        return
    fi

    # Skip non-markdown files
    if [[ ! "$file" =~ \.md$ ]]; then
        return
    fi

    # Debounce: skip if processed recently
    local current_time=$(date +%s)
    local last_time=${last_processed["$file"]:-0}
    local time_diff=$((current_time - last_time))

    if [ $time_diff -lt $DEBOUNCE_SECONDS ]; then
        return
    fi

    last_processed["$file"]=$current_time

    # Check if file actually changed
    if [ "$event" = "MODIFY" ]; then
        if ! check_if_changed "$file"; then
            echo -e "${BLUE}⏭${NC}  Skipped (unchanged): $relative_path"
            return
        fi
    fi

    local file_hash=$(calculate_file_hash "$file")
    local file_size=$(stat -c%s "$file" 2>/dev/null || echo "0")

    echo -e "${GREEN}📝${NC} Processing: $relative_path"
    echo "   Event: $event | Size: $file_size bytes"

    # Trigger Python API endpoint for re-embedding
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_ENDPOINT" \
        -H "Content-Type: application/json" \
        -d "{
            \"file_path\": \"$file\",
            \"relative_path\": \"$relative_path\",
            \"file_hash\": \"$file_hash\",
            \"file_size\": $file_size,
            \"event\": \"$event\",
            \"timestamp\": \"$(date -Iseconds)\"
        }" 2>&1)

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
        echo -e "   ${GREEN}✓${NC} Re-embedding triggered"
    else
        echo -e "   ${YELLOW}⚠${NC} Webhook failed (HTTP $HTTP_CODE)"
    fi

    echo ""
}

# Start watching
echo "👀 Watching for changes..."
echo "   Press Ctrl+C to stop"
echo ""

# Watch for file changes
inotifywait -m -r -e modify,create,delete,move \
    --format '%w%f|%e' \
    --exclude '\.obsidian|\.git|\.trash' \
    "$VAULT_DIR" 2>/dev/null | while IFS='|' read -r filepath event; do

    case "$event" in
        MODIFY|CREATE|MOVED_TO)
            process_file "$filepath" "$event"
            ;;
        DELETE|MOVED_FROM)
            relative_path="${filepath#$VAULT_DIR/}"
            echo -e "${YELLOW}🗑${NC}  Deleted: $relative_path"
            echo ""
            ;;
    esac
done
