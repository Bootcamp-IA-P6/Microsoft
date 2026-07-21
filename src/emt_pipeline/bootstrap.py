import math
import shutil
import ssl
import tempfile
import time
import urllib.request
import zipfile
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from pyspark.sql import functions as F
from pyspark.sql.types import (
    BooleanType,
    DateType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

from .common import (
    TZ_NOTE,
    UTC,
    bronze_row,
    http_json,
    load_emt_credentials,
    login_token,
    norm_name,
    sha_rk,
    stop_id_str,
)

GTFS_DOWNLOAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; emt-pipeline/0.1; "
        "+https://github.com/Bootcamp-IA-P6/Microsoft)"
    ),
    "Accept": "application/zip,application/octet-stream,*/*",
    "Connection": "close",
}


def download_gtfs_zip(url: str, dest: Path, *, attempts: int = 5) -> None:
    """Download GTFS zip with retries — Fabric urllib often hits SSL EOF on datos.emtmadrid.es."""
    url = str(url).strip()
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    last_err: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            if tmp.exists():
                tmp.unlink()
            print(f"Downloading GTFS (attempt {attempt}/{attempts}) from {url} ...")
            _download_via_requests(url, tmp)
            if tmp.stat().st_size < 1024:
                raise RuntimeError(f"Downloaded file too small ({tmp.stat().st_size} bytes)")
            tmp.replace(dest)
            print(f"GTFS saved → {dest} ({dest.stat().st_size} bytes)")
            return
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            print(f"GTFS download failed (attempt {attempt}/{attempts}): {exc!r}")
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
            if attempt < attempts:
                time.sleep(min(2 ** attempt, 30))

    # Last resort: urllib with explicit TLS 1.2+ context (some runtimes differ)
    try:
        print("GTFS download: falling back to urllib + SSL context ...")
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers=GTFS_DOWNLOAD_HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=120) as resp:
            with open(tmp, "wb") as out:
                shutil.copyfileobj(resp, out)
        if tmp.stat().st_size < 1024:
            raise RuntimeError(f"Downloaded file too small ({tmp.stat().st_size} bytes)")
        tmp.replace(dest)
        print(f"GTFS saved via urllib → {dest} ({dest.stat().st_size} bytes)")
        return
    except Exception as exc:  # noqa: BLE001
        last_err = exc
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass

    raise RuntimeError(
        f"Failed to download GTFS after {attempts} attempts (+ urllib fallback): {last_err}"
    ) from last_err


def _download_via_requests(url: str, tmp: Path) -> None:
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError(
            "requests is required for GTFS download; add it to env_emt_pipeline"
        ) from exc

    with requests.Session() as session:
        session.headers.update(GTFS_DOWNLOAD_HEADERS)
        with session.get(url, stream=True, timeout=(30, 180), allow_redirects=True) as resp:
            resp.raise_for_status()
            with open(tmp, "wb") as out:
                for chunk in resp.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        out.write(chunk)


def resolve_zip_path(preferred: str) -> Path:
    p = Path(preferred)
    if p.is_file():
        return p
    parent = (
        p.parent
        if p.parent.as_posix().endswith("gtfs")
        else Path("/lakehouse/default/Files/gtfs")
    )
    if parent.is_dir():
        for cand in sorted(parent.glob("*.zip")):
            print(f"Using zip found: {cand}")
            return cand
    raise FileNotFoundError(f"GTFS zip not found at {preferred}. Upload to Lakehouse Files/gtfs/.")


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


SILVER_SEED_SCHEMA = StructType(
    [
        StructField("_rk", StringType(), False),
        StructField("stop_id", StringType(), False),
        StructField("line_id", StringType(), False),
        StructField("line_label", StringType(), False),
        StructField("direction_id", IntegerType(), True),
        StructField("bus_id", StringType(), True),
        StructField("destination", StringType(), True),
        StructField("eta_seconds", IntegerType(), True),
        StructField("datetime_polling", TimestampType(), False),
        StructField("ingested_at", TimestampType(), False),
        StructField("stop_name", StringType(), True),
        StructField("stop_lat", DoubleType(), True),
        StructField("stop_lon", DoubleType(), True),
        StructField("direction_text", StringType(), True),
        StructField("name_a", StringType(), True),
        StructField("name_b", StringType(), True),
        StructField("is_terminus", BooleanType(), True),
        StructField("catalog_loaded_at", DateType(), True),
        StructField("day_type", StringType(), True),
        StructField("map_ok", BooleanType(), True),
    ]
)


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
    bronze_df.write.format("delta").mode("append").saveAsTable("bronze_emt_raw")
    print(f"Appended {len(bronze_rows)} bronze row(s) (lines_info/calendar/line_stops)")

    seed_df = spark.createDataFrame(seed_rows, schema=SILVER_SEED_SCHEMA)
    if spark.catalog.tableExists("silver_emt"):
        spark.sql(
            """
            DELETE FROM silver_emt
            WHERE bus_id IS NULL
              AND eta_seconds IS NULL
              AND destination IS NULL
            """
        )
    seed_df.write.format("delta").mode("append").saveAsTable("silver_emt")
    print(f"Seeded silver_emt catalogue rows: {seed_df.count()}")
    print(f"silver_emt total: {spark.table('silver_emt').count()}")

    scope_stops = sorted({r["stop_id"] for r in seed_rows})
    out_path = Path("/lakehouse/default/Files/config/scope_stop_ids.txt")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(",".join(scope_stops) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    display(seed_df.orderBy("stop_id", "line_id", "direction_id").limit(50))

