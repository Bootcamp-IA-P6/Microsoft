# Fabric notebook — contract v4.3 S2 servicealerts → silver_alerts → gold alert_*
#
# Prereq: nb_create_tables (+ gold rows from arrives path ideally)
# No %pip / no Environment: stdlib urllib + inlined GTFS-RT protobuf decoder
# Pipeline: schedule separately from arrives (~5 min POC; contract ~300s)
# Guide: docs/manual-lakehouse-ingestion.md

# COMMAND ----------

# MAGIC %md
# MAGIC # Alerts → bronze → silver_alerts → gold `alert_*` (contract v4.3 · Phase 1)
# MAGIC Does **not** update ETA / freq / stale columns.

# COMMAND ----------

bronze_table = "bronze_emt_raw"  # @param {type:"string"}
silver_alerts_table = "silver_alerts"  # @param {type:"string"}
gold_table = "gold_emt_stop_line"  # @param {type:"string"}
servicealerts_url = "https://openapi.emtmadrid.es/v1/bus/servicealerts/proto"  # @param {type:"string"}
verbose_display = False  # @param {type:"boolean"}

# COMMAND ----------

# MAGIC %md
# MAGIC ## Shared helpers (inlined)

# COMMAND ----------

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TZ_NOTE = "Europe/Madrid"
UTC = timezone.utc
MADRID = ZoneInfo("Europe/Madrid")
HTTP_HEADERS_BASE = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; emt-pipeline/0.1; "
        "+https://github.com/Bootcamp-IA-P6/Microsoft)"
    ),
    "Accept": "application/x-protobuf,application/octet-stream,*/*",
    "Connection": "close",
}


def utc_now_iso_z() -> str:
    now = datetime.now(UTC)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def delta_sql_retry(spark, sql: str, *, label: str, attempts: int = 6) -> None:
    """Retry Delta MERGE/DELETE on ConcurrentAppendException (arrives+alerts share gold)."""
    last: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            spark.sql(sql)
            if attempt > 1:
                print(f"{label}: succeeded on attempt {attempt}/{attempts}")
            return
        except Exception as exc:  # noqa: BLE001
            last = exc
            msg = str(exc)
            concurrent = (
                "ConcurrentAppendException" in type(exc).__name__
                or "ConcurrentAppendException" in msg
                or "DELTA_CONCURRENT_APPEND" in msg
                or "ConcurrentTransactionException" in msg
            )
            if not concurrent or attempt >= attempts:
                raise
            sleep_s = min(2**attempt, 30)
            print(
                f"{label}: concurrent Delta write "
                f"(attempt {attempt}/{attempts}); retry in {sleep_s}s"
            )
            time.sleep(sleep_s)
    raise RuntimeError(f"{label}: exhausted retries") from last


def _is_transient_http_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    if "unexpected_eof" in msg or "ssl" in msg or "connection" in msg or "timed out" in msg:
        return True
    try:
        import requests

        return isinstance(
            exc,
            (
                requests.exceptions.SSLError,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError,
            ),
        )
    except ImportError:
        return False


