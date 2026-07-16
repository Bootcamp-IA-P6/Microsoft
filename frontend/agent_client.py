"""
agent_client.py — Capa única por la que el frontend habla con "el agente",
sin que a app.py le importe si detrás hay Fabric+Azure, un agente local,
o el mock de Fase 2.

Cómo cambiar de backend
------------------------
Ajusta AGENT_BACKEND más abajo (o la variable de entorno AGENT_BACKEND):

    "mock"   -> usa mock_client.py (fixtures locales). Es el default hoy.
    "local"  -> llama al agente que Raúl ya tiene corriendo en local.
    "azure"  -> llama al Data Agent desplegado en Azure/Fabric vía MCP.

Si el backend elegido falla (no está levantado, credenciales no puestas,
etc.), se hace fallback automático a "mock" para que la demo nunca se
quede sin responder — pero se avisa en la respuesta y en los logs.
"""

from __future__ import annotations

import os
import logging

import mock_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent_client")

# ---------------------------------------------------------------------------
# Selector de backend. Cambiar aquí cuando haya algo real que probar,
# o exportar la variable de entorno AGENT_BACKEND antes de correr streamlit.
# ---------------------------------------------------------------------------
AGENT_BACKEND = os.environ.get("AGENT_BACKEND", "mock")  # "mock" | "local" | "azure"


def ask(question: str, lang: str = "es") -> tuple[str, str]:
    """
    Punto de entrada único usado por app.py.

    Devuelve (respuesta, backend_usado) — el segundo valor es solo para
    mostrar en la UI un pequeño indicador de "modo demo" vs "en vivo",
    útil mientras seguimos conectando piezas.
    """
    if AGENT_BACKEND == "azure":
        try:
            return _ask_azure_agent(question, lang), "azure"
        except Exception as e:
            logger.warning("Fallo conexión Azure, usando mock. Detalle: %s", e)
            return mock_client.answer(question), "mock (fallback: azure no disponible)"

    if AGENT_BACKEND == "local":
        try:
            return _ask_local_agent(question, lang), "local"
        except Exception as e:
            logger.warning("Fallo conexión agente local, usando mock. Detalle: %s", e)
            return mock_client.answer(question), "mock (fallback: local no disponible)"

    # default / explícito
    return mock_client.answer(question), "mock"


# ---------------------------------------------------------------------------
# TODO (Raúl / equipo AI Developer): agente LOCAL — plan B
# ---------------------------------------------------------------------------
# Cuando el agente local esté listo para conectarse desde fuera de su propio
# notebook/proceso, esta función es la única que hay que rellenar.
#
# Dos formas típicas de exponerlo, elige la que ya tengan montada:
#
#   (a) Si el agente corre como servidor HTTP local (ej. FastAPI en :8000):
#
#       import requests
#       def _ask_local_agent(question: str, lang: str) -> str:
#           resp = requests.post(
#               "http://localhost:8000/ask",
#               json={"question": question, "lang": lang},
#               timeout=15,
#           )
#           resp.raise_for_status()
#           return resp.json()["answer"]
#
#   (b) Si el agente es importable directamente como función Python
#       (mismo entorno, sin red):
#
#       from local_agent import run_agent  # ajustar import real
#       def _ask_local_agent(question: str, lang: str) -> str:
#           return run_agent(question, lang=lang)
#
def _ask_local_agent(question: str, lang: str) -> str:
    raise NotImplementedError(
        "Conectar aquí con el agente local de Raúl. Ver comentario TODO arriba."
    )


# ---------------------------------------------------------------------------
# TODO (equipo, cuando haya acceso F4 + despliegue en Azure): Data Agent
# vía MCP — el backend "de verdad" para producción
# ---------------------------------------------------------------------------
# Idea general: el servidor MCP (Fase 4) expone el agente como una tool
# (ask_dataagent). Desde Streamlit Cloud, este proceso hace de cliente MCP
# y llama a esa tool contra el servidor MCP desplegado en Azure.
#
# Con el SDK oficial de Anthropic + MCP (usar el mismo patrón que en las
# llamadas server-side de la API, ver docs de Anthropic sobre mcp_servers):
#
#   import anthropic
#   client = anthropic.Anthropic()  # ANTHROPIC_API_KEY en Streamlit secrets
#
#   def _ask_azure_agent(question: str, lang: str) -> str:
#       response = client.messages.create(
#           model="claude-sonnet-4-6",
#           max_tokens=1000,
#           messages=[{"role": "user", "content": question}],
#           mcp_servers=[{
#               "type": "url",
#               "url": os.environ["MCP_SERVER_URL"],  # URL del server MCP en Azure
#               "name": "emt-data-agent",
#           }],
#       )
#       # extraer el texto de la respuesta (puede venir en varios content blocks)
#       texts = [b.text for b in response.content if b.type == "text"]
#       return "\n".join(texts)
#
# Credenciales/URLs a poner en Streamlit Cloud > Settings > Secrets, NUNCA
# hardcodeadas en este archivo:
#   ANTHROPIC_API_KEY, MCP_SERVER_URL, (lo que pida Fabric/Azure AD si aplica)
#
def _ask_azure_agent(question: str, lang: str) -> str:
    raise NotImplementedError(
        "Conectar aquí con el Data Agent desplegado en Azure vía MCP. "
        "Ver comentario TODO arriba — pendiente de permisos F4."
    )
