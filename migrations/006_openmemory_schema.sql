-- Migration 006: OpenMemory Schema
-- AI Stack - Long-term memory system with multi-sector classification
-- Embedding model: nomic-embed-text (768 dimensions)

-- ============================================================================
-- MEMORIES TABLE - Core memory storage
-- ============================================================================
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Content
    content TEXT NOT NULL,
    content_summary TEXT,  -- Optional LLM-generated summary

    -- Classification
    memory_type TEXT DEFAULT 'explicit',  -- explicit, implicit, inferred
    source TEXT DEFAULT 'chat',  -- chat, import, api, system, manual

    -- Source tracking
    source_reference TEXT,  -- conversation_id, import_file, etc.
    source_metadata JSONB,  -- Additional context

    -- Importance scoring
    salience_score FLOAT DEFAULT 0.5,  -- 0.0 (trivial) to 1.0 (critical)
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP,

    -- Temporal context
    temporal_context TEXT,  -- "morning", "2024-05", "before project X"
    event_timestamp TIMESTAMP,  -- When the remembered event occurred

    -- Enrichment
    entities JSONB,  -- Extracted entities: [{type: "person", value: "John"}, ...]
    sentiment FLOAT,  -- -1.0 (negative) to 1.0 (positive)
    topics TEXT[],  -- Extracted topics

    -- Lifecycle
    is_archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMP,
    archived_reason TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_salience CHECK (salience_score >= 0.0 AND salience_score <= 1.0),
    CONSTRAINT valid_sentiment CHECK (sentiment IS NULL OR (sentiment >= -1.0 AND sentiment <= 1.0))
);

-- Indexes for memories
CREATE INDEX idx_memories_user ON memories(user_id);
CREATE INDEX idx_memories_source ON memories(source);
CREATE INDEX idx_memories_source_ref ON memories(source_reference);
CREATE INDEX idx_memories_salience ON memories(salience_score DESC);
CREATE INDEX idx_memories_access_count ON memories(access_count DESC);
CREATE INDEX idx_memories_created ON memories(created_at DESC);
CREATE INDEX idx_memories_accessed ON memories(last_accessed_at DESC NULLS LAST);
CREATE INDEX idx_memories_topics ON memories USING GIN(topics);
CREATE INDEX idx_memories_archived ON memories(is_archived) WHERE is_archived = FALSE;
CREATE INDEX idx_memories_temporal ON memories(event_timestamp DESC NULLS LAST);

-- Full-text search on memory content
CREATE INDEX idx_memories_text_search ON memories USING GIN(
    to_tsvector('english', content || ' ' || COALESCE(content_summary, ''))
);

-- Updated_at trigger
CREATE TRIGGER update_memories_updated_at
    BEFORE UPDATE ON memories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger: Increment access_count on reads
CREATE OR REPLACE FUNCTION increment_memory_access()
RETURNS TRIGGER AS $$
BEGIN
    NEW.access_count = OLD.access_count + 1;
    NEW.last_accessed_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- MEMORY SECTORS - Multi-dimensional classification
-- ============================================================================
CREATE TABLE IF NOT EXISTS memory_sectors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,

    -- Sector classification
    sector TEXT NOT NULL,  -- semantic, episodic, procedural, emotional, reflective
    confidence FLOAT DEFAULT 1.0,  -- Classification confidence 0.0-1.0

    -- Vector embedding reference
    qdrant_point_id TEXT,  -- Format: "{memory_id}_{sector}"
    embedding_dimensions INTEGER DEFAULT 768,  -- nomic-embed-text
    embedding_model TEXT DEFAULT 'nomic-embed-text',

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_sector CHECK (sector IN ('semantic', 'episodic', 'procedural', 'emotional', 'reflective')),
    CONSTRAINT valid_confidence CHECK (confidence >= 0.0 AND confidence <= 1.0),
    UNIQUE(memory_id, sector)
);

-- Indexes for sectors
CREATE INDEX idx_sectors_memory ON memory_sectors(memory_id);
CREATE INDEX idx_sectors_sector ON memory_sectors(sector);
CREATE INDEX idx_sectors_confidence ON memory_sectors(confidence DESC);
CREATE INDEX idx_sectors_qdrant ON memory_sectors(qdrant_point_id);

