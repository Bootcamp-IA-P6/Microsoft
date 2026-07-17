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
import os
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

import agent_client

try:
    import azure.cognitiveservices.speech as speechsdk
except ImportError:  # pragma: no cover - fallback para entornos sin paquete aún instalado
    speechsdk = None
from i18n import LANGUAGES, t
from themes import THEMES, APP_TITLE, APP_TAGLINE, APP_USAGE, get_theme

FEEDBACK_LOG = Path(__file__).parent / "feedback_log.jsonl"
MAP_IMAGE_PATH = Path(__file__).parent / "assets" / "mapa.png"
NAVI_ICON_PATH = Path(__file__).parent / "assets" / "navi_icon.svg"
NAVI_AVATAR_PATH = Path(__file__).parent / "assets" / "navi_avatar.svg"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_env_file() -> None:
    """Carga variables desde el archivo .env del proyecto si existe."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()


def transcribe_from_microphone() -> tuple[str | None, str | None]:
    """Transcribe una frase desde el micrófono usando Azure Speech."""
    if speechsdk is None:
        return None, "La librería azure-cognitiveservices-speech no está instalada."

    region = st.session_state.get("azure_speech_region", "") or os.getenv("AZURE_SPEECH_REGION", "")
    key = st.session_state.get("azure_speech_key", "") or os.getenv("AZURE_SPEECH_KEY", "")
    language = st.session_state.get("azure_speech_language", "") or os.getenv("AZURE_SPEECH_LANGUAGE", "es-ES")

    if not region or not key:
        return None, "Faltan AZURE_SPEECH_REGION o AZURE_SPEECH_KEY en el archivo .env."

    try:
        speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        speech_config.speech_recognition_language = language
        audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
        recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

        result = recognizer.recognize_once_async().get()

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return result.text, None
        if result.reason == speechsdk.ResultReason.NoMatch:
            return None, "No se detectó voz. Inténtalo de nuevo."
        if result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speechsdk.CancellationDetails.from_result(result)
            return None, f"Reconocimiento cancelado: {cancellation_details.reason}"
        return None, "No se pudo transcribir la voz."
    except Exception as exc:  # pragma: no cover - depende del entorno del usuario
        return None, f"Error al conectar con Azure Speech: {exc}"


# ---------------------------------------------------------------------------
# Configuración de página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=f"{APP_TITLE} —  {APP_TAGLINE}",
    page_icon=str(NAVI_ICON_PATH),
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
if "azure_speech_region" not in st.session_state:
    st.session_state.azure_speech_region = os.getenv("AZURE_SPEECH_REGION", "")
if "azure_speech_key" not in st.session_state:
    st.session_state.azure_speech_key = os.getenv("AZURE_SPEECH_KEY", "")
if "azure_speech_language" not in st.session_state:
    st.session_state.azure_speech_language = os.getenv("AZURE_SPEECH_LANGUAGE", "es-ES")
if "chat_input_text" not in st.session_state:
    st.session_state.chat_input_text = ""
if "voice_status" not in st.session_state:
    st.session_state.voice_status = ""

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
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');

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
        background-color: var(--app-bg) !important;
    }}
    [data-testid="stChatInput"] {{
        background-color: var(--app-bg) !important;
        border: var(--app-border-width) solid var(--app-border) !important;
        color: var(--app-text) !important;
        box-shadow: none !important;
        color-scheme: dark !important;
    }}
    [data-testid="stChatInput"] > div,
    [data-testid="stChatInput"] > div > div,
    [data-testid="stChatInput"] > div > div > div,
    [data-testid="stChatInput"] div,
    [data-testid="stChatInput"] textarea,
    [data-testid="stChatInput"] input,
    [data-testid="stChatInput"] [contenteditable="true"],
    [data-testid="stChatInput"] [contenteditable="plaintext-only"] {{
        color: var(--app-text) !important;
        background-color: var(--app-bg) !important;
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        caret-color: var(--app-text) !important;
        -webkit-text-fill-color: var(--app-text) !important;
        -webkit-appearance: none !important;
        appearance: none !important;
        color-scheme: dark !important;
    }}
    textarea:focus,
    input:focus,
    [contenteditable="true"]:focus,
    [contenteditable="plaintext-only"]:focus {{
        color: var(--app-text) !important;
        background-color: var(--app-bg) !important;
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        -webkit-text-fill-color: var(--app-text) !important;
    }}
    textarea::placeholder,
    input::placeholder {{
        color: var(--app-text-secondary) !important;
        opacity: 1 !important;
    }}
    ::selection {{
        background-color: var(--app-accent) !important;
        color: var(--app-bg) !important;
    }}
    

    /* Fondo de la zona de chat, que se quedaba blanco al hacer scroll y desplegable del mapa */
    [data-testid="stBottom"] > div {{
        background-color: var(--app-bg) !important;
    }}
    [data-testid="stExpander"] {{
        background-color: var(--app-bg-card) !important;
        border: var(--app-border-width) solid var(--app-border) !important;
        border-radius: 12px !important;
    }}
    [data-testid="stExpander"] > div:first-child {{
        background-color: var(--app-bg-card) !important;
        color: var(--app-text) !important;
        border-radius: 12px !important;
    }}
    [data-testid="stExpander"] > div:nth-child(2) {{
        background-color: var(--app-bg-card) !important;
        color: var(--app-text) !important;
        border-radius: 0 0 12px 12px !important;
    }}
    [data-testid="stExpander"] summary {{
        background-color: var(--app-bg-card) !important;
        color: var(--app-text) !important;
    }}
    [data-testid="stExpander"] summary span {{
        color: var(--app-text) !important;
    }}
    [data-testid="stExpander"] * {{
        color: var(--app-text) !important;
    }}
    [data-testid="stExpander"]:hover {{
        background-color: var(--app-bg-card) !important;
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
        font-family: 'Nunito', sans-serif;
    }}
    .app-tagline {{
        color: var(--app-primary);
        margin-bottom: 0.25em;
        font-family: 'Poppins', sans-serif;
        font-weight: 600;
        font-size: 0.95em;
    }}
    .app-usage {{
        color: var(--app-text-secondary);
        margin-bottom: 1.1em;
        font-family: 'Poppins', sans-serif;
        font-size: 0.92em;
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

    st.markdown(
        "<div style='margin-top: 0.7rem; margin-bottom: 0.4rem; font-weight: 700;'>Tamaño de texto</div>",
        unsafe_allow_html=True,
    )
    left_col, switch_col, right_col = st.columns([2.2, 1.2, 2.2])
    with left_col:
        st.caption("Normal")
    with switch_col:
        text_size_enabled = st.toggle(
            "",
            value=st.session_state.text_size == "large",
            key="text_size_switch",
        )
    with right_col:
        st.caption("Grande")

    text_size_choice = "large" if text_size_enabled else "normal"
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
header_col1, header_col2 = st.columns([1, 8])
with header_col1:
    st.image(str(NAVI_ICON_PATH), width=48)
with header_col2:
    st.markdown(
        f"<div class='app-title' style='display: inline-block; margin-bottom: 0.1em; margin-right: 0.4em;'>{APP_TITLE}</div>"
        f"<div class='app-tagline' style='display: inline-block; margin-bottom: 0.1em;'> —  {APP_TAGLINE}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(f"<div class='app-usage' style='margin-top: 0; margin-bottom: 0.8em;'>{APP_USAGE}</div>", unsafe_allow_html=True)

if MAP_IMAGE_PATH.exists():
    with st.expander("🗺️ Ver mapa del alcance"):
        st.caption("Mapa del alcance del servicio")
        st.image(str(MAP_IMAGE_PATH), use_container_width=True)
else:
    st.info("Añade tu imagen PNG en la carpeta assets con el nombre mapa.png para mostrar el mapa del alcance.")

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
    with st.chat_message("assistant", avatar=str(NAVI_AVATAR_PATH)):
        st.write(t(lang, "welcome"))

for i, msg in enumerate(st.session_state.history):
    avatar = str(NAVI_AVATAR_PATH) if msg["role"] == "assistant" else None
    with st.chat_message(msg["role"], avatar=avatar):
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
with st.form("chat_form", clear_on_submit=False):
    cols = st.columns([7, 1, 1])
    with cols[0]:
        question = st.text_input(
            "",
            key="chat_input_text",
            label_visibility="collapsed",
            placeholder=t(lang, "chat_placeholder"),
        )
    with cols[1]:
        send_clicked = st.form_submit_button("➤", help=t(lang, "send_message"))
    with cols[2]:
        mic_clicked = st.form_submit_button("🎙️", help=t(lang, "voice_button_help"))

    if mic_clicked:
        transcript, error = transcribe_from_microphone()
        if transcript:
            st.session_state.chat_input_text = transcript
            st.session_state.voice_status = t(lang, "voice_transcribed")
            st.toast(t(lang, "voice_transcribed"))
        else:
            st.session_state.voice_status = error or t(lang, "voice_error")
            st.toast(error or t(lang, "voice_error"))
        st.rerun()

    if send_clicked and question:
        st.session_state.history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.write(question)

        with st.chat_message("assistant", avatar=str(NAVI_AVATAR_PATH)):
            with st.spinner(t(lang, "thinking")):
                answer_text, backend_used = agent_client.ask(question, lang=lang)
            st.write(answer_text)

        st.session_state.history.append({
            "role": "assistant",
            "content": answer_text,
            "backend": backend_used,
        })
        st.session_state.chat_input_text = ""
        st.session_state.voice_status = ""
        st.rerun()

if st.session_state.get("voice_status"):
    st.caption(st.session_state["voice_status"])
