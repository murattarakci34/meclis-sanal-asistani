"""
ChatGPT tarzı chat arayüzü.
Çalıştır:  streamlit run app.py
"""

from __future__ import annotations

import html

import streamlit as st

import chat_store
from document_loader import kaynak_fingerprint
from rag import SourceRAG

APP_NAME = "Meclis Sanal Asistanı"

# Dairesel Türk bayrağı (SVG)
FLAG_SVG = """
<svg class="tr-flag" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="50" cy="50" r="50" fill="#E30A17"/>
  <circle cx="42" cy="50" r="20" fill="#fff"/>
  <circle cx="48" cy="50" r="16" fill="#E30A17"/>
  <polygon fill="#fff" points="67,50 61.2,52.1 62.8,58.1 57.8,54.2 52,57.5 55.2,52.1 50,50 55.2,47.9 52,42.5 57.8,45.8 62.8,41.9 61.2,47.9"/>
</svg>
"""

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🇹🇷",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
  --bg: #212121;
  --sidebar: #181818;
  --hover: #2a2a2a;
  --active: #2f2f2f;
  --input: #303030;
  --line: #2a2a2a;
  --text: #f3f3f3;
  --muted: #9b9b9b;
  --green: #10a37f;
}

html, body, [class*="css"], .stApp {
  font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif !important;
}

.stApp { background: var(--bg) !important; color: var(--text) !important; }

/* —— Header: Deploy gizle, menü aç kalsın —— */
header[data-testid="stHeader"] { background: transparent !important; }
div[data-testid="stToolbar"] { display: flex !important; visibility: visible !important; }
div[data-testid="stToolbar"] [data-testid="stToolbarActions"],
div[data-testid="stDecoration"],
#MainMenu, footer { display: none !important; }

[data-testid="stSidebarCollapsedControl"] {
  position: fixed !important;
  top: 10px !important;
  left: 10px !important;
  z-index: 2147483647 !important;
  display: flex !important;
  visibility: visible !important;
  opacity: 1 !important;
}
[data-testid="stSidebarCollapsedControl"] button,
button[data-testid="stBaseButton-headerNoPadding"] {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 40px !important;
  height: 40px !important;
  border-radius: 10px !important;
  background: #2f2f2f !important;
  border: 1px solid #3d3d3d !important;
  color: #fff !important;
  box-shadow: 0 4px 14px rgba(0,0,0,.35) !important;
}
[data-testid="stSidebarCollapsedControl"] span { color: #fff !important; }

/* —— Ana alan —— */
div.block-container {
  padding: 3.25rem 1.25rem 8rem !important;
  max-width: 740px !important;
}

/* —— Sidebar —— */
section[data-testid="stSidebar"] {
  background: var(--sidebar) !important;
  border-right: 1px solid var(--line) !important;
}
section[data-testid="stSidebar"] > div:first-child {
  background: var(--sidebar) !important;
  padding: 10px 10px 24px !important;
}
section[data-testid="stSidebar"] * { color: var(--text) !important; }

section[data-testid="stSidebar"] .stButton > button {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  color: var(--text) !important;
  border-radius: 10px !important;
  justify-content: flex-start !important;
  text-align: left !important;
  font-weight: 400 !important;
  font-size: 0.9rem !important;
  line-height: 1.25 !important;
  padding: 0.6rem 0.75rem !important;
  min-height: 42px !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
  background: var(--hover) !important;
}

/* Yeni sohbet */
section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:first-of-type .stButton > button,
section[data-testid="stSidebar"] .stButton > button[kind="secondary"] {
  /* fallback */
}

/* Arama */
section[data-testid="stSidebar"] .stTextInput input {
  background: #212121 !important;
  border: 1px solid #333 !important;
  border-radius: 999px !important;
  color: var(--text) !important;
  font-size: 0.875rem !important;
  padding: 0.55rem 0.9rem !important;
}
section[data-testid="stSidebar"] .stTextInput input::placeholder {
  color: var(--muted) !important;
}

/* Sohbet satırı: sol başlık, sağ sil */
section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] {
  gap: 0.15rem !important;
  align-items: center !important;
  margin-bottom: 2px !important;
  border-radius: 10px !important;
}
section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:hover {
  background: var(--hover);
}

