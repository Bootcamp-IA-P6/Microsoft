import os
import traceback

import agent_mcp
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DEMO_API_KEY = os.environ.get("DEMO_API_KEY")
if not DEMO_API_KEY:
    raise RuntimeError(
        "La variable de entorno DEMO_API_KEY no está definida. "
        "El servidor no arrancará sin ella."
    )

mcp_agent = agent_mcp.EMTAgentMCP()

app = FastAPI(title="NAVI Chat Proxy", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://handy-north-cb414576f1-westeurope.webapp.fabricapps.net",
        "http://localhost:5173",
    ],
    allow_methods=["POST"],
    allow_headers=["Content-Type", "X-Demo-Key"],
)


class ChatRequest(BaseModel):
    question: str
    language: str = "es"


class ChatResponse(BaseModel):
    answerText: str


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, x_demo_key: str = Header(...)):
    if x_demo_key != DEMO_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="X-Demo-Key inválido. Revisá la clave configurada en DEMO_API_KEY.",
        )

    try:
        answer_text = await mcp_agent.ask(req.question)
        return ChatResponse(answerText=answer_text)
    except Exception:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=(
                "No se pudo obtener respuesta del agente en este momento. "
                "Intentalo de nuevo más tarde."
            ),
        )


"""
Para correr el servidor:

1. Instalar dependencias:
   pip install fastapi uvicorn python-dotenv azure-identity mcp

2. Levantar:
   uvicorn server:app --host 0.0.0.0 --port 8000

   Asegurate de tener las variables de entorno definidas:
   - DEMO_API_KEY
   - FABRIC_MCP_URL  (usada por agent_mcp.py)
"""