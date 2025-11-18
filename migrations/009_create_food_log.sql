-- Migration 009: Create Food Log Table
-- Track daily food consumption with vectorization support

CREATE TABLE IF NOT EXISTS food_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Core required fields
    food_name TEXT NOT NULL,
    location TEXT NOT NULL CHECK (location IN ('home', 'outside')),
    preference TEXT NOT NULL CHECK (preference IN ('liked', 'disliked', 'favorite')),

    -- Restaurant name (required if location='outside')
    restaurant_name TEXT,

    -- Optional metadata
    description TEXT,
    consumed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    meal_type TEXT CHECK (meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')),
    ingredients TEXT[],
    tags TEXT[],
    calories INTEGER,
    notes TEXT,

    -- Vectorization support (for AI recommendations)
    embedding_generated BOOLEAN DEFAULT false,
    last_recommended_at TIMESTAMP WITH TIME ZONE,

    -- Merge tracking
    merged_from_ids UUID[],
    is_merged BOOLEAN DEFAULT false,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraint: restaurant_name required if outside
    CONSTRAINT check_restaurant_name CHECK (
        (location = 'home') OR (location = 'outside' AND restaurant_name IS NOT NULL)
    )
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_food_log_user_id ON food_log(user_id);
CREATE INDEX IF NOT EXISTS idx_food_log_consumed_at ON food_log(consumed_at DESC);
CREATE INDEX IF NOT EXISTS idx_food_log_food_name ON food_log(food_name);
CREATE INDEX IF NOT EXISTS idx_food_log_preference ON food_log(preference);
CREATE INDEX IF NOT EXISTS idx_food_log_location ON food_log(location);
CREATE INDEX IF NOT EXISTS idx_food_log_restaurant ON food_log(restaurant_name);

-- GIN index for array fields (for tag search)
CREATE INDEX IF NOT EXISTS idx_food_log_tags ON food_log USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_food_log_ingredients ON food_log USING GIN(ingredients);

-- Index for duplicate detection
CREATE INDEX IF NOT EXISTS idx_food_log_name_lower ON food_log(LOWER(food_name));

-- View for food recommendations (liked/favorite foods not eaten recently)
CREATE OR REPLACE VIEW food_recommendations AS
SELECT
    id,
    food_name,
    description,
    preference,
    consumed_at,
    EXTRACT(DAYS FROM (CURRENT_TIMESTAMP - consumed_at))::INTEGER as days_since_eaten,
    location,
    restaurant_name,
    ingredients,
    tags
FROM food_log
WHERE preference IN ('liked', 'favorite')
  AND is_merged = false
ORDER BY
    CASE preference
        WHEN 'favorite' THEN 1
        WHEN 'liked' THEN 2
        ELSE 3
    END,
    consumed_at ASC  -- Oldest first (haven't eaten in a while)
LIMIT 20;

-- Function to get food statistics
CREATE OR REPLACE FUNCTION get_food_stats(p_user_id UUID DEFAULT '00000000-0000-0000-0000-000000000001')
RETURNS TABLE(
    total_entries BIGINT,
    liked_count BIGINT,
    disliked_count BIGINT,
    favorite_count BIGINT,
    home_count BIGINT,
    outside_count BIGINT,
    favorite_meal_type TEXT,
    top_restaurant TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) FILTER (WHERE is_merged = false)::BIGINT as total_entries,
        COUNT(*) FILTER (WHERE preference = 'liked' AND is_merged = false)::BIGINT as liked_count,
        COUNT(*) FILTER (WHERE preference = 'disliked' AND is_merged = false)::BIGINT as disliked_count,
        COUNT(*) FILTER (WHERE preference = 'favorite' AND is_merged = false)::BIGINT as favorite_count,
        COUNT(*) FILTER (WHERE location = 'home' AND is_merged = false)::BIGINT as home_count,
        COUNT(*) FILTER (WHERE location = 'outside' AND is_merged = false)::BIGINT as outside_count,
        (
            SELECT meal_type
            FROM food_log
            WHERE user_id = p_user_id AND meal_type IS NOT NULL AND is_merged = false
            GROUP BY meal_type
            ORDER BY COUNT(*) DESC
            LIMIT 1
        ) as favorite_meal_type,
        (
            SELECT restaurant_name
            FROM food_log
            WHERE user_id = p_user_id AND restaurant_name IS NOT NULL AND is_merged = false
            GROUP BY restaurant_name
            ORDER BY COUNT(*) DESC
            LIMIT 1
        ) as top_restaurant
    FROM food_log
    WHERE user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- Function to find potential duplicate entries (fuzzy match)
CREATE OR REPLACE FUNCTION find_duplicate_foods(p_user_id UUID DEFAULT '00000000-0000-0000-0000-000000000001')
RETURNS TABLE(
    id1 UUID,
    id2 UUID,
    food_name1 TEXT,
    food_name2 TEXT,
    location1 TEXT,
    location2 TEXT,
    restaurant1 TEXT,
    restaurant2 TEXT,
    consumed_at1 TIMESTAMP WITH TIME ZONE,
    consumed_at2 TIMESTAMP WITH TIME ZONE,
    similarity_score REAL
) AS $$
BEGIN
    RETURN QUERY
    WITH food_pairs AS (
        SELECT
            f1.id as id1,
            f2.id as id2,
            f1.food_name as food_name1,
            f2.food_name as food_name2,
            f1.location as location1,
            f2.location as location2,
            f1.restaurant_name as restaurant1,
            f2.restaurant_name as restaurant2,
            f1.consumed_at as consumed_at1,
            f2.consumed_at as consumed_at2,
            -- Simple similarity score based on lowercase match
            CASE
                WHEN LOWER(f1.food_name) = LOWER(f2.food_name) THEN 1.0
                WHEN LOWER(f1.food_name) LIKE '%' || LOWER(f2.food_name) || '%'
                  OR LOWER(f2.food_name) LIKE '%' || LOWER(f1.food_name) || '%' THEN 0.8
                ELSE 0.0
            END as similarity_score
        FROM food_log f1
        CROSS JOIN food_log f2
        WHERE f1.user_id = p_user_id
          AND f2.user_id = p_user_id
          AND f1.id < f2.id  -- Avoid duplicate pairs
          AND f1.is_merged = false
          AND f2.is_merged = false
    )
    SELECT *
    FROM food_pairs
    WHERE similarity_score >= 0.8
    ORDER BY similarity_score DESC, consumed_at1 DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to merge two food entries
CREATE OR REPLACE FUNCTION merge_food_entries(
    p_keep_id UUID,
    p_merge_id UUID,
    p_user_id UUID DEFAULT '00000000-0000-0000-0000-000000000001'
)
RETURNS BOOLEAN AS $$
DECLARE
    v_merged_ids UUID[];
BEGIN
    -- Get any previously merged IDs from the entry being merged
    SELECT COALESCE(merged_from_ids, ARRAY[]::UUID[]) || ARRAY[p_merge_id]
    INTO v_merged_ids
    FROM food_log
    WHERE id = p_keep_id AND user_id = p_user_id;

    -- Update the kept entry with merged IDs
    UPDATE food_log
    SET
        merged_from_ids = v_merged_ids,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_keep_id AND user_id = p_user_id;

    -- Mark the merged entry as merged
    UPDATE food_log
    SET
        is_merged = true,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_merge_id AND user_id = p_user_id;

    RETURN true;
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE food_log IS 'Track daily food consumption with AI-powered recommendations';
COMMENT ON FUNCTION find_duplicate_foods IS 'Find potential duplicate food entries for maintenance';
COMMENT ON FUNCTION merge_food_entries IS 'Merge two food entries, keeping one and marking the other as merged';
