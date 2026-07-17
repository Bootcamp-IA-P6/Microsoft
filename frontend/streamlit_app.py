import json
import sys
from pathlib import Path

import streamlit as st
from groq import Groq

# frontend/streamlit_app.py necesita llegar a agents/mock_client.py y a
# config.py en la raiz. Se agregan ambas carpetas al path explicitamente,
# porque frontend/ y agents/ son carpetas hermanas, no hay import directo.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))                 # para `import config`
sys.path.insert(0, str(_ROOT / "agents"))       # para `import mock_client`

from config import GROQ_API_KEY, MODEL, require_groq_key  # noqa: E402
from mock_client import MockClient  # noqa: E402

require_groq_key()
groq_client = Groq(api_key=GROQ_API_KEY)
data = MockClient()

system_prompt = (_ROOT / "agents" / "prompt.md").read_text(encoding="utf-8")

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_eta_by_stop_line",
            "description": "Obtiene el tiempo estimado de llegada de una linea especifica a una parada. stop_id debe ser un numero, NUNCA un nombre.",
            "parameters": {
                "type": "object",
                "properties": {
                    "stop_id": {"type": "string", "description": "ID numerico de la parada como string (ej: '723')"},
                    "line_label": {"type": "string", "description": "Etiqueta de la linea (ej: 'M1', '46')"}
                },
                "required": ["stop_id", "line_label"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_arrivals_at_stop",
            "description": "Obtiene todas las llegadas estimadas a una parada. stop_id debe ser un numero, NUNCA un nombre.",
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
            "name": "search_stop_by_name",
            "description": "Busca paradas por nombre parcial. Usa ESTA tool primero si el usuario da un nombre en vez de un ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Nombre parcial de la parada (ej: 'Callao', 'Sevilla')"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_lines_for_stop",
            "description": "Obtiene todas las lineas que pasan por una parada. stop_id debe ser un numero, NUNCA un nombre.",
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
            "description": "Verifica si una linea pasa por una parada. stop_id debe ser un numero, NUNCA un nombre.",
            "parameters": {
                "type": "object",
                "properties": {
                    "stop_id": {"type": "string", "description": "ID numerico de la parada como string (ej: '723')"},
                    "line_label": {"type": "string", "description": "Etiqueta de la linea (ej: 'M1', '27')"}
                },
                "required": ["stop_id", "line_label"]
            }
        }
    }
]


def execute_tool(name, args):
    try:
        stop_id = int(args["stop_id"]) if "stop_id" in args else None
    except (ValueError, TypeError):
        return json.dumps({
            "error": (
                f"stop_id invalido: '{args.get('stop_id')}'. Debe ser un ID "
                f"numerico. Si tenes un nombre de parada, usa primero "
                f"search_stop_by_name para obtener el stop_id correcto."
            )
        })
    if name == "get_eta_by_stop_line":
        result = data.get_gold_by_stop_line(stop_id, args["line_label"])
        if result is None:
            return json.dumps({"found": False})
        return json.dumps({"found": True, "data": result})
    elif name == "get_all_arrivals_at_stop":
        results = data.get_gold_by_stop(stop_id)
        if not results:
            return json.dumps({"found": False})
        return json.dumps({"found": True, "data": results})
    elif name == "search_stop_by_name":
        results = data.search_stop_by_name(args["name"])
        if not results:
            return json.dumps({"found": False})
        return json.dumps({"found": True, "data": results})
    elif name == "get_lines_for_stop":
        results = data.get_lines_for_stop(stop_id)
        return json.dumps({"found": True, "data": results})
    elif name == "line_passes_stop":
        result = data.line_passes_stop(stop_id, args["line_label"])
        return json.dumps({"passes": result})
    return json.dumps({"error": f"Tool desconocida: {name}"})


def ask(question):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]
    for _ in range(4):
        try:
            response = groq_client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.1,
                max_tokens=800
            )
        except Exception:
            return "Error de conexion con el modelo. Intenta de nuevo."

        msg = response.choices[0].message
        if not msg.tool_calls:
            return msg.content
        messages.append(msg)
        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)
            result = execute_tool(fn_name, fn_args)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })
    return "No pude resolver tu consulta."


if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("EMT Madrid")
st.caption("Zona Sol / Gran Via")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Escribe tu pregunta..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.spinner("Pensando..."):
        response = ask(prompt)
    with st.chat_message("assistant"):
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})