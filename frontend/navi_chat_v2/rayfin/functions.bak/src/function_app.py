"""
function_app.py
---------------
Fabric User Data Function (Python) — proxy de chat hacia el Fabric Data Agent
vía protocolo MCP sobre Streamable HTTP.

Contrato de entrada/salida:
    @udf.function()
    def chat(question: str, language: str) -> dict:
        returns {"answerText": str}

El runtime de Fabric UDF provee el módulo `fabric.functions` de forma nativa;
no se instala por pip.  Este archivo se sube directamente a través del portal
de Fabric (Fabric UDF) o la API REST de UserDataFunctions.

Dependencias pip necesarias en el entorno UDF:
    mcp  (SDK MCP Python: ClientSession + streamable_http_client)
    azure-identity  (ManagedIdentityCredential / DefaultAzureCredential)

=============================================================================
PASOS MANUALES FUERA DE ESTE CÓDIGO (no los ejecuto yo):
=============================================================================
1. Habilitar acceso público al UDF en la configuración del item de Fabric
   (Fabric portal → User Data Functions → Settings → Allow anonymous access).

2. Registrar una aplicación en Entra ID (Azure AD) para el frontend:
   - App registration → Redirect URI:
       https://handy-north-cb414576f1-westeurope.webapp.fabricapps.net
   - Authentication → "Allow public client flows" = Yes

3. Agregar el permiso delegado a la app registrada:
   - API permissions → Add a permission → Microsoft APIs → Fabric
   - Permission: UserDataFunction.Execute.All (delegated)

4. Configurar CORS en el UDF (o en el gateway de Fabric si aplica) para
   aceptar el origen del frontend:
       https://handy-north-cb414576f1-westeurope.webapp.fabricapps.net

5. Asegurar que DATA_AGENT_URL o FABRIC_MCP_URL está definida en el
   entorno del UDF de Fabric (apunta al endpoint MCP del Data Agent).
=============================================================================
"""

import os
import re
import time
from typing import Any

import fabric.functions as fn
from azure.identity import DefaultAzureCredential
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"

# Caché global a nivel de módulo (persiste entre requests del runtime UDF)
_cached_token: str | None = None
_token_expires_at: float = 0
_cached_tool_name: str | None = None


_credential = DefaultAzureCredential()


def _get_auth_headers() -> dict[str, str]:
    """
    Obtiene un token de acceso Fabric usando la Managed Identity del runtime
    UDF, con caché (refresca 60 s antes de expirar).
    DefaultAzureCredential intenta, en orden:
      1. EnvironmentCredential (vars AZURE_*)
      2. ManagedIdentityCredential (la identidad del resource en Fabric)
      3. AzureCliCredential (solo desarrollo local con `az login`)
    """
    global _cached_token, _token_expires_at

    now = time.time()
    if not _cached_token or now >= _token_expires_at - 60:
        token = _credential.get_token(FABRIC_SCOPE)
        _cached_token = token.token
        _token_expires_at = token.expires_on

    return {"Authorization": f"Bearer {_cached_token}"}


def _get_data_agent_url() -> str:
    """
    Resuelve la URL del Data Agent probando DATA_AGENT_URL primero y
    FABRIC_MCP_URL como fallback (compatibilidad con agent_mcp.py).
    """
    url = os.getenv("DATA_AGENT_URL") or os.getenv("FABRIC_MCP_URL")
    if not url:
        raise RuntimeError(
            "Falta definir DATA_AGENT_URL o FABRIC_MCP_URL en el entorno del UDF."
        )
    return url


async def _call_data_agent(question: str, headers: dict[str, str]) -> str:
    """
    Conecta al Fabric Data Agent vía MCP Streamable HTTP, descubre el tool
    disponible (con caché), invoca con userQuestion y extrae la respuesta textual.
    """
    global _cached_tool_name

    data_agent_url = _get_data_agent_url()

    async with streamable_http_client(data_agent_url, headers=headers) as (
        read,
        write,
        _,
    ):
        async with ClientSession(read, write) as session:
            await session.initialize()

            if _cached_tool_name is None:
                tools_result = await session.list_tools()
                if not tools_result.tools:
                    raise RuntimeError("El Data Agent no expuso ningún tool por MCP")
                _cached_tool_name = tools_result.tools[0].name

            result = await session.call_tool(
                _cached_tool_name, {"userQuestion": question}
            )

            if result.isError:
                raise RuntimeError(
                    f"Data Agent devolvió error: {result.content}"
                )

            text_parts = [
                c.text
                for c in (result.content or [])
                if hasattr(c, "type") and c.type == "text" and hasattr(c, "text")
            ]
            return "\n".join(text_parts) or "No se pudo obtener respuesta."


