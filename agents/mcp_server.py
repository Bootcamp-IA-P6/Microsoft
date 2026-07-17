import json
import sys
from mcp.server.fastmcp import FastMCP

from mock_client import MockClient

mcp = FastMCP("emt-madrid")
data = MockClient()


@mcp.tool()
def get_eta_by_stop_line(stop_id: str, line_label: str) -> str:
    """Obtiene el tiempo estimado de llegada de una linea especifica a una parada.

    Args:
        stop_id: ID numerico de la parada como string (ej: '723')
        line_label: Etiqueta de la linea (ej: 'M1', '46')
    """
    result = data.get_gold_by_stop_line(int(stop_id), line_label)
    if result is None:
        return json.dumps({"found": False, "message": "No hay datos para esa parada y linea"})
    return json.dumps({"found": True, "data": result})


@mcp.tool()
def get_all_arrivals_at_stop(stop_id: str) -> str:
    """Obtiene todas las llegadas estimadas de todas las lineas a una parada.

    Args:
        stop_id: ID numerico de la parada como string (ej: '723')
    """
    results = data.get_gold_by_stop(int(stop_id))
    if not results:
        return json.dumps({"found": False, "message": "No hay datos para esa parada"})
    return json.dumps({"found": True, "data": results})


@mcp.tool()
def search_stop_by_name(name: str) -> str:
    """Busca paradas por nombre parcial.

    Args:
        name: Nombre parcial de la parada (ej: 'Callao', 'Sevilla', 'Canalejas')
    """
    results = data.search_stop_by_name(name)
    if not results:
        return json.dumps({"found": False, "message": "No se encontro ninguna parada con ese nombre"})
    return json.dumps({"found": True, "data": results})


@mcp.tool()
def get_lines_for_stop(stop_id: str) -> str:
    """Obtiene todas las lineas que pasan por una parada.

    Args:
        stop_id: ID numerico de la parada como string (ej: '723')
    """
    results = data.get_lines_for_stop(int(stop_id))
    return json.dumps({"found": True, "data": results})


@mcp.tool()
def line_passes_stop(stop_id: str, line_label: str) -> str:
    """Verifica si una linea especifica pasa por una parada.

    Args:
        stop_id: ID numerico de la parada como string (ej: '723')
        line_label: Etiqueta de la linea (ej: 'M1', '27')
    """
    result = data.line_passes_stop(int(stop_id), line_label)
    return json.dumps({"passes": result})


if __name__ == "__main__":
    if "--sse" in sys.argv:
        import sys as _sys
        _sys.argv = [a for a in _sys.argv if a != "--sse"]
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")