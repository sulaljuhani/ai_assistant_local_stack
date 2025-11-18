-- Migration 007: Performance Optimization
-- AI Stack - Additional indexes and materialized views for common queries

-- ============================================================================
-- COMPOSITE INDEXES FOR COMMON QUERY PATTERNS
-- ============================================================================

-- Memories: Most relevant memories (salience + recency + access)
CREATE INDEX IF NOT EXISTS idx_memories_relevance
    ON memories(salience_score DESC, access_count DESC, created_at DESC)
    WHERE is_archived = FALSE;

-- Memories: Recent high-salience memories
CREATE INDEX IF NOT EXISTS idx_memories_recent_important
    ON memories(created_at DESC, salience_score DESC)
    WHERE is_archived = FALSE AND salience_score > 0.7;

-- Memories: User + source combination (for filtering by import source)
CREATE INDEX IF NOT EXISTS idx_memories_user_source
    ON memories(user_id, source, created_at DESC);

-- Tasks: Active tasks by priority
CREATE INDEX IF NOT EXISTS idx_tasks_active_priority
    ON tasks(user_id, priority DESC, due_date ASC)
    WHERE status NOT IN ('done', 'cancelled');

-- Tasks: Overdue tasks
CREATE INDEX IF NOT EXISTS idx_tasks_overdue
    ON tasks(user_id, due_date ASC)
    WHERE status NOT IN ('done', 'cancelled') AND due_date < NOW();

-- Events: Upcoming events by user
CREATE INDEX IF NOT EXISTS idx_events_upcoming
    ON events(user_id, start_time ASC)
    WHERE status != 'cancelled' AND start_time > NOW();

-- Reminders: Pending reminders by time
CREATE INDEX IF NOT EXISTS idx_reminders_pending_time
    ON reminders(user_id, remind_at ASC)
    WHERE status = 'pending' AND remind_at > NOW();

-- Notes: Recently modified notes
CREATE INDEX IF NOT EXISTS idx_notes_recent_modified
    ON notes(user_id, updated_at DESC)
    WHERE is_embedded = TRUE;

-- Documents: Recently processed documents
CREATE INDEX IF NOT EXISTS idx_documents_recent_processed
    ON documents(user_id, processed_at DESC)
    WHERE status = 'completed';

-- ============================================================================
-- MATERIALIZED VIEW: Daily Summary
-- ============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS daily_summary AS
SELECT
    u.id AS user_id,
    CURRENT_DATE AS summary_date,

    -- Reminders
    (SELECT COUNT(*) FROM reminders r
     WHERE r.user_id = u.id
     AND DATE(r.remind_at) = CURRENT_DATE
     AND r.status = 'pending') AS reminders_today,

    -- Tasks
    (SELECT COUNT(*) FROM tasks t
     WHERE t.user_id = u.id
     AND DATE(t.due_date) = CURRENT_DATE
     AND t.status NOT IN ('done', 'cancelled')) AS tasks_due_today,

    (SELECT COUNT(*) FROM tasks t
     WHERE t.user_id = u.id
     AND t.status = 'done'
     AND DATE(t.completed_at) = CURRENT_DATE) AS tasks_completed_today,

    -- Events
    (SELECT COUNT(*) FROM events e
     WHERE e.user_id = u.id
     AND DATE(e.start_time) = CURRENT_DATE
     AND e.status != 'cancelled') AS events_today,

    -- Memories
    (SELECT COUNT(*) FROM memories m
     WHERE m.user_id = u.id
     AND DATE(m.created_at) = CURRENT_DATE) AS memories_created_today,

    -- Notes
    (SELECT COUNT(*) FROM notes n
     WHERE n.user_id = u.id
     AND DATE(n.updated_at) = CURRENT_DATE) AS notes_modified_today,

    NOW() AS last_refreshed
FROM users u;

CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_summary_user_date
    ON daily_summary(user_id, summary_date);

-- Function to refresh daily summary
CREATE OR REPLACE FUNCTION refresh_daily_summary()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY daily_summary;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- MATERIALIZED VIEW: Memory Sector Distribution
-- ============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS memory_sector_stats AS
SELECT
    u.id AS user_id,
    ms.sector,
    COUNT(DISTINCT m.id) AS memory_count,
    AVG(m.salience_score) AS avg_salience,
    SUM(m.access_count) AS total_accesses,
    MAX(m.created_at) AS latest_memory_at,
    NOW() AS last_refreshed
FROM users u
LEFT JOIN memories m ON u.id = m.user_id AND m.is_archived = FALSE
LEFT JOIN memory_sectors ms ON m.id = ms.memory_id
GROUP BY u.id, ms.sector;

CREATE UNIQUE INDEX IF NOT EXISTS idx_memory_sector_stats_user_sector
    ON memory_sector_stats(user_id, sector);

CREATE OR REPLACE FUNCTION refresh_memory_sector_stats()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY memory_sector_stats;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- STATISTICS FUNCTIONS
-- ============================================================================

