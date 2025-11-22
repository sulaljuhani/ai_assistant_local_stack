# 🍽️ Food Tracker Updates - Implementation Summary

This document details all updates made to the food tracking system based on your requirements.

---

## ✅ Requirements Implemented

### 1. ✅ Simplified Required Fields
**Requirement:** Make columns optional except for name, at home/outside, and preference

**Implementation:**
- **Required fields:** `food_name`, `location` (home/outside), `preference` (liked/disliked/favorite)
- **All other fields are optional:** description, meal_type, ingredients, tags, calories, notes, consumed_at
- Database constraint ensures restaurant_name is required when location='outside'

**Schema:**
```sql
CREATE TABLE food_log (
    -- Required
    food_name TEXT NOT NULL,
    location TEXT NOT NULL CHECK (location IN ('home', 'outside')),
    preference TEXT NOT NULL CHECK (preference IN ('liked', 'disliked', 'favorite')),

    -- Optional
    restaurant_name TEXT,  -- Required if location='outside'
    description TEXT,
    meal_type TEXT,
    ingredients TEXT[],
    tags TEXT[],
    calories INTEGER,
    notes TEXT,
    consumed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

### 2. ✅ Duplicate Detection & Merging System
**Requirement:** Weekly maintenance script to detect and merge similar entries

**Implementation:**

#### Database Functions Added:
1. **`find_duplicate_foods()`** - Finds potential duplicates using fuzzy matching
   - Exact match: similarity = 1.0
   - Partial match: similarity = 0.8
   - Returns pairs with similarity >= 0.8

2. **`merge_food_entries(keep_id, merge_id)`** - Merges two entries
   - Keeps one entry, marks other as `is_merged = true`
   - Tracks merge history in `merged_from_ids` array

#### Maintenance Script:
**File:** `scripts/food-maintenance.sh` (executable)

**Features:**
- Scans for duplicates using SQL function
- Shows side-by-side comparison of potential duplicates
- Interactive prompts:
  1. Keep Entry 1, merge Entry 2 into it
  2. Keep Entry 2, merge Entry 1 into it
  3. Keep both (not duplicates)
  4. Skip (decide later)
- Shows statistics after completion
- Displays cron command for weekly scheduling

**Weekly Automation:**
```bash
# Add to crontab:
0 10 * * 0 /path/to/scripts/food-maintenance.sh
# Runs every Sunday at 10 AM
```

**Merge Tracking Fields:**
```sql
merged_from_ids UUID[],     -- Array of merged entry IDs
is_merged BOOLEAN DEFAULT false  -- True if entry was merged into another
```

**Views & Queries:**
- All queries filter `is_merged = false` to exclude merged entries
- `get_food_stats()` function excludes merged entries from counts

---

### 3. ✅ Restaurant Name Column
**Requirement:** Separate column for restaurant name when food is bought outside

**Implementation:**
```sql
restaurant_name TEXT,

CONSTRAINT check_restaurant_name CHECK (
    (location = 'home') OR (location = 'outside' AND restaurant_name IS NOT NULL)
)
```

**Features:**
- Database constraint enforces restaurant_name when location='outside'
- AnythingLLM skill validates before sending to database
- Visualization shows top restaurants
- Statistics track restaurant visits

**New Views:**
- **Top Restaurants View** (view #10 in viewer)
  - Shows visit count, favorites, liked/disliked breakdown
  - Last visit date

---

### 4. ✅ New Rating System: Liked/Disliked/Favorite
**Requirement:** Replace 5-star rating with liked/disliked/favorite status

**Implementation:**
```sql
preference TEXT NOT NULL CHECK (preference IN ('liked', 'disliked', 'favorite'))
```

**Removed Fields:**
- `rating INTEGER` (1-5 stars) ❌
- `liked BOOLEAN` ❌
- `would_eat_again BOOLEAN` ❌

**New Field:**
- `preference TEXT` ✅ (liked/disliked/favorite)

**Impact on Recommendations:**
```sql
-- Old query
WHERE liked = true AND rating >= 4

-- New query
WHERE preference IN ('liked', 'favorite')
ORDER BY
    CASE preference
        WHEN 'favorite' THEN 1  -- Favorites first
        WHEN 'liked' THEN 2
    END,
    consumed_at ASC  -- Then oldest
