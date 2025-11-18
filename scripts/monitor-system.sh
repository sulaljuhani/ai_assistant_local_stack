#!/bin/bash
# AI Stack - System Monitoring Dashboard
# Real-time health monitoring of all AI Stack components

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
REFRESH_INTERVAL="${REFRESH_INTERVAL:-5}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5434}"

clear

while true; do
    clear
    echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  AI Stack - System Monitor                $(date '+%H:%M:%S')${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo ""

    # ================================================================
    # CONTAINER STATUS
    # ================================================================
    echo -e "${BLUE}📦 CONTAINERS STATUS${NC}"
    echo ""

    CONTAINERS=("postgres-ai-stack" "qdrant-ai-stack" "redis-ai-stack" "ollama-ai-stack" "mcp-server-ai-stack" "n8n-ai-stack" "anythingllm-ai-stack")

    for container in "${CONTAINERS[@]}"; do
        if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${container}$"; then
            STATUS=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "unknown")
            UPTIME=$(docker inspect --format='{{.State.StartedAt}}' "$container" 2>/dev/null | xargs -I {} date -d {} '+%s' 2>/dev/null || echo "0")
            CURRENT=$(date +%s)
            UPTIME_SEC=$((CURRENT - UPTIME))
            UPTIME_HUMAN=$(printf '%dd %dh %dm' $((UPTIME_SEC/86400)) $((UPTIME_SEC%86400/3600)) $((UPTIME_SEC%3600/60)))

            if [ "$STATUS" = "running" ]; then
                echo -e "  ${GREEN}✓${NC} ${container} ${GREEN}(${UPTIME_HUMAN})${NC}"
            else
                echo -e "  ${RED}✗${NC} ${container} ${RED}(${STATUS})${NC}"
            fi
        else
            echo -e "  ${YELLOW}⚠${NC} ${container} ${YELLOW}(not found)${NC}"
        fi
    done

    echo ""

    # ================================================================
    # DATABASE STATISTICS
    # ================================================================
    echo -e "${BLUE}🗄️  DATABASE STATISTICS${NC}"
    echo ""

    if docker ps --format '{{.Names}}' | grep -q "postgres-ai-stack"; then
        DB_STATS=$(docker exec postgres-ai-stack psql -U aistack_user -d aistack -tAc "
            SELECT
                (SELECT COUNT(*) FROM memories WHERE is_archived = FALSE) as memories,
                (SELECT COUNT(*) FROM conversations) as conversations,
                (SELECT COUNT(*) FROM tasks WHERE status NOT IN ('done', 'cancelled')) as active_tasks,
                (SELECT COUNT(*) FROM reminders WHERE status = 'pending') as pending_reminders,
                (SELECT COUNT(*) FROM events WHERE start_time > NOW() AND status != 'cancelled') as upcoming_events,
                (SELECT COUNT(*) FROM notes) as notes
        " 2>/dev/null)

        if [ -n "$DB_STATS" ]; then
            IFS='|' read -r MEMORIES CONVERSATIONS TASKS REMINDERS EVENTS NOTES <<< "$DB_STATS"
            echo -e "  Memories: ${GREEN}${MEMORIES}${NC}"
            echo -e "  Conversations: ${GREEN}${CONVERSATIONS}${NC}"
            echo -e "  Active Tasks: ${YELLOW}${TASKS}${NC}"
            echo -e "  Pending Reminders: ${YELLOW}${REMINDERS}${NC}"
            echo -e "  Upcoming Events: ${CYAN}${EVENTS}${NC}"
            echo -e "  Notes: ${GREEN}${NOTES}${NC}"
        else
            echo -e "  ${RED}✗ Could not fetch statistics${NC}"
        fi
    else
        echo -e "  ${YELLOW}⚠ PostgreSQL not running${NC}"
    fi

    echo ""

    # ================================================================
    # QDRANT COLLECTIONS
    # ================================================================
    echo -e "${BLUE}🔍 QDRANT COLLECTIONS${NC}"
    echo ""

    if curl -sf http://localhost:6333/collections > /dev/null 2>&1; then
        COLLECTIONS=$(curl -s http://localhost:6333/collections 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for c in data.get('result', {}).get('collections', []):
        print(f\"{c['name']}:{c.get('points_count', 0)}\")
except:
    pass
" 2>/dev/null)

        if [ -n "$COLLECTIONS" ]; then
            while IFS=':' read -r name count; do
                echo -e "  ${name}: ${GREEN}${count}${NC} points"
            done <<< "$COLLECTIONS"
        else
            echo -e "  ${YELLOW}⚠ No collections data${NC}"
        fi
    else
        echo -e "  ${RED}✗ Qdrant not accessible${NC}"
    fi

    echo ""

    # ================================================================
    # OLLAMA MODELS
    # ================================================================
    echo -e "${BLUE}🤖 OLLAMA MODELS${NC}"
    echo ""

    if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        MODELS=$(curl -s http://localhost:11434/api/tags 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for m in data.get('models', []):
        size_gb = m.get('size', 0) / 1024 / 1024 / 1024
        print(f\"{m['name']}:{size_gb:.1f}\")
except:
    pass
" 2>/dev/null)

        if [ -n "$MODELS" ]; then
            while IFS=':' read -r name size; do
                echo -e "  ${name}: ${GREEN}${size}GB${NC}"
            done <<< "$MODELS"
        else
            echo -e "  ${YELLOW}⚠ No models loaded${NC}"
        fi
    else
        echo -e "  ${RED}✗ Ollama not accessible${NC}"
    fi

    echo ""

    # ================================================================
    # RESOURCE USAGE
    # ================================================================
    echo -e "${BLUE}📊 RESOURCE USAGE${NC}"
    echo ""

    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null | grep "ai-stack" | while read -r line; do
        echo "  $line"
    done

    echo ""

    # ================================================================
    # DISK USAGE
    # ================================================================
    echo -e "${BLUE}💾 DISK USAGE${NC}"
    echo ""

    df -h 2>/dev/null | grep -E "(appdata|ai_stack)" | awk '{print "  " $6 ": " $3 "/" $2 " (" $5 " used)"}'

    echo ""

    # ================================================================
    # FOOTER
    # ================================================================
    echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo -e "  Refresh: ${REFRESH_INTERVAL}s | Press Ctrl+C to exit"
    echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"

    sleep "$REFRESH_INTERVAL"
done
