# 🍽️ Food Log Feature - Track What You Eat with AI Recommendations

A complete food tracking system with AI-powered recommendations. Log what you eat through natural conversation with AnythingLLM, and get personalized suggestions based on foods you liked but haven't eaten recently.

## 🎯 What Does This Do?

The Food Log feature:

- **Natural Food Logging** - Tell AnythingLLM what you ate and it logs everything
- **AI Vectorization** - Each meal is embedded for semantic search
- **Smart Recommendations** - Get suggestions for foods you enjoyed but haven't had in a while
- **Rich Metadata** - Track made vs bought, ratings, ingredients, tags, calories, and more
- **Beautiful Visualizations** - Terminal-based dashboard to view your food history

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Conversational Input** | "I had chicken tikka masala for dinner, I made it myself, rating 5/5" |
| **Vector Search** | Find similar foods using semantic search in Qdrant |
| **Smart Filtering** | Get recommendations for foods you liked that you haven't eaten recently |
| **Rich Queries** | Search by name, date range, tags, ingredients, rating |
| **Statistics Dashboard** | View stats like made vs bought, average ratings, favorite meal types |
| **Duplicate Detection** | Track when you last ate specific foods |

## 📦 What's Included

✅ **Database Migration** - `009_create_food_log.sql` with 18 columns
✅ **n8n Workflow** - `19-food-log.json` with vectorization pipeline
✅ **AnythingLLM Skills** - `log-food.js` and `recommend-food.js`
✅ **Qdrant Collection** - `food_memories` (768-dim vectors)
✅ **Visualization Script** - `view-food-log.sh` with 9 different views
✅ **Setup Script** - `setup-food-log.sh` for automated deployment

## 🚀 Quick Start

### 1. Run Setup Script
```bash
cd /home/user/ai_assistant_local_stack
./scripts/setup-food-log.sh
```

This will:
- Create the `food_log` table in PostgreSQL
- Create the `food_memories` collection in Qdrant
- Display instructions for importing the workflow and skills

### 2. Import n8n Workflow
1. Open n8n at http://localhost:5678
2. Go to **Workflows** → **Import from File**
3. Select: `n8n-workflows/19-food-log.json`
4. Click **Activate** to enable the workflow

### 3. Install AnythingLLM Skills
1. Open AnythingLLM at http://localhost:3001
2. Go to **Settings** → **Agent Skills**
3. Click **Import Custom Skill**
4. Upload both:
   - `anythingllm-skills/log-food.js`
   - `anythingllm-skills/recommend-food.js`
5. Enable them in your workspace

### 4. Test It Out!

**Log some food:**
```
You: "I ate spaghetti carbonara for dinner. I made it myself, it was amazing! Rating 5 stars. Used bacon, eggs, parmesan."

AI: ✅ Logged "spaghetti carbonara" successfully! This has been vectorized for future recommendations.
```

**Get recommendations:**
```
You: "What should I eat that I liked but haven't had in a while?"

AI: 🍽️ Here are 5 recommendations based on foods you liked:

1. **Spaghetti Carbonara** Rating: ⭐⭐⭐⭐⭐ Last eaten: 45 days ago (made)
   Homemade pasta with bacon, eggs, and parmesan

2. **Chicken Tikka Masala** Rating: ⭐⭐⭐⭐⭐ Last eaten: 30 days ago (made)
   Spicy Indian curry, absolutely delicious!
```

## 📊 Database Schema

### Table: `food_log`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | UUID | References users table |
| `food_name` | TEXT | Name of the food |
| `description` | TEXT | Description, how it tasted, etc. |
| `made_or_bought` | TEXT | 'made' or 'bought' |
| `consumed_at` | TIMESTAMP | When you ate it |
| `meal_type` | TEXT | 'breakfast', 'lunch', 'dinner', 'snack' |
| `rating` | INTEGER | 1-5 stars |
| `liked` | BOOLEAN | Did you like it? |
| `would_eat_again` | BOOLEAN | Would you eat it again? |
| `ingredients` | TEXT[] | Array of ingredients |
| `tags` | TEXT[] | Tags like 'spicy', 'healthy', 'italian' |
| `calories` | INTEGER | Approximate calories |
| `restaurant_or_recipe` | TEXT | Where you got it from |
| `notes` | TEXT | Additional notes |
| `embedding_generated` | BOOLEAN | Has this been vectorized? |
| `last_recommended_at` | TIMESTAMP | When was this last recommended |
| `created_at` | TIMESTAMP | Record creation time |
| `updated_at` | TIMESTAMP | Last update time |

