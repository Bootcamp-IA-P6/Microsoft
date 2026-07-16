# Fabric notebook source — docs v1.1
#
# How to use (Fabric UI):
#   1. Run nb_create_tables
#   2. Upload GTFS zip → Lakehouse Files/gtfs/gtfs_emt.zip
#   3. New Notebook → name: nb_bootstrap_gtfs_silver → attach Lakehouse
#   4. Split on "# COMMAND ----------" → Run All
#   5. Copy printed scope_stop_ids into nb_ingest_emt_arrives
#
# Contract: docs/01 §3 geofence, docs/02 §5 GTFS, docs/03 §5–§7, docs/04 §7
#
# NOTE: Do NOT use spark.read.csv("/lakehouse/default/Files/...") — OneLake returns
# HTTP 400 on HEAD. Extract to local /tmp and read with pandas → Spark DataFrame.

# COMMAND ----------

# MAGIC %md
# MAGIC # Bootstrap GTFS → silver dims + scope_stop_ids
# MAGIC - `silver_stops_dim` / `silver_lines_dim` / `silver_stop_lines`
# MAGIC - `in_scope` = Sol circle 600 m (`docs/01` §3)
# MAGIC - `is_terminus` = `stop_sequence = 1` (`docs/04` §3)
# MAGIC
# MAGIC GTFS files are read via **pandas on local /tmp** (avoids Fabric OneLake 400 on `spark.read.csv`).

# COMMAND ----------

gtfs_zip_path = "/lakehouse/default/Files/gtfs/gtfs_emt.zip"  # @param {type:"string"}
gtfs_zip_url = ""  # @param {type:"string"}
geofence_lat = 40.416729  # @param {type:"number"}
geofence_lon = -3.703339  # @param {type:"number"}
geofence_radius_m = 600  # @param {type:"number"}

# COMMAND ----------

import math
import re
import shutil
import tempfile
import urllib.request
import zipfile
from datetime import date
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
)

SOL_LAT = float(geofence_lat)
SOL_LON = float(geofence_lon)
RADIUS_M = float(geofence_radius_m)
CATALOG_DATE = date.today()


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def to_int_stop_id(raw) -> int | None:
    s = str(raw or "").strip()
    if not s:
        return None
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    m = re.search(r"(\d+)$", s)
    return int(m.group(1)) if m else None


def resolve_zip_path(preferred: str) -> Path:
    """Accept gtfs_emt.zip (whatever is under Files/gtfs/)."""
    p = Path(preferred)
    if p.is_file():
        return p
    parent = p.parent if p.parent.as_posix().endswith("gtfs") else Path("/lakehouse/default/Files/gtfs")
    if parent.is_dir():
        for cand in sorted(parent.glob("*.zip")):
            print(f"Using zip found: {cand}")
            return cand
    raise FileNotFoundError(
        f"GTFS zip not found at {preferred}.\n"
        "Upload a .zip to Lakehouse Files/gtfs/ (e.g. gtfs_emt.zip)."
    )