-- ============================================================================
-- CONVERSATIONS - Group related memories
-- ============================================================================
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Identification
    title TEXT,
    source TEXT NOT NULL,  -- anythingllm, chatgpt, claude, gemini, api
    external_id TEXT,  -- Original conversation ID from source system

    -- Timing
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    duration_minutes INTEGER,

    -- Content
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER,  -- Approximate token count

    -- Summary
    summary TEXT,  -- LLM-generated conversation summary
    key_topics TEXT[],
    main_entities JSONB,  -- Important people, places, things mentioned

    -- Metadata
    metadata JSONB,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for conversations
CREATE INDEX idx_conversations_user ON conversations(user_id);
CREATE INDEX idx_conversations_source ON conversations(source);
CREATE INDEX idx_conversations_external_id ON conversations(external_id);
CREATE INDEX idx_conversations_started ON conversations(started_at DESC);
CREATE INDEX idx_conversations_topics ON conversations USING GIN(key_topics);

-- Updated_at trigger
CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add conversation reference to memories
ALTER TABLE memories ADD COLUMN IF NOT EXISTS conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_memories_conversation ON memories(conversation_id);

-- ============================================================================
-- MEMORY LINKS - Relationships between memories
-- ============================================================================
CREATE TABLE IF NOT EXISTS memory_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    to_memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,

    -- Link properties
    link_type TEXT NOT NULL,  -- similar, contradicts, elaborates, caused_by, related_to, temporal_sequence
    strength FLOAT DEFAULT 0.5,  -- 0.0 (weak) to 1.0 (strong)

    -- How the link was created
    created_by TEXT DEFAULT 'system',  -- system, user, llm
    confidence FLOAT DEFAULT 0.8,

    -- Metadata
    metadata JSONB,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_link_strength CHECK (strength >= 0.0 AND strength <= 1.0),
    CONSTRAINT valid_link_confidence CHECK (confidence >= 0.0 AND confidence <= 1.0),
    CONSTRAINT no_self_link CHECK (from_memory_id != to_memory_id),
    UNIQUE(from_memory_id, to_memory_id, link_type)
);

-- Indexes for links
CREATE INDEX idx_links_from ON memory_links(from_memory_id);
CREATE INDEX idx_links_to ON memory_links(to_memory_id);
CREATE INDEX idx_links_type ON memory_links(link_type);
CREATE INDEX idx_links_strength ON memory_links(strength DESC);

-- Bidirectional link index
CREATE INDEX idx_links_both ON memory_links(from_memory_id, to_memory_id);
CREATE INDEX idx_links_both_reverse ON memory_links(to_memory_id, from_memory_id);

-- ============================================================================
-- IMPORTED CHATS - Track what's been imported
-- ============================================================================
CREATE TABLE IF NOT EXISTS imported_chats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Source identification
    source TEXT NOT NULL,  -- chatgpt, claude, gemini, other
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_hash TEXT NOT NULL,  -- SHA-256 to prevent duplicates

    -- Import results
    conversations_count INTEGER DEFAULT 0,
    messages_count INTEGER DEFAULT 0,
    memories_created INTEGER DEFAULT 0,

    -- Processing
    import_status TEXT DEFAULT 'completed',  -- completed, failed, partial
    error_message TEXT,
    processing_time_seconds INTEGER,

    -- Timestamps
    imported_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(user_id, file_hash)
);