### Indexes

- User ID lookup: `idx_food_log_user_id`
- Date ordering: `idx_food_log_consumed_at`
- Name search: `idx_food_log_food_name`
- Liked foods: `idx_food_log_liked`
- Rating lookup: `idx_food_log_rating`
- Tag search (GIN): `idx_food_log_tags`
- Ingredient search (GIN): `idx_food_log_ingredients`

### Views

**`food_recommendations`** - Shows foods you liked (rating ≥ 4) that you haven't eaten recently:
```sql
SELECT * FROM food_recommendations;
```

### Functions

**`get_food_stats()`** - Returns statistics about your food log:
```sql
SELECT * FROM get_food_stats();
```

Returns:
- Total entries
- Liked vs disliked count
- Average rating
- Made vs bought count
- Favorite meal type

## 🔄 n8n Workflow Architecture

The workflow (`19-food-log.json`) has two webhook endpoints:

### 1. `/webhook/log-food` (POST)

**Flow:**
```
Webhook → Insert to PostgreSQL → Prepare Embedding Text
  → Generate Embedding (Ollama) → Store in Qdrant
  → Mark as Vectorized → Respond
```

**Input Parameters:**
```json
{
  "food_name": "Pizza Margherita",
  "description": "Classic Italian pizza with fresh mozzarella",
  "made_or_bought": "bought",
  "meal_type": "dinner",
  "rating": 4,
  "liked": true,
  "would_eat_again": true,
  "ingredients": ["dough", "tomato sauce", "mozzarella", "basil"],
  "tags": ["italian", "comfort-food"],
  "calories": 800,
  "restaurant_or_recipe": "Mario's Pizza Place",
  "notes": "Best pizza in town!",
  "consumed_at": "2025-11-18T19:30:00Z"
}
```

**Embedding Generation:**
- Combines: food_name + description + meal_type + notes
- Model: `nomic-embed-text` (768 dimensions)
- Stored in Qdrant collection: `food_memories`

### 2. `/webhook/recommend-food` (POST)

**Flow:**
```
Webhook → Generate Query Embedding → Search Similar Foods in Qdrant
  → Get Full Details from PostgreSQL → Filter by Date
  → Return Top 5 Oldest Liked Foods
```

**Input Parameters:**
```json
{
  "query": "something spicy and healthy"
}
```

**Recommendation Logic:**
1. Convert query to 768-dim vector using Ollama
2. Search Qdrant for similar foods (filter: `liked = true`)
3. Get full details from PostgreSQL
4. Sort by `consumed_at ASC` (oldest first)
5. Return top 5 results

## 🎨 Visualization Dashboard

Run the interactive terminal viewer:
```bash
./scripts/view-food-log.sh
```

### Available Views

| View | Description |
|------|-------------|
| **1. Recent Entries** | Last 10 foods logged with ratings |
| **2. Statistics** | Total entries, avg rating, made vs bought |
| **3. Top Rated** | All foods rated 4+ stars |
| **4. Recommendations** | Foods you liked but haven't eaten recently |
| **5. Search by Name** | Find specific foods |
| **6. All Entries** | Complete table (paginated) |
| **7. Date Range** | Filter by start/end date |
| **8. By Tag** | Search by tags like 'spicy', 'healthy' |
| **9. Made vs Bought** | Compare homemade vs purchased foods |

**Example Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
       🍽️  FOOD LOG DATABASE VIEWER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Recent Food Entries (Last 10)

 food_name          | rating      | made_or_bought | meal_type | when_eaten       | liked
--------------------+-------------+----------------+-----------+------------------+-------
 Chicken Tikka      | ⭐⭐⭐⭐⭐ | made           | dinner    | 2025-11-18 19:30 | 👍
 Caesar Salad       | ⭐⭐⭐⭐  | bought         | lunch     | 2025-11-18 12:15 | 👍
 Avocado Toast      | ⭐⭐⭐    | made           | breakfast | 2025-11-18 08:00 | 👍
