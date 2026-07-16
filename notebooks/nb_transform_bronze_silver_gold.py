# Fabric notebook source — docs v1.1
#
# How to use (Fabric UI):
#   1. Run nb_create_tables → nb_bootstrap_gtfs_silver → nb_ingest_emt_arrives
#   2. New Notebook → name: nb_transform_bronze_silver_gold → attach Lakehouse
#   3. Split on "# COMMAND ----------" → Run All
#   4. Run All again → silver insert must be 0 (idempotent)
#   5. Continuous: Pipeline every ~60s → ingest → this transform
#      (set incremental=True for steady polling)
#
# Contract: docs/03, docs/04 §6–§8, docs/05 §2–§3

# COMMAND ----------

# MAGIC %md
# MAGIC # Transform bronze → silver → gold
# MAGIC - Flatten Arrive[] → `silver_arrival_observations` (dedup `_rk`)
# MAGIC - Catalogue LEFT JOIN → `gold_stop_line_eta_latest`
# MAGIC - Empty Arrive still rebuilds gold (`docs/04` §8)
# MAGIC - `is_stale` after 3 × 60 s (`docs/05` §2)

# COMMAND ----------

poll_interval_sec = 60  # @param {type:"number"}
stale_multiplier = 3  # @param {type:"number"}
bronze_table = "bronze_emt_raw"  # @param {type:"string"}
# True = only bronze newer than last silver ingest (use for 60s Pipeline)
# False = reprocess all bronze (idempotent via _rk; good for first tests)
incremental = True  # @param {type:"boolean"}

# COMMAND ----------

import hashlib
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from pyspark.sql import Window
from pyspark.sql import functions as F
from pyspark.sql.types import (
    BooleanType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

STALE_AFTER_SEC = int(poll_interval_sec) * int(stale_multiplier)
MADRID = ZoneInfo("Europe/Madrid")
UTC = timezone.utc


def parse_api_datetime_to_utc_naive(raw: str | None) -> datetime | None:
    """docs/04 §6 agreed: UTC storage; naive envelope datetime = Europe/Madrid → UTC."""
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        try:
            if "." not in s:
                return None
            main, rest = s.split(".", 1)
            frac = "".join(ch for ch in rest if ch.isdigit())[:6]
            tzpart = "".join(ch for ch in rest if not ch.isdigit())
            dt = datetime.fromisoformat(f"{main}.{frac}{tzpart}")
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=MADRID)
    return dt.astimezone(UTC).replace(tzinfo=None, microsecond=0)


def sha_rk(stop_id: int, line_id: str, bus_id: str, datetime_polling: datetime) -> str:
    ts = datetime_polling.isoformat(sep="T", timespec="seconds")
    return hashlib.sha256(f"{stop_id}{line_id}{bus_id}{ts}".encode("utf-8")).hexdigest()


def to_int_or_none(v):
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return None


# COMMAND ----------

# MAGIC %md
# MAGIC ## Bronze → `silver_arrival_observations` (`docs/04` §6)

# COMMAND ----------

bronze = spark.table(bronze_table).filter("api_code = '00' AND endpoint = 'arrives'")

if incremental and spark.catalog.tableExists("silver_arrival_observations"):
    max_ing = spark.table("silver_arrival_observations").agg(F.max("ingested_at")).collect()[0][0]
    if max_ing is not None:
        bronze = bronze.filter(F.col("ingested_at") > F.lit(max_ing))
        print(f"Incremental: bronze ingested_at > {max_ing}")

bronze_rows = bronze.collect()
print(f"Bronze rows to process: {len(bronze_rows)}")

sl_map = {
    (r["stop_id"], r["line_label"]): r["line_id"]
    for r in spark.table("silver_stop_lines")
    .select("stop_id", "line_label", "line_id")
    .dropDuplicates(["stop_id", "line_label"])
    .collect()
}
ld_map = {
    r["line_label"]: r["line_id"]
    for r in spark.table("silver_lines_dim")
    .select("line_label", "line_id")
    .dropDuplicates(["line_label"])
    .collect()
}

candidates: list[dict] = []
quarantine: list[str] = []

