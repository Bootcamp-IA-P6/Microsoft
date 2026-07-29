import asyncio
from agents.emt_specialist.agent_mcp import EMTAgentMCP

async def main():
    agent = EMTAgentMCP()
    respuesta = await agent.ask("¿Cuánto tarda la línea 5 en llegar a la parada 5907?", verbose=True)
    print(respuesta)

asyncio.run(main())