```

## 🤖 AnythingLLM Skills

### Skill 1: `log-food`

**Description:** Log food you ate with details like name, made/bought, rating, and notes.

**Parameters:**
- `food_name` (required) - Name of the food
- `made_or_bought` (optional) - 'made' or 'bought'
- `description` (optional) - How it tasted, ingredients, etc.
- `meal_type` (optional) - 'breakfast', 'lunch', 'dinner', 'snack'
- `rating` (optional) - 1-5 stars
- `liked` (optional) - true/false
- `would_eat_again` (optional) - true/false
- `ingredients` (optional) - Array of ingredients
- `tags` (optional) - Array of tags
- `calories` (optional) - Approximate calories
- `restaurant_or_recipe` (optional) - Where you got it
- `notes` (optional) - Additional notes
- `consumed_at` (optional) - ISO timestamp (defaults to now)

**Example Usage:**
```
"Log that I ate homemade lasagna for dinner. I made it with beef, ricotta, and marinara sauce. Rating 5 stars, definitely eating again!"
```

### Skill 2: `recommend-food`

**Description:** Get AI-powered food recommendations based on what you've logged.

**Parameters:**
- `query` (optional) - Refine recommendations (e.g., "something spicy", "healthy lunch")

**Example Usage:**
```
"What should I eat that I liked but haven't had recently?"
"Recommend me something spicy and vegetarian"
"What's a good comfort food I haven't had in a while?"
```

## 💡 Usage Examples

### Example 1: Logging Breakfast
```
You: "I had scrambled eggs with avocado for breakfast this morning. Made it myself, super healthy, 4 stars."

AI: ✅ Logged "scrambled eggs with avocado" successfully! This has been vectorized for future recommendations.
```

### Example 2: Tracking Restaurant Meals
```
You: "Ate at Joe's Diner - had their famous burger and fries. Bought it, rated 5/5, absolutely delicious. Tags: comfort-food, american. About 1200 calories."

AI: ✅ Logged "famous burger and fries" successfully!
```

### Example 3: Getting Contextual Recommendations
```
You: "I want something spicy but healthy for lunch"

AI: 🍽️ Here are 3 recommendations:

1. **Thai Green Curry** ⭐⭐⭐⭐⭐ Last eaten: 52 days ago (made)
   Spicy coconut curry with vegetables and chicken

2. **Spicy Tofu Bowl** ⭐⭐⭐⭐ Last eaten: 38 days ago (made)
   Healthy bowl with marinated tofu, sriracha, and quinoa
```

### Example 4: Tracking Ingredients for Recipes
```
You: "Made chicken tikka masala tonight. Ingredients: chicken, yogurt, tomatoes, cream, garam masala, cumin, ginger, garlic. Rating 5 stars, took 2 hours but worth it!"

AI: ✅ Logged "chicken tikka masala" successfully!
```

## 🔍 Advanced Queries

### SQL Queries You Can Run

**Find your most-eaten foods:**
```sql
SELECT food_name, COUNT(*) as times_eaten
FROM food_log
GROUP BY food_name
ORDER BY times_eaten DESC
LIMIT 10;
```

**Compare homemade vs restaurant quality:**
```sql
SELECT made_or_bought, AVG(rating) as avg_rating
FROM food_log
WHERE rating IS NOT NULL
GROUP BY made_or_bought;
```

**Find foods you haven't eaten in 30+ days:**
```sql
SELECT food_name,
       EXTRACT(DAYS FROM (CURRENT_TIMESTAMP - consumed_at))::INTEGER as days_ago,
       rating
FROM food_log
WHERE EXTRACT(DAYS FROM (CURRENT_TIMESTAMP - consumed_at)) > 30
  AND liked = true
