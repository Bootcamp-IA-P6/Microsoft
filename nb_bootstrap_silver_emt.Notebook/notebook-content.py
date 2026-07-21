# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "6fc8888d-9aaf-46c0-b6fc-5aace3d34640",
# META       "default_lakehouse_name": "lh_emt_madrid",
# META       "default_lakehouse_workspace_id": "8bfdf6eb-bff5-4647-9484-daa63a5b7ff0",
# META       "known_lakehouses": [
# META         {
# META           "id": "6fc8888d-9aaf-46c0-b6fc-5aace3d34640"
# META         }
# META       ]
# META     }
# META   }
# META }

# MARKDOWN ********************

# # Bootstrap → seed `silver_emt` (contract v4.2)
# 1. GTFS stops → Sol geofence 600 m (`in_scope`)
# 2. Candidate `line_id` from GTFS trips touching in-scope stops
# 3. S1 `GET …/lines/{lineId}/stops/{1|2}/` = paso SoT
# 4. Seed rows into `silver_emt` (bus_id NULL) + bronze `line_stops` / `calendar`

# PARAMETERS CELL ********************

gtfs_zip_path = "/lakehouse/default/Files/gtfs/gtfs_emt.zip"  # @param {type:"string"}
gtfs_zip_url = "https://datos.emtmadrid.es/dataset/9b23259a-4491-494b-9695-36a7709b2c12/resource/3cba2058-9833-422c-a704-bf992d31d2ee/download/gtfs_emt.zip"  # @param {type:"string"}
geofence_lat = 40.416729  # @param {type:"number"}
geofence_lon = -3.703339  # @param {type:"number"}
geofence_radius_m = 600  # @param {type:"number"}
variable_library_name = "var_emt_madrid"  # @param {type:"string"}
# Optional comma list of EMT internal line ids (e.g. "027,014"). Empty = discover from GTFS.
line_ids_override = ""  # @param {type:"string"}


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import hashlib
import json
import math
import re
import shutil
import tempfile
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

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

BASE_URL = "https://openapi.emtmadrid.es"
SOL_LAT = float(geofence_lat)
SOL_LON = float(geofence_lon)
RADIUS_M = float(geofence_radius_m)
CATALOG_DATE = date.today()
MADRID = ZoneInfo("Europe/Madrid")
UTC = timezone.utc
TZ_NOTE = "Europe/Madrid"

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


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def stop_id_str(raw) -> str | None:
    s = str(raw or "").strip()
    if not s:
        return None
    if re.fullmatch(r"-?\d+", s):
        return str(int(s))
    m = re.search(r"(\d+)$", s)
    return str(int(m.group(1))) if m else None


def load_variable_library(library_name: str):
    try:
        import notebookutils

        return notebookutils.variableLibrary.getLibrary(library_name)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"Cannot load Variable Library '{library_name}': {exc}"
        ) from exc


def lib_get(lib, name: str) -> str:
    if hasattr(lib, "getVariable"):
        try:
            return str(lib.getVariable(name) or "").strip()
        except Exception:  # noqa: BLE001
            pass
    try:
        return str(lib[name] or "").strip()
    except Exception:  # noqa: BLE001
        pass
    return str(getattr(lib, name, None) or "").strip()


def load_emt_credentials(library_name: str) -> tuple[str, str]:
    lib = load_variable_library(library_name)
    client_id = lib_get(lib, "EMT_CLIENT_ID")
    pass_key = lib_get(lib, "EMT_MADRID_PASS_KEY")
    if not client_id or not pass_key:
        raise ValueError("Variable Library needs EMT_CLIENT_ID and EMT_MADRID_PASS_KEY")
    return client_id, pass_key


def _http_json(method: str, path: str, headers=None, body=None) -> tuple[dict, int]:
    req = urllib.request.Request(
        f"{BASE_URL}{path}", data=body, headers=headers or {}, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8")), int(resp.status)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {path}: {raw[:300]}") from exc


def emt_login(client_id: str, pass_key: str) -> str:
    payload, _ = _http_json(
        "GET",
        "/v1/mobilitylabs/user/login/",
        headers={"X-ClientId": client_id, "passKey": pass_key},
    )
    if str(payload.get("code", "")) not in ("00", "01"):
        raise RuntimeError(f"login failed: {payload.get('description')}")
    return payload["data"][0]["accessToken"]


