-- Migration 003: Tasks Table
-- AI Stack - Task management with Todoist sync support

CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,

    -- Content
    title TEXT NOT NULL,
    description TEXT,
    notes TEXT,

    -- Status
    status TEXT DEFAULT 'todo',  -- todo, in_progress, waiting, done, cancelled
    completed_at TIMESTAMP,

    -- Timing
    due_date TIMESTAMP,
    start_date TIMESTAMP,
    duration_minutes INTEGER,  -- Estimated duration

    -- Priority
    priority INTEGER DEFAULT 0,  -- 0=none, 1=low, 2=medium, 3=high, 4=urgent

    -- Recurrence (for recurring tasks)
    is_recurring BOOLEAN DEFAULT FALSE,
    recurrence_rule TEXT,  -- RRULE format
    recurrence_parent_id UUID REFERENCES tasks(id) ON DELETE CASCADE,

    -- Todoist integration
    todoist_id TEXT UNIQUE,
    todoist_project_id TEXT,
    todoist_section_id TEXT,
    todoist_parent_id TEXT,
    todoist_order INTEGER,
    todoist_sync_at TIMESTAMP,

    -- Dependencies
    depends_on UUID[] DEFAULT ARRAY[]::UUID[],  -- Array of task IDs this depends on
    blocks UUID[] DEFAULT ARRAY[]::UUID[],       -- Array of task IDs this blocks

    -- Organization
    tags TEXT[],
    labels TEXT[],
    project TEXT,

    -- Metadata
    metadata JSONB,
    checklist JSONB,  -- Array of subtasks: [{text: "...", done: false}, ...]

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_tasks_user ON tasks(user_id);
CREATE INDEX idx_tasks_category ON tasks(category_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_due_date ON tasks(due_date);
CREATE INDEX idx_tasks_priority ON tasks(priority DESC);
CREATE INDEX idx_tasks_todoist_id ON tasks(todoist_id);
CREATE INDEX idx_tasks_parent ON tasks(recurrence_parent_id);
CREATE INDEX idx_tasks_tags ON tasks USING GIN(tags);
CREATE INDEX idx_tasks_labels ON tasks USING GIN(labels);

-- Full-text search
CREATE INDEX idx_tasks_text_search ON tasks USING GIN(
    to_tsvector('english', title || ' ' || COALESCE(description, '') || ' ' || COALESCE(notes, ''))
);

-- Composite indexes for common queries
CREATE INDEX idx_tasks_status_due ON tasks(status, due_date) WHERE status != 'done' AND status != 'cancelled';
CREATE INDEX idx_tasks_user_status ON tasks(user_id, status);

-- Updated_at trigger
CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger: Auto-set completed_at when status changes to done
CREATE OR REPLACE FUNCTION set_task_completed_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'done' AND OLD.status != 'done' THEN
        NEW.completed_at = NOW();
    ELSIF NEW.status != 'done' THEN
        NEW.completed_at = NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER task_status_completed
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    WHEN (OLD.status IS DISTINCT FROM NEW.status)
    EXECUTE FUNCTION set_task_completed_at();

-- Helper function: Get tasks due soon
CREATE OR REPLACE FUNCTION get_tasks_due_soon(days_ahead INTEGER DEFAULT 7)
RETURNS TABLE (
    id UUID,
    title TEXT,
    due_date TIMESTAMP,
    priority INTEGER,
    status TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT t.id, t.title, t.due_date, t.priority, t.status
    FROM tasks t
    WHERE t.status NOT IN ('done', 'cancelled')
      AND t.due_date IS NOT NULL
      AND t.due_date <= NOW() + INTERVAL '1 day' * days_ahead
    ORDER BY t.due_date ASC, t.priority DESC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE tasks IS 'Task management with Todoist sync support and dependencies';
