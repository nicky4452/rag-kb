"""
generator.py — Build a grounded prompt from retrieved chunks and call Groq LLM.
               Answers only using the provided context; cites uncertainty when needed.
"""
from __future__ import annotations

import streamlit as st
from groq import Groq

MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 1024
TEMPERATURE = 0.2

SYSTEM_PROMPT = """You are a precise, helpful research assistant.
Answer the user's question using ONLY the context chunks provided below.
If the answer cannot be found in the context, say so clearly — do not fabricate.
Be concise but thorough. Use markdown formatting (bullet lists, bold headings) where helpful.
Never mention "chunk" or "vector" — refer to the source as "the document"."""


@st.cache_resource
def get_groq_client() -> Groq:
    return Groq(api_key=st.secrets["groq"]["api_key"])


def _build_context(chunks: list[dict]) -> str:
    if not chunks:
        return "No relevant context was found in the document."
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(f"[Passage {i}]\n{chunk['text']}")
    return "\n\n".join(parts)


def generate_answer(question: str, chunks: list[dict]) -> str:
    """
    Given a question and retrieved chunks, generate a grounded answer via Groq.
    """
    context = _build_context(chunks)
    user_message = f"Context from the document:\n\n{context}\n\n---\n\nQuestion: {question}"

    client = get_groq_client()
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    return response.choices[0].message.content.strip()
