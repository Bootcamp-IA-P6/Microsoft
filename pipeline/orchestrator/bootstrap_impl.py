"""Bootstrap catalogue seed into silver_arrives."""
from __future__ import annotations

import tempfile
import zipfile
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from pipeline.common.datetime_utils import UTC, MADRID
from pipeline.common.keys import sha_rk
from pipeline.common.parsing import stop_id_str
from pipeline.config.constants import BRONZE_TABLE, SILVER_ARRIVES
from pipeline.config.settings import load_emt_credentials
from pipeline.ingestion.bronze_writer import bronze_row
from pipeline.ingestion.emt_client import http_json, login_token
from pipeline.ingestion.gtfs_static import (
    download_gtfs_zip,
    haversine_m,
    resolve_zip_path,
)
from pipeline.validation.schema import BRONZE_SCHEMA, SILVER_SEED_SCHEMA


def run_bootstrap(
    spark,
    *,
    gtfs_zip_path: str,
    gtfs_zip_url: str,
    geofence_lat: float,
    geofence_lon: float,
    geofence_radius_m: int,
    variable_library_name: str,
    line_ids_override: str,
) -> None:
    sol_lat = float(geofence_lat)
    sol_lon = float(geofence_lon)
    radius_m = float(geofence_radius_m)
    catalog_date = date.today()

    if str(gtfs_zip_url).strip():
        download_gtfs_zip(str(gtfs_zip_url).strip(), Path(gtfs_zip_path))

    zip_path = resolve_zip_path(gtfs_zip_path)
    print(f"Zip: {zip_path} ({zip_path.stat().st_size} bytes)")

    local_root = Path(tempfile.mkdtemp(prefix="gtfs_"))
    with zipfile.ZipFile(zip_path.as_posix(), "r") as zf:
        zf.extractall(local_root.as_posix())

    stops_file = next(local_root.rglob("stops.txt"), None)
    if stops_file is None:
        raise FileNotFoundError(f"stops.txt not found under {local_root}")
    gtfs_dir = stops_file.parent
    for name in ("stops.txt", "routes.txt", "trips.txt", "stop_times.txt"):
        if not (gtfs_dir / name).is_file():
            raise FileNotFoundError(f"Missing {gtfs_dir / name}")

    stops_pdf = pd.read_csv(gtfs_dir / "stops.txt", dtype=str, keep_default_na=False)
    stop_attrs: dict[str, dict] = {}
    in_scope_ids: set[str] = set()
    for _, r in stops_pdf.iterrows():
        sid = stop_id_str(r.get("stop_id"))
        if sid is None:
            continue
        try:
            lat = float(str(r.get("stop_lat", "")).strip() or "nan")
            lon = float(str(r.get("stop_lon", "")).strip() or "nan")
        except ValueError:
            lat, lon = float("nan"), float("nan")
        in_scope = (
            lat == lat and lon == lon and haversine_m(sol_lat, sol_lon, lat, lon) <= radius_m
        )
        stop_attrs[sid] = {
            "stop_name": r.get("stop_name") or None,
            "stop_lat": None if lat != lat else lat,
            "stop_lon": None if lon != lon else lon,
            "in_scope": in_scope,
        }
        if in_scope:
            in_scope_ids.add(sid)
    print(f"GTFS stops parsed={len(stop_attrs)} in_scope={len(in_scope_ids)}")
    if not in_scope_ids:
        raise RuntimeError("No in-scope stops — check geofence / GTFS")

    routes_pdf = pd.read_csv(gtfs_dir / "routes.txt", dtype=str, keep_default_na=False)
    trips_pdf = pd.read_csv(gtfs_dir / "trips.txt", dtype=str, keep_default_na=False)
    st_pdf = pd.read_csv(
        gtfs_dir / "stop_times.txt",
        dtype=str,
        keep_default_na=False,
        usecols=lambda c: c in {"trip_id", "stop_id", "stop_sequence"},
    )
    route_label = {
        str(r["route_id"]).strip(): (
            str(r.get("route_short_name") or "").strip() or str(r["route_id"]).strip()
        )
        for _, r in routes_pdf.iterrows()
    }
    trip_route = {
        str(r["trip_id"]).strip(): str(r["route_id"]).strip() for _, r in trips_pdf.iterrows()
    }
    trip_dir = {}
    for _, r in trips_pdf.iterrows():
        try:
            trip_dir[str(r["trip_id"]).strip()] = int(str(r.get("direction_id") or "0"))
        except ValueError:
            trip_dir[str(r["trip_id"]).strip()] = 0

    candidate_lines: set[str] = set()
    terminus_keys: set[tuple[str, str, int]] = set()
    for _, r in st_pdf.iterrows():
        sid = stop_id_str(r.get("stop_id"))
        tid = str(r.get("trip_id") or "").strip()
        if sid not in in_scope_ids or tid not in trip_route:
            continue
        lid = trip_route[tid]
        candidate_lines.add(lid)
        try:
            seq = int(str(r.get("stop_sequence") or "0"))
        except ValueError:
            seq = 0
        if seq == 1:
            terminus_keys.add((sid, lid, trip_dir.get(tid, 0)))

    manual = [x.strip() for x in str(line_ids_override or "").split(",") if x.strip()]
    if manual:
        candidate_lines = set(manual)
        print(f"line_ids_override → {sorted(candidate_lines)}")
    else:
        print(f"Candidate line_ids from GTFS∩geofence: {len(candidate_lines)}")

    shutil.rmtree(local_root, ignore_errors=True)

    client_id, pass_key = load_emt_credentials(variable_library_name)
    token = login_token(client_id, pass_key)
    today = date.today().strftime("%Y%m%d")
    bronze_rows: list[dict] = []

    info_payload, info_status = http_json(
        "GET",
        f"/v2/transport/busemtmad/lines/info/{today}/",
        headers={"accessToken": token},
        timeout=60,
    )
    bronze_rows.append(bronze_row("EMT_OPENAPI", "lines_info", today, info_status, info_payload))
    line_meta: dict[str, dict] = {}
    if str(info_payload.get("code", "")) == "00":
        for block in info_payload.get("data", []) or []:
            lid = str(block.get("line") or "").strip()
            if lid:
                line_meta[lid] = {
                    "line_label": str(block.get("label") or route_label.get(lid) or lid).strip(),
                    "name_a": block.get("nameA") or block.get("name_a"),
                    "name_b": block.get("nameB") or block.get("name_b"),
                }

    cal_payload, cal_status = http_json(
        "GET",
        f"/v1/transport/busemtmad/calendar/{today}/{today}/",
        headers={"accessToken": token},
        timeout=60,
    )
    bronze_rows.append(bronze_row("EMT_OPENAPI", "calendar", today, cal_status, cal_payload))
    day_type = "LA"
    if str(cal_payload.get("code", "")) == "00":
        for block in cal_payload.get("data", []) or []:
            dt = str(block.get("dayType") or block.get("DayType") or "").strip().upper()
            if dt in ("LA", "SA", "FE"):
                day_type = dt
                break

    seed_keys: dict[tuple[str, str, int], dict] = {}
    path_to_dir = {"1": 0, "2": 1}
    now_utc = datetime.now(UTC).replace(tzinfo=None, microsecond=0)
    for lid in sorted(candidate_lines):
        for path, direction_id in path_to_dir.items():
            try:
                payload, status = http_json(
                    "GET",
                    f"/v1/transport/busemtmad/lines/{lid}/stops/{path}/",
                    headers={"accessToken": token},
                    timeout=60,
                )
            except Exception as exc:  # noqa: BLE001
                print(f"  line_stops {lid}/{path}: FAIL {exc}")
                time.sleep(0.3)
                continue

            bronze_rows.append(
                bronze_row("EMT_OPENAPI", "line_stops", f"{lid}:{path}", status, payload)
            )
            if str(payload.get("code", "")) != "00":
                print(f"  line_stops {lid}/{path}: api_code={payload.get('code')}")
                time.sleep(0.2)
                continue

            meta = line_meta.get(lid, {})
            label = meta.get("line_label") or route_label.get(lid) or lid
            name_a = meta.get("name_a")
            name_b = meta.get("name_b")

            for block in payload.get("data", []) or []:
                stops_list = block.get("stops") or []
                first_sid = stop_id_str(stops_list[0].get("stop")) if stops_list else None
                for st in stops_list:
                    sid = stop_id_str(st.get("stop"))
                    if sid is None or sid not in in_scope_ids:
                        continue
                    attrs = stop_attrs.get(sid, {})
                    is_term = (sid, lid, direction_id) in terminus_keys or first_sid == sid
                    seed_keys[(sid, lid, direction_id)] = {
                        "line_label": label,
                        "stop_name": attrs.get("stop_name") or st.get("name"),
                        "stop_lat": attrs.get("stop_lat"),
                        "stop_lon": attrs.get("stop_lon"),
                        "name_a": name_a,
                        "name_b": name_b,
                        "is_terminus": bool(is_term),
                    }
            time.sleep(0.15)

    if not seed_keys:
        raise RuntimeError("No S1 line-stops seed rows. Check EMT credentials / geofence.")

    seed_rows = []
    for (sid, lid, direction_id), meta in sorted(seed_keys.items()):
        seed_rows.append(
            {
                "_rk": sha_rk(sid, lid, direction_id, None, now_utc),
                "stop_id": sid,
                "line_id": lid,
                "line_label": meta["line_label"],
                "direction_id": direction_id,
                "bus_id": None,
                "destination": None,
                "eta_seconds": None,
                "datetime_polling": now_utc,
                "ingested_at": now_utc,
                "stop_name": meta["stop_name"],
                "stop_lat": meta["stop_lat"],
                "stop_lon": meta["stop_lon"],
                "direction_text": None,
                "name_a": meta["name_a"],
                "name_b": meta["name_b"],
                "is_terminus": meta["is_terminus"],
                "catalog_loaded_at": catalog_date,
                "day_type": day_type,
                "map_ok": True,
            }
        )

    bronze_df = spark.createDataFrame(bronze_rows)
    bronze_df.write.format("delta").mode("append").saveAsTable(BRONZE_TABLE)
    print(f"Appended {len(bronze_rows)} bronze row(s) (lines_info/calendar/line_stops)")

    seed_df = spark.createDataFrame(seed_rows, schema=SILVER_SEED_SCHEMA)
    if spark.catalog.tableExists(SILVER_ARRIVES):
        spark.sql(
            f"""
            DELETE FROM {SILVER_ARRIVES}
            WHERE bus_id IS NULL
              AND eta_seconds IS NULL
              AND destination IS NULL
            """
        )
    seed_df.write.format("delta").mode("append").saveAsTable(SILVER_ARRIVES)
    print(f"Seeded silver_arrives catalogue rows: {seed_df.count()}")
    print(f"silver_arrives total: {spark.table(SILVER_ARRIVES).count()}")

    scope_stops = sorted({r["stop_id"] for r in seed_rows})
    out_path = Path("/lakehouse/default/Files/config/scope_stop_ids.txt")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(",".join(scope_stops) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    display(seed_df.orderBy("stop_id", "line_id", "direction_id").limit(50))