if str(gtfs_zip_url).strip():
    dest = Path(gtfs_zip_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading GTFS from {gtfs_zip_url} ...")
    urllib.request.urlretrieve(str(gtfs_zip_url).strip(), dest.as_posix())

zip_path = resolve_zip_path(gtfs_zip_path)
print(f"Zip: {zip_path} ({zip_path.stat().st_size} bytes)")

# Extract to DRIVER local disk — not OneLake Files (avoids spark.read 400)
local_root = Path(tempfile.mkdtemp(prefix="gtfs_"))
print(f"Extracting to local temp: {local_root}")
with zipfile.ZipFile(zip_path.as_posix(), "r") as zf:
    zf.extractall(local_root.as_posix())

stops_file = next(local_root.rglob("stops.txt"), None)
if stops_file is None:
    raise FileNotFoundError(f"stops.txt not found under {local_root}")

gtfs_dir = stops_file.parent
print(f"GTFS folder: {gtfs_dir}")
for name in ("stops.txt", "routes.txt", "trips.txt", "stop_times.txt"):
    if not (gtfs_dir / name).is_file():
        raise FileNotFoundError(f"Missing {gtfs_dir / name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## silver_stops_dim

# COMMAND ----------

# pandas on local path — do not use spark.read.csv on Lakehouse Files paths
stops_pdf = pd.read_csv(gtfs_dir / "stops.txt", dtype=str, keep_default_na=False)

stop_rows = []
skipped = 0
for _, r in stops_pdf.iterrows():
    sid = to_int_stop_id(r.get("stop_id"))
    if sid is None:
        skipped += 1
        continue
    lat_s = str(r.get("stop_lat", "")).strip()
    lon_s = str(r.get("stop_lon", "")).strip()
    try:
        lat = float(lat_s) if lat_s else None
        lon = float(lon_s) if lon_s else None
    except ValueError:
        lat, lon = None, None
    in_scope = (
        lat is not None
        and lon is not None
        and haversine_m(SOL_LAT, SOL_LON, lat, lon) <= RADIUS_M
    )
    stop_rows.append(
        {
            "stop_id": sid,
            "stop_name": r.get("stop_name") or None,
            "stop_lat": lat,
            "stop_lon": lon,
            "direction_text": None,
            "in_scope": bool(in_scope),
            "catalog_loaded_at": CATALOG_DATE,
        }
    )

stops_schema = StructType(
    [
        StructField("stop_id", IntegerType(), True),
        StructField("stop_name", StringType(), True),
        StructField("stop_lat", DoubleType(), True),
        StructField("stop_lon", DoubleType(), True),
        StructField("direction_text", StringType(), True),
        StructField("in_scope", BooleanType(), True),
        StructField("catalog_loaded_at", DateType(), True),
    ]
)
silver_stops = spark.createDataFrame(stop_rows, schema=stops_schema).dropDuplicates(["stop_id"])
silver_stops.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    "silver_stops_dim"
)
print(
    f"silver_stops_dim: {silver_stops.count()} "
    f"(skipped={skipped}, in_scope={silver_stops.filter('in_scope = true').count()})"
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## silver_lines_dim + silver_stop_lines

# COMMAND ----------

routes_pdf = pd.read_csv(gtfs_dir / "routes.txt", dtype=str, keep_default_na=False)
trips_pdf = pd.read_csv(gtfs_dir / "trips.txt", dtype=str, keep_default_na=False)
# Only columns we need (keeps memory down)
st_pdf = pd.read_csv(
    gtfs_dir / "stop_times.txt",
    dtype=str,
    keep_default_na=False,
    usecols=lambda c: c in {"trip_id", "stop_id", "stop_sequence"},
)

routes = (
    spark.createDataFrame(routes_pdf[["route_id", "route_short_name"]].fillna(""))
    .select(
        F.col("route_id").alias("line_id"),
        F.coalesce(
            F.nullif(F.trim(F.col("route_short_name")), F.lit("")),
            F.col("route_id"),
        ).alias("line_label"),
    )
)

trip_cols = ["route_id", "trip_id", "direction_id"]
if "trip_headsign" in trips_pdf.columns:
    trip_cols.append("trip_headsign")
else:
    trips_pdf["trip_headsign"] = ""
    trip_cols.append("trip_headsign")

trips = (
    spark.createDataFrame(trips_pdf[trip_cols].fillna(""))
    .select(
        F.col("route_id").alias("line_id"),
        F.col("trip_id"),
        F.col("direction_id").cast("int").alias("direction_id"),
        F.trim(F.col("trip_headsign")).alias("trip_headsign"),
    )
)

headsigns = (
    trips.filter(F.col("trip_headsign").isNotNull() & (F.col("trip_headsign") != ""))
    .groupBy("line_id", "direction_id")
    .agg(F.first("trip_headsign").alias("headsign"))
)
name_a = headsigns.filter("direction_id = 0").select(
    F.col("line_id"), F.col("headsign").alias("name_a")
)
name_b = headsigns.filter("direction_id = 1").select(
    F.col("line_id"), F.col("headsign").alias("name_b")
)

stop_times = spark.createDataFrame(
    st_pdf[["trip_id", "stop_id", "stop_sequence"]].fillna("")
).select(
    F.col("trip_id"),
    F.col("stop_id").alias("stop_id_raw"),
    F.col("stop_sequence").cast("int").alias("stop_sequence"),
)

raw_to_int = []
for _, r in stops_pdf.iterrows():
    sid = to_int_stop_id(r.get("stop_id"))
    if sid is not None:
        raw_to_int.append((str(r.get("stop_id")), sid))
stop_id_map = spark.createDataFrame(raw_to_int, ["stop_id_raw", "stop_id"]).dropDuplicates(
    ["stop_id_raw"]
)

graph = (
    stop_times.join(stop_id_map, on="stop_id_raw", how="inner")
    .join(trips, on="trip_id", how="inner")
    .join(routes, on="line_id", how="inner")
    .select("stop_id", "line_id", "line_label", "direction_id", "stop_sequence")
    .filter(F.col("direction_id").isin(0, 1))
)

terminus = (
    graph.filter(F.col("stop_sequence") == 1)
    .select("stop_id", "line_id", "direction_id")
    .distinct()
    .withColumn("is_terminus", F.lit(True))
)

stop_lines = (
    graph.select("stop_id", "line_id", "line_label", "direction_id")
    .distinct()
    .join(terminus, on=["stop_id", "line_id", "direction_id"], how="left")
    .withColumn("is_terminus", F.coalesce(F.col("is_terminus"), F.lit(False)))
    .withColumn("catalog_loaded_at", F.lit(CATALOG_DATE))
)

stop_lines.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    "silver_stop_lines"
)
print(f"silver_stop_lines: {stop_lines.count()}")

in_scope_stops = spark.table("silver_stops_dim").filter("in_scope = true").select("stop_id")
lines_in_scope = (
    stop_lines.join(in_scope_stops, on="stop_id", how="inner")
    .select("line_id")
    .distinct()
    .withColumn("in_scope", F.lit(True))
)

silver_lines = (
    routes.join(name_a, on="line_id", how="left")
    .join(name_b, on="line_id", how="left")
    .join(lines_in_scope, on="line_id", how="left")
    .withColumn("in_scope", F.coalesce(F.col("in_scope"), F.lit(False)))
    .withColumn("catalog_loaded_at", F.lit(CATALOG_DATE))
    .select("line_id", "line_label", "name_a", "name_b", "in_scope", "catalog_loaded_at")
    .dropDuplicates(["line_id"])
)

silver_lines.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    "silver_lines_dim"
)
print(
    f"silver_lines_dim: {silver_lines.count()} "
    f"(in_scope={silver_lines.filter('in_scope = true').count()})"
)

# cleanup local extract
shutil.rmtree(local_root, ignore_errors=True)
print(f"Cleaned temp {local_root}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Freeze scope_stop_ids (docs/01 pending deliverable)

# COMMAND ----------

scope_df = (
    spark.table("silver_stops_dim")
    .filter("in_scope = true")
    .select("stop_id", "stop_name", "stop_lat", "stop_lon")
    .orderBy("stop_id")
)
display(scope_df)

ids = [str(r["stop_id"]) for r in scope_df.collect()]
scope_csv = ",".join(ids)
print(f"\nin_scope count = {len(ids)}")
print("Paste into nb_ingest_emt_arrives → stop_ids:\n")
print(scope_csv)

out_path = Path("/lakehouse/default/Files/config/scope_stop_ids.txt")
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(scope_csv + "\n", encoding="utf-8")
print(f"\nWrote {out_path}")
