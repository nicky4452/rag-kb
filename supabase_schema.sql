-- ============================================================
-- RAG Knowledge Base — Supabase schema
-- Run this in: Supabase Dashboard → SQL Editor
-- No RLS, no UUID — user_id is stored as plain email (text)
-- ============================================================

-- Documents index
CREATE TABLE IF NOT EXISTS rag_documents (
    id          bigserial PRIMARY KEY,
    user_id     text        NOT NULL,           -- email address
    name        text        NOT NULL,           -- original filename
    chunk_count integer     NOT NULL DEFAULT 0,
    uploaded_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT rag_documents_user_doc_unique UNIQUE (user_id, name)
);

-- Per-document chat history
CREATE TABLE IF NOT EXISTS rag_messages (
    id         bigserial PRIMARY KEY,
    user_id    text        NOT NULL,
    doc_name   text        NOT NULL,
    role       text        NOT NULL CHECK (role IN ('user', 'assistant')),
    content    text        NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Indexes for fast lookup
CREATE INDEX IF NOT EXISTS idx_rag_documents_user  ON rag_documents (user_id);
CREATE INDEX IF NOT EXISTS idx_rag_messages_lookup ON rag_messages  (user_id, doc_name, created_at);
