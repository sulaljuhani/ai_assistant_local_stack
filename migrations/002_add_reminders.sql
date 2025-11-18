-- Migration 002: Reminders Table
-- AI Stack - Reminders with recurring support and notifications

CREATE TABLE IF NOT EXISTS reminders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,

    -- Content
    title TEXT NOT NULL,
    description TEXT,

    -- Timing
    remind_at TIMESTAMP NOT NULL,
    timezone TEXT DEFAULT 'UTC',

    -- Recurrence
    is_recurring BOOLEAN DEFAULT FALSE,
    recurrence_rule TEXT,  -- RRULE format (daily, weekly, monthly, etc.)
    recurrence_end_date TIMESTAMP,

    -- Status
    status TEXT DEFAULT 'pending',  -- pending, fired, completed, snoozed, cancelled
    fired_at TIMESTAMP,
    completed_at TIMESTAMP,
    snoozed_until TIMESTAMP,

    -- Notification
    notification_sent BOOLEAN DEFAULT FALSE,
    notification_channels TEXT[] DEFAULT ARRAY['system'],  -- system, email, webhook
    notification_sound TEXT DEFAULT 'default',

    -- Priority
    priority INTEGER DEFAULT 0,  -- 0=normal, 1=high, 2=urgent

    -- Metadata
    tags TEXT[],
    metadata JSONB,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_reminders_user ON reminders(user_id);
CREATE INDEX idx_reminders_category ON reminders(category_id);
CREATE INDEX idx_reminders_remind_at ON reminders(remind_at);
CREATE INDEX idx_reminders_status ON reminders(status);
CREATE INDEX idx_reminders_priority ON reminders(priority DESC);
CREATE INDEX idx_reminders_pending ON reminders(remind_at) WHERE status = 'pending';
CREATE INDEX idx_reminders_tags ON reminders USING GIN(tags);

-- Full-text search on title and description
CREATE INDEX idx_reminders_text_search ON reminders USING GIN(to_tsvector('english', title || ' ' || COALESCE(description, '')));

-- Updated_at trigger
CREATE TRIGGER update_reminders_updated_at
    BEFORE UPDATE ON reminders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Helper function: Get upcoming reminders
CREATE OR REPLACE FUNCTION get_reminders_due(minutes_ahead INTEGER DEFAULT 60)
RETURNS TABLE (
    id UUID,
    title TEXT,
    remind_at TIMESTAMP,
    priority INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT r.id, r.title, r.remind_at, r.priority
    FROM reminders r
    WHERE r.status = 'pending'
      AND r.remind_at <= NOW() + INTERVAL '1 minute' * minutes_ahead
      AND r.remind_at > NOW()
    ORDER BY r.remind_at ASC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE reminders IS 'Reminders with recurring support and notification tracking';