```

**Display:**
- Favorite: ⭐
- Liked: 👍
- Disliked: 👎

---

### 5. ✅ Integration with Existing Dashboards
**Requirement:** Make visualization work with monitor-system.sh

**Implementation:**

#### Added to `monitor-system.sh`:
```bash
# Food Log Statistics (in DATABASE STATISTICS section)
Food Log Entries: 42 (⭐15 favorites, 🍽️28 restaurants)
```

**Displays:**
- Total food log entries (excluding merged)
- Favorite count
- Restaurant meal count

#### Enhanced `view-food-log.sh`:
**11 views (up from 9):**
1. Recent Food Entries (last 10)
2. Food Statistics (using `get_food_stats()`)
3. Favorite Foods (preference='favorite')
4. Recommendations (from view)
5. Search by Food Name
6. All Entries (paginated)
7. Entries by Date Range
8. Foods by Tag
9. **Home vs Outside Statistics** (NEW)
10. **Top Restaurants** (NEW)
11. **Find Duplicates** (NEW - maintenance mode)

**Integration Features:**
- Same color scheme as monitor-system.sh
- Same database connection method
- Compatible with existing scripts
- Can be run alongside monitor-system.sh

---

### 6. ✅ Multi-Food Entry Support
**Requirement:** "pizza and pasta" stored as one entry unless specified

**Implementation:**

**In AnythingLLM Skill (`log-food.js`):**
```javascript
food_name: {
    type: "string",
    description: "Name of the food. Can be multiple items (e.g., 'pizza and pasta', 'burger and fries'). Will be stored as one entry unless you explicitly ask for separate entries.",
    required: true
}
```

**Behavior:**
- Default: Multiple foods in one string = single entry
  - Input: "I ate pizza and pasta"
  - Stored as: `food_name = "pizza and pasta"`

- Explicit separation: User requests separate entries
  - Input: "I ate pizza and pasta, log them separately"
  - Agent should call skill twice:
    - Entry 1: `food_name = "pizza"`
    - Entry 2: `food_name = "pasta"`

**Database Support:**
- Single `food_name TEXT` field can contain compound names
- Vectorization works on full string, capturing semantic meaning
- Search works for partial matches: "pizza" finds "pizza and pasta"

---

## 📊 Updated Database Schema

### Table: `food_log`

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `id` | UUID | ✅ | Primary key |
| `user_id` | UUID | ✅ | References users table |
| **CORE REQUIRED FIELDS** |
| `food_name` | TEXT | ✅ | Name (can be compound like "pizza and pasta") |
| `location` | TEXT | ✅ | 'home' or 'outside' |
| `preference` | TEXT | ✅ | 'liked', 'disliked', or 'favorite' |
| **RESTAURANT** |
| `restaurant_name` | TEXT | ⚠️ | Required if location='outside' |
| **OPTIONAL METADATA** |
| `description` | TEXT | ❌ | How it tasted, etc. |
| `consumed_at` | TIMESTAMP | ❌ | Defaults to now |
| `meal_type` | TEXT | ❌ | breakfast/lunch/dinner/snack |
| `ingredients` | TEXT[] | ❌ | Array of ingredients |
| `tags` | TEXT[] | ❌ | Array of tags |
| `calories` | INTEGER | ❌ | Approximate calories |
| `notes` | TEXT | ❌ | Additional notes |
| **MERGE TRACKING** |
| `merged_from_ids` | UUID[] | ❌ | IDs of merged entries |
| `is_merged` | BOOLEAN | ❌ | Default false |
| **VECTORIZATION** |
| `embedding_generated` | BOOLEAN | ❌ | Default false |
| `last_recommended_at` | TIMESTAMP | ❌ | Last recommendation time |
| **TIMESTAMPS** |
| `created_at` | TIMESTAMP | ❌ | Auto-set |
| `updated_at` | TIMESTAMP | ❌ | Auto-update |

### Indexes (9 total)

```sql
CREATE INDEX idx_food_log_user_id ON food_log(user_id);
CREATE INDEX idx_food_log_consumed_at ON food_log(consumed_at DESC);
CREATE INDEX idx_food_log_food_name ON food_log(food_name);
CREATE INDEX idx_food_log_preference ON food_log(preference);
CREATE INDEX idx_food_log_location ON food_log(location);
CREATE INDEX idx_food_log_restaurant ON food_log(restaurant_name);
CREATE INDEX idx_food_log_tags ON food_log USING GIN(tags);
CREATE INDEX idx_food_log_ingredients ON food_log USING GIN(ingredients);
CREATE INDEX idx_food_log_name_lower ON food_log(LOWER(food_name));  -- For duplicates
```

### Functions (3 total)

1. **`get_food_stats()`** - Returns statistics
   - Output: total_entries, liked_count, disliked_count, favorite_count, home_count, outside_count, favorite_meal_type, top_restaurant

2. **`find_duplicate_foods()`** - Finds potential duplicates
   - Uses fuzzy matching (exact = 1.0, partial = 0.8)
   - Returns pairs with similarity >= 0.8

3. **`merge_food_entries(keep_id, merge_id)`** - Merges entries
   - Marks merged entry as `is_merged = true`
   - Updates `merged_from_ids` array

### Views (1 total)

**`food_recommendations`**
```sql
-- Shows liked/favorite foods not eaten recently
-- Prioritizes favorites over liked
-- Excludes merged entries
```

---

## 🔄 Updated n8n Workflow

**File:** `n8n-workflows/19-food-log.json`

### Changes:

1. **Log Food Endpoint** (`/webhook/log-food`)
   ```sql
   INSERT INTO food_log (
       user_id, food_name, location, preference,
       restaurant_name, description, consumed_at,
       meal_type, ingredients, tags, calories, notes
   )
   ```

2. **Qdrant Payload Updated:**
   ```json
   "payload": {
       "food_name": "...",
       "location": "home|outside",
       "preference": "liked|disliked|favorite",
       "restaurant_name": "..."
   }
   ```

3. **Recommend Food Filter Updated:**
   ```json
   "filter": {
       "should": [
           {"key": "preference", "match": {"value": "liked"}},
           {"key": "preference", "match": {"value": "favorite"}}
       ]
   }
   ```

---

## 🤖 Updated AnythingLLM Skills

### `log-food.js` Changes:

**Required Parameters (3):**
1. `food_name` - Can contain multiple foods
2. `location` - 'home' or 'outside'
3. `preference` - 'liked', 'disliked', or 'favorite'

**Conditional Requirement:**
- `restaurant_name` - Required if location='outside'

**Validation Added:**
- Checks location is 'home' or 'outside'
- Checks preference is 'liked', 'disliked', or 'favorite'
- Enforces restaurant_name when location='outside'
- Returns clear error messages

**Response Format:**
```
✅ Logged "pizza and pasta" successfully! 👍 🏠
   This has been vectorized for future recommendations.

