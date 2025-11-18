#!/bin/bash
# Food Log Maintenance Script
# Detects duplicate entries and offers to merge them
# Can be run manually or scheduled weekly via cron

set -euo pipefail

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Database connection details
DB_HOST="localhost"
DB_PORT="5434"
DB_NAME="aistack"
DB_USER="aistack_user"
export PGPASSWORD="aistack_password"

echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${CYAN}       🧹 FOOD LOG MAINTENANCE${NC}"
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Function to execute SQL
execute_query() {
    local query="$1"
    docker exec -i postgres-ai-stack psql -U "$DB_USER" -d "$DB_NAME" -c "$query"
}

# Function to execute SQL and return result
execute_query_result() {
    local query="$1"
    docker exec -i postgres-ai-stack psql -U "$DB_USER" -d "$DB_NAME" -t -A -c "$query"
}

# Check for duplicates
echo -e "${YELLOW}🔍 Scanning for duplicate food entries...${NC}\n"

DUPLICATE_COUNT=$(execute_query_result "SELECT COUNT(*) FROM find_duplicate_foods();")

if [ "$DUPLICATE_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✅ No duplicates found! Your food log is clean.${NC}"
    exit 0
fi

echo -e "${YELLOW}Found ${DUPLICATE_COUNT} potential duplicate(s)!${NC}\n"

# Get duplicates and process them
execute_query "
SELECT
    id1,
    food_name1,
    location1,
    COALESCE(restaurant1, 'N/A') as restaurant1,
    TO_CHAR(consumed_at1, 'YYYY-MM-DD') as date1,
    id2,
    food_name2,
    location2,
    COALESCE(restaurant2, 'N/A') as restaurant2,
    TO_CHAR(consumed_at2, 'YYYY-MM-DD') as date2,
    ROUND(similarity_score::numeric, 2) as similarity
FROM find_duplicate_foods()
ORDER BY similarity_score DESC;
" > /tmp/food_duplicates.txt

# Read duplicates and ask user
IFS='|' read -r header < /tmp/food_duplicates.txt

echo -e "${BOLD}${CYAN}Potential Duplicates:${NC}\n"
cat /tmp/food_duplicates.txt
echo ""

# Process each duplicate pair
tail -n +2 /tmp/food_duplicates.txt | while IFS='|' read -r id1 food1 loc1 rest1 date1 id2 food2 loc2 rest2 date2 sim; do
    # Trim whitespace
    id1=$(echo "$id1" | xargs)
    id2=$(echo "$id2" | xargs)
    food1=$(echo "$food1" | xargs)
    food2=$(echo "$food2" | xargs)
    loc1=$(echo "$loc1" | xargs)
    loc2=$(echo "$loc2" | xargs)
    rest1=$(echo "$rest1" | xargs)
    rest2=$(echo "$rest2" | xargs)
    date1=$(echo "$date1" | xargs)
    date2=$(echo "$date2" | xargs)
    sim=$(echo "$sim" | xargs)

    echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}Similarity: ${sim}${NC}\n"
    echo -e "${CYAN}Entry 1:${NC}"
    echo "  • Food: $food1"
    echo "  • Location: $loc1"
    if [ "$rest1" != "N/A" ]; then
        echo "  • Restaurant: $rest1"
    fi
    echo "  • Date: $date1"
    echo ""
    echo -e "${CYAN}Entry 2:${NC}"
    echo "  • Food: $food2"
    echo "  • Location: $loc2"
    if [ "$rest2" != "N/A" ]; then
        echo "  • Restaurant: $rest2"
    fi
    echo "  • Date: $date2"
    echo ""

    # Ask user what to do
    echo -e "${BOLD}What would you like to do?${NC}"
    echo "  1) Keep Entry 1, merge Entry 2 into it"
    echo "  2) Keep Entry 2, merge Entry 1 into it"
    echo "  3) Keep both (not duplicates)"
    echo "  4) Skip (decide later)"
    echo ""
    read -p "Enter choice [1-4]: " choice

    case $choice in
        1)
            echo -e "\n${YELLOW}Merging Entry 2 into Entry 1...${NC}"
            execute_query "SELECT merge_food_entries('$id1'::uuid, '$id2'::uuid);" > /dev/null
            echo -e "${GREEN}✅ Merged successfully!${NC}\n"
            ;;
        2)
            echo -e "\n${YELLOW}Merging Entry 1 into Entry 2...${NC}"
            execute_query "SELECT merge_food_entries('$id2'::uuid, '$id1'::uuid);" > /dev/null
            echo -e "${GREEN}✅ Merged successfully!${NC}\n"
            ;;
        3)
            echo -e "\n${BLUE}ℹ️  Keeping both entries as separate.${NC}\n"
            # Could mark them as "not duplicates" in future enhancement
            ;;
        4)
            echo -e "\n${BLUE}⏭️  Skipping for now.${NC}\n"
            ;;
        *)
            echo -e "\n${RED}Invalid choice. Skipping.${NC}\n"
            ;;
    esac
done

# Cleanup
rm -f /tmp/food_duplicates.txt

echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${GREEN}       ✅ MAINTENANCE COMPLETE${NC}"
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Show statistics
echo -e "${BOLD}Current Statistics:${NC}"
execute_query "SELECT * FROM get_food_stats();"

echo -e "\n${CYAN}💡 Tip: Add this to your crontab for weekly maintenance:${NC}"
echo -e "${CYAN}   0 10 * * 0 $SCRIPT_DIR/food-maintenance.sh${NC}"
echo -e "${CYAN}   (Runs every Sunday at 10 AM)${NC}\n"