def http_bytes(url: str, *, timeout: int = 60, attempts: int = 5) -> tuple[bytes, int]:
    """Fetch bytes — prefer requests if present, else stdlib urllib (Pipeline-safe)."""
    last_err: Exception | None = None

    def _via_requests():
        import requests

        resp = requests.get(
            url,
            headers=HTTP_HEADERS_BASE,
            timeout=timeout,
            allow_redirects=True,
        )
        if resp.status_code in {408, 425, 429, 500, 502, 503, 504}:
            raise RuntimeError(f"HTTP {resp.status_code} on servicealerts")
        if resp.status_code >= 400:
            raise RuntimeError(
                f"HTTP {resp.status_code} on servicealerts: {resp.text[:300]}"
            )
        return resp.content, int(resp.status_code)

    def _via_urllib():
        import urllib.error
        import urllib.request

        req = urllib.request.Request(url, headers=HTTP_HEADERS_BASE, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read(), int(resp.status)
        except urllib.error.HTTPError as exc:
            if exc.code in {408, 425, 429, 500, 502, 503, 504}:
                raise RuntimeError(f"HTTP {exc.code} on servicealerts") from exc
            body = exc.read()[:300] if hasattr(exc, "read") else b""
            raise RuntimeError(
                f"HTTP {exc.code} on servicealerts: {body!r}"
            ) from exc

    use_requests = True
    try:
        import requests  # noqa: F401
    except ImportError:
        use_requests = False

    for attempt in range(1, attempts + 1):
        try:
            raw, status = _via_requests() if use_requests else _via_urllib()
            return raw, status
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if attempt < attempts and (
                _is_transient_http_error(exc)
                or "HTTP 5" in str(exc)
                or "HTTP 429" in str(exc)
            ):
                sleep_s = min(2**attempt, 20)
                print(
                    f"servicealerts fetch failed "
                    f"(attempt {attempt}/{attempts}): {exc!r}; retry in {sleep_s}s"
                )
                time.sleep(sleep_s)
                continue
            raise
    raise RuntimeError(f"servicealerts fetch failed: {last_err}")


# --- Inlined GTFS-RT FeedMessage decoder (servicealerts subset; no pip) ---
_GTFS_CAUSE = {
    1: "UNKNOWN_CAUSE",
    2: "OTHER_CAUSE",
    3: "TECHNICAL_PROBLEM",
    4: "STRIKE",
    5: "DEMONSTRATION",
    6: "ACCIDENT",
    7: "HOLIDAY",
    8: "WEATHER",
    9: "MAINTENANCE",
    10: "CONSTRUCTION",
    11: "POLICE_ACTIVITY",
    12: "MEDICAL_EMERGENCY",
}
_GTFS_EFFECT = {
    1: "NO_SERVICE",
    2: "REDUCED_SERVICE",
    3: "SIGNIFICANT_DELAYS",
    4: "DETOUR",
    5: "ADDITIONAL_SERVICE",
    6: "MODIFIED_SERVICE",
    7: "OTHER_EFFECT",
    8: "UNKNOWN_EFFECT",
    9: "STOP_MOVED",
    10: "NO_EFFECT",
    11: "ACCESSIBILITY_ISSUE",
}


def _pb_read_varint(buf: bytes, i: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        b = buf[i]
        i += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, i
        shift += 7


def _pb_skip(buf: bytes, i: int, wt: int) -> int:
    if wt == 0:
        _, i = _pb_read_varint(buf, i)
        return i
    if wt == 1:
        return i + 8
    if wt == 2:
        ln, i = _pb_read_varint(buf, i)
        return i + ln
    if wt == 5:
        return i + 4
    raise ValueError(f"unknown protobuf wire type {wt}")


def _pb_parse(buf: bytes, i: int, end: int, handlers: dict, out=None):
    if out is None:
        out = {}
    while i < end:
        key, i = _pb_read_varint(buf, i)
        fn, wt = key >> 3, key & 7
        if fn in handlers:
            i = handlers[fn](buf, i, wt, out)
        else:
            i = _pb_skip(buf, i, wt)
    return out, i


def _pb_len(buf: bytes, i: int, wt: int) -> tuple[int, int]:
    if wt != 2:
        raise ValueError("expected length-delimited")
    ln, i = _pb_read_varint(buf, i)
    return i, i + ln


def _pb_translated(buf: bytes, i: int, end: int) -> dict:
    translations: list[dict] = []

    def h_tr(buf, i, wt, out):
        i0, i1 = _pb_len(buf, i, wt)

        def h_text(buf, i, wt, o):
            a, b = _pb_len(buf, i, wt)
            o["text"] = buf[a:b].decode("utf-8", "replace")
            return b

        def h_lang(buf, i, wt, o):
            a, b = _pb_len(buf, i, wt)
            o["language"] = buf[a:b].decode("utf-8", "replace")
            return b

        translations.append(_pb_parse(buf, i0, i1, {1: h_text, 2: h_lang})[0])
        return i1

    _pb_parse(buf, i, end, {1: h_tr})
    return {"translation": translations}


def _pb_time_range(buf: bytes, i: int, end: int) -> dict:
    def h_start(buf, i, wt, out):
        v, i = _pb_read_varint(buf, i)
        out["start"] = str(v)
        return i

    def h_end(buf, i, wt, out):
        v, i = _pb_read_varint(buf, i)
        out["end"] = str(v)
        return i

    return _pb_parse(buf, i, end, {1: h_start, 2: h_end})[0]


def _pb_entity_selector(buf: bytes, i: int, end: int) -> dict:
    def h_agency(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["agency_id"] = buf[a:b].decode("utf-8", "replace")
        return b

    def h_route(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["route_id"] = buf[a:b].decode("utf-8", "replace")
        return b

    def h_rtype(buf, i, wt, out):
        v, i = _pb_read_varint(buf, i)
        out["route_type"] = v
        return i

    def h_trip(buf, i, wt, out):
        return _pb_skip(buf, i, wt)

    def h_stop(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["stop_id"] = buf[a:b].decode("utf-8", "replace")
        return b

    return _pb_parse(
        buf, i, end, {1: h_agency, 2: h_route, 3: h_rtype, 4: h_trip, 5: h_stop}
    )[0]


def _pb_alert(buf: bytes, i: int, end: int) -> dict:
    out = {"active_period": [], "informed_entity": []}

    def h_period(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["active_period"].append(_pb_time_range(buf, a, b))
        return b

    def h_ie(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["informed_entity"].append(_pb_entity_selector(buf, a, b))
        return b

    def h_cause(buf, i, wt, out):
        v, i = _pb_read_varint(buf, i)
        out["cause"] = _GTFS_CAUSE.get(v, str(v))
        return i

    def h_effect(buf, i, wt, out):
        v, i = _pb_read_varint(buf, i)
        out["effect"] = _GTFS_EFFECT.get(v, str(v))
        return i

    def h_url(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["url"] = _pb_translated(buf, a, b)
        return b

    def h_header(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["header_text"] = _pb_translated(buf, a, b)
        return b

    def h_desc(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["description_text"] = _pb_translated(buf, a, b)
        return b

    return _pb_parse(
        buf,
        i,
        end,
        {
            1: h_period,
            5: h_ie,
            6: h_cause,
            7: h_effect,
            8: h_url,
            10: h_header,
            11: h_desc,
        },
        out=out,
    )[0]


def _pb_entity(buf: bytes, i: int, end: int) -> dict:
    def h_id(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["id"] = buf[a:b].decode("utf-8", "replace")
        return b

    def h_alert(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["alert"] = _pb_alert(buf, a, b)
        return b

    return _pb_parse(buf, i, end, {1: h_id, 5: h_alert})[0]


def _pb_header(buf: bytes, i: int, end: int) -> dict:
    def h_ver(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["gtfs_realtime_version"] = buf[a:b].decode("utf-8", "replace")
        return b

    def h_inc(buf, i, wt, out):
        v, i = _pb_read_varint(buf, i)
        out["incrementality"] = v
        return i

    def h_ts(buf, i, wt, out):
        v, i = _pb_read_varint(buf, i)
        out["timestamp"] = str(v)
        return i

    return _pb_parse(buf, i, end, {1: h_ver, 2: h_inc, 3: h_ts})[0]


def decode_feed_to_dict(raw: bytes) -> dict:
    """Decode GTFS-RT FeedMessage without gtfs-realtime-bindings (Pipeline-safe)."""
    out: dict = {"header": {}, "entity": []}

    def h_header(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["header"] = _pb_header(buf, a, b)
        return b

    def h_ent(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt)
        out["entity"].append(_pb_entity(buf, a, b))
        return b

    result = _pb_parse(raw, 0, len(raw), {1: h_header, 2: h_ent}, out=out)[0]
    return result


def pick_translated(field) -> str | None:
    if not isinstance(field, dict):
        return None
    texts = field.get("translation") or []
    if not texts:
        return None
    for t in texts:
        if isinstance(t, dict) and t.get("language") == "es" and t.get("text"):
            return str(t["text"])
    first = texts[0] if isinstance(texts[0], dict) else None
    if first and first.get("text"):
        return str(first["text"])
    return None


def unix_to_naive_utc(value) -> datetime | None:
    if value is None or value == "":
        return None
    try:
        return datetime.fromtimestamp(int(value), UTC).replace(tzinfo=None)
    except (TypeError, ValueError, OSError):
        return None


def sha_alert_rk(alert_id: str, line_id: str | None, snapshot_at: datetime) -> str:
    ts = snapshot_at.isoformat(sep="T", timespec="seconds")
    parts = [str(alert_id), "" if line_id is None else str(line_id), ts]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def bronze_row_alerts(http_status: int, payload_obj: dict) -> dict:
    payload_s = json.dumps(payload_obj, ensure_ascii=False)
    return {
        "ingest_id": str(uuid.uuid4()),
        "ingested_at": utc_now_iso_z(),
        "source_system": "MDB_GTFS_RT",
        "resource_kind": "servicealerts",
        "resource_key": "proto",
        "http_status": str(http_status),
        "api_code": "",
        "api_description": None,
        "payload": payload_s,
        "content_sha256": hashlib.sha256(payload_s.encode("utf-8")).hexdigest(),
        "timezone_note": TZ_NOTE,
    }


# COMMAND ----------

from pyspark.sql.types import (
    BooleanType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

BRONZE_SCHEMA = StructType(
    [
        StructField(c, StringType(), True)
        for c in [
            "ingest_id",
            "ingested_at",
            "source_system",
            "resource_kind",
            "resource_key",
            "http_status",
            "api_code",
            "api_description",
            "payload",
            "content_sha256",
            "timezone_note",
        ]
    ]
)

SILVER_ALERTS_SCHEMA = StructType(
    [
        StructField("_rk", StringType(), False),
        StructField("alert_id", StringType(), True),
        StructField("line_id", StringType(), True),
        StructField("alert_header", StringType(), True),
        StructField("alert_cause", StringType(), True),
        StructField("alert_effect", StringType(), True),
        StructField("alert_url", StringType(), True),
        StructField("active_period_start", TimestampType(), True),
        StructField("active_period_end", TimestampType(), True),
        StructField("snapshot_at", TimestampType(), True),
        StructField("ingested_at", TimestampType(), True),
        StructField("map_ok", BooleanType(), True),
    ]
)

GOLD_ALERT_STAGE_SCHEMA = StructType(
    [
        StructField("line_id", StringType(), False),
        StructField("alert_active", BooleanType(), False),
        StructField("alert_header", StringType(), True),
        StructField("alert_cause", StringType(), True),
        StructField("alert_effect", StringType(), True),
        StructField("alert_url", StringType(), True),
    ]
)


# COMMAND ----------

# MAGIC %md
# MAGIC ## A — Fetch S2 → bronze

# COMMAND ----------


def run_alerts_ingest(spark, *, url: str, bronze_table: str) -> dict:
    raw, status = http_bytes(url)
    payload = decode_feed_to_dict(raw)
    n_ent = len(payload.get("entity") or [])
    print(f"Fetched servicealerts HTTP {status}, bytes={len(raw)}, entities={n_ent}")
    row = bronze_row_alerts(status, payload)
    spark.createDataFrame([row], schema=BRONZE_SCHEMA).write.format("delta").mode(
        "append"
    ).saveAsTable(bronze_table)
    print(f"Appended 1 → {bronze_table} (resource_kind=servicealerts)")
    return payload


payload = run_alerts_ingest(spark, url=servicealerts_url, bronze_table=bronze_table)


# COMMAND ----------

# MAGIC %md
# MAGIC ## B — Transform → silver_alerts (latest-only) → gold alert_*

# COMMAND ----------


def known_line_ids(spark) -> set[str]:
    """One small collect of distinct line_ids from gold (preferred) or silver_arrives."""
    ids: set[str] = set()
    if spark.catalog.tableExists(gold_table):
        for r in spark.table(gold_table).select("line_id").distinct().collect():
            if r["line_id"]:
                ids.add(str(r["line_id"]).strip())
        if ids:
            return ids
    if spark.catalog.tableExists("silver_arrives"):
        for r in spark.table("silver_arrives").select("line_id").distinct().collect():
            if r["line_id"]:
                ids.add(str(r["line_id"]).strip())
    return ids


def expand_silver_rows(
    payload: dict, known: set[str], ingested_at: datetime
) -> tuple[list[dict], datetime]:
    header = payload.get("header") or {}
    snap = unix_to_naive_utc(header.get("timestamp")) or ingested_at
    rows: list[dict] = []
    unmapped = 0

    for ent in payload.get("entity") or []:
        if not isinstance(ent, dict):
            continue
        alert = ent.get("alert") or {}
        if not alert:
            continue
        alert_id = str(ent.get("id") or "").strip()
        if not alert_id:
            continue

        header_txt = pick_translated(alert.get("header_text"))
        url_txt = pick_translated(alert.get("url"))
        cause = alert.get("cause")
        effect = alert.get("effect")
        cause_s = str(cause) if cause is not None else None
        effect_s = str(effect) if effect is not None else None

        periods = alert.get("active_period") or []
        starts = [
            unix_to_naive_utc(p.get("start")) for p in periods if isinstance(p, dict)
        ]
        ends = [unix_to_naive_utc(p.get("end")) for p in periods if isinstance(p, dict)]
        starts = [t for t in starts if t is not None]
        ends = [t for t in ends if t is not None]
        period_start = min(starts) if starts else None
        period_end = max(ends) if ends else None

        route_ids: list[str | None] = []
        for ie in alert.get("informed_entity") or []:
            if not isinstance(ie, dict):
                continue
            # Never join on RT stop_id (EMT leaves it empty)
            rid = ie.get("route_id")
            rid_s = str(rid).strip() if rid not in (None, "") else None
            if rid_s:
                route_ids.append(rid_s)
        if not route_ids:
            route_ids = [None]

        for rid in route_ids:
            map_ok = bool(rid and rid in known)
            if rid and not map_ok:
                unmapped += 1
            # Contract: line_id NULL when map_ok=false; _rk still hashes route_id for uniqueness
            rows.append(
                {
                    "_rk": sha_alert_rk(alert_id, rid, snap),
                    "alert_id": alert_id,
                    "line_id": rid if map_ok else None,
                    "alert_header": header_txt,
                    "alert_cause": cause_s,
                    "alert_effect": effect_s,
                    "alert_url": url_txt,
                    "active_period_start": period_start,
                    "active_period_end": period_end,
                    "snapshot_at": snap,
                    "ingested_at": ingested_at,
                    "map_ok": map_ok,
                }
            )

    print(f"silver_alerts candidate rows={len(rows)} unmapped_route_refs={unmapped}")
    return rows, snap


def project_gold_alerts(spark, *, now_naive: datetime) -> list[dict]:
    """One stage row per gold line_id; alert_active from silver periods vs now."""
    if not spark.catalog.tableExists(gold_table):
        print(f"{gold_table} missing — skip Gold MERGE")
        return []

    by_line: dict[str, dict] = {}
    for r in (
        spark.table(silver_alerts_table)
        .filter("map_ok = true AND line_id IS NOT NULL")
        .collect()
    ):
        start = r["active_period_start"]
        end = r["active_period_end"]
        # No period bounds ⇒ always active (GTFS-RT)
        if start is not None and now_naive < start:
            continue
        if end is not None and now_naive >= end:
            continue
        lid = str(r["line_id"])
        aid = str(r["alert_id"] or "")
        prev = by_line.get(lid)
        if prev is None or aid < prev["alert_id"]:
            by_line[lid] = {
                "alert_id": aid,
                "alert_header": r["alert_header"],
                "alert_cause": r["alert_cause"],
                "alert_effect": r["alert_effect"],
                "alert_url": r["alert_url"],
            }

    gold_lines = [
        str(r["line_id"])
        for r in spark.table(gold_table).select("line_id").distinct().collect()
        if r["line_id"]
    ]
    stage = []
    for lid in gold_lines:
        hit = by_line.get(lid)
        if hit:
            stage.append(
                {
                    "line_id": lid,
                    "alert_active": True,
                    "alert_header": hit["alert_header"],
                    "alert_cause": hit["alert_cause"],
                    "alert_effect": hit["alert_effect"],
                    "alert_url": hit["alert_url"],
                }
            )
        else:
            stage.append(
                {
                    "line_id": lid,
                    "alert_active": False,
                    "alert_header": None,
                    "alert_cause": None,
                    "alert_effect": None,
                    "alert_url": None,
                }
            )
    active_n = sum(1 for s in stage if s["alert_active"])
    print(f"gold alert stage lines={len(stage)} active={active_n}")
    return stage


def run_alerts_transform(spark, payload: dict) -> None:
    if not spark.catalog.tableExists(silver_alerts_table):
        raise RuntimeError(f"{silver_alerts_table} missing — run nb_create_tables")

    known = known_line_ids(spark)
    print(f"Known line_id count={len(known)}")
    ingested_at = datetime.now(UTC).replace(tzinfo=None, microsecond=0)
    silver_rows, snap = expand_silver_rows(payload, known, ingested_at)

    # latest-only snapshot replace
    spark.sql(f"DELETE FROM {silver_alerts_table}")
    if silver_rows:
        spark.createDataFrame(silver_rows, schema=SILVER_ALERTS_SCHEMA).write.format(
            "delta"
        ).mode("append").saveAsTable(silver_alerts_table)
    print(f"{silver_alerts_table} rows written={len(silver_rows)} snapshot_at={snap}")

    # now as Europe/Madrid instant → naive UTC for comparing stored timestamps
    now_naive = datetime.now(MADRID).astimezone(UTC).replace(tzinfo=None, microsecond=0)
    stage = project_gold_alerts(spark, now_naive=now_naive)
    if not stage:
        print("No gold lines to update")
        return

    spark.createDataFrame(stage, schema=GOLD_ALERT_STAGE_SCHEMA).createOrReplaceTempView(
        "gold_alerts_stage"
    )
    delta_sql_retry(
        spark,
        f"""
        MERGE INTO {gold_table} AS t
        USING gold_alerts_stage AS s
        ON t.line_id = s.line_id
        WHEN MATCHED THEN UPDATE SET
          t.alert_active = s.alert_active,
          t.alert_header = s.alert_header,
          t.alert_cause = s.alert_cause,
          t.alert_effect = s.alert_effect,
          t.alert_url = s.alert_url
        """,
        label="gold alerts MERGE",
    )
    print(f"MERGE {gold_table} alert_* by line_id done")
    if verbose_display:
        display(
            spark.table(gold_table)
            .filter("alert_active = true")
            .select(
                "stop_id",
                "line_id",
                "direction_id",
                "alert_active",
                "alert_header",
                "alert_cause",
                "alert_effect",
            )
            .orderBy("line_id", "stop_id")
            .limit(40)
        )
        print("=== SUMMARY (contract v4.3 alerts) ===")
        print(f"bronze={spark.table(bronze_table).count()}")
        print(f"silver_alerts={spark.table(silver_alerts_table).count()}")
        print(
            f"gold alert_active=true: "
            f"{spark.table(gold_table).filter('alert_active = true').count()}"
        )
    else:
        print("=== SUMMARY (contract v4.3 alerts · phase1) ===")
        print(f"stage_lines={len(stage)} verbose_display=False")


run_alerts_transform(spark, payload)
