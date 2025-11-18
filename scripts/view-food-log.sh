#!/bin/bash
# Food Log Visualization Script
# Display food log database content in a formatted table
# Integrates with AI Stack monitoring system

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

echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${CYAN}       🍽️  FOOD LOG DATABASE VIEWER${NC}"
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Database connection details
DB_HOST="localhost"
DB_PORT="5434"
DB_NAME="aistack"
DB_USER="aistack_user"
export PGPASSWORD="aistack_password"

# Function to execute SQL and display results
execute_query() {
    local query="$1"
    docker exec -i postgres-ai-stack psql -U "$DB_USER" -d "$DB_NAME" -c "$query"
}

# Main menu
show_menu() {
    echo -e "${BOLD}${YELLOW}Select a view:${NC}"
    echo "  1) Recent Food Entries (last 10)"
    echo "  2) Food Statistics"
    echo "  3) Favorite Foods"
    echo "  4) Recommendations (foods you liked, not eaten recently)"
    echo "  5) Search by Food Name"
    echo "  6) All Entries (full table)"
    echo "  7) Entries by Date Range"
    echo "  8) Foods by Tag"
    echo "  9) Home vs Outside Statistics"
    echo " 10) Top Restaurants"
    echo " 11) Find Duplicates (maintenance)"
    echo "  0) Exit"
    echo ""
    read -p "Enter choice [0-11]: " choice
    echo ""
}

# View 1: Recent entries
view_recent() {
    echo -e "${BOLD}${GREEN}📋 Recent Food Entries (Last 10)${NC}\n"
    execute_query "
        SELECT
            food_name,
            CASE preference
                WHEN 'favorite' THEN '⭐ Favorite'
                WHEN 'liked' THEN '👍 Liked'
                WHEN 'disliked' THEN '👎 Disliked'
            END as preference,
            CASE location
                WHEN 'home' THEN '🏠 Home'
                WHEN 'outside' THEN '🍽️ Outside'
            END as location,
            COALESCE(restaurant_name, '-') as restaurant,
            meal_type,
            TO_CHAR(consumed_at, 'YYYY-MM-DD HH24:MI') as when_eaten
        FROM food_log
        WHERE is_merged = false
        ORDER BY consumed_at DESC
        LIMIT 10;
    "
}

# View 2: Statistics
view_stats() {
    echo -e "${BOLD}${GREEN}📊 Food Log Statistics${NC}\n"
    execute_query "SELECT * FROM get_food_stats();"
}

# View 3: Favorite foods
view_favorites() {
    echo -e "${BOLD}${GREEN}⭐ Favorite Foods${NC}\n"
    execute_query "
        SELECT
            food_name,
            CASE location
                WHEN 'home' THEN '🏠 Home'
                WHEN 'outside' THEN '🍽️ Outside'
            END as location,
            COALESCE(restaurant_name, '-') as restaurant,
            TO_CHAR(consumed_at, 'YYYY-MM-DD') as date,
            meal_type
        FROM food_log
        WHERE preference = 'favorite'
          AND is_merged = false
        ORDER BY consumed_at DESC
        LIMIT 20;
    "
}

# View 4: Recommendations
view_recommendations() {
    echo -e "${BOLD}${GREEN}💡 Recommended Foods (Liked/Favorite, Not Eaten Recently)${NC}\n"
    execute_query "
        SELECT
            food_name,
            CASE preference
                WHEN 'favorite' THEN '⭐'
                WHEN 'liked' THEN '👍'
            END as pref,
            days_since_eaten || ' days ago' as last_eaten,
            CASE location
                WHEN 'home' THEN '🏠'
                WHEN 'outside' THEN '🍽️'
            END as loc,
            COALESCE(restaurant_name, '-') as restaurant
        FROM food_recommendations;
    "
}

# View 5: Search by name
search_by_name() {
    read -p "Enter food name to search: " search_term
    echo -e "\n${BOLD}${GREEN}🔍 Search Results for: $search_term${NC}\n"
    execute_query "
        SELECT
            food_name,
            description,
            CASE preference
                WHEN 'favorite' THEN '⭐ Favorite'
                WHEN 'liked' THEN '👍 Liked'
                WHEN 'disliked' THEN '👎 Disliked'
            END as preference,
            CASE location
                WHEN 'home' THEN '🏠 Home'
                WHEN 'outside' THEN '🍽️ Outside'
            END as location,
            COALESCE(restaurant_name, '-') as restaurant,
            TO_CHAR(consumed_at, 'YYYY-MM-DD HH24:MI') as when_eaten,
            notes
        FROM food_log
        WHERE food_name ILIKE '%$search_term%'
          AND is_merged = false
        ORDER BY consumed_at DESC;
    "
}

