"""Non-Spark arrives poll → bronze-shaped events (Phase 4 UDF-ready).

Uses pipeline.ingestion.emt_client (no Spark). Catalogue stop list must be
supplied (CSV env / arg) — does not query silver_arrives.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Allow `python -m` / script from repo root
_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from pipeline.config.settings import load_emt_credentials  # noqa: E402
from pipeline.ingestion.bronze_writer import bronze_row  # noqa: E402
from pipeline.ingestion.emt_client import (  # noqa: E402
    EmtTokenSession,
    TokenExpiredError,
    fetch_arrives,
)
from rti.ingest.emit import emit_events  # noqa: E402


def _parse_stops(raw: str) -> list[str]:
    return [s.strip() for s in str(raw or "").split(",") if s.strip()]


def load_stops_from_file(path: str) -> list[str]:
    """Supports bootstrap scope_stop_ids.txt (one comma-separated line) or one id per line."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    stops: list[str] = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        if "," in ln:
            stops.extend(_parse_stops(ln))
        else:
            stops.append(ln)
    # unique preserve order
    seen = set()
    out = []
    for s in stops:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def poll_arrives_events(
    *,
    stop_ids: list[str],
    variable_library_name: str = "var_emt_madrid",
    max_retries_per_stop: int = 2,
    token_skew_sec: int = 90,
    client_id: str | None = None,
    pass_key: str | None = None,
) -> list[dict]:
    if not stop_ids:
        raise ValueError("stop_ids required (no Spark catalogue lookup in RTI ingest)")
    if not client_id or not pass_key:
        client_id, pass_key = load_emt_credentials(variable_library_name)
    session = EmtTokenSession(client_id, pass_key, token_skew_sec)
    rows: list[dict] = []
    failures: list[str] = []
    t0 = time.time()
    for sid in stop_ids:
        payload = None
        status = None
        last_err = None
        for attempt in range(int(max_retries_per_stop) + 1):
            try:
                token = session.ensure()
                payload, status = fetch_arrives(token, sid)
                break
            except TokenExpiredError as exc:
                last_err = exc
                session.ensure(force=True)
                time.sleep(0.5)
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                time.sleep(1 + attempt)
        if payload is None:
            failures.append(f"stop {sid}: {last_err}")
            continue
        if str(payload.get("code", "")) != "00":
            failures.append(f"stop {sid}: api_code={payload.get('code')}")
            continue
        rows.append(
            bronze_row("EMT_OPENAPI", "arrives", str(sid), status or 200, payload)
        )
        print(f"  stop {sid}: ok")
    print(f"Round {time.time() - t0:.1f}s success={len(rows)} fail={len(failures)}")
    for f in failures:
        print(f"  fail: {f}")
    if not rows:
        raise RuntimeError("No arrives events\n" + "\n".join(failures))
    return rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Poll EMT arrives → bronze events (no Spark)")
    p.add_argument("--stops", default=os.environ.get("EMT_STOP_IDS", ""), help="comma-separated")
    p.add_argument("--stops-file", default=os.environ.get("EMT_STOPS_FILE", ""))
    p.add_argument("--var-lib", default="var_emt_madrid")
    p.add_argument("--emit", default=os.environ.get("EMT_EMIT_MODE", "jsonl"))
    p.add_argument("--jsonl", default=os.environ.get("EMT_EMIT_JSONL", "rti/out/bronze_arrives.jsonl"))
    args = p.parse_args(argv)

    stops = _parse_stops(args.stops)
    if args.stops_file:
        stops = load_stops_from_file(args.stops_file)
    # Optional: Fabric notebookutils credentials only work inside Fabric
    client_id = os.environ.get("EMT_CLIENT_ID")
    pass_key = os.environ.get("EMT_MADRID_PASS_KEY")
    events = poll_arrives_events(
        stop_ids=stops,
        variable_library_name=args.var_lib,
        client_id=client_id,
        pass_key=pass_key,
    )
    emit_events(events, mode=args.emit, jsonl_path=args.jsonl)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
