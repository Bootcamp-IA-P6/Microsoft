import json
import statistics
from datetime import datetime

from pyspark.sql import Window
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
    MADRID,
    UTC,
    norm_name,
    parse_api_datetime_to_utc_naive,
    sha_rk,
    to_int_or_none,
)
from .fabric import latest_catalog_rows


SILVER_SCHEMA = StructType(
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

GOLD_SCHEMA = StructType(
    [
        StructField("stop_id", StringType(), False),
        StructField("line_id", StringType(), False),
        StructField("direction_id", IntegerType(), False),
        StructField("line_label", StringType(), False),
        StructField("stop_name", StringType(), False),
        StructField("direction_text", StringType(), True),
        StructField("name_a", StringType(), True),
        StructField("name_b", StringType(), True),
        StructField("destination", StringType(), True),
        StructField("eta_seconds_1", IntegerType(), True),
        StructField("bus_id_1", StringType(), True),
        StructField("eta_seconds_2", IntegerType(), True),
        StructField("bus_id_2", StringType(), True),
        StructField("has_upcoming_bus", BooleanType(), False),
        StructField("is_stale", BooleanType(), False),
        StructField("origin_stop_notice", BooleanType(), False),
        StructField("is_terminus", BooleanType(), False),
        StructField("catalog_loaded_at", DateType(), False),
        StructField("day_type", StringType(), False),
        StructField("updated_at", TimestampType(), False),
        StructField("freq_observed_weekday_min", DoubleType(), True),
        StructField("freq_observed_weekend_min", DoubleType(), True),
        StructField("freq_sample_size_weekday", IntegerType(), True),
        StructField("freq_sample_size_weekend", IntegerType(), True),
        StructField("alert_active", BooleanType(), False),
        StructField("alert_header", StringType(), True),
        StructField("alert_cause", StringType(), True),
        StructField("alert_effect", StringType(), True),
        StructField("alert_url", StringType(), True),
    ]
)


def map_destination_to_direction(destination: str | None, name_a, name_b) -> int | None:
    d = norm_name(destination)
    if not d:
        return None
    nb, na = norm_name(name_b), norm_name(name_a)
    if nb and (d == nb or nb in d or d in nb):
        return 0
    if na and (d == na or na in d or d in na):
        return 1
    return None


def median_gaps_minutes(timestamps: list[datetime]) -> tuple[float | None, int]:
    uniq = sorted(set(timestamps))
    n = len(uniq)
    if n < 2:
        return None, n
    gaps = [(uniq[i] - uniq[i - 1]).total_seconds() / 60.0 for i in range(1, n)]
    gaps = [g for g in gaps if g > 0]
    if not gaps:
        return None, n
    return float(statistics.median(gaps)), n


def run_transform(spark, *, stale_after_sec: int, bronze_table: str, incremental: bool, freq_min_samples: int) -> None:
    stale_after_sec = int(stale_after_sec)
    freq_min = int(freq_min_samples)

    if not spark.catalog.tableExists("silver_emt"):
        raise RuntimeError("silver_emt missing — run nb_bootstrap_silver_emt")

    cat_rows = latest_catalog_rows(spark)
    cat_by_grain = {(r["stop_id"], r["line_id"], int(r["direction_id"])): r for r in cat_rows}
    label_at_stop: dict[tuple[str, str], str] = {}
    line_names: dict[str, tuple[str | None, str | None]] = {}
    for r in cat_rows:
        label_at_stop[(r["stop_id"], r["line_label"])] = r["line_id"]
        line_names[r["line_id"]] = (r["name_a"], r["name_b"])
    day_type_today = next((r["day_type"] for r in cat_rows if r["day_type"]), "LA")
    print(f"Catalogue grains={len(cat_by_grain)} day_type={day_type_today}")

    bronze = (
        spark.table(bronze_table)
        .withColumn("ingested_at_ts", F.to_timestamp(F.col("ingested_at")))
        .filter("resource_kind = 'arrives' AND api_code = '00'")
    )
    if incremental:
        max_poll = (
            spark.table("silver_emt")
            .filter("bus_id IS NOT NULL OR eta_seconds IS NOT NULL")
            .agg(F.max("ingested_at"))
            .collect()[0][0]
        )
        max_any = spark.table("silver_emt").agg(F.max("ingested_at")).collect()[0][0]
        cutoff = max_poll or max_any
        if cutoff is not None:
            bronze = bronze.filter(F.col("ingested_at_ts") > F.lit(cutoff))
            print(f"Incremental bronze ingested_at > {cutoff}")

    bronze_list = bronze.orderBy("ingested_at_ts").collect()
    print(f"Bronze arrives rows to process: {len(bronze_list)}")

    candidates: list[dict] = []
    quarantine: list[str] = []

    for br in bronze_list:
        try:
            payload = json.loads(br["payload"])
        except (TypeError, json.JSONDecodeError) as exc:
            quarantine.append(f"bad JSON key={br['resource_key']}: {exc}")
            continue

        dt_poll = parse_api_datetime_to_utc_naive(payload.get("datetime"))
        ingested_at_ts = br["ingested_at_ts"]
        if dt_poll is None:
            dt_poll = (
                ingested_at_ts.replace(microsecond=0)
                if ingested_at_ts
                else datetime.now(UTC).replace(tzinfo=None, microsecond=0)
            )
        stop_key = str(br["resource_key"])
        ingested_at = ingested_at_ts

        label_to_line: dict[str, str] = {}
        for block in payload.get("data", []) or []:
            for si in block.get("StopInfo", []) or []:
                for ln in si.get("lines", []) or []:
                    label = str(ln.get("label") or "").strip()
                    line_id = str(ln.get("line") or "").strip()
                    if label and line_id:
                        label_to_line[label] = line_id

        arrives_found = False
        for block in payload.get("data", []) or []:
            for arr in block.get("Arrive", []) or []:
                arrives_found = True
                line_label = str(arr.get("line") or "").strip()
                if not line_label:
                    quarantine.append(f"missing label stop={stop_key}")
                    continue
                sid = str(to_int_or_none(arr.get("stop")) or stop_key)
                bus_raw = arr.get("bus")
                bus_id = None if bus_raw is None or bus_raw == "" else str(bus_raw).strip()
                destination = str(arr.get("destination") or "").strip() or None
                eta = to_int_or_none(arr.get("estimateArrive"))
                line_id = label_to_line.get(line_label) or label_at_stop.get((sid, line_label))
                map_ok = line_id is not None
                if not map_ok:
                    line_id = line_label
                    quarantine.append(f"map_ok=false stop={sid} label={line_label}")
                name_a = name_b = None
                if map_ok:
                    name_a, name_b = line_names.get(line_id, (None, None))
                direction_id = map_destination_to_direction(destination, name_a, name_b)
                denorm = None
                if map_ok and direction_id is not None:
                    denorm = cat_by_grain.get((sid, line_id, direction_id))
                if denorm is None and map_ok:
                    for (s, l, _d), row in cat_by_grain.items():
                        if s == sid and l == line_id:
                            denorm = row
                            break
                if direction_id is None:
                    quarantine.append(
                        f"no direction match stop={sid} label={line_label} dest={destination}"
                    )
                    map_ok = False
                candidates.append(
                    {
                        "_rk": sha_rk(sid, line_id, direction_id, bus_id, dt_poll),
                        "stop_id": sid,
                        "line_id": str(line_id),
                        "line_label": line_label,
                        "direction_id": direction_id,
                        "bus_id": bus_id,
                        "destination": destination,
                        "eta_seconds": eta,
                        "datetime_polling": dt_poll,
                        "ingested_at": ingested_at,
                        "stop_name": denorm["stop_name"] if denorm else None,
                        "stop_lat": denorm["stop_lat"] if denorm else None,
                        "stop_lon": denorm["stop_lon"] if denorm else None,
                        "direction_text": denorm["direction_text"] if denorm else None,
                        "name_a": name_a if name_a is not None else (denorm["name_a"] if denorm else None),
                        "name_b": name_b if name_b is not None else (denorm["name_b"] if denorm else None),
                        "is_terminus": denorm["is_terminus"] if denorm else False,
                        "catalog_loaded_at": denorm["catalog_loaded_at"] if denorm else None,
                        "day_type": (denorm["day_type"] if denorm else None) or day_type_today,
                        "map_ok": bool(map_ok and direction_id is not None),
                    }
                )

        if not arrives_found:
            for (s, l, d), row in cat_by_grain.items():
                if s != stop_key:
                    continue
                candidates.append(
                    {
                        "_rk": sha_rk(s, l, d, None, dt_poll),
                        "stop_id": s,
                        "line_id": l,
                        "line_label": row["line_label"],
                        "direction_id": d,
                        "bus_id": None,
                        "destination": None,
                        "eta_seconds": None,
                        "datetime_polling": dt_poll,
                        "ingested_at": ingested_at,
                        "stop_name": row["stop_name"],
                        "stop_lat": row["stop_lat"],
                        "stop_lon": row["stop_lon"],
                        "direction_text": row["direction_text"],
                        "name_a": row["name_a"],
                        "name_b": row["name_b"],
                        "is_terminus": row["is_terminus"],
                        "catalog_loaded_at": row["catalog_loaded_at"],
                        "day_type": row["day_type"] or day_type_today,
                        "map_ok": True,
                    }
                )

    print(f"Candidates={len(candidates)} quarantine={len(quarantine)}")
    for q in quarantine[:30]:
        print(f"  Q: {q}")

    inserted = 0
    if candidates:
        cand_df = spark.createDataFrame(candidates, schema=SILVER_SCHEMA).dropDuplicates(["_rk"])
        existing = spark.table("silver_emt").select("_rk")
        new_df = cand_df.join(existing, on="_rk", how="left_anti")
        inserted = new_df.count()
        if inserted:
            new_df.write.format("delta").mode("append").saveAsTable("silver_emt")
    print(f"Inserted silver poll rows: {inserted}")
    print(f"silver_emt total: {spark.table('silver_emt').count()}")

    polls = (
        spark.table("silver_emt")
        .filter("bus_id IS NOT NULL AND map_ok = true")
        .select("line_id", "bus_id", "datetime_polling", "day_type")
        .collect()
    )
    seen = set()
    by_line_window: dict[tuple[str, str], list[datetime]] = {}
    for p in polls:
        key = (p["line_id"], p["bus_id"], p["datetime_polling"])
        if key in seen:
            continue
        seen.add(key)
        if p["day_type"] not in ("LA", "SA", "FE"):
            continue
        window = "weekday" if p["day_type"] == "LA" else "weekend"
        by_line_window.setdefault((p["line_id"], window), []).append(p["datetime_polling"])

    freq_by_line: dict[str, dict] = {}
    for (lid, window), ts_list in by_line_window.items():
        med, n = median_gaps_minutes(ts_list)
        slot = freq_by_line.setdefault(
            lid,
            {
                "freq_observed_weekday_min": None,
                "freq_observed_weekend_min": None,
                "freq_sample_size_weekday": 0,
                "freq_sample_size_weekend": 0,
            },
        )
        if window == "weekday":
            slot["freq_sample_size_weekday"] = n
            slot["freq_observed_weekday_min"] = med if n >= freq_min else None
        else:
            slot["freq_sample_size_weekend"] = n
            slot["freq_observed_weekend_min"] = med if n >= freq_min else None

    alert_by_line: dict[str, dict] = {}
    sa = (
        spark.table(bronze_table)
        .filter("resource_kind = 'servicealerts'")
        .withColumn("_ts", F.to_timestamp(F.col("ingested_at")))
        .orderBy(F.col("_ts").desc())
        .limit(1)
        .collect()
    )
    if sa:
        print("servicealerts bronze present — alert projection not fully wired; default false")

    now_utc = datetime.now(UTC).replace(tzinfo=None, microsecond=0)
    latest_polls = (
        spark.table("silver_emt")
        .filter("map_ok = true AND direction_id IS NOT NULL")
        .withColumn(
            "_rn",
            F.row_number().over(
                Window.partitionBy("stop_id", "line_id", "direction_id").orderBy(
                    F.col("datetime_polling").desc()
                )
            ),
        )
        .filter("_rn = 1")
        .drop("_rn")
    )
    poll_ts_per_grain = {
        (r["stop_id"], r["line_id"], int(r["direction_id"])): r["datetime_polling"]
        for r in latest_polls.collect()
    }
    silver_all = (
        spark.table("silver_emt")
        .filter("map_ok = true AND direction_id IS NOT NULL")
        .collect()
    )
    buses_at: dict[tuple, list] = {}
    for r in silver_all:
        g = (r["stop_id"], r["line_id"], int(r["direction_id"]))
        ts = poll_ts_per_grain.get(g)
        if ts is None or r["datetime_polling"] != ts:
            continue
        if r["bus_id"] is None and r["eta_seconds"] is None:
            buses_at.setdefault(g, [])
            continue
        buses_at.setdefault(g, []).append(r)

    gold_rows = []
    for (sid, lid, did), cat in cat_by_grain.items():
        g = (sid, lid, did)
        buses = sorted(
            [b for b in buses_at.get(g, []) if b.get("eta_seconds") is not None],
            key=lambda b: b["eta_seconds"],
        )
        updated_at = poll_ts_per_grain.get(g) or now_utc
        eta1 = buses[0]["eta_seconds"] if len(buses) > 0 else None
        bus1 = buses[0]["bus_id"] if len(buses) > 0 else None
        dest = buses[0]["destination"] if len(buses) > 0 else None
        eta2 = buses[1]["eta_seconds"] if len(buses) > 1 else None
        bus2 = buses[1]["bus_id"] if len(buses) > 1 else None
        is_terminus = bool(cat["is_terminus"])
        has_bus = eta1 is not None
        is_stale = (now_utc - updated_at).total_seconds() > stale_after_sec
        origin_notice = bool(is_terminus and eta1 is None)
        freq = freq_by_line.get(
            lid,
            {
                "freq_observed_weekday_min": None,
                "freq_observed_weekend_min": None,
                "freq_sample_size_weekday": 0,
                "freq_sample_size_weekend": 0,
            },
        )
        alert = alert_by_line.get(
            lid,
            {
                "alert_active": False,
                "alert_header": None,
                "alert_cause": None,
                "alert_effect": None,
                "alert_url": None,
            },
        )
        gold_rows.append(
            {
                "stop_id": sid,
                "line_id": lid,
                "direction_id": did,
                "line_label": cat["line_label"],
                "stop_name": cat["stop_name"] or sid,
                "direction_text": cat["direction_text"],
                "name_a": cat["name_a"],
                "name_b": cat["name_b"],
                "destination": dest,
                "eta_seconds_1": eta1,
                "bus_id_1": bus1,
                "eta_seconds_2": eta2,
                "bus_id_2": bus2,
                "has_upcoming_bus": has_bus,
                "is_stale": bool(is_stale),
                "origin_stop_notice": origin_notice,
                "is_terminus": is_terminus,
                "catalog_loaded_at": cat["catalog_loaded_at"],
                "day_type": cat["day_type"] or day_type_today,
                "updated_at": updated_at,
                "freq_observed_weekday_min": freq["freq_observed_weekday_min"],
                "freq_observed_weekend_min": freq["freq_observed_weekend_min"],
                "freq_sample_size_weekday": int(freq["freq_sample_size_weekday"] or 0),
                "freq_sample_size_weekend": int(freq["freq_sample_size_weekend"] or 0),
                "alert_active": bool(alert["alert_active"]),
                "alert_header": alert["alert_header"],
                "alert_cause": alert["alert_cause"],
                "alert_effect": alert["alert_effect"],
                "alert_url": alert["alert_url"],
            }
        )

    if not gold_rows:
        print("No gold rows — catalogue empty?")
    else:
        gold_df = spark.createDataFrame(gold_rows, schema=GOLD_SCHEMA)
        gold_df.createOrReplaceTempView("gold_stage")
        spark.sql(
            """
            MERGE INTO gold_emt_stop_line AS t
            USING gold_stage AS s
            ON t.stop_id = s.stop_id
               AND t.line_id = s.line_id
               AND t.direction_id = s.direction_id
            WHEN MATCHED THEN UPDATE SET *
            WHEN NOT MATCHED THEN INSERT *
            """
        )
        print(f"MERGE gold_emt_stop_line rows staged={len(gold_rows)}")
        display(
            spark.table("gold_emt_stop_line")
            .orderBy("stop_id", "line_id", "direction_id")
            .limit(40)
        )

    print("=== SUMMARY (contract v4.2) ===")
    print(f"stale_after_sec={stale_after_sec} silver_inserted={inserted}")
    print(f"bronze={spark.table(bronze_table).count()}")
    print(f"silver_emt={spark.table('silver_emt').count()}")
    print(f"gold_emt_stop_line={spark.table('gold_emt_stop_line').count()}")
    dup = spark.table("silver_emt").groupBy("_rk").count().filter("count > 1").count()
    print(f"duplicate _rk={dup} (must be 0)")

