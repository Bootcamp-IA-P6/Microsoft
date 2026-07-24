"""Emit bronze-shaped events without Spark (Phase 4 / UDF)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def to_jsonl_line(event: dict[str, Any]) -> str:
    return json.dumps(event, ensure_ascii=False)


def write_jsonl(path: str | Path, events: list[dict[str, Any]]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        for ev in events:
            f.write(to_jsonl_line(ev) + "\n")


def emit_events(
    events: list[dict[str, Any]],
    *,
    mode: str | None = None,
    jsonl_path: str | None = None,
) -> int:
    """
    mode:
      - jsonl (default): append to jsonl_path or EMT_EMIT_JSONL
      - stdout: print each event
      - eventstream: placeholder — set EMT_EVENTSTREAM_CONN later
    """
    mode = (mode or os.environ.get("EMT_EMIT_MODE") or "jsonl").lower()
    if not events:
        return 0
    if mode == "stdout":
        for ev in events:
            print(to_jsonl_line(ev))
        return len(events)
    if mode == "eventstream":
        raise NotImplementedError(
            "Eventstream emit not wired yet — use jsonl/stdout or set connection in Fabric UDF"
        )
    path = jsonl_path or os.environ.get("EMT_EMIT_JSONL") or "rti/out/bronze_events.jsonl"
    write_jsonl(path, events)
    print(f"Wrote {len(events)} event(s) → {path}")
    return len(events)
