"""
agent.py

Agente especialista EMT (Fase 3, Issue 3) corriendo contra el mock, usando la
Anthropic API como backend LLM (Plan B mientras se resuelven accesos Azure).

CONTRATO DE REEMPLAZO:
- El bloque `call_llm` es el ÚNICO que cambia al migrar a Azure OpenAI /
    Fabric Data Agent, o a otro proveedor (Groq, OpenRouter, NVIDIA NIM...).
    El resto (tools, system prompt, mock_client) no se toca.
- Cuando Z2 cierre gold real, solo se reemplaza mock_client.py -> fabric_client.py
    con las mismas 4 firmas.

"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from anthropic import Anthropic

from mock_client import MockDataClient

# Carga .env desde la raíz del repo, sin importar desde dónde se ejecute el script.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

MODEL = "claude-sonnet-5"  # Sonnet 5 es buen balance costo/calidad para este agente.
PROMPT_PATH = Path(__file__).resolve().parent / "system_prompt_v1.txt"

# ---- Definición de tools (mapea 1:1 a los métodos de mock_client) ----

TOOLS = [
    {
        "name": "get_gold_by_stop",
        "description": "Devuelve todas las líneas con ETA para una parada (stop_id).",
        "input_schema": {
            "type": "object",
            "properties": {"stop_id": {"type": "integer"}},
            "required": ["stop_id"],
        },
    },
    {
        "name": "get_gold_by_stop_line",
        "description": (
            "Devuelve el ETA de una línea específica en una parada específica. "
            "Devuelve null si la línea no pasa por esa parada."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "stop_id": {"type": "integer"},
                "line_id": {"type": "string", "description": "Código de línea, ej. '001' para M1"},
            },
            "required": ["stop_id", "line_id"],
        },
    },
    {
        "name": "search_stop_by_name",
        "description": "Busca paradas por nombre (coincidencia parcial). Usar cuando el usuario da un nombre en vez de un código.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "get_lines_for_stop",
        "description": "Lista todas las líneas que sirven una parada según el catálogo estático (sin ETA en vivo).",
        "input_schema": {
            "type": "object",
            "properties": {"stop_id": {"type": "integer"}},
            "required": ["stop_id"],
        },
    },
]


class EMTAgent:
    def __init__(self, fixtures_path: str = None, prompt_path: Path = PROMPT_PATH):
        self.client_data = MockDataClient(fixtures_path)
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Falta ANTHROPIC_API_KEY. Creá un archivo .env en la raíz del "
                "repo (copiá .env.example) con tu key ahí."
            )
        self.llm = Anthropic(api_key=api_key)

    def _execute_tool(self, name: str, tool_input: dict):
        method = getattr(self.client_data, name)
        return method(**tool_input)

    def call_llm(self, messages: list) -> dict:
        """Único punto de contacto con el LLM. Cambiar acá al migrar de proveedor."""
        return self.llm.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=self.system_prompt,
            tools=TOOLS,
            messages=messages,
        )

    def ask(self, question: str, verbose: bool = False) -> str:
        messages = [{"role": "user", "content": question}]

        while True:
            response = self.call_llm(messages)

            if response.stop_reason != "tool_use":
                # Respuesta final en texto
                text_blocks = [b.text for b in response.content if b.type == "text"]
                return "\n".join(text_blocks)

            # Hay tool calls: ejecutarlas y devolver los resultados
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                if verbose:
                    print(f"  [tool_use] {block.name}({block.input})")
                try:
                    result = self._execute_tool(block.name, block.input)
                except Exception as e:
                    result = {"error": str(e)}
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })
            messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    agent = EMTAgent()
    pregunta = "¿Cuánto tarda la línea M1 en llegar a la parada 4035?"
    print("P:", pregunta)
    print("R:", agent.ask(pregunta, verbose=True))
