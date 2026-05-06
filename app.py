import streamlit as st
from db import get_supabase, ensure_user, save_message, get_messages, get_user_docs, delete_document
from ingestor import ingest_file
from retriever import retrieve_chunks
from generator import generate_answer

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="KnowledgeBase AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Landing page ──────────────────────────────────────────────────────────────
if "user_name" not in st.session_state:
    st.session_state.user_name = None

if not st.session_state.user_name:
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Mono:wght@400;500&display=swap');

        html, body, [data-testid="stAppViewContainer"] {
            background: #0a0a0f;
            color: #e8e6e3;
            font-family: 'DM Mono', monospace;
        }
        .login-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 80vh;
            gap: 2rem;
        }
        .login-title {
            font-family: 'Syne', sans-serif;
            font-weight: 800;
            font-size: 4rem;
            letter-spacing: -0.04em;
            background: linear-gradient(135deg, #e8e6e3 0%, #7c6fff 60%, #ff6b9d 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-align: center;
            line-height: 1;
        }
        .login-sub {
            font-size: 0.95rem;
            color: #6b6873;
            text-align: center;
            letter-spacing: 0.05em;
        }
        .stTextInput > div > input {
            background: #0f0f17 !important;
            border: 1px solid #1e1e2e !important;
            border-radius: 6px !important;
            color: #e8e6e3 !important;
            font-family: 'DM Mono', monospace !important;
            font-size: 0.9rem !important;
            text-align: center !important;
            padding: 0.75rem !important;
        }
        .stTextInput > div > input:focus {
            border-color: #7c6fff !important;
            box-shadow: 0 0 0 2px rgba(124,111,255,0.2) !important;
        }
        .stButton > button {
            background: #7c6fff !important;
            color: #fff !important;
            border: none !important;
            border-radius: 6px !important;
            padding: 0.75rem 2.5rem !important;
            font-family: 'DM Mono', monospace !important;
            font-size: 0.9rem !important;
            letter-spacing: 0.08em !important;
            text-transform: uppercase !important;
            transition: all 0.2s ease !important;
        }
        .stButton > button:hover {
            background: #6a5cf0 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 8px 24px rgba(124, 111, 255, 0.35) !important;
        }
    </style>
    <div class="login-container">
        <div class="login-title">KnowledgeBase<br>AI</div>
        <div class="login-sub">no google. no passwords. just your name and some vectors.</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 0.6, 1])
    with col2:
        name = st.text_input("", placeholder="what's your name?", label_visibility="collapsed")
        if st.button("🧠 Enter the Brain", use_container_width=True):
            if name.strip():
                st.session_state.user_name = name.strip().lower().replace(" ", "_")
                st.rerun()
            else:
                st.error("please enter your name first!")
    st.stop()

