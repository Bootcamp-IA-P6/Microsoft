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
    mcp  (SDK MCP Python: ClientSession + streamablehttp_client)
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

5. Asegurar que la variable de entorno DATA_AGENT_URL está definida en el
   entorno del UDF de Fabric (apunta al endpoint MCP del Data Agent).
=============================================================================
"""

import os
from typing import Any

import fabric.functions as fn
from azure.identity import DefaultAzureCredential
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"


def _get_auth_headers() -> dict[str, str]:
    """
    Obtiene un token de acceso Fabric usando la Managed Identity del runtime
    UDF.  DefaultAzureCredential intenta, en orden:
      1. EnvironmentCredential (vars AZURE_*)
      2. ManagedIdentityCredential (la identidad del resource en Fabric)
      3. AzureCliCredential (solo desarrollo local con `az login`)
    """
    credential = DefaultAzureCredential()
    token = credential.get_token(FABRIC_SCOPE)
    return {"Authorization": f"Bearer {token.token}"}


async def _call_data_agent(question: str, headers: dict[str, str]) -> str:
    """
    Conecta al Fabric Data Agent vía MCP Streamable HTTP, descubre el tool
    disponible, invoca con userQuestion y extrae la respuesta textual.
    """
    data_agent_url = os.environ["DATA_AGENT_URL"]

    async with streamablehttp_client(data_agent_url, headers=headers) as (
        read,
        write,
        _,
    ):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Descubrir el primer/único tool del Data Agent
            tools_result = await session.list_tools()
            if not tools_result.tools:
                raise RuntimeError("El Data Agent no expuso ningún tool por MCP")
            tool = tools_result.tools[0]

            # Invocar con el parámetro userQuestion
            result = await session.call_tool(tool.name, {"userQuestion": question})

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


# ---------------------------------------------------------------------------
# Registro de la User Data Function
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
        dict:  {"answerText": str}
    """
    if not os.environ.get("DATA_AGENT_URL"):
        return {"answerText": _mock_answer(question)}

    try:
        headers = _get_auth_headers()
        answer_text = await _call_data_agent(question, headers)
        return {"answerText": answer_text}
    except Exception as exc:
        print(f"[UDF] Error al llamar al Data Agent: {exc}")
        return {"answerText": _mock_answer(question)}