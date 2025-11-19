-- ==============================================================================
-- Migration 006: Memory System Tables
-- ==============================================================================
-- Creates tables for:
-- - conversations: Conversation grouping and source tracking
-- - memories: Chat turn storage with salience scoring
-- - memory_sectors: Multi-dimensional memory classification
-- - memory_links: Relationships between memories
-- - imported_chats: Import deduplication tracking
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- Conversations Table
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    title TEXT NOT NULL DEFAULT 'Untitled Conversation',
    source TEXT NOT NULL DEFAULT 'chat', -- chat, chatgpt, claude, gemini, anythingllm
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_conversations_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_source ON conversations(source);
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at DESC);

-- ------------------------------------------------------------------------------
-- Memories Table
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS memories (
    id SERIAL PRIMARY KEY,
    conversation_id UUID,
    user_id UUID NOT NULL,
    role TEXT NOT NULL, -- user, assistant, system
    content TEXT NOT NULL,
    summary TEXT,
    salience_score FLOAT NOT NULL DEFAULT 0.5 CHECK (salience_score >= 0.0 AND salience_score <= 1.0),
    source TEXT NOT NULL DEFAULT 'chat',
    access_count INTEGER NOT NULL DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_memories_conversation FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    CONSTRAINT fk_memories_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_memories_conversation_id ON memories(conversation_id);
CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_salience_score ON memories(salience_score DESC);
CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_last_accessed_at ON memories(last_accessed_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_source ON memories(source);

-- Full-text search index on content
CREATE INDEX IF NOT EXISTS idx_memories_content_fts ON memories USING gin(to_tsvector('english', content));

-- ------------------------------------------------------------------------------
-- Memory Sectors Table
-- Multi-dimensional classification for flexible retrieval
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS memory_sectors (
    id SERIAL PRIMARY KEY,
    memory_id INTEGER NOT NULL,
    sector TEXT NOT NULL, -- semantic, episodic, procedural, emotional, reflective
    weight FLOAT NOT NULL DEFAULT 1.0 CHECK (weight >= 0.0 AND weight <= 1.0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_memory_sectors_memory FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE,
    CONSTRAINT chk_valid_sector CHECK (sector IN ('semantic', 'episodic', 'procedural', 'emotional', 'reflective')),
    CONSTRAINT uq_memory_sector UNIQUE (memory_id, sector)
);

CREATE INDEX IF NOT EXISTS idx_memory_sectors_memory_id ON memory_sectors(memory_id);
CREATE INDEX IF NOT EXISTS idx_memory_sectors_sector ON memory_sectors(sector);

-- ------------------------------------------------------------------------------
-- Memory Links Table
-- Relationships and connections between memories
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS memory_links (
    id SERIAL PRIMARY KEY,
    source_memory_id INTEGER NOT NULL,
    target_memory_id INTEGER NOT NULL,
    link_type TEXT NOT NULL, -- reference, continuation, related, contradicts, elaborates
    strength FLOAT NOT NULL DEFAULT 0.5 CHECK (strength >= 0.0 AND strength <= 1.0),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_memory_links_source FOREIGN KEY (source_memory_id) REFERENCES memories(id) ON DELETE CASCADE,
    CONSTRAINT fk_memory_links_target FOREIGN KEY (target_memory_id) REFERENCES memories(id) ON DELETE CASCADE,
    CONSTRAINT chk_no_self_link CHECK (source_memory_id != target_memory_id),
    CONSTRAINT uq_memory_link UNIQUE (source_memory_id, target_memory_id, link_type)
);

CREATE INDEX IF NOT EXISTS idx_memory_links_source ON memory_links(source_memory_id);
CREATE INDEX IF NOT EXISTS idx_memory_links_target ON memory_links(target_memory_id);
CREATE INDEX IF NOT EXISTS idx_memory_links_type ON memory_links(link_type);

-- ------------------------------------------------------------------------------
-- Imported Chats Table
-- Track imported chat exports for deduplication
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS imported_chats (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    source TEXT NOT NULL, -- claude, chatgpt, gemini
    file_hash TEXT NOT NULL, -- SHA256 of file content
    filename TEXT,
    conversations_count INTEGER NOT NULL DEFAULT 0,
    messages_count INTEGER NOT NULL DEFAULT 0,
    import_status TEXT NOT NULL DEFAULT 'pending', -- pending, processing, completed, failed
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_imported_chats_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT uq_imported_file UNIQUE (user_id, file_hash)
);

CREATE INDEX IF NOT EXISTS idx_imported_chats_user_id ON imported_chats(user_id);
CREATE INDEX IF NOT EXISTS idx_imported_chats_source ON imported_chats(source);
CREATE INDEX IF NOT EXISTS idx_imported_chats_status ON imported_chats(import_status);
CREATE INDEX IF NOT EXISTS idx_imported_chats_imported_at ON imported_chats(imported_at DESC);

-- ==============================================================================
-- Helper Functions
-- ==============================================================================

-- Function to update conversation updated_at timestamp
CREATE OR REPLACE FUNCTION update_conversation_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE conversations
    SET updated_at = NOW()
    WHERE id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update conversation timestamp when memory is added
DROP TRIGGER IF EXISTS trg_update_conversation_timestamp ON memories;
CREATE TRIGGER trg_update_conversation_timestamp
    AFTER INSERT ON memories
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_timestamp();

-- ==============================================================================
-- Success Notification
-- ==============================================================================
DO $$
BEGIN
    RAISE NOTICE 'Migration 006 completed: Memory system tables created';
    RAISE NOTICE '  - conversations';
    RAISE NOTICE '  - memories';
    RAISE NOTICE '  - memory_sectors';
    RAISE NOTICE '  - memory_links';
    RAISE NOTICE '  - imported_chats';
END $$;
