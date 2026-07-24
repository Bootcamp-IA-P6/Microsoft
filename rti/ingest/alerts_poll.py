"""Non-Spark servicealerts poll → bronze-shaped event (Phase 4 UDF-ready)."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from pipeline.config.constants import SERVICEALERTS_URL  # noqa: E402
from pipeline.ingestion.bronze_writer import bronze_row_alerts  # noqa: E402
from pipeline.ingestion.gtfs_rt_client import decode_feed_to_dict, http_bytes  # noqa: E402
from rti.ingest.emit import emit_events  # noqa: E402


def poll_alerts_event(*, url: str = SERVICEALERTS_URL) -> dict:
    raw, status = http_bytes(url)
    payload = decode_feed_to_dict(raw)
    n_ent = len(payload.get("entity") or [])
    print(f"Fetched servicealerts HTTP {status}, bytes={len(raw)}, entities={n_ent}")
    return bronze_row_alerts(status, payload)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Poll EMT servicealerts → bronze event")
    p.add_argument("--url", default=os.environ.get("EMT_SERVICEALERTS_URL", SERVICEALERTS_URL))
    p.add_argument("--emit", default=os.environ.get("EMT_EMIT_MODE", "jsonl"))
    p.add_argument("--jsonl", default=os.environ.get("EMT_EMIT_JSONL", "rti/out/bronze_alerts.jsonl"))
    args = p.parse_args(argv)
    ev = poll_alerts_event(url=args.url)
    emit_events([ev], mode=args.emit, jsonl_path=args.jsonl)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