def _enrich_response(text: str) -> dict[str, Any]:
    """
    Parsea el texto plano del Data Agent y extrae metadatos estructurados
    (stop_id, line_number, wait_time) para construir el contrato
    ChatEnrichedResponse.  map_data se deja como None porque las
    coordenadas se resuelven desde el lado cliente.
    """
    chat: dict[str, Any] = {"text": text}
    map_data: Any = None

    m = re.search(r"parada\s+(\d{3,5})", text, re.IGNORECASE)
    if m:
        chat["stop_id"] = m.group(1)

    m = re.search(r"l[ií]neas?\s*(\d+)", text, re.IGNORECASE)
    if m:
        chat["line_number"] = m.group(1)

    m = re.search(r"parada\s+\d+\s*[\(]?([A-Za-zÁÉÍÓÚÑáéíóúñ\s]+)[\)]?", text)
    if m:
        candidate = m.group(1).strip().rstrip(")")
        if candidate:
            chat["stop_name"] = candidate

    m = re.search(r"(?:en|tarda)\s*(\d+)\s*(?:minutos?|min)", text, re.IGNORECASE)
    if m:
        chat["wait_time"] = f"{m.group(1)} min"

    return {"chat_message": chat, "map_data": map_data}


def _mock_answer(question: str) -> str:
    """Respuesta simulada para desarrollo local sin Data Agent."""
    q = question.lower()
    if "cercanías" in q or "renfe" in q:
        return (
            "La estación de Cercanías más cercana es Sol. "
            "Puedes tomar la línea C-3 o C-4."
        )
    if "autobús" in q or "bus" in q:
        return (
            'La parada de autobús más cercana es "Gran Vía - Montera" '
            "(líneas 51, 146)."
        )
    if "metro" in q:
        return "La estación de Metro más cercana es Gran Vía (líneas 1, 5)."
    return (
        "Madrid tiene una amplia red de transporte. "
        "¿Qué tipo de transporte te interesa?"
    )


def _validate_feedback(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Valida y normaliza el payload de feedback entrante.
    Retorna el payload limpio o lanza ValueError si es inválido.
    """
    msg_id = payload.get("message_id")
    fb_type = payload.get("feedback_type")
    if not msg_id:
        raise ValueError("message_id es requerido")
    if fb_type not in ("like", "dislike"):
        raise ValueError("feedback_type debe ser 'like' o 'dislike'")
    return {
        "message_id": str(msg_id),
        "feedback_type": fb_type,
        "question": str(payload.get("question", "")),
        "answer_text": str(payload.get("answer_text", "")),
        "timestamp": int(payload.get("timestamp", time.time() * 1000)),
    }


# ---------------------------------------------------------------------------
# Registro de las User Data Functions
# ---------------------------------------------------------------------------

udf = fn.UserDataFunctions()


@udf.function()
async def chat(question: str, language: str) -> dict[str, Any]:
    """
    Proxy de chat hacia el Fabric Data Agent.

    Parámetros:
        question (str):  Pregunta del usuario en lenguaje natural.
        language  (str): Código de idioma (ej. "es", "en").

    Retorna:
        dict:  {"chat_message": {"text": str, "stop_id"?: str, ...}, "map_data": null}
    """
    if not os.getenv("DATA_AGENT_URL") and not os.getenv("FABRIC_MCP_URL"):
        return _enrich_response(_mock_answer(question))

    try:
        headers = _get_auth_headers()
        answer_text = await _call_data_agent(question, headers)
        return _enrich_response(answer_text)
    except Exception as exc:
        print(f"[UDF] Error al llamar al Data Agent: {exc}")
        return _enrich_response(_mock_answer(question))


@udf.function()
def save_feedback(
    message_id: str,
    feedback_type: str,
    question: str,
    answer_text: str,
    timestamp: int,
) -> dict[str, Any]:
    """
    Recibe feedback del usuario (like/dislike) sobre una respuesta.
    Por ahora persiste en logs; en producción conectar a una tabla
    Fabric Lakehouse / Kusto / SQL.

    Parámetros:
        message_id    (str): ID único del mensaje en el frontend.
        feedback_type (str): "like" o "dislike".
        question      (str): Pregunta original del usuario.
        answer_text   (str): Respuesta del agente.
        timestamp     (int): Timestamp (ms) del mensaje original.

    Retorna:
        dict: {"status": "ok", "message_id": str}
    """
    payload = _validate_feedback({
        "message_id": message_id,
        "feedback_type": feedback_type,
        "question": question,
        "answer_text": answer_text,
        "timestamp": timestamp,
    })

    print(f"[FEEDBACK] message_id={payload['message_id']} "
          f"type={payload['feedback_type']} "
          f"question={payload['question']!r} "
          f"answer_len={len(payload['answer_text'])}")
    return {"status": "ok", "message_id": payload["message_id"]}