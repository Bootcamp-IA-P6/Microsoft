from __future__ import annotations

import asyncio
import importlib.util
import os
import logging
from pathlib import Path

import mock_client  # el mock_client.py de frontend/, sin tocar — ya funcionaba

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent_client")

AGENT_BACKEND = os.environ.get("AGENT_BACKEND", "azure")  # "mock" | "local" | "azure"

# --- Carga explícita de agent_mcp.py por ruta de archivo, SIN tocar sys.path ---
# Esto evita cualquier colisión con otro módulo que se llame igual en el
# proyecto (como pasó con mock_client). No hace falta sys.path.insert para
# nada de esto.
_AGENT_MCP_PATH = Path(__file__).resolve().parents[1] / "agents" / "emt_specialist" / "agent_mcp.py"


def _load_agent_mcp_module():
    spec = importlib.util.spec_from_file_location("emt_agent_mcp_module", _AGENT_MCP_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_azure_agent = None  # singleton perezoso


def _get_azure_agent():
    global _azure_agent
    if _azure_agent is None:
        mod = _load_agent_mcp_module()
        _azure_agent = mod.EMTAgentMCP()
    return _azure_agent


def ask(question: str, lang: str = "es") -> tuple[str, str]:
    """Punto de entrada único usado por app.py."""
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

    return mock_client.answer(question), "mock"


def _ask_local_agent(question: str, lang: str) -> str:
    raise NotImplementedError()


def _ask_azure_agent(question: str, lang: str) -> str:
    agent = _get_azure_agent()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    if loop.is_running():
        # Si Streamlit ya tiene un loop corriendo en este hilo
        import nest_asyncio
        nest_asyncio.apply()
        return loop.run_until_complete(agent.ask(question, verbose=False))
    else:
        return loop.run_until_complete(agent.ask(question, verbose=False))