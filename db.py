"""
db.py — Supabase client + all DB helpers.
user_id is stored as plain email (text), no UUID, no RLS.
"""
import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timezone


@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["service_role_key"]
    return create_client(url, key)


# ── User ──────────────────────────────────────────────────────────────────────

def ensure_user(email: str) -> None:
    """No-op here since we use email directly — kept for future extensibility."""
    pass


# ── Documents ─────────────────────────────────────────────────────────────────

def upsert_document(user_id: str, name: str, chunk_count: int) -> None:
    sb = get_supabase()
    sb.table("rag_documents").upsert(
        {
            "user_id": user_id,
            "name": name,
            "chunk_count": chunk_count,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="user_id,name",
    ).execute()


def get_user_docs(user_id: str) -> list[dict]:
    sb = get_supabase()
    res = (
        sb.table("rag_documents")
        .select("id, name, chunk_count, uploaded_at")
        .eq("user_id", user_id)
        .order("uploaded_at", desc=True)
        .execute()
    )
    return res.data or []


def delete_document(user_id: str, name: str) -> None:
    """Delete doc record + all messages for that doc."""
    sb = get_supabase()
    sb.table("rag_documents").delete().eq("user_id", user_id).eq("name", name).execute()
    sb.table("rag_messages").delete().eq("user_id", user_id).eq("doc_name", name).execute()


# ── Messages ──────────────────────────────────────────────────────────────────

def save_message(user_id: str, doc_name: str, role: str, content: str) -> None:
    sb = get_supabase()
    sb.table("rag_messages").insert(
        {
            "user_id": user_id,
            "doc_name": doc_name,
            "role": role,
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()


def get_messages(user_id: str, doc_name: str) -> list[dict]:
    sb = get_supabase()
    res = (
        sb.table("rag_messages")
        .select("role, content")
        .eq("user_id", user_id)
        .eq("doc_name", doc_name)
        .order("created_at", desc=False)
        .execute()
    )
    return res.data or []
