"""
app.py — Frontend Streamlit del proyecto EMT Madrid.

Cómo correrlo:
    pip install -r requirements.txt
    streamlit run app.py

Cómo cambiar de backend (mock / local / azure):
    Ver agent_client.py — ahí están los 2 puntos de conexión pendientes
    (agente local de Raúl, y Data Agent en Azure vía MCP), cada uno con
    su TODO explicado paso a paso.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

import agent_client
from i18n import LANGUAGES, t
from themes import THEMES, APP_NAME, get_theme

FEEDBACK_LOG = Path(__file__).parent / "feedback_log.jsonl"


# ---------------------------------------------------------------------------
# Configuración de página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=APP_NAME,
    page_icon="🚌",
    layout="centered",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Estado de sesión
# ---------------------------------------------------------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "es"
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "colorblind"
if "text_size" not in st.session_state:
    st.session_state.text_size = "normal"
if "history" not in st.session_state:
    st.session_state.history = []  # [{"role", "content", "backend"?}]
if "feedback_given" not in st.session_state:
    st.session_state.feedback_given = set()

lang = st.session_state.lang
theme = get_theme(st.session_state.theme_mode)


# ---------------------------------------------------------------------------
# Estilos — paleta inspirada en EMT Madrid (rojo/azul), texto grande y
# botones amplios para que funcione bien para gente mayor y jóvenes.
# ---------------------------------------------------------------------------
BASE_FONT = "22px" if st.session_state.text_size == "large" else "17px"
TITLE_FONT = "34px" if st.session_state.text_size == "large" else "26px"

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;700;800&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Nunito', sans-serif;
        font-size: {BASE_FONT};
    }}

    :root {{
        --app-bg: {theme['bg']};
        --app-bg-card: {theme['bg_card']};
        --app-text: {theme['text']};
        --app-text-secondary: {theme['text_secondary']};
        --app-primary: {theme['primary']};
        --app-accent: {theme['accent']};
        --app-border: {theme['border']};
        --app-border-width: {theme['border_width']};
    }}

    .stApp {{
        background-color: var(--app-bg);
        color: var(--app-text);
    }}

    /* Barra superior nativa de Streamlit (donde vive "Deploy" y el menú) */
    [data-testid="stHeader"] {{
        background-color: var(--app-bg);
    }}
    [data-testid="stToolbar"] * {{
        color: var(--app-text-secondary);
    }}

    [data-testid="stSidebar"] {{
        background-color: var(--app-bg-card);
        border-right: var(--app-border-width) solid var(--app-border);
    }}
    [data-testid="stSidebar"] * {{
        color: var(--app-text);
    }}
    [data-testid="stSidebar"] label p,
    [data-testid="stSidebar"] .stCaption {{
        color: var(--app-text-secondary) !important;
    }}

    /* Caja de entrada del chat, fijada abajo — se quedaba con fondo blanco */
    html, body,
    [data-testid="stAppScrollToBottomContainer"],
    [data-testid="stBottomBlockContainer"],
    [data-testid="stChatInputContainer"] {{
        background-color: var(--app-bg);
    }}
    [data-testid="stChatInput"] {{
        background-color: var(--app-bg-card) !important;
        border: var(--app-border-width) solid var(--app-border) !important;
    }}
    [data-testid="stChatInput"] textarea {{
        color: var(--app-text) !important;
        background-color: transparent !important;
    }}
    [data-testid="stChatInput"] textarea::placeholder {{
        color: var(--app-text-secondary) !important;
        opacity: 1;
    }}

    /* Desplegables (idioma / tema) y sus menús emergentes */
    [data-baseweb="select"] > div {{
        background-color: var(--app-bg) !important;
        color: var(--app-text) !important;
        border: var(--app-border-width) solid var(--app-border) !important;
    }}
    [data-baseweb="select"] * {{
        color: var(--app-text) !important;
    }}
    [data-baseweb="popover"] [data-baseweb="menu"] {{
        background-color: var(--app-bg-card) !important;
    }}
    [data-baseweb="popover"] [data-baseweb="menu"] li {{
        color: var(--app-text) !important;
    }}

    /* Radios (tamaño de texto) — el punto rojo por defecto no encajaba */
    input[type="radio"], input[type="checkbox"] {{
        accent-color: var(--app-accent) !important;
    }}
    [data-testid="stSidebar"] [role="radiogroup"] label p {{
        color: var(--app-text) !important;
    }}

    .app-title {{
        font-size: {TITLE_FONT};
        font-weight: 800;
        color: var(--app-primary);
        margin-bottom: 0.1em;
    }}
    .app-subtitle {{
        color: var(--app-text-secondary);
        margin-bottom: 1.1em;
    }}

    .backend-badge {{
        display: inline-block;
        padding: 4px 12px;
        border-radius: 999px;
        border: var(--app-border-width) solid transparent;
        font-size: 13px;
        font-weight: 700;
        margin-bottom: 1em;
    }}
    .backend-mock {{ background: {theme['badge_mock_bg']}; color: {theme['badge_mock_text']}; }}
    .backend-local {{ background: {theme['badge_local_bg']}; color: {theme['badge_local_text']}; }}
    .backend-azure {{ background: {theme['badge_azure_bg']}; color: {theme['badge_azure_text']}; }}

    /* Burbujas de chat con buen contraste, esquinas suaves */
    [data-testid="stChatMessage"] {{
        border-radius: 18px;
        padding: 0.4em 0.2em;
        background-color: var(--app-bg-card);
        border: var(--app-border-width) solid var(--app-border);
        color: var(--app-text);
    }}
    [data-testid="stChatMessage"] p {{
        color: var(--app-text);
    }}

    /* Botones con área de toque generosa (accesibilidad para mayores) */
    button {{
        min-height: 44px !important;
        border-radius: 12px !important;
    }}
    .stButton > button {{
        background-color: var(--app-bg-card) !important;
        color: var(--app-text) !important;
        border: var(--app-border-width) solid var(--app-border) !important;
    }}

    .feedback-row {{
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: -8px;
        margin-bottom: 12px;
        color: var(--app-text-secondary);
        font-size: 0.85em;
    }}

    footer {{visibility: hidden;}}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Sidebar — idioma, tamaño de texto, estado de conexión
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"### {t(lang, 'sidebar_title')}")

    lang_options = list(LANGUAGES.keys())
    lang_labels = [f"{LANGUAGES[code]['flag']} {LANGUAGES[code]['label']}" for code in lang_options]
    selected_idx = lang_options.index(lang)
    new_idx = st.selectbox(
        t(lang, "sidebar_language"),
        options=range(len(lang_options)),
        format_func=lambda i: lang_labels[i],
        index=selected_idx,
    )
    if lang_options[new_idx] != st.session_state.lang:
        st.session_state.lang = lang_options[new_idx]
        st.rerun()

    st.markdown(
        "<div style='margin-top: 0.5rem; margin-bottom: 0.4rem; font-weight: 700;'>Modo de color</div>",
        unsafe_allow_html=True,
    )
    left_col, switch_col, right_col = st.columns([2.2, 1.2, 2.2])
    with left_col:
        st.caption("Alto contraste")
    with switch_col:
        theme_enabled = st.toggle(
            "",
            value=st.session_state.theme_mode == "dark",
            key="theme_switch",
        )
    with right_col:
        st.caption("Oscuro")

    new_theme_mode = "dark" if theme_enabled else "colorblind"
    if new_theme_mode != st.session_state.theme_mode:
        st.session_state.theme_mode = new_theme_mode
        st.rerun()

    text_size_choice = st.radio(
        t(lang, "sidebar_text_size"),
        options=["normal", "large"],
        format_func=lambda v: t(lang, f"text_size_{v}"),
        index=0 if st.session_state.text_size == "normal" else 1,
        horizontal=True,
    )
    if text_size_choice != st.session_state.text_size:
        st.session_state.text_size = text_size_choice
        st.rerun()

    st.divider()

    if st.button(t(lang, "clear_chat"), use_container_width=True):
        st.session_state.history = []
        st.session_state.feedback_given = set()
        st.rerun()

    st.divider()
    st.caption(t(lang, "footer"))


# ---------------------------------------------------------------------------
# Cabecera
# ---------------------------------------------------------------------------
st.markdown(f"<div class='app-title'>🚌 {APP_NAME}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='app-subtitle'>{t(lang, 'app_subtitle')}</div>", unsafe_allow_html=True)

_badge_class = {
    "mock": "backend-mock",
    "local": "backend-local",
    "azure": "backend-azure",
}
_last_backend = st.session_state.history[-1].get("backend") if st.session_state.history else agent_client.AGENT_BACKEND
_badge_key = "mock" if "mock" in (_last_backend or "mock") else ("azure" if "azure" in (_last_backend or "") else "local")
st.markdown(
    f"<span class='backend-badge {_badge_class[_badge_key]}'>{t(lang, f'backend_badge_{_badge_key}')}</span>",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Historial de chat
# ---------------------------------------------------------------------------
if not st.session_state.history:
    with st.chat_message("assistant"):
        st.write(t(lang, "welcome"))

for i, msg in enumerate(st.session_state.history):
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

        if msg["role"] == "assistant":
            if i in st.session_state.feedback_given:
                st.caption(t(lang, "feedback_thanks"))
            else:
                cols = st.columns([6, 1, 1])
                with cols[0]:
                    st.caption(t(lang, "feedback_prompt"))
                with cols[1]:
                    if st.button("👍", key=f"up_{i}"):
                        st.session_state.feedback_given.add(i)
                        with open(FEEDBACK_LOG, "a", encoding="utf-8") as f:
                            f.write(json.dumps({
                                "ts": datetime.now(timezone.utc).isoformat(),
                                "question": st.session_state.history[i - 1]["content"] if i > 0 else None,
                                "answer": msg["content"],
                                "backend": msg.get("backend"),
                                "feedback": "up",
                            }, ensure_ascii=False) + "\n")
                        st.rerun()
                with cols[2]:
                    if st.button("👎", key=f"down_{i}"):
                        st.session_state.feedback_given.add(i)
                        with open(FEEDBACK_LOG, "a", encoding="utf-8") as f:
                            f.write(json.dumps({
                                "ts": datetime.now(timezone.utc).isoformat(),
                                "question": st.session_state.history[i - 1]["content"] if i > 0 else None,
                                "answer": msg["content"],
                                "backend": msg.get("backend"),
                                "feedback": "down",
                            }, ensure_ascii=False) + "\n")
                        st.rerun()


# ---------------------------------------------------------------------------
# Input del usuario
# ---------------------------------------------------------------------------
question = st.chat_input(t(lang, "chat_placeholder"))

if question:
    st.session_state.history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner(t(lang, "thinking")):
            answer_text, backend_used = agent_client.ask(question, lang=lang)
        st.write(answer_text)

    st.session_state.history.append({
        "role": "assistant",
        "content": answer_text,
        "backend": backend_used,
    })
    st.rerun()