-- Function: Get user activity summary
CREATE OR REPLACE FUNCTION get_user_activity_summary(
    target_user_id UUID DEFAULT '00000000-0000-0000-0000-000000000001'
)
RETURNS TABLE (
    metric TEXT,
    count BIGINT,
    category TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 'Total Memories'::TEXT, COUNT(*)::BIGINT, 'memories'::TEXT
    FROM memories WHERE user_id = target_user_id AND is_archived = FALSE

    UNION ALL
    SELECT 'Total Conversations', COUNT(*), 'memories'
    FROM conversations WHERE user_id = target_user_id

    UNION ALL
    SELECT 'Memory Links', COUNT(*), 'memories'
    FROM memory_links ml
    JOIN memories m ON ml.from_memory_id = m.id
    WHERE m.user_id = target_user_id

    UNION ALL
    SELECT 'Active Tasks', COUNT(*), 'tasks'
    FROM tasks WHERE user_id = target_user_id AND status NOT IN ('done', 'cancelled')

    UNION ALL
    SELECT 'Pending Reminders', COUNT(*), 'reminders'
    FROM reminders WHERE user_id = target_user_id AND status = 'pending'

    UNION ALL
    SELECT 'Upcoming Events (7 days)', COUNT(*), 'events'
    FROM events WHERE user_id = target_user_id
    AND start_time BETWEEN NOW() AND NOW() + INTERVAL '7 days'
    AND status != 'cancelled'

    UNION ALL
    SELECT 'Notes', COUNT(*), 'notes'
    FROM notes WHERE user_id = target_user_id

    UNION ALL
    SELECT 'Documents', COUNT(*), 'documents'
    FROM documents WHERE user_id = target_user_id AND status = 'completed'

    ORDER BY category, metric;
END;
$$ LANGUAGE plpgsql;

-- Function: Get memory quality metrics
CREATE OR REPLACE FUNCTION get_memory_quality_metrics()
RETURNS TABLE (
    total_memories BIGINT,
    high_salience_count BIGINT,
    frequently_accessed_count BIGINT,
    with_links_count BIGINT,
    multi_sector_count BIGINT,
    avg_salience NUMERIC,
    avg_access_count NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT AS total_memories,
        COUNT(*) FILTER (WHERE m.salience_score > 0.7)::BIGINT AS high_salience_count,
        COUNT(*) FILTER (WHERE m.access_count > 5)::BIGINT AS frequently_accessed_count,
        COUNT(DISTINCT ml.from_memory_id)::BIGINT AS with_links_count,
        COUNT(*) FILTER (WHERE sector_count > 1)::BIGINT AS multi_sector_count,
        ROUND(AVG(m.salience_score)::NUMERIC, 3) AS avg_salience,
        ROUND(AVG(m.access_count)::NUMERIC, 2) AS avg_access_count
    FROM memories m
    LEFT JOIN memory_links ml ON m.id = ml.from_memory_id
    LEFT JOIN (
        SELECT memory_id, COUNT(*) as sector_count
        FROM memory_sectors
        GROUP BY memory_id
    ) sc ON m.id = sc.memory_id
    WHERE m.is_archived = FALSE;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- MAINTENANCE FUNCTIONS
-- ============================================================================

-- Function: Archive old low-value memories
CREATE OR REPLACE FUNCTION archive_low_value_memories(
    older_than_days INTEGER DEFAULT 180,
    max_salience FLOAT DEFAULT 0.2,
    max_access_count INTEGER DEFAULT 1
)
RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER;
BEGIN
    WITH to_archive AS (
        UPDATE memories
        SET is_archived = TRUE,
            archived_at = NOW(),
            archived_reason = 'Low value: old, low salience, rarely accessed'
        WHERE is_archived = FALSE
          AND created_at < NOW() - INTERVAL '1 day' * older_than_days
          AND salience_score <= max_salience
          AND access_count <= max_access_count
        RETURNING id
    )
    SELECT COUNT(*) INTO archived_count FROM to_archive;

    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;

-- Function: Clean up orphaned records
CREATE OR REPLACE FUNCTION cleanup_orphaned_records()
RETURNS TABLE (
    table_name TEXT,
    deleted_count BIGINT
) AS $$
BEGIN
    -- Clean up memory sectors without memories
    RETURN QUERY
    WITH deleted AS (
        DELETE FROM memory_sectors ms
        WHERE NOT EXISTS (
            SELECT 1 FROM memories m WHERE m.id = ms.memory_id
        )
        RETURNING ms.id
    )
    SELECT 'memory_sectors'::TEXT, COUNT(*)::BIGINT FROM deleted;

    -- Clean up document chunks without documents
    RETURN QUERY
    WITH deleted AS (
        DELETE FROM document_chunks dc
        WHERE dc.document_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM documents d WHERE d.id = dc.document_id
          )
        RETURNING dc.id
    )
    SELECT 'document_chunks', COUNT(*) FROM deleted;

    -- Clean up file_sync without referenced items
    RETURN QUERY
    WITH deleted AS (
        DELETE FROM file_sync fs
        WHERE (fs.note_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM notes n WHERE n.id = fs.note_id))
           OR (fs.document_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM documents d WHERE d.id = fs.document_id))
        RETURNING fs.id
    )
    SELECT 'file_sync', COUNT(*) FROM deleted;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- ANALYZE TABLES FOR QUERY OPTIMIZATION
-- ============================================================================

-- Run ANALYZE to update statistics (run after initial data load)
-- Uncomment to execute on first migration
-- ANALYZE memories;
-- ANALYZE memory_sectors;
-- ANALYZE conversations;
-- ANALYZE memory_links;
-- ANALYZE tasks;
-- ANALYZE reminders;
-- ANALYZE events;
-- ANALYZE notes;
-- ANALYZE documents;

COMMENT ON MATERIALIZED VIEW daily_summary IS 'Daily activity summary - refresh with SELECT refresh_daily_summary()';
COMMENT ON MATERIALIZED VIEW memory_sector_stats IS 'Memory distribution by sector - refresh with SELECT refresh_memory_sector_stats()';
