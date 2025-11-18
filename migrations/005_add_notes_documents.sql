-- Migration 005: Notes and Documents Tables
-- AI Stack - Notes (Obsidian vault) and document management with chunking

CREATE TABLE IF NOT EXISTS notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,

    -- Content
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    content_type TEXT DEFAULT 'markdown',  -- markdown, plain, html

    -- File information
    file_path TEXT,  -- Relative path in vault (e.g., "daily/2025-11-18.md")
    file_hash TEXT,  -- SHA-256 hash for change detection
    file_size INTEGER,  -- Bytes

    -- Organization
    folder TEXT,  -- Parent folder (e.g., "daily", "projects")
    tags TEXT[],
    aliases TEXT[],

    -- Obsidian frontmatter
    frontmatter JSONB,  -- Parsed YAML frontmatter

    -- Linking
    links_to TEXT[],  -- Array of note titles/paths this links to
    backlinks TEXT[],  -- Array of note titles/paths that link here

    -- Embedding
    is_embedded BOOLEAN DEFAULT FALSE,
    embedded_at TIMESTAMP,
    embedding_model TEXT DEFAULT 'nomic-embed-text',

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    file_modified_at TIMESTAMP
);

-- Indexes
CREATE INDEX idx_notes_user ON notes(user_id);
CREATE INDEX idx_notes_category ON notes(category_id);
CREATE INDEX idx_notes_file_path ON notes(file_path);
CREATE INDEX idx_notes_file_hash ON notes(file_hash);
CREATE INDEX idx_notes_folder ON notes(folder);
CREATE INDEX idx_notes_tags ON notes USING GIN(tags);
CREATE INDEX idx_notes_embedded ON notes(is_embedded);
CREATE INDEX idx_notes_updated ON notes(updated_at DESC);

-- Full-text search
CREATE INDEX idx_notes_text_search ON notes USING GIN(
    to_tsvector('english', title || ' ' || content)
);

-- Updated_at trigger
CREATE TRIGGER update_notes_updated_at
    BEFORE UPDATE ON notes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Documents table (PDFs, DOCX, etc.)
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,

    -- File information
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    file_size INTEGER,
    mime_type TEXT,

    -- Content
    title TEXT,
    extracted_text TEXT,  -- Full extracted text
    page_count INTEGER,

    -- Processing status
    status TEXT DEFAULT 'pending',  -- pending, processing, completed, failed
    processed_at TIMESTAMP,
    error_message TEXT,

    -- Embedding
    is_embedded BOOLEAN DEFAULT FALSE,
    embedded_at TIMESTAMP,
    embedding_model TEXT DEFAULT 'nomic-embed-text',

    -- Metadata
    tags TEXT[],
    metadata JSONB,  -- PDF metadata, EXIF data, etc.

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for documents
CREATE INDEX idx_documents_user ON documents(user_id);
CREATE INDEX idx_documents_category ON documents(category_id);
CREATE INDEX idx_documents_file_path ON documents(file_path);
CREATE INDEX idx_documents_file_hash ON documents(file_hash);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_embedded ON documents(is_embedded);
CREATE INDEX idx_documents_tags ON documents USING GIN(tags);

-- Full-text search on documents
CREATE INDEX idx_documents_text_search ON documents USING GIN(
    to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(extracted_text, ''))
);

-- Updated_at trigger for documents
CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Document chunks table (for RAG)
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    note_id UUID REFERENCES notes(id) ON DELETE CASCADE,

    -- Chunk information
    chunk_index INTEGER NOT NULL,  -- 0-based index
    chunk_text TEXT NOT NULL,
    chunk_size INTEGER,  -- Characters

    -- Context
    page_number INTEGER,  -- For PDFs
    section_title TEXT,
    preceding_context TEXT,  -- Text before this chunk
    following_context TEXT,  -- Text after this chunk

    -- Embedding
    qdrant_point_id TEXT,  -- ID in Qdrant vector DB
    embedding_model TEXT DEFAULT 'nomic-embed-text',

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for chunks
CREATE INDEX idx_chunks_document ON document_chunks(document_id);
CREATE INDEX idx_chunks_note ON document_chunks(note_id);
CREATE INDEX idx_chunks_index ON document_chunks(chunk_index);
CREATE INDEX idx_chunks_qdrant ON document_chunks(qdrant_point_id);

-- Unique constraint: one chunk per document/note at each index
CREATE UNIQUE INDEX idx_chunks_document_unique ON document_chunks(document_id, chunk_index)
    WHERE document_id IS NOT NULL;
CREATE UNIQUE INDEX idx_chunks_note_unique ON document_chunks(note_id, chunk_index)
    WHERE note_id IS NOT NULL;

-- File sync tracking table
CREATE TABLE IF NOT EXISTS file_sync (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- File information
    file_path TEXT NOT NULL,
    file_type TEXT NOT NULL,  -- note, document
    file_hash TEXT NOT NULL,

    -- Sync status
    last_synced_at TIMESTAMP DEFAULT NOW(),
    sync_status TEXT DEFAULT 'synced',  -- synced, pending, failed
    error_message TEXT,

    -- References
    note_id UUID REFERENCES notes(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,

    UNIQUE(file_path)
);

CREATE INDEX idx_file_sync_user ON file_sync(user_id);
CREATE INDEX idx_file_sync_path ON file_sync(file_path);
CREATE INDEX idx_file_sync_hash ON file_sync(file_hash);
CREATE INDEX idx_file_sync_status ON file_sync(sync_status);

COMMENT ON TABLE notes IS 'Markdown notes from Obsidian vault with linking and embedding support';
COMMENT ON TABLE documents IS 'Binary documents (PDFs, DOCX) with text extraction';
COMMENT ON TABLE document_chunks IS 'Text chunks for RAG vector search';
COMMENT ON TABLE file_sync IS 'Track file changes for vault watcher';
