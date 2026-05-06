"""
ingestor.py — Reads uploaded file, chunks it, embeds with HuggingFace,
               upserts vectors into Pinecone, and records in Supabase.
"""
from __future__ import annotations

import io
import re
import streamlit as st
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
from db import get_supabase, upsert_document

# ── Config ────────────────────────────────────────────────────────────────────
CHUNK_SIZE = 512       # characters
CHUNK_OVERLAP = 64
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
PINECONE_DIM = 384
BATCH_SIZE = 96


# ── Cached resources ──────────────────────────────────────────────────────────

@st.cache_resource
def get_embedder() -> SentenceTransformer:
    return SentenceTransformer(EMBED_MODEL)


@st.cache_resource
def get_pinecone_index():
    pc = Pinecone(api_key=st.secrets["pinecone"]["api_key"])
    index_name = st.secrets["pinecone"]["index_name"]

    existing = [i.name for i in pc.list_indexes()]
    if index_name not in existing:
        pc.create_index(
            name=index_name,
            dimension=PINECONE_DIM,
            metric="cosine",
            spec=ServerlessSpec(
                cloud=st.secrets["pinecone"].get("cloud", "aws"),
                region=st.secrets["pinecone"].get("region", "us-east-1"),
            ),
        )
    return pc.Index(index_name)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_text(file) -> str:
    """Extract raw text from PDF or TXT upload."""
    name: str = file.name.lower()
    raw: bytes = file.read()

    if name.endswith(".pdf"):
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(raw))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)

    # Fallback: treat as UTF-8 text
    return raw.decode("utf-8", errors="replace")


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Simple sliding-window character chunker."""
    text = re.sub(r"\s+", " ", text).strip()
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap
    return [c for c in chunks if len(c.strip()) > 20]


def _safe_vector_id(user_id: str, doc_name: str, idx: int) -> str:
    safe_user = re.sub(r"[^a-zA-Z0-9_-]", "_", user_id)
    safe_doc = re.sub(r"[^a-zA-Z0-9_-]", "_", doc_name)
    return f"{safe_user}__{safe_doc}__{idx}"


# ── Public API ────────────────────────────────────────────────────────────────

def ingest_file(file, user_id: str) -> int:
    """
    Full pipeline: extract → chunk → embed → upsert Pinecone → save to Supabase.
    Returns the number of chunks created.
    """
    doc_name = file.name

    # 1. Extract
    text = _extract_text(file)
    if not text.strip():
        raise ValueError("No extractable text found in the document.")

    # 2. Chunk
    chunks = _chunk_text(text)
    if not chunks:
        raise ValueError("Document produced no valid chunks.")

    # 3. Embed
    embedder = get_embedder()
    embeddings = embedder.encode(chunks, batch_size=32, show_progress_bar=False).tolist()

    # 4. Upsert into Pinecone in batches
    index = get_pinecone_index()
    vectors = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        vec_id = _safe_vector_id(user_id, doc_name, i)
        vectors.append(
            {
                "id": vec_id,
                "values": embedding,
                "metadata": {
                    "user_id": user_id,
                    "doc_name": doc_name,
                    "chunk_index": i,
                    "text": chunk,
                },
            }
        )

    for i in range(0, len(vectors), BATCH_SIZE):
        index.upsert(vectors=vectors[i : i + BATCH_SIZE])

    # 5. Record in Supabase
    upsert_document(user_id, doc_name, len(chunks))

    return len(chunks)