/* Sil butonu — 2. kolon: her zaman görünür */
section[data-testid="stSidebar"] div[data-testid="column"]:nth-child(2) .stButton > button {
  justify-content: center !important;
  text-align: center !important;
  min-width: 42px !important;
  width: 42px !important;
  min-height: 42px !important;
  padding: 0 !important;
  font-size: 1.05rem !important;
  color: #c8c8c8 !important;
  opacity: 1 !important;
  visibility: visible !important;
  background: transparent !important;
}
section[data-testid="stSidebar"] div[data-testid="column"]:nth-child(2) .stButton > button:hover {
  background: #3a3a3a !important;
  color: #ff6b6b !important;
}

/* Aktif sohbet vurgusu — JS yok; Streamlit primary kullanıyoruz */
section[data-testid="stSidebar"] .stButton > button[kind="primary"],
section[data-testid="stSidebar"] button[data-testid="baseButton-primary"] {
  background: var(--active) !important;
  border: none !important;
  color: var(--text) !important;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 8px 14px;
  font-weight: 600;
  font-size: 0.88rem;
  color: var(--text);
  line-height: 1.25;
}
.nav-brand .dot {
  flex-shrink: 0;
  width: 28px; height: 28px; border-radius: 50%;
  overflow: hidden;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 0 1px rgba(255,255,255,.12);
}
.nav-brand .dot .tr-flag,
.empty-hero .logo .tr-flag {
  width: 100%;
  height: 100%;
  display: block;
}
.nav-label {
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--muted) !important;
  padding: 14px 10px 6px;
}

/* —— Mesajlar —— */
[data-testid="stChatMessage"] {
  background: transparent !important;
  padding: 0.9rem 0.15rem !important;
  gap: 0.85rem !important;
}
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li {
  color: var(--text) !important;
  line-height: 1.7 !important;
  font-size: 1rem !important;
}
[data-testid="stChatMessage"] img {
  border-radius: 999px !important;
}

/* Chat input — ChatGPT hap */
[data-testid="stBottomBlockContainer"] {
  background: linear-gradient(180deg, transparent, var(--bg) 28%) !important;
  padding-bottom: 1rem !important;
}
[data-testid="stChatInput"] {
  background: transparent !important;
}
[data-testid="stChatInput"] {
  padding: 0 0.35rem !important;
}
[data-testid="stChatInput"] textarea,
[data-testid="stChatInput"] > div {
  background: var(--input) !important;
  border: 1px solid #404040 !important;
  border-radius: 28px !important;
  color: var(--text) !important;
  font-size: 1rem !important;
  box-shadow: 0 0 0 0 transparent !important;
}
[data-testid="stChatInput"] textarea {
  padding: 0.95rem 1.25rem !important;
  line-height: 1.45 !important;
}
[data-testid="stChatInput"] > div {
  padding-left: 0.35rem !important;
  padding-right: 0.35rem !important;
}
[data-testid="stChatInput"] textarea:focus {
  border-color: #565656 !important;
  box-shadow: none !important;
}