✅ Logged "burger" successfully! ⭐ 🍽️
   Restaurant: Five Guys
   This has been vectorized for future recommendations.
```

### `recommend-food.js` Changes:

**Updated Display:**
```
🍽️ Here are 5 recommendations:

1. **Spaghetti Carbonara** ⭐ 🏠 Last eaten: 45 days ago
2. **Burger** 👍 🍽️ Last eaten: 30 days ago Restaurant: Five Guys
```

---

## 📂 Files Modified

| File | Lines Changed | Description |
|------|---------------|-------------|
| `migrations/009_create_food_log.sql` | 212 | Complete rewrite with new schema |
| `anythingllm-skills/log-food.js` | 166 | Updated for new fields & validation |
| `anythingllm-skills/recommend-food.js` | 76 | Updated display format |
| `n8n-workflows/19-food-log.json` | 3 sections | Updated INSERT, payload, filter |
| `scripts/view-food-log.sh` | 307 | Added 3 new views, updated all queries |
| `scripts/monitor-system.sh` | +15 lines | Added food log statistics |
| `scripts/food-maintenance.sh` | 131 | NEW - Duplicate detection & merging |

**New Files:**
- `scripts/food-maintenance.sh` (executable)
- `docs/FOOD_TRACKER_UPDATES.md` (this file)

---

## 🎯 Usage Examples

### Example 1: Log Food at Home
```
You: "I ate spaghetti carbonara at home, it was my favorite!"