# View 6: All entries
view_all() {
    echo -e "${BOLD}${GREEN}📖 All Food Entries${NC}\n"
    execute_query "
        SELECT
            food_name,
            description,
            CASE location WHEN 'home' THEN '🏠' ELSE '🍽️' END as loc,
            CASE preference
                WHEN 'favorite' THEN '⭐'
                WHEN 'liked' THEN '👍'
                WHEN 'disliked' THEN '👎'
            END as pref,
            meal_type,
            TO_CHAR(consumed_at, 'YYYY-MM-DD') as date
        FROM food_log
        WHERE is_merged = false
        ORDER BY consumed_at DESC;
    " | less
}

# View 7: Date range
view_date_range() {
    read -p "Enter start date (YYYY-MM-DD): " start_date
    read -p "Enter end date (YYYY-MM-DD): " end_date
    echo -e "\n${BOLD}${GREEN}📅 Entries from $start_date to $end_date${NC}\n"
    execute_query "
        SELECT
            TO_CHAR(consumed_at, 'YYYY-MM-DD') as date,
            food_name,
            meal_type,
            CASE preference
                WHEN 'favorite' THEN '⭐'
                WHEN 'liked' THEN '👍'
                WHEN 'disliked' THEN '👎'
            END as pref,
            CASE location WHEN 'home' THEN '🏠' ELSE '🍽️' END as loc
        FROM food_log
        WHERE consumed_at::date BETWEEN '$start_date' AND '$end_date'
          AND is_merged = false
        ORDER BY consumed_at;
    "
}

# View 8: By tag
view_by_tag() {
    read -p "Enter tag to search: " tag
    echo -e "\n${BOLD}${GREEN}🏷️  Entries tagged with: $tag${NC}\n"
    execute_query "
        SELECT
            food_name,
            array_to_string(tags, ', ') as all_tags,
            CASE preference
                WHEN 'favorite' THEN '⭐'
                WHEN 'liked' THEN '👍'
                WHEN 'disliked' THEN '👎'
            END as pref,
            TO_CHAR(consumed_at, 'YYYY-MM-DD') as date
        FROM food_log
        WHERE '$tag' = ANY(tags)
          AND is_merged = false
        ORDER BY consumed_at DESC;
    "
}

# View 9: Home vs Outside stats
view_home_vs_outside() {
    echo -e "${BOLD}${GREEN}🏠 vs 🍽️  Home vs Outside Statistics${NC}\n"
    execute_query "
        SELECT
            CASE location
                WHEN 'home' THEN '🏠 Home'
                WHEN 'outside' THEN '🍽️ Outside'
            END as location,
            COUNT(*) as count,
            COUNT(*) FILTER (WHERE preference = 'favorite') as favorites,
            COUNT(*) FILTER (WHERE preference = 'liked') as liked,
            COUNT(*) FILTER (WHERE preference = 'disliked') as disliked
        FROM food_log
        WHERE is_merged = false
        GROUP BY location;
    "
}

# View 10: Top restaurants
view_top_restaurants() {
    echo -e "${BOLD}${GREEN}🏆 Top Restaurants${NC}\n"
    execute_query "
        SELECT
            restaurant_name,
            COUNT(*) as visits,
            COUNT(*) FILTER (WHERE preference = 'favorite') as favorites,
            COUNT(*) FILTER (WHERE preference = 'liked') as liked,
            COUNT(*) FILTER (WHERE preference = 'disliked') as disliked,
            TO_CHAR(MAX(consumed_at), 'YYYY-MM-DD') as last_visit
        FROM food_log
        WHERE restaurant_name IS NOT NULL
          AND is_merged = false
        GROUP BY restaurant_name
        ORDER BY visits DESC, favorites DESC
        LIMIT 10;
    "
}

# View 11: Find duplicates
view_duplicates() {
    echo -e "${BOLD}${GREEN}🔍 Potential Duplicate Entries${NC}\n"
    execute_query "
        SELECT
            food_name1 as food_1,
            food_name2 as food_2,
            ROUND(similarity_score::numeric, 2) as similarity,
            TO_CHAR(consumed_at1, 'YYYY-MM-DD') as date_1,
            TO_CHAR(consumed_at2, 'YYYY-MM-DD') as date_2
        FROM find_duplicate_foods()
        LIMIT 20;
    "

    echo -e "\n${YELLOW}💡 Tip: Run './scripts/food-maintenance.sh' to merge duplicates interactively${NC}\n"
}

# Main loop
while true; do
    show_menu

    case $choice in
        1) view_recent ;;
        2) view_stats ;;
        3) view_favorites ;;
        4) view_recommendations ;;
        5) search_by_name ;;
        6) view_all ;;
        7) view_date_range ;;
        8) view_by_tag ;;
        9) view_home_vs_outside ;;
        10) view_top_restaurants ;;
        11) view_duplicates ;;
        0)
            echo -e "${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice. Please try again.${NC}\n"
            ;;
    esac

    echo ""
    read -p "Press Enter to continue..."
    clear
done