for br in bronze_rows:
    try:
        payload = json.loads(br["payload_json"])
    except (TypeError, json.JSONDecodeError) as exc:
        quarantine.append(f"bad JSON stop={br['request_stop_id']}: {exc}")
        continue

    dt_poll = parse_api_datetime_to_utc_naive(payload.get("datetime"))
    if dt_poll is None:
        quarantine.append(f"bad datetime stop={br['request_stop_id']}")
        continue

    # line_id from same-payload StopInfo.lines (docs/04 §6)
    label_to_line: dict[str, str] = {}
    for block in payload.get("data", []) or []:
        for si in block.get("StopInfo", []) or []:
            for ln in si.get("lines", []) or []:
                label = str(ln.get("label") or "").strip()
                line_id = str(ln.get("line") or "").strip()
                if label and line_id:
                    label_to_line[label] = line_id

    for block in payload.get("data", []) or []:
        for arr in block.get("Arrive", []) or []:
            line_label = str(arr.get("line") or "").strip()
            bus_raw = arr.get("bus")
            if not line_label or bus_raw is None or bus_raw == "":
                quarantine.append(f"missing keys stop={br['request_stop_id']}")
                continue

            stop_id = to_int_or_none(arr.get("stop"))
            if stop_id is None:
                stop_id = int(br["request_stop_id"])

            bus_id = str(bus_raw).strip()
            destination = str(arr.get("destination") or "").strip()
            eta = to_int_or_none(arr.get("estimateArrive"))  # null kept; row not discarded

            line_id = label_to_line.get(line_label)
            if not line_id:
                line_id = sl_map.get((stop_id, line_label))
            if not line_id:
                line_id = ld_map.get(line_label)
            if not line_id:
                quarantine.append(
                    f"unresolved line_id stop={stop_id} label={line_label} bus={bus_id}"
                )
                continue

            candidates.append(
                {
                    "_rk": sha_rk(stop_id, line_id, bus_id, dt_poll),
                    "stop_id": stop_id,
                    "line_id": line_id,
                    "line_label": line_label,
                    "bus_id": bus_id,
                    "destination": destination,
                    "eta_seconds": eta,
                    "datetime_polling": dt_poll,
                    "ingested_at": br["ingested_at"],
                }
            )

print(f"Candidates: {len(candidates)}; quarantine: {len(quarantine)}")
for q in quarantine[:25]:
    print(f"  QUARANTINE: {q}")
if len(quarantine) > 25:
    print(f"  ... +{len(quarantine) - 25} more")

obs_schema = StructType(
    [
        StructField("_rk", StringType(), False),
        StructField("stop_id", IntegerType(), False),
        StructField("line_id", StringType(), False),
        StructField("line_label", StringType(), False),
        StructField("bus_id", StringType(), False),
        StructField("destination", StringType(), False),
        StructField("eta_seconds", IntegerType(), True),
        StructField("datetime_polling", TimestampType(), False),
        StructField("ingested_at", TimestampType(), False),
    ]
)

inserted = 0
if candidates:
    cand_df = spark.createDataFrame(candidates, schema=obs_schema).dropDuplicates(["_rk"])
    if spark.catalog.tableExists("silver_arrival_observations"):
        existing = spark.table("silver_arrival_observations").select("_rk")
        new_df = cand_df.join(existing, on="_rk", how="left_anti")
    else:
        new_df = cand_df
    inserted = new_df.count()
    if inserted:
        new_df.write.format("delta").mode("append").saveAsTable("silver_arrival_observations")

