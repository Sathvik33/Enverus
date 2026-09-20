import streamlit as st
import requests
import os
import html
from pathlib import Path

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Multimodal RAG — Agent-as-a-Judge", page_icon="🔍", layout="wide")

st.markdown("""
<style>
    .main-header { font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem; }
    .sub-header { font-size: 1rem; opacity: 0.75; margin-bottom: 2rem; }
    .metric-card { background: rgba(59, 130, 246, 0.08); border-radius: 8px; padding: 1rem; text-align: center; }
    .evidence-box { background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.2); border-left: 4px solid #3b82f6; padding: 0.85rem; margin: 0.5rem 0; border-radius: 6px; color: inherit; white-space: pre-wrap; line-height: 1.5; }
    .citation { background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3); padding: 0.25rem 0.6rem; border-radius: 4px; font-size: 0.85rem; color: inherit; display: inline-block; margin: 0.2rem 0.1rem; }
    .auth-card { background: rgba(59, 130, 246, 0.05); border: 1px solid rgba(59, 130, 246, 0.15); border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🔍 Multimodal RAG — Agent-as-a-Judge</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Evidence-grounded multimodal retrieval-augmented generation</div>', unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "document_id" not in st.session_state:
    st.session_state.document_id = None
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "shown_sources" not in st.session_state:
    st.session_state.shown_sources = set()

with st.sidebar:
    st.header("👤 Account")

    if st.session_state.current_user:
        st.success(f"Signed in as **{st.session_state.current_user['email']}**")
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.current_user = None
            st.rerun()

        st.divider()
        st.header("📜 Chat History")
        try:
            hist_resp = requests.get(
                f"{BACKEND_URL}/api/history",
                params={"user_id": st.session_state.current_user["id"]},
                timeout=10,
            )
            if hist_resp.status_code == 200:
                hist_items = hist_resp.json().get("items", [])
                if hist_items:
                    for item in hist_items[:15]:
                        q_preview = item["query"][:35] + ("..." if len(item["query"]) > 35 else "")
                        time_str = item["created_at"][11:16] if len(item["created_at"]) >= 16 else ""
                        if st.button(f"🕒 {time_str} {q_preview}", key=f"hist_{item['id']}", use_container_width=True):
                            st.session_state.messages = [
                                {"role": "user", "content": item["query"]},
                                {
                                    "role": "assistant",
                                    "content": item["answer"],
                                    "evidence": item.get("evidence", []),
                                    "citations": item.get("citations", []),
                                    "trace": {},
                                }
                            ]
                            st.session_state.shown_sources = set()
                            st.rerun()

                    if st.button("🗑️ Clear History", use_container_width=True):
                        requests.delete(
                            f"{BACKEND_URL}/api/history",
                            params={"user_id": st.session_state.current_user["id"]},
                            timeout=10,
                        )
                        st.rerun()
                else:
                    st.caption("No history yet. Ask a question to begin!")
            else:
                st.caption("Could not load history.")
        except Exception:
            st.caption("History service unavailable.")
    else:
        auth_tab_in, auth_tab_up = st.tabs(["🔑 Sign In", "✨ Sign Up"])

        with auth_tab_in:
            with st.form("signin_form"):
                in_email = st.text_input("Email", placeholder="you@example.com")
                in_password = st.text_input("Password", type="password")
                submit_in = st.form_submit_button("Sign In", use_container_width=True)
                if submit_in:
                    if not in_email or not in_password:
                        st.error("Please enter email and password")
                    else:
                        try:
                            resp = requests.post(
                                f"{BACKEND_URL}/api/auth/signin",
                                json={"email": in_email.strip(), "password": in_password},
                                timeout=15,
                            )
                            if resp.status_code == 200:
                                data = resp.json()
                                st.session_state.current_user = data["user"]
                                st.success("Signed in successfully!")
                                st.rerun()
                            else:
                                err = resp.json().get("detail", "Sign in failed")
                                st.error(err)
                        except Exception as ex:
                            st.error(f"Connection error: {ex}")

        with auth_tab_up:
            with st.form("signup_form"):
                up_email = st.text_input("Email", placeholder="you@example.com")
                up_password = st.text_input("Password (min 6 chars)", type="password")
                submit_up = st.form_submit_button("Create Account", use_container_width=True)
                if submit_up:
                    if not up_email or not up_password:
                        st.error("Please fill in all fields")
                    elif len(up_password) < 6:
                        st.error("Password must be at least 6 characters")
                    else:
                        try:
                            resp = requests.post(
                                f"{BACKEND_URL}/api/auth/signup",
                                json={"email": up_email.strip(), "password": up_password},
                                timeout=15,
                            )
                            if resp.status_code == 200:
                                data = resp.json()
                                st.session_state.current_user = data["user"]
                                st.success("Account created successfully!")
                                st.rerun()
                            else:
                                err = resp.json().get("detail", "Sign up failed")
                                st.error(err)
                        except Exception as ex:
                            st.error(f"Connection error: {ex}")

    st.divider()
    st.header("📄 Document Management")

    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
    if uploaded_file and st.button("📤 Ingest Document"):
        with st.spinner("Uploading and processing..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                resp = requests.post(f"{BACKEND_URL}/api/documents/upload", files=files, timeout=300)
                if resp.status_code == 200:
                    data = resp.json()
                    st.session_state.document_id = data["document_id"]
                    st.success(f"Document uploaded! ID: {data['document_id'][:8]}...")
                else:
                    st.error(f"Upload failed: {resp.text}")
            except Exception as e:
                st.error(f"Connection error: {e}")

    st.divider()

    doc_id_input = st.text_input("Or enter Document ID:", value=st.session_state.document_id or "")
    if doc_id_input:
        st.session_state.document_id = doc_id_input

    if st.session_state.document_id:
        try:
            resp = requests.get(f"{BACKEND_URL}/api/documents/{st.session_state.document_id}", timeout=10)
            if resp.status_code == 200:
                doc = resp.json()
                st.markdown("### Document Status")
                st.markdown(f"**{doc.get('filename', 'Unknown')}**")

                col1, col2 = st.columns(2)
                col1.metric("Status", doc.get("status", "?"))
                col2.metric("Pages", doc.get("total_pages", 0))

                col3, col4, col5 = st.columns(3)
                col3.metric("Text Chunks", doc.get("text_chunks", 0))
                col4.metric("Tables", doc.get("table_chunks", 0))
                col5.metric("Images", doc.get("images", 0))
        except Exception:
            st.warning("Could not fetch document status")

    st.divider()
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.session_state.shown_sources = set()
        st.rerun()

for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        if msg["role"] == "assistant":
            has_sources = bool(msg.get("citations") or msg.get("evidence"))
            if has_sources:
                is_shown = idx in st.session_state.shown_sources
                btn_label = "🔼 Hide Sources" if is_shown else "📚 Sources"
                if st.button(btn_label, key=f"toggle_sources_{idx}"):
                    if is_shown:
                        st.session_state.shown_sources.remove(idx)
                    else:
                        st.session_state.shown_sources.add(idx)
                    st.rerun()

                if is_shown:
                    if msg.get("citations"):
                        st.markdown("**📌 Sources:**")
                        for c in msg["citations"]:
                            sec = c.get("section", "")
                            sec_text = f", {sec}" if sec else ""
                            st.markdown(f'<span class="citation">Page {c.get("page_number", "?")}{sec_text} ({c.get("source_type", "text")})</span>', unsafe_allow_html=True)

                    if msg.get("evidence"):
                        with st.expander("📋 Retrieved Evidence", expanded=True):
                            for e in msg.get("evidence", []):
                                source_type = e.get("source_type", "text")
                                icon = {"text": "📝", "table": "📊", "image": "🖼️", "text_bm25": "🔤"}.get(source_type, "📄")
                                sec = e.get("section", "")
                                sec_text = f" — {sec}" if sec else ""
                                st.markdown(f"**{icon} {source_type.upper()}** — Page {e.get('page_number', '?')}{sec_text}")
                                snippet = html.escape(e.get("content", "")[:500])
                                st.markdown(f'<div class="evidence-box">{snippet}</div>', unsafe_allow_html=True)

                                if source_type == "image" and e.get("image_path"):
                                    img_path = Path(e["image_path"])
                                    if img_path.exists():
                                        st.image(str(img_path), caption=e.get("caption", ""), width=400)

                                st.markdown(f"Score: `{e.get('score', 0):.4f}`")
                                st.divider()

                    trace = msg.get("trace", {})
                    if trace:
                        with st.expander("🔬 View Retrieval Process", expanded=False):
                            qa = trace.get("query_analysis", {})
                            st.markdown(f"**Query Type:** {qa.get('query_type', '?')}")
                            st.markdown(f"**Needs Text:** {qa.get('needs_text', True)} | **Tables:** {qa.get('needs_table', False)} | **Images:** {qa.get('needs_image', False)}")
                            st.markdown("---")

                            steps = [
                                ("Query Analysis", "query_analysis"),
                                ("Dense Text Results", "text_results"),
                                ("BM25 Results", "bm25_results"),
                                ("Table Results", "table_results"),
                                ("Image Results", "image_results"),
                                ("RRF Fusion", "rrf_results"),
                                ("Reranked Results", "reranked_results"),
                                ("Final Evidence", "final_evidence"),
                            ]

                            for step_name, key in steps:
                                data = trace.get(key, [])
                                if isinstance(data, dict):
                                    st.markdown(f"**{step_name}:** {data}")
                                elif isinstance(data, list):
                                    st.markdown(f"**{step_name}:** {len(data)} results")
                                else:
                                    st.markdown(f"**{step_name}:** {data}")

if prompt := st.chat_input("Ask about the research paper..."):
    if not st.session_state.document_id:
        st.warning("Please upload a document or enter a Document ID first.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Searching and generating answer..."):
                try:
                    payload = {"document_id": st.session_state.document_id, "query": prompt}
                    if st.session_state.current_user:
                        payload["user_id"] = st.session_state.current_user["id"]

                    resp = requests.post(
                        f"{BACKEND_URL}/api/chat",
                        json=payload,
                        timeout=120,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        answer = data.get("answer", "No answer")
                        st.markdown(answer)

                        msg_data = {
                            "role": "assistant",
                            "content": answer,
                            "evidence": data.get("evidence", []),
                            "citations": data.get("citations", []),
                            "trace": data.get("retrieval_trace", {}),
                        }
                        st.session_state.messages.append(msg_data)
                    else:
                        error_msg = f"Error: {resp.text}"
                        st.error(error_msg)
                        st.session_state.messages.append({"role": "assistant", "content": error_msg})
                except Exception as e:
                    error_msg = f"Connection error: {e}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

        st.rerun()
