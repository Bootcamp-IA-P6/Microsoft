"""
agent_groq.py
-------------
Agente especialista EMT adaptado para Groq (SDK compatible con OpenAI).
Plan B de Plan B: mientras Anthropic API no tiene crédito cargado, esto corre
gratis contra Groq. Mismo mock_client y system_prompt que agent.py.

NOTA SOBRE EL MODELO:
llama-3.3-70b-versatile es conocido por generar tool calls mal formadas
ocasionalmente (error 400 'tool_use_failed', ver docs de Groq:
https://console.groq.com/docs/tool-use/local-tool-calling). Usamos
openai/gpt-oss-120b, que es el modelo que la propia documentación de Groq
usa en sus ejemplos de tool calling por ser más confiable en esto.
Igual agregamos reintento con temperatura reducida, patrón oficial de Groq
para este caso.
"""

import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from mock_client import MockDataClient

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

MODEL = "openai/gpt-oss-120b"  # más confiable que llama-3.3-70b para tool calling
PROMPT_PATH = Path(__file__).resolve().parent / "system_prompt_v1.txt"
MAX_RETRIES = 3

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_gold_by_stop",
            "description": "Devuelve todas las líneas con ETA para una parada (stop_id).",
            "parameters": {
                "type": "object",
                "properties": {"stop_id": {"type": "integer"}},
                "required": ["stop_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_gold_by_stop_line",
            "description": "Devuelve el ETA de una línea específica en una parada específica. Devuelve null si la línea no pasa por esa parada.",
            "parameters": {
                "type": "object",
                "properties": {
                    "stop_id": {"type": "integer"},
                    "line": {"type": "string", "description": "Código interno (ej. '001') o etiqueta visible (ej. 'M1'), cualquiera de los dos sirve"},
                },
                "required": ["stop_id", "line"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_stop_by_name",
            "description": "Busca paradas por nombre (coincidencia parcial). Usar cuando el usuario da un nombre de calle/parada en vez de un código.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_lines_for_stop",
            "description": "Lista todas las líneas que sirven una parada según el catálogo estático (sin ETA en vivo).",
            "parameters": {
                "type": "object",
                "properties": {"stop_id": {"type": "integer"}},
                "required": ["stop_id"],
            },
        },
    },
]


class EMTAgent:
    def __init__(self, fixtures_path: str = None, prompt_path: Path = PROMPT_PATH):
        self.client_data = MockDataClient(fixtures_path)
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

        # Parche de seguridad por si Git Bash / Windows arrastran un SSL_CERT_FILE roto
        if "SSL_CERT_FILE" in os.environ and not os.path.exists(os.environ["SSL_CERT_FILE"]):
            del os.environ["SSL_CERT_FILE"]

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Falta GROQ_API_KEY. Agregala a tu archivo .env en la raíz del proyecto."
            )
        self.llm = Groq(api_key=api_key)

    # Alias que el modelo a veces alucina en vez del nombre real del parámetro.
    _PARAM_ALIASES = {
        "get_gold_by_stop_line": {"line_code": "line", "line_id": "line", "linea": "line"},
    }

    def _execute_tool(self, name: str, tool_input: dict):
        aliases = self._PARAM_ALIASES.get(name, {})
        normalized = {}
        for key, value in tool_input.items():
            normalized[aliases.get(key, key)] = value
        method = getattr(self.client_data, name)
        return method(**normalized)

    def call_llm(self, messages: list) -> dict:
        """Llamada al LLM con reintento en caso de tool call mal formada
        (patrón oficial de Groq para el error tool_use_failed)."""
        formatted_messages = [{"role": "system", "content": self.system_prompt}] + messages
        temperature = 0.7

        for attempt in range(MAX_RETRIES):
            try:
                return self.llm.chat.completions.create(
                    model=MODEL,
                    messages=formatted_messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    max_tokens=1024,
                    temperature=temperature,
                )
            except Exception as e:
                is_tool_error = getattr(e, "status_code", None) == 400
                if is_tool_error and attempt < MAX_RETRIES - 1:
                    temperature = max(temperature - 0.2, 0.1)
                    print(f"  [retry] tool call falló, reintentando con temperature={temperature}")
                    time.sleep(0.5)
                    continue
                raise

    def ask(self, question: str, verbose: bool = False) -> str:
        messages = [{"role": "user", "content": question}]

        while True:
            response = self.call_llm(messages)
            response_message = response.choices[0].message

            if not response_message.tool_calls:
                return response_message.content

            # Guardamos el mensaje del asistente como dict explícito (no el
            # objeto del SDK), para evitar problemas de serialización en la
            # siguiente vuelta del loop.
            messages.append({
                "role": "assistant",
                "content": response_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in response_message.tool_calls
                ],
            })

            for tool_call in response_message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                if verbose:
                    print(f"  [tool_use] -> {tool_name}({tool_args})")

                try:
                    result = self._execute_tool(tool_name, tool_args)
                except Exception as e:
                    result = {"error": str(e)}

                if verbose:
                    print(f"  [tool_result] -> {result}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })


if __name__ == "__main__":
    agent = EMTAgent()
    pregunta = "¿Cuánto tarda la línea M1 en llegar a la parada 4035?"
    print(f"Pregunta: {pregunta}\n")
    respuesta = agent.ask(pregunta, verbose=True)
    print(f"\nRespuesta final:\n{respuesta}")