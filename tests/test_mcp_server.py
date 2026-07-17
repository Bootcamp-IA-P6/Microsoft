import asyncio
import json
import sys
from pathlib import Path

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession


TOOLS_TEST = [
    {
        "name": "search_stop_by_name",
        "args": {"name": "Canalejas"},
        "expect_found": True,
        "check": lambda data: data["data"][0]["stop_id"] == 4039
    },
    {
        "name": "search_stop_by_name",
        "args": {"name": "NoExisteEstaParada"},
        "expect_found": False
    },
    {
        "name": "get_all_arrivals_at_stop",
        "args": {"stop_id": "723"},
        "expect_found": True,
        "check": lambda data: len(data["data"]) >= 3
    },
    {
        "name": "get_all_arrivals_at_stop",
        "args": {"stop_id": "9999"},
        "expect_found": False
    },
    {
        "name": "get_eta_by_stop_line",
        "args": {"stop_id": "4039", "line_label": "M1"},
        "expect_found": True,
        "check": lambda data: data["data"]["eta_seconds"] == 597
    },
    {
        "name": "get_eta_by_stop_line",
        "args": {"stop_id": "4039", "line_label": "999"},
        "expect_found": False
    },
    {
        "name": "get_lines_for_stop",
        "args": {"stop_id": "5837"},
        "expect_found": True,
        "check": lambda data: data["data"][0]["line_label"] == "M1"
    },
    {
        "name": "line_passes_stop",
        "args": {"stop_id": "723", "line_label": "46"},
        "passes": True
    },
    {
        "name": "line_passes_stop",
        "args": {"stop_id": "723", "line_label": "27"},
        "passes": False
    },
]


async def run_tests():
    # tests/test_mcp_server.py -> raiz -> agents/ (donde vive mcp_server.py).
    # Ruta absoluta: funciona sin importar desde donde se lance pytest/python.
    agents_dir = Path(__file__).resolve().parent.parent / "agents"

    # IMPORTANTE: se usa sys.executable (el python del .venv activo) en vez de
    # "uv run mcp_server.py". uv run a veces imprime mensajes de sincronizacion
    # de dependencias a stdout (ej. al agregar una libreria nueva), y eso
    # corrompe el protocolo stdio de MCP -- causa "Connection closed" aunque
    # mcp_server.py en si funcione perfecto.
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["mcp_server.py"],
        cwd=str(agents_dir),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print(f"Tools registradas: {[t.name for t in tools.tools]}")
            print(f"Total: {len(tools.tools)}\n")

            passed = 0
            failed = 0

            for test in TOOLS_TEST:
                name = test["name"]
                args = test["args"]
                label = f"{name}({args})"

                result = await session.call_tool(name, arguments=args)
                content = result.content[0].text
                data = json.loads(content)

                if "expect_found" in test:
                    if test["expect_found"]:
                        if data.get("found"):
                            if "check" in test and not test["check"](data):
                                print(f"  FAIL {label} -> check no superado")
                                print(f"        dato: {data}")
                                failed += 1
                            else:
                                print(f"  OK   {label}")
                                passed += 1
                        else:
                            print(f"  FAIL {label} -> expected found=True, got found=False")
                            print(f"        dato: {data}")
                            failed += 1
                    else:
                        if not data.get("found"):
                            print(f"  OK   {label} (correctamente no encontrado)")
                            passed += 1
                        else:
                            print(f"  FAIL {label} -> expected found=False, got found=True")
                            print(f"        dato: {data}")
                            failed += 1

                elif "passes" in test:
                    if data.get("passes") == test["passes"]:
                        print(f"  OK   {label} (passes={test['passes']})")
                        passed += 1
                    else:
                        print(f"  FAIL {label} -> expected passes={test['passes']}, got passes={data.get('passes')}")
                        failed += 1

            print(f"\n{passed} passed, {failed} failed")
            return failed == 0


if __name__ == "__main__":
    ok = asyncio.run(run_tests())
    exit(0 if ok else 1)