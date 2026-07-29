"""
agent_mcp.py
------------
Cliente MCP simple para el Fabric Data Agent (EMT Madrid), expuesto como
servidor MCP remoto sobre streamable HTTP.

CAMBIO DE DISEÑO (2026-07-23): ya no orquesta con un LLM propio (Claude/
Anthropic). El Data Agent expone un único tool (el agente mismo) y ya
devuelve la respuesta final redactada en lenguaje natural usando sus propias
Instructions configuradas en el portal de Fabric — no hace falta volver a
redactar de este lado. Esto además cumple el mandato del stakeholder de no
usar proveedores fuera de Microsoft/Azure/Fabric.

Requiere: pip install mcp azure-identity python-dotenv --break-system-packages
Variables de entorno (.env):
    FABRIC_MCP_URL=https://api.fabric.microsoft.com/v1/mcp/workspaces/{WorkspaceId}/dataagents/{DataAgentId}/agent
"""

import os
from pathlib import Path
import time

from azure.identity import AzureCliCredential
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

MCP_URL = os.environ.get("FABRIC_MCP_URL")
FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"


class EMTAgentMCP:
    
    def __init__(self, mcp_url: str = MCP_URL):
        if not mcp_url:
            raise RuntimeError("Falta FABRIC_MCP_URL en .env")
        self.mcp_url = mcp_url

        # Parche de seguridad por si Git Bash / Windows arrastran un
        # SSL_CERT_FILE roto (heredado del agent_mcp.py original).
        if "SSL_CERT_FILE" in os.environ and not os.path.exists(os.environ["SSL_CERT_FILE"]):
            del os.environ["SSL_CERT_FILE"]

        self._credential = AzureCliCredential()
        self._tool_name: str | None = None
        self._cached_token: str | None = None
        self._token_expires_at: float = 0

    def _get_headers(self) -> dict:
        now = time.time()
        if not self._cached_token or now >= self._token_expires_at - 60:
            token = self._credential.get_token(FABRIC_SCOPE)
            self._cached_token = token.token
            self._token_expires_at = token.expires_on
        return {"Authorization": f"Bearer {self._cached_token}"}

    async def _resolve_tool_name(self, session: ClientSession) -> str:
        if self._tool_name:
            return self._tool_name
        tools_result = await session.list_tools()
        if not tools_result.tools:
            raise RuntimeError("El Data Agent no expuso ningún tool por MCP")
        
        tool = tools_result.tools[0]
        print(f"\n[DEBUG] Esquema exacto de entrada del tool '{tool.name}':")
        print(tool.inputSchema)
        print("-" * 50)
        
        self._tool_name = tool.name
        return self._tool_name

    async def ask(self, question: str, verbose: bool = False) -> str:
        async with streamablehttp_client(self.mcp_url, headers=self._get_headers()) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tool_name = await self._resolve_tool_name(session)

                if verbose:
                    print(f"  [tool_use MCP] {tool_name}(userQuestion={question!r})")

                # Invocación con el parámetro correcto: userQuestion
                result = await session.call_tool(tool_name, {"userQuestion": question})
                answer = result.content[0].text if result.content else "No obtuve respuesta del agente."

                if verbose:
                    print(f"  [tool_result MCP] {answer}")

                return answer


async def main():
    agent = EMTAgentMCP()
    pregunta = "¿Cuánto tarda la línea 5 en llegar a la parada 5907?"
    print("P:", pregunta)
    respuesta = await agent.ask(pregunta, verbose=True)
    print("R:", respuesta)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())