/* Empty hero — ChatGPT */
.empty-hero {
  min-height: min(62vh, 560px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 1.5rem 1rem 2rem;
}
.empty-hero .logo {
  width: 52px; height: 52px; border-radius: 50%;
  overflow: hidden;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 1rem;
  box-shadow: 0 6px 20px rgba(227,10,23,.35), 0 0 0 1px rgba(255,255,255,.12);
}
.empty-hero .brand {
  margin: 0 0 0.65rem !important;
  font-size: clamp(1.35rem, 3.8vw, 1.7rem) !important;
  font-weight: 700 !important;
  color: var(--text) !important;
  letter-spacing: -0.03em;
}
.empty-hero h1 {
  margin: 0 0 0.45rem !important;
  font-size: clamp(1.05rem, 2.8vw, 1.2rem) !important;
  font-weight: 500 !important;
  color: var(--muted) !important;
  letter-spacing: -0.01em;
}
.empty-hero p {
  margin: 0 !important;
  color: var(--muted) !important;
  font-size: 0.9rem !important;
  max-width: 28rem;
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.15rem 0 1rem;
}
.top-bar .title {
  color: var(--text);
  font-weight: 600;
  font-size: 0.92rem;
  max-width: min(70vw, 520px);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  opacity: 0.92;
}

hr { border-color: var(--line) !important; margin: 0.75rem 0 !important; }

/* —— Mobil —— */
@media (max-width: 768px) {
  div.block-container {
    padding: 3.5rem 0.75rem 7.5rem !important;
  }
  .empty-hero {
    min-height: 48vh;
    padding: 1rem 0.5rem;
  }
  section[data-testid="stSidebar"] {
    width: min(88vw, 320px) !important;
  }
  section[data-testid="stSidebar"] > div:first-child {
    padding: 12px 10px 28px !important;
  }
  section[data-testid="stSidebar"] .stButton > button {
    min-height: 44px !important;
    font-size: 0.92rem !important;
  }
  section[data-testid="stSidebar"] div[data-testid="column"]:nth-child(2) .stButton > button {
    min-width: 44px !important;
    width: 44px !important;
    min-height: 44px !important;
    font-size: 1.15rem !important;
  }
  [data-testid="stChatInput"] textarea {
    font-size: 16px !important; /* iOS zoom engelle */
  }
  .top-bar .title { max-width: 72vw; }
}
</style>
""",
    unsafe_allow_html=True,
)


def init_state() -> None:
    if "rag" not in st.session_state:
        st.session_state.rag = None
    if "chunk_count" not in st.session_state:
        st.session_state.chunk_count = 0
    if "load_error" not in st.session_state:
        st.session_state.load_error = None
    if "search_q" not in st.session_state:
        st.session_state.search_q = ""
    if "kaynak_fp" not in st.session_state:
        st.session_state.kaynak_fp = ""
    if "current_chat_id" not in st.session_state:
        st.session_state.current_chat_id = None
        st.session_state.messages = []
        st.session_state.chat_title = "Yeni sohbet"


def persist_messages() -> None:
    cid = st.session_state.current_chat_id
    if not cid:
        return
    chat = chat_store.load_chat(cid)
    if not chat:
        return
    chat["messages"] = st.session_state.messages
    chat["title"] = st.session_state.get("chat_title") or chat.get("title") or "Yeni sohbet"
    chat_store.save_chat(chat)


def ensure_chat_exists() -> str:
    if st.session_state.current_chat_id:
        return st.session_state.current_chat_id
    chat = chat_store.create_chat(st.session_state.get("chat_title") or "Yeni sohbet")
    st.session_state.current_chat_id = chat["id"]
    return chat["id"]


def switch_chat(chat_id: str) -> None:
    chat = chat_store.load_chat(chat_id)
    if not chat:
        return
    st.session_state.current_chat_id = chat_id
    st.session_state.messages = chat.get("messages") or []
    st.session_state.chat_title = chat.get("title") or "Yeni sohbet"


def start_new_chat() -> None:
    st.session_state.current_chat_id = None
    st.session_state.messages = []
    st.session_state.chat_title = "Yeni sohbet"


def ensure_rag(force: bool = False) -> SourceRAG | None:
    fp = kaynak_fingerprint()
    needs_reload = (
        force
        or st.session_state.rag is None
        or fp != st.session_state.kaynak_fp
    )
    if not needs_reload:
        return st.session_state.rag
    try:
        rag = st.session_state.rag if st.session_state.rag is not None else SourceRAG()
        st.session_state.chunk_count = rag.reload()
        st.session_state.rag = rag
        st.session_state.kaynak_fp = fp
        st.session_state.load_error = None
        return rag
    except Exception as exc:  # noqa: BLE001
        st.session_state.load_error = str(exc)
        st.session_state.rag = None
        return None


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            f'<div class="nav-brand"><span class="dot">{FLAG_SVG}</span> {html.escape(APP_NAME)}</div>',
            unsafe_allow_html=True,
        )

        if st.button("＋  Yeni sohbet", use_container_width=True, key="btn_new"):
            start_new_chat()
            st.rerun()

        st.text_input(
            "search",
            key="search_q",
            placeholder="Sohbetlerde ara",
            label_visibility="collapsed",
        )

        st.markdown('<div class="nav-label">Sohbetler</div>', unsafe_allow_html=True)

        chats = [
            c
            for c in chat_store.search_chats(st.session_state.search_q)
            if c.get("message_count", 0) > 0
        ]

        if not chats:
            st.caption("Henüz sohbet yok")
        else:
            for item in chats:
                active = item["id"] == st.session_state.current_chat_id
                left, right = st.columns([5.2, 1], gap="small")
                with left:
                    label = item["title"] or "Sohbet"
                    if len(label) > 36:
                        label = label[:35] + "…"
                    clicked = st.button(
                        label,
                        key=f"open_{item['id']}",
                        use_container_width=True,
                        type="primary" if active else "secondary",
                    )
                    if clicked:
                        switch_chat(item["id"])
                        st.rerun()
                with right:
                    # Görünür sil ikonu (× Streamlit’te kaybolabiliyordu)
                    if st.button(
                        "🗑️",
                        key=f"del_{item['id']}",
                        use_container_width=True,
                        help="Sohbeti sil",
                    ):
                        chat_store.delete_chat(item["id"])
                        if item["id"] == st.session_state.current_chat_id:
                            start_new_chat()
                        st.rerun()


def render_empty_state() -> None:
    name = html.escape(APP_NAME)
    st.markdown(
        f"""
        <div class="empty-hero">
          <div class="logo">{FLAG_SVG}</div>
          <p class="brand">{name}</p>
          <h1>Nasıl yardımcı olabilirim?</h1>
          <p>Meclis belgeleri ve genel soruların için buradayım.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_messages() -> None:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def handle_prompt(prompt: str) -> None:
    if not st.session_state.messages:
        st.session_state.chat_title = chat_store.title_from_message(prompt)

    ensure_chat_exists()
    st.session_state.messages.append({"role": "user", "content": prompt})
    persist_messages()

    with st.chat_message("user"):
        st.markdown(prompt)

    rag = st.session_state.rag
    if rag is None:
        answer = "Sistem hazır değil. API key ve kaynakları kontrol et."
        with st.chat_message("assistant"):
            st.error(answer)
    else:
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[:-1]
            if m["role"] in ("user", "assistant")
        ]
        with st.chat_message("assistant"):
            with st.spinner(""):
                try:
                    answer, _ = rag.chat(prompt, history=history)
                except Exception as exc:  # noqa: BLE001
                    answer = f"Hata: {exc}"
            st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    persist_messages()


def main() -> None:
    init_state()
    render_sidebar()

    title = html.escape(st.session_state.get("chat_title") or APP_NAME)
    if st.session_state.messages:
        st.markdown(
            f'<div class="top-bar"><span class="title">{title}</span></div>',
            unsafe_allow_html=True,
        )

    if st.session_state.rag is None and st.session_state.load_error is None:
        with st.spinner("Yükleniyor…"):
            ensure_rag()

    if st.session_state.load_error:
        st.error(st.session_state.load_error)
        st.info("API key → `config.py` → `OPENAI_API_KEY`")
        return

    if not st.session_state.messages:
        render_empty_state()
    else:
        render_messages()

    prompt = st.chat_input("Bir mesaj yazın")
    if prompt:
        handle_prompt(prompt)


if __name__ == "__main__":
    main()