def bronze_row(
    *,
    source_system: str,
    resource_kind: str,
    resource_key: str,
    http_status: int,
    api_code: str | None,
    api_description: str | None,
    payload_obj: dict,
) -> dict:
    payload_s = json.dumps(payload_obj, ensure_ascii=False)
    return {
        "ingest_id": str(uuid.uuid4()),
        "ingested_at": datetime.now(UTC).replace(tzinfo=None),
        "source_system": source_system,
        "resource_kind": resource_kind,
        "resource_key": resource_key,
        "http_status": http_status,
        "api_code": api_code,
        "api_description": api_description,
        "payload": payload_s,
        "content_sha256": hashlib.sha256(payload_s.encode("utf-8")).hexdigest(),
        "timezone_note": TZ_NOTE,
    }


def sha_rk(stop_id, line_id, direction_id, bus_id, datetime_polling: datetime) -> str:
    ts = datetime_polling.isoformat(sep="T", timespec="seconds")
    parts = [
        str(stop_id),
        str(line_id),
        "" if direction_id is None else str(direction_id),
        "" if bus_id is None else str(bus_id),
        ts,
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


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
    raise FileNotFoundError(
        f"GTFS zip not found at {preferred}. Upload to Lakehouse Files/gtfs/."
    )


def norm_name(s: str | None) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().upper())

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 1) GTFS → in-scope stops + candidate lines

# CELL ********************

if str(gtfs_zip_url).strip():
    dest = Path(gtfs_zip_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading GTFS from {gtfs_zip_url} ...")
    urllib.request.urlretrieve(str(gtfs_zip_url).strip(), dest.as_posix())

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
        lat == lat
        and lon == lon
        and haversine_m(SOL_LAT, SOL_LON, lat, lon) <= RADIUS_M
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
if len(in_scope_ids) < 1:
    raise RuntimeError("No in-scope stops — check geofence / GTFS")

# Candidate line_ids: GTFS routes that serve at least one in-scope stop
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
terminus_keys: set[tuple[str, str, int]] = set()  # stop, line, gtfs direction (hint only)
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

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 2) S1 lines/info + calendar + line stops → seed

# CELL ********************

client_id, pass_key = load_emt_credentials(variable_library_name)
token = emt_login(client_id, pass_key)
today = date.today().strftime("%Y%m%d")
bronze_rows: list[dict] = []

# lines/info → label, nameA, nameB
info_payload, info_status = _http_json(
    "GET",
    f"/v2/transport/busemtmad/lines/info/{today}/",
    headers={"accessToken": token},
)
bronze_rows.append(
    bronze_row(
        source_system="EMT_OPENAPI",
        resource_kind="lines_info",
        resource_key=today,
        http_status=info_status,
        api_code=str(info_payload.get("code", "")),
        api_description=info_payload.get("description"),
        payload_obj=info_payload,
    )
)
line_meta: dict[str, dict] = {}
if str(info_payload.get("code", "")) == "00":
    for block in info_payload.get("data", []) or []:
        lid = str(block.get("line") or "").strip()
        if not lid:
            continue
        line_meta[lid] = {
            "line_label": str(block.get("label") or route_label.get(lid) or lid).strip(),
            "name_a": block.get("nameA") or block.get("name_a"),
            "name_b": block.get("nameB") or block.get("name_b"),
        }
print(f"lines/info meta rows: {len(line_meta)}")

# calendar → day_type for today
cal_payload, cal_status = _http_json(
    "GET",
    f"/v1/transport/busemtmad/calendar/{today}/{today}/",
    headers={"accessToken": token},
)
bronze_rows.append(
    bronze_row(
        source_system="EMT_OPENAPI",
        resource_kind="calendar",
        resource_key=today,
        http_status=cal_status,
        api_code=str(cal_payload.get("code", "")),
        api_description=cal_payload.get("description"),
        payload_obj=cal_payload,
    )
)
day_type = "LA"
if str(cal_payload.get("code", "")) == "00":
    for block in cal_payload.get("data", []) or []:
        dt = str(block.get("dayType") or block.get("DayType") or "").strip().upper()
        if dt in ("LA", "SA", "FE"):
            day_type = dt
            break
print(f"day_type today = {day_type}")

# line stops SoT
seed_keys: dict[tuple[str, str, int], dict] = {}
path_to_dir = {"1": 0, "2": 1}
now_utc = datetime.now(UTC).replace(tzinfo=None, microsecond=0)

