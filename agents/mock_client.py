import json
from pathlib import Path

FIXTURES_PATH = Path(__file__).parent / "fixtures_fase2.json"


class MockClient:
    def __init__(self, path: str | None = None):
        with open(path or FIXTURES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._gold = data["gold_stop_line_eta_latest"]
        self._stops = data["silver_stops_dim"]
        self._stop_lines = data["silver_stop_lines"]

    def get_gold_by_stop(self, stop_id: int) -> list[dict]:
        return [r for r in self._gold if r["stop_id"] == stop_id]

    def get_gold_by_stop_line(self, stop_id: int, line_label: str) -> dict | None:
        for r in self._gold:
            if r["stop_id"] == stop_id and r["line_label"] == line_label:
                return r
        return None

    def search_stop_by_name(self, name: str) -> list[dict]:
        name_lower = name.lower().strip()
        return [
            s for s in self._stops
            if name_lower in s["stop_name"].lower()
        ]

    def get_lines_for_stop(self, stop_id: int) -> list[dict]:
        return [r for r in self._stop_lines if r["stop_id"] == stop_id]

    def line_passes_stop(self, stop_id: int, line_label: str) -> bool:
        return any(
            r["line_label"] == line_label
            for r in self._stop_lines
            if r["stop_id"] == stop_id
        )