"""Arrives bronze → silver_arrives → gold ETA/freq MERGE (not alert_*)."""
from __future__ import annotations

import json
from datetime import datetime

from pyspark.sql import Window
from pyspark.sql import functions as F

from pipeline.aggregate.frequency import compute_freq_by_line_spark
from pipeline.common.datetime_utils import UTC, parse_api_datetime_to_utc_naive
from pipeline.common.delta_retry import delta_sql_retry
from pipeline.common.keys import sha_rk
from pipeline.common.parsing import to_int_or_none
from pipeline.common.timing import phase1_timer
from pipeline.config.constants import GOLD_TABLE, SILVER_ARRIVES
from pipeline.transform.enrich import latest_catalog_rows, map_destination_to_direction
from pipeline.validation.schema import GOLD_ARRIVES_SCHEMA, SILVER_ARRIVES_SCHEMA


def run_transform(
    spark,
    *,
    stale_after_sec: int,
    bronze_table: str,
    incremental: bool,
    freq_min_samples: int,
    verbose_display: bool = False,
) -> None:
    lap = phase1_timer()
    stale_after_sec = int(stale_after_sec)
    freq_min = int(freq_min_samples)

    if not spark.catalog.tableExists(SILVER_ARRIVES):
        raise RuntimeError("silver_arrives missing — run nb_bootstrap_gtfs_silver")

    cat_rows = latest_catalog_rows(spark)
    cat_by_grain = {(r["stop_id"], r["line_id"], int(r["direction_id"])): r for r in cat_rows}
    grains_by_stop: dict[str, list] = {}
    label_at_stop: dict[tuple[str, str], str] = {}
    line_names: dict[str, tuple[str | None, str | None]] = {}
    for r in cat_rows:
        sid, lid, did = r["stop_id"], r["line_id"], int(r["direction_id"])
        grains_by_stop.setdefault(sid, []).append(((sid, lid, did), r))
        label_at_stop[(sid, r["line_label"])] = lid
        line_names[lid] = (r["name_a"], r["name_b"])
    day_type_today = next((r["day_type"] for r in cat_rows if r["day_type"]), "LA")
    print(f"Catalogue grains={len(cat_by_grain)} day_type={day_type_today}")
    lap("catalogue loaded")

    bronze = (
        spark.table(bronze_table)
        .withColumn("ingested_at_ts", F.to_timestamp(F.col("ingested_at")))
        .filter("resource_kind = 'arrives' AND api_code = '00'")
    )
    if incremental:
        cut_row = (
            spark.table(SILVER_ARRIVES)
            .agg(
                F.max(
                    F.when(
                        F.col("bus_id").isNotNull() | F.col("eta_seconds").isNotNull(),
                        F.col("ingested_at"),
                    )
                ).alias("max_poll"),
                F.max("ingested_at").alias("max_any"),
            )
            .collect()[0]
        )
        cutoff = cut_row["max_poll"] or cut_row["max_any"]
        if cutoff is not None:
            bronze = bronze.filter(F.col("ingested_at_ts") > F.lit(cutoff))
            print(f"Incremental bronze ingested_at > {cutoff}")

    bronze_list = bronze.orderBy("ingested_at_ts").collect()
    print(f"Bronze arrives rows to process: {len(bronze_list)}")
    lap("bronze collected")

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
                    for (_g, row) in grains_by_stop.get(sid, []):
                        if _g[1] == line_id:
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
            for (g, row) in grains_by_stop.get(stop_key, []):
                s, l, d = g
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
    lap("candidates built")

    inserted = 0
    if candidates:
        cand_df = spark.createDataFrame(candidates, schema=SILVER_ARRIVES_SCHEMA).dropDuplicates(["_rk"])
        existing = spark.table(SILVER_ARRIVES).select("_rk")
        new_df = cand_df.join(existing, on="_rk", how="left_anti")
        # Single materialization: count then write from cache (avoid take+write double join)
        new_df = new_df.cache()
        try:
            inserted = int(new_df.count())
            if inserted:
                new_df.write.format("delta").mode("append").saveAsTable(SILVER_ARRIVES)
        finally:
            new_df.unpersist()
    print(f"Inserted silver poll rows: {inserted}")
    lap("silver append")

    freq_by_line = compute_freq_by_line_spark(spark, freq_min=freq_min)
    lap("freq agg")

    now_utc = datetime.now(UTC).replace(tzinfo=None, microsecond=0)
    latest_polls = (
        spark.table(SILVER_ARRIVES)
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
    # Phase 1: only rows belonging to each grain's latest poll (not full history collect)
    current = (
        spark.table(SILVER_ARRIVES)
        .alias("s")
        .join(
            latest_polls.select(
                "stop_id",
                "line_id",
                "direction_id",
                F.col("datetime_polling").alias("_latest"),
            ).alias("l"),
            on=["stop_id", "line_id", "direction_id"],
        )
        .where(F.col("s.datetime_polling") == F.col("_latest"))
        .select("s.*")
    )
    current_rows = current.collect()
    lap(f"latest silver collected n={len(current_rows)}")

    poll_ts_per_grain: dict[tuple, datetime] = {}
    buses_at: dict[tuple, list] = {}
    for r in current_rows:
        g = (r["stop_id"], r["line_id"], int(r["direction_id"]))
        poll_ts_per_grain[g] = r["datetime_polling"]
        if r["bus_id"] is None and r["eta_seconds"] is None:
            buses_at.setdefault(g, [])
            continue
        buses_at.setdefault(g, []).append(r)

    gold_rows = []
    for (sid, lid, did), cat in cat_by_grain.items():
        g = (sid, lid, did)
        buses = sorted(
            [b for b in buses_at.get(g, []) if b["eta_seconds"] is not None],
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
            }
        )

    if not gold_rows:
        print("No gold rows — catalogue empty?")
    else:
        gold_df = spark.createDataFrame(gold_rows, schema=GOLD_ARRIVES_SCHEMA)
        gold_df.createOrReplaceTempView("gold_arrives_stage")
        delta_sql_retry(
            spark,
            f"""
            MERGE INTO {GOLD_TABLE} AS t
            USING gold_arrives_stage AS s
            ON t.stop_id = s.stop_id
               AND t.line_id = s.line_id
               AND t.direction_id = s.direction_id
            WHEN MATCHED THEN UPDATE SET
              t.line_label = s.line_label,
              t.stop_name = s.stop_name,
              t.direction_text = s.direction_text,
              t.name_a = s.name_a,
              t.name_b = s.name_b,
              t.destination = s.destination,
              t.eta_seconds_1 = s.eta_seconds_1,
              t.bus_id_1 = s.bus_id_1,
              t.eta_seconds_2 = s.eta_seconds_2,
              t.bus_id_2 = s.bus_id_2,
              t.has_upcoming_bus = s.has_upcoming_bus,
              t.is_stale = s.is_stale,
              t.origin_stop_notice = s.origin_stop_notice,
              t.is_terminus = s.is_terminus,
              t.catalog_loaded_at = s.catalog_loaded_at,
              t.day_type = s.day_type,
              t.updated_at = s.updated_at,
              t.freq_observed_weekday_min = s.freq_observed_weekday_min,
              t.freq_observed_weekend_min = s.freq_observed_weekend_min,
              t.freq_sample_size_weekday = s.freq_sample_size_weekday,
              t.freq_sample_size_weekend = s.freq_sample_size_weekend
            WHEN NOT MATCHED THEN INSERT (
              stop_id, line_id, direction_id, line_label, stop_name,
              direction_text, name_a, name_b, destination,
              eta_seconds_1, bus_id_1, eta_seconds_2, bus_id_2,
              has_upcoming_bus, is_stale, origin_stop_notice, is_terminus,
              catalog_loaded_at, day_type, updated_at,
              freq_observed_weekday_min, freq_observed_weekend_min,
              freq_sample_size_weekday, freq_sample_size_weekend,
              alert_active, alert_header, alert_cause, alert_effect, alert_url
            ) VALUES (
              s.stop_id, s.line_id, s.direction_id, s.line_label, s.stop_name,
              s.direction_text, s.name_a, s.name_b, s.destination,
              s.eta_seconds_1, s.bus_id_1, s.eta_seconds_2, s.bus_id_2,
              s.has_upcoming_bus, s.is_stale, s.origin_stop_notice, s.is_terminus,
              s.catalog_loaded_at, s.day_type, s.updated_at,
              s.freq_observed_weekday_min, s.freq_observed_weekend_min,
              s.freq_sample_size_weekday, s.freq_sample_size_weekend,
              false, NULL, NULL, NULL, NULL
            )
            """,
            label="gold arrives MERGE",
        )
        print(f"MERGE {GOLD_TABLE} (arrives cols only) staged={len(gold_rows)}")
        if verbose_display:
            display(
                spark.table(GOLD_TABLE)
                .orderBy("stop_id", "line_id", "direction_id")
                .limit(40)
            )
    lap("gold merge")

    print("=== SUMMARY (contract v4.3 arrives · phase1) ===")
    print(f"stale_after_sec={stale_after_sec} silver_inserted={inserted}")
    if verbose_display:
        print(f"bronze={spark.table(bronze_table).count()}")
        print(f"silver_arrives={spark.table(SILVER_ARRIVES).count()}")
        print(f"gold={spark.table(GOLD_TABLE).count()}")
        dup = (
            spark.table(SILVER_ARRIVES)
            .groupBy("_rk")
            .count()
            .filter("count > 1")
            .count()
        )
        print(f"duplicate _rk={dup} (must be 0)")
    else:
        print("verbose_display=False — skipped table count jobs")
    lap("done")