ORDER BY consumed_at ASC;
```

**Get meal type distribution:**
```sql
SELECT meal_type, COUNT(*) as count
FROM food_log
WHERE meal_type IS NOT NULL
GROUP BY meal_type;
```

## 🔧 Customization

### Adding Custom Fields

Edit `migrations/009_create_food_log.sql` and add columns:

```sql
ALTER TABLE food_log ADD COLUMN price NUMERIC(10,2);
ALTER TABLE food_log ADD COLUMN location TEXT;
ALTER TABLE food_log ADD COLUMN companions TEXT[];
```

### Adjusting Recommendation Logic

Edit the n8n workflow (`19-food-log.json`):
- Change `limit: 10` to show more/fewer recommendations
- Adjust filter criteria (e.g., `rating >= 5` for only 5-star foods)
- Modify the date sorting to prioritize by rating instead

### Creating Custom Views

Add to `scripts/view-food-log.sh`:

```bash
view_vegetarian() {
    echo -e "\n${BOLD}${GREEN}🥗 Vegetarian Foods${NC}\n"
    execute_query "
        SELECT food_name, rating, consumed_at
        FROM food_log
        WHERE 'vegetarian' = ANY(tags)
        ORDER BY consumed_at DESC;
    "
}
```

## 📈 Use Cases

### 1. Health Tracking
- Log everything you eat with calorie counts
- Track homemade vs purchased food ratios
- Identify your healthiest favorite meals

### 2. Recipe Discovery
- Find recipes you loved but forgot about
- Track ingredient combinations that work well
- Build a personal cookbook from successful experiments

### 3. Restaurant Recommendations
- Remember which restaurants you loved
- Never forget a great dish you had months ago
- Track your favorite menu items by cuisine type

### 4. Dietary Planning
- Get suggestions that fit your preferences
- Avoid food fatigue by rotating favorites
- Discover patterns in your eating habits

### 5. Social Sharing
- Share your food log with friends/family
- Export statistics for nutritionists
- Track group meal ratings

## 🛠️ Troubleshooting

### Issue: Skills not showing in AnythingLLM

**Solution:**
1. Check that skills are uploaded to AnythingLLM
2. Verify they're enabled in workspace settings
3. Restart AnythingLLM container: `docker restart anythingllm-ai-stack`

### Issue: n8n workflow not triggering

**Solution:**
1. Ensure workflow is activated (toggle on)
2. Check webhook URL: `http://n8n-ai-stack:5678/webhook/log-food`
3. View execution logs in n8n for errors

### Issue: No recommendations returned

**Solution:**
1. Verify you have logged food with `liked = true`
2. Check Qdrant has the `food_memories` collection:
   ```bash
   curl http://localhost:6333/collections/food_memories
   ```
3. Ensure embeddings are being generated (check `embedding_generated` column)

### Issue: Visualization script fails

**Solution:**
1. Check PostgreSQL is running: `docker ps | grep postgres`
2. Verify database connection:
   ```bash
   docker exec postgres-ai-stack psql -U aistack_user -d aistack -c "SELECT 1;"
   ```
3. Ensure migration has run: `SELECT COUNT(*) FROM food_log;`

## 📚 Files Reference

| File | Location | Purpose |
|------|----------|---------|
| Migration | `migrations/009_create_food_log.sql` | Creates table, indexes, views, functions |
| Workflow | `n8n-workflows/19-food-log.json` | Handles logging and recommendations |
| Log Skill | `anythingllm-skills/log-food.js` | AnythingLLM skill for logging |
| Recommend Skill | `anythingllm-skills/recommend-food.js` | AnythingLLM skill for recommendations |
| Viewer | `scripts/view-food-log.sh` | Interactive terminal dashboard |
| Setup | `scripts/setup-food-log.sh` | Automated setup script |

## 🎯 Next Steps

After setting up the food log:

1. **Start Logging**: Log your next few meals to build up data
2. **Add Tags**: Use consistent tags like 'vegetarian', 'spicy', 'healthy' for better filtering
3. **Rate Everything**: Ratings power the recommendation engine
4. **Use the Viewer**: Explore your data with `./scripts/view-food-log.sh`
5. **Get Recommendations**: Ask "What should I eat?" in AnythingLLM

## 🤝 Integration Ideas

- **Sync with MyFitnessPal**: Import calorie data
- **Google Keep Integration**: Log from notes (see next section)
- **Calendar Events**: Auto-log meals from calendar entries
- **Photo Uploads**: OCR receipts for automatic logging
- **Nutrition API**: Auto-fill nutritional information

---

**Built as part of the AI Stack Local Assistant**
For more features, see the main [README.md](/home/user/ai_assistant_local_stack/README.md)