AI calls: log-food(
    food_name="spaghetti carbonara",
    location="home",
    preference="favorite"
)

Response: ✅ Logged "spaghetti carbonara" successfully! ⭐ 🏠
```

### Example 2: Log Food at Restaurant
```
You: "I had a burger at Five Guys, I liked it"

AI calls: log-food(
    food_name="burger",
    location="outside",
    preference="liked",
    restaurant_name="Five Guys"
)

Response: ✅ Logged "burger" successfully! 👍 🍽️
          Restaurant: Five Guys
```

### Example 3: Multi-Food Entry
```
You: "I ate pizza and pasta for dinner at home, loved it!"

AI calls: log-food(
    food_name="pizza and pasta",
    location="home",
    preference="favorite",
    meal_type="dinner"
)

Stored as single entry with food_name = "pizza and pasta"
```

### Example 4: Run Maintenance
```bash
$ ./scripts/food-maintenance.sh

🔍 Scanning for duplicate food entries...
Found 2 potential duplicate(s)!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Similarity: 1.00

Entry 1:
  • Food: Pizza
  • Location: home
  • Date: 2025-11-10

Entry 2:
  • Food: pizza
  • Location: outside
  • Restaurant: Dominos
  • Date: 2025-11-15

What would you like to do?
  1) Keep Entry 1, merge Entry 2 into it
  2) Keep Entry 2, merge Entry 1 into it
  3) Keep both (not duplicates)
  4) Skip (decide later)

Enter choice [1-4]: 2

Merging Entry 1 into Entry 2...
✅ Merged successfully!
```

---

## 🔧 Setup Instructions

### 1. Run Database Migration
```bash
docker exec -i postgres-ai-stack psql -U aistack_user -d aistack < migrations/009_create_food_log.sql
```

### 2. Create Qdrant Collection
```bash
curl -X PUT "http://localhost:6333/collections/food_memories" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 768,
      "distance": "Cosine"
    }
  }'
```

### 3. Import n8n Workflow
1. Open n8n at http://localhost:5678
2. Workflows → Import from File
3. Select: `n8n-workflows/19-food-log.json`
4. Activate workflow

### 4. Install AnythingLLM Skills
1. Open AnythingLLM at http://localhost:3001
2. Settings → Agent Skills
3. Upload: `log-food.js` and `recommend-food.js`
4. Enable in workspace

### 5. Setup Weekly Maintenance (Optional)
```bash
# Add to crontab
crontab -e

# Add line:
0 10 * * 0 /home/user/ai_assistant_local_stack/scripts/food-maintenance.sh
```

---

## ✅ Testing Checklist

- [ ] Run migration successfully
- [ ] Create Qdrant collection
- [ ] Import and activate n8n workflow
- [ ] Install AnythingLLM skills
- [ ] Test logging food at home
- [ ] Test logging food at restaurant (with restaurant_name)
- [ ] Test multi-food entry ("pizza and pasta")
- [ ] Test with favorite/liked/disliked preferences
- [ ] Run `./scripts/view-food-log.sh` - try all 11 views
- [ ] Run `./scripts/monitor-system.sh` - check food log stats appear
- [ ] Run `./scripts/food-maintenance.sh` - test duplicate detection
- [ ] Get recommendations via AnythingLLM
- [ ] Verify Qdrant vectorization working

---

## 📈 Benefits of Changes

### Simplified UX
- Only 3 required fields (down from complex rating system)
- Clear preference levels (liked/disliked/favorite)
- Natural language: "at home" vs "home/outside"

### Better Data Quality
- Restaurant tracking for outside meals
- Duplicate detection prevents data bloat
- Merge history preserved

### Enhanced Recommendations
- Favorites prioritized in recommendations
- Restaurant suggestions for outside meals
- Multi-food entries capture meal context

### Maintenance
- Weekly automated cleanup
- Interactive merge process
- Statistics show data health

---

**All requirements implemented! 🎉**

For questions or issues, refer to the main documentation files.
