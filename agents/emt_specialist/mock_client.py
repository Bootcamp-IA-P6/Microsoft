"""
mock_client.py
---------------
Simula acceso a `gold_emt_stop_line` (contract v4.2) vía fixture JSON
mientras el pipeline Fabric acumula datos reales.

Reemplazo futuro: consultar Lakehouse `gold_emt_stop_line` directamente.
"""

import json
from pathlib import Path
from typing import Optional

DEFAULT_FIXTURES_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "mocks" / "fixtures_fase2.json"
)


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

        # Prefer contract v4.2 key; fall back to legacy fixture key during migration
        self._gold = self._data.get("gold_emt_stop_line") or self._data.get(
            "gold_stop_line_eta_latest", []
        )
        self._stops_dim = self._data.get("silver_stops_dim")
        if self._stops_dim is None:
            # Derive distinct stops from gold (v4 has stop_name on gold)
            seen = {}
            for row in self._gold:
                sid = str(row["stop_id"])
                if sid not in seen:
                    seen[sid] = {
                        "stop_id": sid,
                        "stop_name": row.get("stop_name") or sid,
                    }
            self._stops_dim = list(seen.values())
        self._stop_lines = self._data.get("silver_stop_lines")
        if self._stop_lines is None:
            self._stop_lines = [
                {
                    "stop_id": str(r["stop_id"]),
                    "line_id": r["line_id"],
                    "line_label": r["line_label"],
                    "direction_id": r.get("direction_id"),
                }
                for r in self._gold
            ]

    def get_gold_by_stop(self, stop_id) -> list[dict]:
        """Filas gold_emt_stop_line para una parada."""
        sid = str(stop_id)
        return [row for row in self._gold if str(row["stop_id"]) == sid]

    def get_gold_by_stop_line(self, stop_id, line: str) -> Optional[dict]:
        """Fila gold por stop + line_id o line_label."""
        sid = str(stop_id)
        line_norm = line.strip().lower()
        for row in self._gold:
            if str(row["stop_id"]) != sid:
                continue
            if (
                str(row["line_id"]).lower() == line_norm
                or str(row["line_label"]).lower() == line_norm
            ):
                return row
        return None

    def search_stop_by_name(self, name: str) -> list[dict]:
        name_lower = name.lower()
        return [
            row
            for row in self._stops_dim
            if name_lower in str(row.get("stop_name", "")).lower()
        ]

    def get_lines_for_stop(self, stop_id) -> list[dict]:
        sid = str(stop_id)
        return [row for row in self._stop_lines if str(row["stop_id"]) == sid]


if __name__ == "__main__":
    client = MockDataClient()
    print("US-01:", client.get_gold_by_stop_line(4035, "001"))
    print("US-02:", len(client.get_gold_by_stop(4035)), "filas")
    print("US-03:", client.search_stop_by_name("mercado"))
    print("Líneas 4035:", client.get_lines_for_stop(4035))
