"""Phase 5: bootstrap catalogue seeds → Eventhouse via es_emt_arrives_silver."""
from __future__ import annotations

import sys
from pathlib import Path


def _ensure_repo_paths() -> None:
    """Allow notebook to import rti/ when Files/python or repo root is on path."""
    candidates = [
        Path("/lakehouse/default/Files/python"),
        Path("/lakehouse/default/Files"),
    ]
    # Workspace-relative when running from cloned repo
    here = Path(__file__).resolve()
    candidates.append(here.parents[2])  # repo root
    for p in candidates:
        s = str(p)
        if p.exists() and s not in sys.path:
            sys.path.insert(0, s)


def run_bootstrap_eh(
    *,
    client_id: str,
    pass_key: str,
    arrives_silver_conn: str,
    arrives_silver_hub: str = "",
    gtfs_zip_path: str = "/lakehouse/default/Files/gtfs/gtfs_emt.zip",
    gtfs_zip_url: str = "",
    geofence_lat: float = 40.416729,
    geofence_lon: float = -3.703339,
    geofence_radius_m: int = 600,
    line_ids_override: str = "",
) -> str:
    """
    Build silver_arrives_seed rows and send to Eventstream → silver_arrives.
    Does NOT touch Lakehouse. Does NOT delete old seeds (append-only; readers use max catalog_loaded_at).
    """
    import importlib

    _ensure_repo_paths()
    # Login with the same client UDF/LH bootstrap use (X-ClientId + passKey) — before GTFS work.
    from pipeline.ingestion.emt_client import login_token as emt_login

    print("bootstrap_eh: EMT auth via pipeline.ingestion.emt_client (X-ClientId+passKey)")
    _token = emt_login(client_id, pass_key)
    print("bootstrap_eh: EMT login OK")

    import rti.lib.bootstrap_seed as bootstrap_seed

    bootstrap_seed = importlib.reload(bootstrap_seed)
    url = (gtfs_zip_url or "").strip() or bootstrap_seed.DEFAULT_GTFS_URL
    rows = bootstrap_seed.build_catalogue_seed_rows(
        client_id=client_id,
        pass_key=pass_key,
        gtfs_zip_path=gtfs_zip_path,
        gtfs_zip_url=url,
        geofence_lat=geofence_lat,
        geofence_lon=geofence_lon,
        geofence_radius_m=geofence_radius_m,
        line_ids_override=line_ids_override,
        access_token=_token,
    )
    n = bootstrap_seed.send_events_to_eventhub(arrives_silver_conn, arrives_silver_hub, rows)
    stops = len({r["stop_id"] for r in rows})
    return f"bootstrap_eh ok seeds_sent={n} grains={len(rows)} stops={stops}"
