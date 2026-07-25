"""
mock_client.py — Backend de datos MOCK para Fase 2 (sin Fabric todavía).

Implementa exactamente las 4 firmas de método que ya definió el equipo en
mock_fixtures_fase2.json ("cómo_usar_este_mock"), leyendo el fixture
isomórfico a gold_stop_line_eta_latest + silver_*_dim.

⚠️ Este archivo es TEMPORAL. Cuando Z2 cierre gold en Fabric, este cliente
se reemplaza por una conexión real (ver agent_client.py) manteniendo las
mismas firmas de método, para que el resto del código no cambie.

También incluye un `answer()` muy simple (matching por texto contra
test_cases del propio fixture) SOLO para poder probar la interfaz de
Streamlit end-to-end sin depender de que el agente real esté conectado.
No es NLU real — es un plan C de UI, no el agente.
"""

from __future__ import annotations

import difflib
import json
from pathlib import Path

FIXTURES_PATH = Path(__file__).parent / "fixtures_fase2.json"


def _load_fixtures() -> dict:
    with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


_FIXTURES = _load_fixtures()
_GOLD = _FIXTURES["gold_stop_line_eta_latest"]
_STOPS_DIM = _FIXTURES["silver_stops_dim"]
_STOP_LINES = _FIXTURES["silver_stop_lines"]
_TEST_CASES = _FIXTURES["test_cases"]


# ---------------------------------------------------------------------------
# Las 4 firmas acordadas en el fixture (paso_2a a paso_2d)
# ---------------------------------------------------------------------------

def get_gold_by_stop(stop_id: int) -> list[dict]:
    """Todas las líneas/ETAs vigentes para una parada."""
    return [row for row in _GOLD if row["stop_id"] == stop_id]


def get_gold_by_stop_line(stop_id: int, line_id: str) -> dict | None:
    """Fila exacta (parada, línea)."""
    for row in _GOLD:
        if row["stop_id"] == stop_id and row["line_id"] == line_id:
            return row
    return None


def search_stop_by_name(name: str) -> list[dict]:
    """Búsqueda de parada por nombre (coincidencia parcial, sin acentos estrictos)."""
    name_lower = name.strip().lower()
    return [
        s for s in _STOPS_DIM
        if name_lower in s["stop_name"].lower()
    ]


def get_lines_for_stop(stop_id: int) -> list[str]:
    """Líneas (catálogo estático) que sirven una parada, exista o no bus ahora."""
    return [sl["line_label"] for sl in _STOP_LINES if sl["stop_id"] == stop_id]


# ---------------------------------------------------------------------------
# Respuesta "conversacional" de juguete, solo para probar la UI
# ---------------------------------------------------------------------------

def answer(question: str) -> str:
    """
    Empareja la pregunta contra las preguntas de ejemplo del fixture y
    devuelve la respuesta esperada pre-escrita.

    Esto NO es el agente — es un simulador para que la interfaz de
    Streamlit tenga algo real que mostrar mientras se conecta el backend
    de verdad (Azure Data Agent o agente local). Ver agent_client.py.
    """
    preguntas = []
    respuestas = []
    for case in _TEST_CASES.values():
        if "pregunta" in case:
            preguntas.append(case["pregunta"])
            respuestas.append(case["respuesta_esperada"])
        else:
            # casos con pregunta_1 / pregunta_2 (distincion_sin_bus_vs_linea_no_pasa)
            for k in case:
                if k.startswith("pregunta_"):
                    suffix = k.split("_")[-1]
                    preguntas.append(case[k])
                    respuestas.append(case.get(f"respuesta_esperada_{suffix}", ""))

    match = difflib.get_close_matches(question, preguntas, n=1, cutoff=0.35)
    if match:
        idx = preguntas.index(match[0])
        return respuestas[idx]

    return (
        "No tengo esa información con los datos de prueba que tengo cargados "
        "ahora mismo (modo demo). Prueba con una pregunta sobre una parada o "
        "línea del centro de Madrid."
    )
