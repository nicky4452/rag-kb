"""
retriever.py — Query Pinecone for top-k chunks relevant to the user's question,
               filtered strictly to the active user + document.
"""
from __future__ import annotations

import streamlit as st
from ingestor import get_embedder, get_pinecone_index

TOP_K = 5


def retrieve_chunks(query: str, user_id: str, doc_name: str, top_k: int = TOP_K) -> list[dict]:
    """
    Embed query, search Pinecone with metadata filter,
    return list of dicts: {text, score, chunk_index}.
    """
    embedder = get_embedder()
    query_vec = embedder.encode([query], show_progress_bar=False)[0].tolist()

    index = get_pinecone_index()

    results = index.query(
        vector=query_vec,
        top_k=top_k,
        include_metadata=True,
        filter={
            "user_id": {"$eq": user_id},
            "doc_name": {"$eq": doc_name},
        },
    )

    chunks = []
    for match in results.get("matches", []):
        meta = match.get("metadata", {})
        chunks.append(
            {
                "text": meta.get("text", ""),
                "score": float(match.get("score", 0)),
                "chunk_index": meta.get("chunk_index", -1),
            }
        )

    # Sort by chunk order for coherent context
    chunks.sort(key=lambda c: c["chunk_index"])
    return chunks
