import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Sube 2 niveles: agents/emt_specialist/ -> agents/ -> raiz del proyecto
_ROOT = Path(__file__).resolve().parent.parent.parent
_AGENTS_DIR = _ROOT / "agents"
sys.path.insert(0, str(_ROOT))         # para `import config`
sys.path.insert(0, str(_AGENTS_DIR))    # para `import mock_client` (sin relativos,
                                         # asi se puede correr con `python agent_groq.py`
                                         # directo, sin necesitar -m ni __init__.py)
from config import GROQ_API_KEY, MODEL  # noqa: E402

from groq import Groq, BadRequestError
from mock_client import MockClient  # noqa: E402

system_prompt = Path(__file__).parent.parent.joinpath("prompt.md").read_text(encoding="utf-8")

_data = MockClient()

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_eta_by_stop_line",
            "description": "Obtiene el tiempo estimado de llegada de una linea a una parada.",
            "parameters": {
                "type": "object",
                "properties": {
                    "line": {"type": "string", "description": "Alias: line_id, line_code, linea"},
                    "line_id": {"type": "string", "description": "Alias: line, line_code, linea"},
                    "line_code": {"type": "string", "description": "Alias: line, line_id, linea"},
                    "stop_id": {"type": "string", "description": "ID de parada como string"}
                },
                "required": ["stop_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_arrivals_at_stop",
            "description": "Obtiene todas las llegadas estimadas a una parada.",
            "parameters": {
                "type": "object",
                "properties": {
                    "stop_id": {"type": "string", "description": "ID de parada como string"}
                },
                "required": ["stop_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_stop_by_name",
            "description": "Busca paradas por nombre parcial. Usa ESTA tool primero si el usuario da un nombre en vez de un ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Nombre parcial de la parada"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_lines_for_stop",
            "description": "Obtiene todas las lineas que pasan por una parada.",
            "parameters": {
                "type": "object",
                "properties": {
                    "stop_id": {"type": "string", "description": "ID numerico de la parada como string (ej: '723')"}
                },
                "required": ["stop_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "line_passes_stop",
            "description": "Verifica si una linea pasa por una parada.",
            "parameters": {
                "type": "object",
                "properties": {
                    "line": {"type": "string", "description": "Alias: line_id, line_code, linea"},
                    "stop_id": {"type": "string", "description": "ID de parada como string"}
                },
                "required": ["stop_id", "line"]
            }
        }
    }
]


def _normalize_args(args: dict) -> dict:
    """Normaliza aliases de nombres de campos que el LLM a veces usa
    de forma distinta (line vs line_id vs line_code vs linea)."""
    normalized = {}
    alias_map = {
        "line_id": "line_label", "line_code": "line_label", "linea": "line_label",
        "line": "line_label",
        "stop_id": "stop_id",
        "name": "name",
    }
    for key, value in args.items():
        canonical = alias_map.get(key, key)
        normalized[canonical] = value
    return normalized


def _execute_tool(name: str, args: dict) -> str:
    """Misma logica que frontend/streamlit_app.py::execute_tool, para que
    ambos frentes (Streamlit y este agente standalone) den resultados
    identicos ante la misma pregunta."""
    try:
        stop_id = int(args["stop_id"]) if "stop_id" in args else None
    except (ValueError, TypeError):
        # El modelo mando un nombre (ej. "Sevilla") en vez de un stop_id
        # numerico -- probablemente se salteo el paso de search_stop_by_name.
        # Devolvemos un error legible para que el LLM lo lea y se corrija
        # solo en el siguiente turno, en vez de reventar el programa entero.
        return json.dumps({
            "error": (
                f"stop_id invalido: '{args.get('stop_id')}'. Debe ser un ID "
                f"numerico. Si tenes un nombre de parada, usa primero "
                f"search_stop_by_name para obtener el stop_id correcto."
            )
        })
    if name == "get_eta_by_stop_line":
        result = _data.get_gold_by_stop_line(stop_id, args.get("line_label"))
        if result is None:
            return json.dumps({"found": False})
        return json.dumps({"found": True, "data": result})
    elif name == "get_all_arrivals_at_stop":
        results = _data.get_gold_by_stop(stop_id)
        if not results:
            return json.dumps({"found": False})
        return json.dumps({"found": True, "data": results})
    elif name == "search_stop_by_name":
        results = _data.search_stop_by_name(args["name"])
        if not results:
            return json.dumps({"found": False})
        return json.dumps({"found": True, "data": results})
    elif name == "get_lines_for_stop":
        results = _data.get_lines_for_stop(stop_id)
        return json.dumps({"found": True, "data": results})
    elif name == "line_passes_stop":
        result = _data.line_passes_stop(stop_id, args.get("line_label"))
        return json.dumps({"passes": result})
    return json.dumps({"error": f"Tool desconocida: {name}"})


async def call_llm_with_retry(messages: list[dict], temperature: float = 0.1, max_retries: int = 3) -> Any:
    groq_client = Groq(api_key=GROQ_API_KEY)
    for attempt in range(max_retries):
        try:
            return groq_client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=temperature,
                max_tokens=800
            )
        except BadRequestError as e:
            if "tool_use_failed" in str(e):
                new_temp = max(0.1, temperature - 0.2)
                if new_temp < 0.1:
                    return None
                print(f"  [retry {attempt + 1}] tool_use_failed, bajando temperatura a {new_temp}")
                temperature = new_temp
                continue
            raise
    return None


async def ask_async(question: str) -> str:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]
    temperature = 0.1

    for _ in range(4):
        response = await call_llm_with_retry(messages, temperature)
        if response is None:
            return "No pude resolver tu consulta."

        msg = response.choices[0].message
        if not msg.tool_calls:
            return msg.content

        assistant_msg = {"role": "assistant", "content": msg.content}
        assistant_msg["tool_calls"] = [
            {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in msg.tool_calls
        ]
        messages.append(assistant_msg)

        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name
            try:
                fn_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                continue
            fn_args = _normalize_args(fn_args)
            result = _execute_tool(fn_name, fn_args)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

    return "No pude resolver tu consulta."


def ask(question: str) -> str:
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(ask_async(question))
    finally:
        loop.close()


if __name__ == "__main__":
    if not GROQ_API_KEY:
        print("ERROR: define GROQ_API_KEY en el .env de la raiz del proyecto")
        exit(1)

    test_questions = [
        "Cuanto tarda el M1 en Canalejas?",
        "Que buses llegan a Gran Via-Callao?",
        "Que lineas pasan por Sevilla?",
        "Por que se retrasa la linea 46?",
        "Cuando llega el 27 a Gran Via-Callao?",
    ]

    for q in test_questions:
        print(f"USER: {q}")
        answer = ask(q)
        print(f"AGENT: {answer}\n")