print(f"Inserted silver observations: {inserted}")
print(f"Total silver_arrival_observations: {spark.table('silver_arrival_observations').count()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver → `gold_stop_line_eta_latest` (`docs/04` §8, `docs/05` §2)

# COMMAND ----------

bronze_ok = spark.table(bronze_table).filter("api_code = '00' AND endpoint = 'arrives'")
latest_bronze = (
    bronze_ok.withColumn(
        "rn",
        F.row_number().over(
            Window.partitionBy("request_stop_id").orderBy(F.col("ingested_at").desc())
        ),
    )
    .filter("rn = 1")
    .drop("rn")
)
latest_list = latest_bronze.collect()
print(f"Stops with successful poll: {len(latest_list)}")

stop_lines = spark.table("silver_stop_lines")
lines_dim = spark.table("silver_lines_dim").select("line_id", "name_a", "name_b")
obs_all = spark.table("silver_arrival_observations")
now_utc = datetime.now(UTC).replace(tzinfo=None)
gold_rows: list[dict] = []

for br in latest_list:
    stop_id = int(br["request_stop_id"])
    try:
        payload = json.loads(br["payload_json"])
    except (TypeError, json.JSONDecodeError):
        print(f"Skip gold stop={stop_id}: bad JSON")
        continue

    poll_ts = parse_api_datetime_to_utc_naive(payload.get("datetime"))
    if poll_ts is None:
        poll_ts = br["ingested_at"]
        if getattr(poll_ts, "tzinfo", None) is not None:
            poll_ts = poll_ts.astimezone(UTC).replace(tzinfo=None)
        if hasattr(poll_ts, "replace"):
            poll_ts = poll_ts.replace(microsecond=0)

    is_stale = (now_utc - poll_ts).total_seconds() > STALE_AFTER_SEC

    cat_rows = (
        stop_lines.filter(F.col("stop_id") == stop_id)
        .groupBy("stop_id", "line_id", "line_label")
        .agg(F.max(F.col("is_terminus").cast("int")).alias("is_terminus_any"))
        .collect()
    )
    if not cat_rows:
        print(f"No catalogue lines for stop={stop_id}; skip")
        continue

    obs = (
        obs_all.filter(F.col("stop_id") == stop_id)
        .filter(F.col("datetime_polling") == F.lit(poll_ts))
        .collect()
    )

    # One gold row per line: min non-null eta (docs/03 grain = stop+line)
    best_by_line: dict[str, dict] = {}
    for o in obs:
        lid = o["line_id"]
        cur = best_by_line.get(lid)
        if cur is None:
            best_by_line[lid] = o
            continue
        eta_new, eta_old = o["eta_seconds"], cur["eta_seconds"]
        if eta_old is None and eta_new is not None:
            best_by_line[lid] = o
        elif eta_new is not None and eta_old is not None and eta_new < eta_old:
            best_by_line[lid] = o

    line_ids = [c["line_id"] for c in cat_rows]
    headers = {
        r["line_id"]: (r["name_a"] or "", r["name_b"] or "")
        for r in lines_dim.filter(F.col("line_id").isin(line_ids)).collect()
    }

    for c in cat_rows:
        lid = c["line_id"]
        o = best_by_line.get(lid)
        is_terminus = bool(c["is_terminus_any"])

        if o is not None and o["eta_seconds"] is not None:
            has_bus = True
            eta = int(o["eta_seconds"])
            dest = (o["destination"] or "").strip()
        else:
            has_bus = False
            eta = None
            dest = (o["destination"] or "").strip() if o is not None else ""

        # docs/04 §8: destination fallback name_a / name_b / ""
        if not dest:
            name_a, name_b = headers.get(lid, ("", ""))
            dest = name_a or name_b or ""

        # docs/04 §3: null ETA on terminus → origin_stop_notice
        origin_notice = bool(is_terminus and eta is None)

        gold_rows.append(
            {
                "stop_id": stop_id,
                "line_id": lid,
                "line_label": c["line_label"],
                "destination": dest,
                "eta_seconds": eta,
                "has_upcoming_bus": has_bus,
                "origin_stop_notice": origin_notice,
                "is_stale": bool(is_stale),
                "updated_at": poll_ts,
            }
        )

gold_schema = StructType(
    [
        StructField("stop_id", IntegerType(), False),
        StructField("line_id", StringType(), False),
        StructField("line_label", StringType(), False),
        StructField("destination", StringType(), False),
        StructField("eta_seconds", IntegerType(), True),
        StructField("has_upcoming_bus", BooleanType(), False),
        StructField("origin_stop_notice", BooleanType(), False),
        StructField("is_stale", BooleanType(), False),
        StructField("updated_at", TimestampType(), False),
    ]
)

if not gold_rows:
    print("No gold rows (need successful bronze + silver_stop_lines).")
else:
    gold_df = spark.createDataFrame(gold_rows, schema=gold_schema).dropDuplicates(
        ["stop_id", "line_id"]
    )
    stops_touched = sorted({r["stop_id"] for r in gold_rows})

    if spark.catalog.tableExists("gold_stop_line_eta_latest"):
        spark.sql(
            f"""
            DELETE FROM gold_stop_line_eta_latest
            WHERE stop_id IN ({",".join(str(s) for s in stops_touched)})
            """
        )
        gold_df.write.format("delta").mode("append").saveAsTable("gold_stop_line_eta_latest")
    else:
        gold_df.write.format("delta").mode("overwrite").option(
            "overwriteSchema", "true"
        ).saveAsTable("gold_stop_line_eta_latest")

    print(f"Gold rebuilt for stops {stops_touched}: {gold_df.count()} rows")
    display(
        spark.table("gold_stop_line_eta_latest")
        .filter(F.col("stop_id").isin(stops_touched))
        .orderBy("stop_id", "line_label")
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary — second Run All should show silver_inserted = 0

# COMMAND ----------

print("=== SUMMARY (docs v1.1) ===")
print(f"stale_after_sec = {STALE_AFTER_SEC}")
print(f"quarantine = {len(quarantine)}")
print(f"silver_inserted_this_run = {inserted}")
print(f"bronze_emt_raw = {spark.table(bronze_table).count()}")
print(f"silver_arrival_observations = {spark.table('silver_arrival_observations').count()}")
print(f"gold_stop_line_eta_latest = {spark.table('gold_stop_line_eta_latest').count()}")
dup = (
    spark.table("silver_arrival_observations")
    .groupBy("_rk")
    .count()
    .filter("count > 1")
    .count()
)
print(f"duplicate _rk = {dup} (must be 0)")