for lid in sorted(candidate_lines):
    for path, direction_id in path_to_dir.items():
        try:
            payload, status = _http_json(
                "GET",
                f"/v1/transport/busemtmad/lines/{lid}/stops/{path}/",
                headers={"accessToken": token},
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  line_stops {lid}/{path}: FAIL {exc}")
            time.sleep(0.3)
            continue

        bronze_rows.append(
            bronze_row(
                source_system="EMT_OPENAPI",
                resource_kind="line_stops",
                resource_key=f"{lid}:{path}",
                http_status=status,
                api_code=str(payload.get("code", "")),
                api_description=payload.get("description"),
                payload_obj=payload,
            )
        )
        if str(payload.get("code", "")) != "00":
            print(f"  line_stops {lid}/{path}: api_code={payload.get('code')}")
            continue

        meta = line_meta.get(lid, {})
        label = meta.get("line_label") or route_label.get(lid) or lid
        name_a = meta.get("name_a")
        name_b = meta.get("name_b")

        for block in payload.get("data", []) or []:
            for st in block.get("stops", []) or []:
                sid = stop_id_str(st.get("stop"))
                if sid is None or sid not in in_scope_ids:
                    continue
                attrs = stop_attrs.get(sid, {})
                is_term = (sid, lid, direction_id) in terminus_keys
                # also terminus if first stop in EMT list
                stops_list = block.get("stops") or []
                if stops_list and stop_id_str(stops_list[0].get("stop")) == sid:
                    is_term = True
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

print(f"Seed triples (stop,line,direction) in-scope: {len(seed_keys)}")
if not seed_keys:
    raise RuntimeError(
        "No S1 line-stops seed rows. Check EMT credentials / line_ids / geofence."
    )

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
            "catalog_loaded_at": CATALOG_DATE,
            "day_type": day_type,
            "map_ok": True,
        }
    )

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 3) Write bronze + overwrite seed catalogue rows in silver_emt

# CELL ********************

from pathlib import Path
from pyspark.sql import functions as F

# -----------------------------
# Bronze
# -----------------------------
bronze_df = spark.createDataFrame(bronze_rows)

bronze_table = "bronze_emt_raw"

if spark.catalog.tableExists(bronze_table):
    target_schema = spark.table(bronze_table).schema

    # auto cast
    for field in target_schema.fields:
        if field.name in bronze_df.columns:
            bronze_df = bronze_df.withColumn(
                field.name,
                F.col(field.name).cast(field.dataType)
            )

    # set order
    target_columns = [field.name for field in target_schema.fields]

    # Add NULL columns if existing columns are missing
    for field in target_schema.fields:
        if field.name not in bronze_df.columns:
            bronze_df = bronze_df.withColumn(
                field.name,
                F.lit(None).cast(field.dataType)
            )

    bronze_df = bronze_df.select(*target_columns)

bronze_df.write \
    .format("delta") \
    .mode("append") \
    .saveAsTable(bronze_table)

print(
    f"Appended {len(bronze_rows)} bronze row(s) "
    "(lines_info/calendar/line_stops)"
)

# -----------------------------
# Silver seed
# -----------------------------
seed_df = spark.createDataFrame(
    seed_rows,
    schema=SILVER_SEED_SCHEMA
)

silver_table = "silver_emt"

# Replace catalogue / empty-poll rows
# Keep rows with actual buses
if spark.catalog.tableExists(silver_table):
    spark.sql(
        f"""
        DELETE FROM {silver_table}
        WHERE bus_id IS NULL
          AND eta_seconds IS NULL
          AND destination IS NULL
        """
    )

    # Automatically fits existing silver table schema
    silver_target_schema = spark.table(silver_table).schema

    for field in silver_target_schema.fields:
        if field.name in seed_df.columns:
            seed_df = seed_df.withColumn(
                field.name,
                F.col(field.name).cast(field.dataType)
            )

    # If the existing silver column does not exist in seed_df, add it as NULL
    for field in silver_target_schema.fields:
        if field.name not in seed_df.columns:
            seed_df = seed_df.withColumn(
                field.name,
                F.lit(None).cast(field.dataType)
            )

    silver_target_columns = [
        field.name
        for field in silver_target_schema.fields
    ]

    seed_df = seed_df.select(*silver_target_columns)

seed_count = seed_df.count()

seed_df.write \
    .format("delta") \
    .mode("append") \
    .saveAsTable(silver_table)

print(f"Seeded silver_emt catalogue rows: {seed_count}")
print(f"silver_emt total: {spark.table(silver_table).count()}")

# -----------------------------
# Scope stop IDs file
# -----------------------------
scope_stops = sorted({
    str(row["stop_id"])
    for row in seed_rows
    if row.get("stop_id") is not None
})

print(f"in_scope stops with paso: {len(scope_stops)}")

out_path = Path(
    "/lakehouse/default/Files/config/scope_stop_ids.txt"
)

out_path.parent.mkdir(
    parents=True,
    exist_ok=True
)

out_path.write_text(
    ",".join(scope_stops) + "\n",
    encoding="utf-8"
)

print(f"Wrote {out_path}")

display(
    seed_df
    .orderBy("stop_id", "line_id", "direction_id")
    .limit(50)
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