# ── User (name-based session) ─────────────────────────────────────────────────
user_email = f"{st.session_state.user_name}@knowledgebase.ai"
ensure_user(user_email)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Mono:wght@400;500&display=swap');

    html, body, [data-testid="stAppViewContainer"] {
        background: #0a0a0f;
        color: #e8e6e3;
        font-family: 'DM Mono', monospace;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #0f0f17 !important;
        border-right: 1px solid #1e1e2e !important;
    }
    [data-testid="stSidebar"] * { color: #e8e6e3 !important; }

    /* Sidebar button hover fix for dark theme */
    [data-testid="stSidebar"] .stButton > button {
        background: transparent !important;
        border: 1px solid #1e1e2e !important;
        color: #e8e6e3 !important;
        font-family: 'DM Mono', monospace !important;
        font-size: 0.8rem !important;
        letter-spacing: 0.04em !important;
        border-radius: 4px !important;
        transition: all 0.15s ease !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: #1e1e2e !important;
        border-color: #7c6fff !important;
        color: #7c6fff !important;
    }

    /* Main action button */
    .main-btn > button {
        background: #7c6fff !important;
        color: #fff !important;
        border: none !important;
        border-radius: 6px !important;
        font-family: 'DM Mono', monospace !important;
        letter-spacing: 0.05em !important;
        text-transform: uppercase !important;
        font-size: 0.8rem !important;
    }
    .main-btn > button:hover {
        background: #6a5cf0 !important;
        box-shadow: 0 4px 16px rgba(124, 111, 255, 0.4) !important;
    }

    /* Header */
    .kb-header {
        font-family: 'Syne', sans-serif;
        font-weight: 800;
        font-size: 1.6rem;
        letter-spacing: -0.02em;
        background: linear-gradient(90deg, #e8e6e3 0%, #7c6fff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0;
    }
    .kb-context-label {
        font-size: 0.7rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #6b6873;
        margin-top: 0.1rem;
    }

    /* Chat messages */
    [data-testid="stChatMessage"] {
        background: #0f0f17 !important;
        border: 1px solid #1e1e2e !important;
        border-radius: 8px !important;
        margin-bottom: 0.5rem !important;
    }
    [data-testid="stChatMessage"][data-testid*="user"] {
        border-color: #7c6fff33 !important;
    }

    /* Selectbox */
    [data-testid="stSelectbox"] > div {
        background: #0f0f17 !important;
        border-color: #1e1e2e !important;
        border-radius: 6px !important;
        font-family: 'DM Mono', monospace !important;
        font-size: 0.85rem !important;
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        background: #0f0f17 !important;
        border: 1px dashed #1e1e2e !important;
        border-radius: 8px !important;
    }

    /* Chat input */
    [data-testid="stChatInput"] {
        background: #0f0f17 !important;
        border-color: #1e1e2e !important;
        border-radius: 8px !important;
        font-family: 'DM Mono', monospace !important;
    }

    /* Dividers */
    hr { border-color: #1e1e2e !important; }

    /* Source expander */
    .streamlit-expanderHeader {
        background: #0f0f17 !important;
        border: 1px solid #1e1e2e !important;
        border-radius: 6px !important;
        font-size: 0.78rem !important;
        letter-spacing: 0.04em !important;
        color: #6b6873 !important;
    }

    /* Metric */
    [data-testid="metric-container"] {
        background: #0f0f17;
        border: 1px solid #1e1e2e;
        border-radius: 8px;
        padding: 0.75rem 1rem;
    }

    /* Success / info / warning */
    .stAlert { border-radius: 6px !important; }

    /* Spinner */
    .stSpinner > div { border-top-color: #7c6fff !important; }

    /* Hide Streamlit branding */
    #MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "active_doc" not in st.session_state:
    st.session_state.active_doc = None
if "doc_loaded" not in st.session_state:
    st.session_state.doc_loaded = False

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="kb-header">🧠 KB·AI</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="kb-context-label">hey, {st.session_state.user_name} 👋</div>', unsafe_allow_html=True)
    st.divider()

    # Upload
    st.markdown("**Upload Document**")
    uploaded = st.file_uploader(
        "PDF or TXT",
        type=["pdf", "txt"],
        label_visibility="collapsed",
    )
    if uploaded:
        col_u1, col_u2 = st.columns([1, 1])
        with col_u1:
            st.markdown('<div class="main-btn">', unsafe_allow_html=True)
            do_ingest = st.button("Ingest →", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        if do_ingest:
            with st.spinner("Chunking & embedding…"):
                try:
                    chunk_count = ingest_file(uploaded, user_email)
                    st.success(f"✓ {chunk_count} chunks indexed")
                except Exception as e:
                    st.error(f"Ingestion failed: {e}")

    st.divider()

    # Document picker
    st.markdown("**Your Documents**")
    docs = get_user_docs(user_email)
    doc_names = [d["name"] for d in docs]

    if doc_names:
        selected = st.selectbox(
            "Active document",
            doc_names,
            label_visibility="collapsed",
        )

        if selected != st.session_state.active_doc:
            st.session_state.active_doc = selected
            st.session_state.doc_loaded = False
            st.session_state.messages = []

        # Load history once per doc switch
        if not st.session_state.doc_loaded:
            history = get_messages(user_email, selected)
            st.session_state.messages = history
            st.session_state.doc_loaded = True

        # Doc stats
        active_meta = next((d for d in docs if d["name"] == selected), None)
        if active_meta:
            st.caption(f"📄 {active_meta['chunk_count']} chunks  ·  {active_meta['uploaded_at'][:10]}")

        # Delete
        if st.button("🗑 Delete document", use_container_width=True):
            with st.spinner("Deleting…"):
                try:
                    delete_document(user_email, selected)
                    st.session_state.active_doc = None
                    st.session_state.messages = []
                    st.session_state.doc_loaded = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Delete failed: {e}")
    else:
        st.caption("No documents yet. Upload one above.")

    st.divider()
    if st.button("🚪 Exit Brain", use_container_width=True):
        st.session_state.user_name = None
        st.session_state.messages = []
        st.session_state.active_doc = None
        st.session_state.doc_loaded = False
        st.rerun()

# ── Main area ─────────────────────────────────────────────────────────────────
if not st.session_state.active_doc:
    st.markdown("""
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
                min-height:60vh;gap:1.5rem;text-align:center;">
        <div style="font-family:'Syne',sans-serif;font-size:3rem;font-weight:800;
                    letter-spacing:-0.04em;color:#1e1e2e;">🧠</div>
        <div style="font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:700;
                    letter-spacing:-0.02em;color:#e8e6e3;">
            Upload a document to begin
        </div>
        <div style="font-size:0.85rem;color:#6b6873;max-width:380px;line-height:1.7;">
            Drop any PDF or TXT file in the sidebar. Your document gets chunked, embedded, 
            and stored — then you chat with it using RAG.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Chat header ───────────────────────────────────────────────────────────────
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown(f'<div class="kb-header">{st.session_state.active_doc}</div>', unsafe_allow_html=True)
    st.markdown('<div class="kb-context-label">RAG · Groq · Pinecone</div>', unsafe_allow_html=True)
with col_h2:
    if st.session_state.messages:
        st.metric("Messages", len(st.session_state.messages))

st.divider()

# ── Render chat history ───────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander("📎 sources", expanded=False):
                for i, src in enumerate(msg["sources"], 1):
                    st.markdown(f"**Chunk {i}** · score `{src.get('score', '—'):.3f}`")
                    st.caption(src.get("text", "")[:400] + "…")

# ── Chat input ────────────────────────────────────────────────────────────────
if prompt := st.chat_input(f"Ask about {st.session_state.active_doc}…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    save_message(user_email, st.session_state.active_doc, "user", prompt)

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving & generating…"):
            try:
                chunks = retrieve_chunks(prompt, user_email, st.session_state.active_doc)
                answer = generate_answer(prompt, chunks)
            except Exception as e:
                answer = f"⚠️ Error: {e}"
                chunks = []

        st.markdown(answer)

        sources = [{"text": c["text"], "score": c.get("score", 0)} for c in chunks]
        if sources:
            with st.expander("📎 sources", expanded=False):
                for i, src in enumerate(sources, 1):
                    st.markdown(f"**Chunk {i}** · score `{src['score']:.3f}`")
                    st.caption(src["text"][:400] + "…")

    assistant_msg = {"role": "assistant", "content": answer, "sources": sources}
    st.session_state.messages.append(assistant_msg)
    save_message(user_email, st.session_state.active_doc, "assistant", answer)