-- Indexes for imported chats
CREATE INDEX idx_imports_user ON imported_chats(user_id);
CREATE INDEX idx_imports_source ON imported_chats(source);
CREATE INDEX idx_imports_hash ON imported_chats(file_hash);
CREATE INDEX idx_imports_status ON imported_chats(import_status);
CREATE INDEX idx_imports_date ON imported_chats(imported_at DESC);

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function: Search memories by content similarity (to be called after Qdrant search)
CREATE OR REPLACE FUNCTION search_memories_by_ids(
    memory_ids UUID[],
    sector_filter TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    salience_score FLOAT,
    access_count INTEGER,
    sectors TEXT[],
    created_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        m.content,
        m.salience_score,
        m.access_count,
        ARRAY_AGG(ms.sector) AS sectors,
        m.created_at
    FROM memories m
    JOIN memory_sectors ms ON m.id = ms.memory_id
    WHERE m.id = ANY(memory_ids)
      AND m.is_archived = FALSE
      AND (sector_filter IS NULL OR ms.sector = sector_filter)
    GROUP BY m.id, m.content, m.salience_score, m.access_count, m.created_at
    ORDER BY m.salience_score DESC, m.access_count DESC;
END;
$$ LANGUAGE plpgsql;

-- Function: Get conversation context
CREATE OR REPLACE FUNCTION get_conversation_context(conv_id UUID)
RETURNS TABLE (
    memory_content TEXT,
    sector TEXT,
    created_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.content,
        ms.sector,
        m.created_at
    FROM memories m
    JOIN memory_sectors ms ON m.id = ms.memory_id
    WHERE m.conversation_id = conv_id
      AND m.is_archived = FALSE
    ORDER BY m.created_at ASC;
END;
$$ LANGUAGE plpgsql;

-- Function: Get related memories via links
CREATE OR REPLACE FUNCTION get_related_memories(memory_id UUID, max_depth INTEGER DEFAULT 2)
RETURNS TABLE (
    related_memory_id UUID,
    content TEXT,
    link_type TEXT,
    link_strength FLOAT,
    depth INTEGER
) AS $$
WITH RECURSIVE memory_graph AS (
    -- Base case: direct links
    SELECT
        ml.to_memory_id AS related_memory_id,
        ml.link_type,
        ml.strength AS link_strength,
        1 AS depth
    FROM memory_links ml
    WHERE ml.from_memory_id = memory_id

    UNION

    -- Recursive case: follow links up to max_depth
    SELECT
        ml.to_memory_id,
        ml.link_type,
        ml.strength,
        mg.depth + 1
    FROM memory_graph mg
    JOIN memory_links ml ON mg.related_memory_id = ml.from_memory_id
    WHERE mg.depth < max_depth
)
SELECT DISTINCT
    mg.related_memory_id,
    m.content,
    mg.link_type,
    mg.link_strength,
    mg.depth
FROM memory_graph mg
JOIN memories m ON mg.related_memory_id = m.id
WHERE m.is_archived = FALSE
ORDER BY mg.depth ASC, mg.link_strength DESC;
$$ LANGUAGE plpgsql;

-- Function: Get memory statistics
CREATE OR REPLACE FUNCTION get_memory_stats()
RETURNS TABLE (
    total_memories BIGINT,
    by_source JSONB,
    by_sector JSONB,
    avg_salience FLOAT,
    total_conversations BIGINT,
    total_links BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT AS total_memories,
        jsonb_object_agg(m.source, cnt) AS by_source,
        jsonb_object_agg(ms.sector, sector_cnt) AS by_sector,
        AVG(m.salience_score)::FLOAT AS avg_salience,
        (SELECT COUNT(*)::BIGINT FROM conversations) AS total_conversations,
        (SELECT COUNT(*)::BIGINT FROM memory_links) AS total_links
    FROM (
        SELECT source, COUNT(*) as cnt
        FROM memories
        WHERE is_archived = FALSE
        GROUP BY source
    ) m
    CROSS JOIN (
        SELECT ms.sector, COUNT(*) as sector_cnt
        FROM memories m
        JOIN memory_sectors ms ON m.id = ms.memory_id
        WHERE m.is_archived = FALSE
        GROUP BY ms.sector
    ) ms
    GROUP BY m.source, m.cnt, ms.sector, ms.sector_cnt;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE memories IS 'Core memory storage with salience scoring and multi-source support';
COMMENT ON TABLE memory_sectors IS 'Multi-dimensional memory classification (semantic, episodic, procedural, emotional, reflective)';
COMMENT ON TABLE conversations IS 'Conversation groupings for organizing related memories';
COMMENT ON TABLE memory_links IS 'Relationships and connections between memories';
COMMENT ON TABLE imported_chats IS 'Track imported chat history to prevent duplicates';

COMMENT ON COLUMN memories.salience_score IS 'Importance score 0.0-1.0, higher = more important';
COMMENT ON COLUMN memories.access_count IS 'Number of times this memory has been retrieved';
COMMENT ON COLUMN memory_sectors.sector IS 'semantic=facts, episodic=events, procedural=how-tos, emotional=preferences, reflective=insights';
COMMENT ON COLUMN memory_links.link_type IS 'Relationship type: similar, contradicts, elaborates, caused_by, related_to, temporal_sequence';
