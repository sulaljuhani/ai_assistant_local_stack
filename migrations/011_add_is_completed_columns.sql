-- Migration 011: Add is_completed boolean columns to reminders and tasks
-- Fixes compatibility between code expectations and schema

-- Add is_completed column to reminders table
ALTER TABLE reminders
ADD COLUMN IF NOT EXISTS is_completed BOOLEAN DEFAULT FALSE;

-- Populate is_completed based on existing status
UPDATE reminders
SET is_completed = (status = 'completed')
WHERE is_completed IS NULL OR is_completed != (status = 'completed');

-- Create trigger to keep is_completed in sync with status for reminders
CREATE OR REPLACE FUNCTION sync_reminder_is_completed()
RETURNS TRIGGER AS $$
BEGIN
    -- When status changes to/from completed, update is_completed
    IF NEW.status = 'completed' THEN
        NEW.is_completed = TRUE;
        IF NEW.completed_at IS NULL THEN
            NEW.completed_at = NOW();
        END IF;
    ELSE
        NEW.is_completed = FALSE;
    END IF;

    -- When is_completed is set directly, update status
    IF NEW.is_completed = TRUE AND OLD.is_completed = FALSE THEN
        NEW.status = 'completed';
        IF NEW.completed_at IS NULL THEN
            NEW.completed_at = NOW();
        END IF;
    ELSIF NEW.is_completed = FALSE AND OLD.is_completed = TRUE THEN
        -- Reset to pending when unmarked as completed
        IF NEW.status = 'completed' THEN
            NEW.status = 'pending';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS sync_reminders_is_completed ON reminders;
CREATE TRIGGER sync_reminders_is_completed
    BEFORE UPDATE ON reminders
    FOR EACH ROW
    EXECUTE FUNCTION sync_reminder_is_completed();

-- Add index for is_completed queries
CREATE INDEX IF NOT EXISTS idx_reminders_is_completed ON reminders(is_completed);
CREATE INDEX IF NOT EXISTS idx_reminders_not_completed_remind_at ON reminders(remind_at) WHERE is_completed = FALSE;

COMMENT ON COLUMN reminders.is_completed IS 'Boolean flag synced with status field - TRUE when status=completed';

-- Add type column to categories table
ALTER TABLE categories
ADD COLUMN IF NOT EXISTS type TEXT DEFAULT 'general';

-- Update existing categories based on usage context
UPDATE categories SET type = 'general' WHERE type IS NULL;

-- Add index for type queries
CREATE INDEX IF NOT EXISTS idx_categories_type ON categories(type);

COMMENT ON COLUMN categories.type IS 'Category type: task, reminder, event, or general';
