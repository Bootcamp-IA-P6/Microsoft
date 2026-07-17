import asyncio
import json
import sys
from pathlib import Path
from typing import TypedDict

# Permite importar config.py desde la raiz del proyecto sin importar
# desde donde se ejecute este script (agents/ o la raiz).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import GROQ_API_KEY, MODEL, require_groq_key  # noqa: E402

from groq import Groq, BadRequestError
from langgraph.graph import StateGraph, START, END
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession

groq_client = Groq(api_key=GROQ_API_KEY)

system_prompt = Path(__file__).parent.joinpath("prompt.md").read_text(encoding="utf-8")


class State(TypedDict):
    question: str
    answer: str
    specialist: str


def mcp_to_groq_tools(mcp_tools):
    groq_tools = []
    for t in mcp_tools:
        properties = {}
        required = []
        if t.inputSchema and "properties" in t.inputSchema:
            properties = t.inputSchema["properties"]
            required = t.inputSchema.get("required", [])
        groq_tools.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        })
    return groq_tools


async def call_llm(session, groq_tools, question):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]
    for _ in range(4):
        try:
            response = groq_client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=groq_tools,
                tool_choice="auto",
                temperature=0.1,
                max_tokens=800
            )
        except BadRequestError:
            continue
        msg = response.choices[0].message
        if not msg.tool_calls:
            return msg.content
        messages.append(msg)
        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)
            print(f"  [mcp] {fn_name}({fn_args})")
            result = await session.call_tool(name=fn_name, arguments=fn_args)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result.content[0].text
            })
    return "No pude resolver tu consulta."


def route_question(state: State) -> str:
    """Router: decide que especialista maneja la pregunta.

    Con un solo especialista (EMT), todo va a emt_specialist.
    Cuando se añadan mas, se añaden ramas aqui sin tocar el grafo.
    """
    return "emt_specialist"


async def create_graph(session, groq_tools):
    async def emt_specialist(state: State) -> dict:
        answer = await call_llm(session, groq_tools, state["question"])
        return {"answer": answer, "specialist": "emt"}

    graph = StateGraph(State)
    graph.add_node("emt_specialist", emt_specialist)
    graph.add_conditional_edges(START, route_question, {"emt_specialist": "emt_specialist"})
    graph.add_edge("emt_specialist", END)
    return graph.compile()


async def main_async():
    require_groq_key()

    # IMPORTANTE: sys.executable (python del .venv activo) en vez de
    # "uv run mcp_server.py" -- uv run puede imprimir mensajes de sync
    # de dependencias a stdout, que corrompen el protocolo stdio de MCP.
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["mcp_server.py"],
        cwd=str(Path(__file__).resolve().parent),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            mcp_tools = await session.list_tools()
            groq_tools = mcp_to_groq_tools(mcp_tools.tools)
            graph = await create_graph(session, groq_tools)

            print("Supervisor EMT -- escribe 'salir' para terminar\n")

            test_questions = [
                "Cuanto tarda el M1 en Canalejas?",
                "Que buses llegan a Gran Via-Callao?",
                "Que lineas pasan por Sevilla?",
                "Por que se retrasa la linea 46?",
                "Cuando llega el 27 a Gran Via-Callao?",
            ]

            for q in test_questions:
                print(f"USER: {q}")
                result = await graph.ainvoke({"question": q})
                print(f"AGENT ({result['specialist']}): {result['answer']}\n")

            print("--- Modo interactivo ---\n")
            while True:
                try:
                    question = input("USER: ")
                except (EOFError, KeyboardInterrupt):
                    break
                if question.strip().lower() in ("salir", "exit", "quit"):
                    break
                if not question.strip():
                    continue
                result = await graph.ainvoke({"question": question})
                print(f"AGENT ({result['specialist']}): {result['answer']}\n")


if __name__ == "__main__":
    asyncio.run(main_async())