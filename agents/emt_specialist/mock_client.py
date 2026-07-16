"""
mock_client.py
---------------
Cliente que simula el acceso a `gold_stop_line_eta_latest` / `silver_stops_dim` /
`silver_stop_lines` usando el fixture JSON, mientras Z2 termina el pipeline real
en Fabric.

IMPORTANTE (contrato de reemplazo):
Cuando gold esté listo en Fabric, este archivo se reemplaza por una versión que
consulta Fabric directamente.

"""

import json
from pathlib import Path
from typing import Optional

# data/mocks/fixtures_fase2.json, relativo a la raíz del repo
DEFAULT_FIXTURES_PATH = Path(__file__).resolve().parents[2] / "data" / "mocks" / "fixtures_fase2.json"


class MockDataClient:
    def __init__(self, fixtures_path: Optional[str] = None):
        path = Path(fixtures_path) if fixtures_path else DEFAULT_FIXTURES_PATH
        if not path.exists():
            raise FileNotFoundError(
                f"No se encontró el fixture en '{path}'. "
                "Verificá que data/mocks/fixtures_fase2.json existe en el repo."
            )
        with open(path, "r", encoding="utf-8") as f:
            self._data = json.load(f)

        self._gold = self._data["gold_stop_line_eta_latest"]
        self._stops_dim = self._data["silver_stops_dim"]
        self._stop_lines = self._data["silver_stop_lines"]

    # Los 4 métodos que el agente usa como tools
    def get_gold_by_stop(self, stop_id: int) -> list[dict]:
        """Todas las líneas/ETAs para una parada. Equivale a filtrar
        gold_stop_line_eta_latest por stop_id."""

        return [row for row in self._gold if row["stop_id"] == stop_id]

    def get_gold_by_stop_line(self, stop_id: int, line: str) -> Optional[dict]:
        """Fila exacta (stop_id, line) en gold. Acepta indistintamente el
        código interno (line_id, ej. '001') o la etiqueta visible (line_label,
        ej. 'M1') — así el modelo no necesita memorizar el mapeo por prompt.
        None si la línea no pasa por esa parada."""

        line_norm = line.strip().lower()
        for row in self._gold:
            if row["stop_id"] != stop_id:
                continue
            if row["line_id"].lower() == line_norm or row["line_label"].lower() == line_norm:
                return row
        return None

    def search_stop_by_name(self, name: str) -> list[dict]:
        """Busca paradas por nombre (coincidencia parcial, case-insensitive)."""
        name_lower = name.lower()
        return [
            row for row in self._stops_dim
            if name_lower in row["stop_name"].lower()
        ]

    def get_lines_for_stop(self, stop_id: int) -> list[dict]:
        """Todas las líneas que sirven una parada, según el catálogo estático
        (silver_stop_lines) — no depende de si hay ETA ahora mismo."""
        return [row for row in self._stop_lines if row["stop_id"] == stop_id]


if __name__ == "__main__":
    # Smoke test rápido, sin agente ni API — solo valida que el mock carga bien.
    client = MockDataClient()
    print("US-01 (gold por stop+line):", client.get_gold_by_stop_line(4035, "001"))
    print("US-02 (gold por stop):", len(client.get_gold_by_stop(4035)), "filas")
    print("US-03 (buscar por nombre):", client.search_stop_by_name("mercado"))
    print("Líneas en parada 4035:", client.get_lines_for_stop(4035))
