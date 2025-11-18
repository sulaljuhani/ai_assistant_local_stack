-- Migration 004: Events Table
-- AI Stack - Calendar events with Google Calendar sync support

CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,

    -- Content
    title TEXT NOT NULL,
    description TEXT,
    location TEXT,
    url TEXT,

    -- Timing
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    timezone TEXT DEFAULT 'UTC',
    is_all_day BOOLEAN DEFAULT FALSE,

    -- Recurrence
    is_recurring BOOLEAN DEFAULT FALSE,
    recurrence_rule TEXT,  -- RRULE format
    recurrence_end_date TIMESTAMP,
    recurrence_parent_id UUID REFERENCES events(id) ON DELETE CASCADE,

    -- Google Calendar integration
    google_calendar_id TEXT,  -- Which calendar (primary, work, etc.)
    google_event_id TEXT UNIQUE,
    google_sync_at TIMESTAMP,
    google_sync_token TEXT,

    -- Attendees
    attendees JSONB,  -- [{email: "...", name: "...", status: "accepted"}, ...]
    organizer TEXT,

    -- Reminders
    reminders INTEGER[] DEFAULT ARRAY[15],  -- Minutes before event [15, 60, 1440]

    -- Status
    status TEXT DEFAULT 'confirmed',  -- confirmed, tentative, cancelled

    -- Metadata
    tags TEXT[],
    metadata JSONB,
    conference_link TEXT,  -- Zoom, Meet, etc.

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_events_user ON events(user_id);
CREATE INDEX idx_events_category ON events(category_id);
CREATE INDEX idx_events_start_time ON events(start_time);
CREATE INDEX idx_events_end_time ON events(end_time);
CREATE INDEX idx_events_google_id ON events(google_event_id);
CREATE INDEX idx_events_google_calendar ON events(google_calendar_id);
CREATE INDEX idx_events_parent ON events(recurrence_parent_id);
CREATE INDEX idx_events_tags ON events USING GIN(tags);
CREATE INDEX idx_events_status ON events(status);

-- Composite index for time-range queries
CREATE INDEX idx_events_time_range ON events(start_time, end_time);

-- Full-text search
CREATE INDEX idx_events_text_search ON events USING GIN(
    to_tsvector('english', title || ' ' || COALESCE(description, '') || ' ' || COALESCE(location, ''))
);

-- Updated_at trigger
CREATE TRIGGER update_events_updated_at
    BEFORE UPDATE ON events
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Constraint: end_time must be after start_time
ALTER TABLE events ADD CONSTRAINT check_event_times
    CHECK (end_time > start_time);

-- Helper function: Get events in time range
CREATE OR REPLACE FUNCTION get_events_in_range(
    start_range TIMESTAMP,
    end_range TIMESTAMP
)
RETURNS TABLE (
    id UUID,
    title TEXT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    location TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT e.id, e.title, e.start_time, e.end_time, e.location
    FROM events e
    WHERE e.status != 'cancelled'
      AND e.start_time < end_range
      AND e.end_time > start_range
    ORDER BY e.start_time ASC;
END;
$$ LANGUAGE plpgsql;

-- Helper function: Get today's events
CREATE OR REPLACE FUNCTION get_events_today()
RETURNS TABLE (
    id UUID,
    title TEXT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    location TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT e.id, e.title, e.start_time, e.end_time, e.location
    FROM events e
    WHERE e.status != 'cancelled'
      AND DATE(e.start_time) = CURRENT_DATE
    ORDER BY e.start_time ASC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE events IS 'Calendar events with Google Calendar sync support';
