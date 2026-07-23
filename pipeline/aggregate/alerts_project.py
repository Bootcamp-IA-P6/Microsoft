"""Project silver_alerts onto gold alert_* stage rows."""
from __future__ import annotations

from datetime import datetime

from pipeline.config.constants import GOLD_TABLE, SILVER_ALERTS, SILVER_ARRIVES


def known_line_ids(
    spark,
    *,
    gold_table: str = GOLD_TABLE,
    silver_arrives: str = SILVER_ARRIVES,
) -> set[str]:
    """Distinct line_ids from gold (preferred) or silver_arrives."""
    ids: set[str] = set()
    if spark.catalog.tableExists(gold_table):
        for r in spark.table(gold_table).select("line_id").distinct().collect():
            if r["line_id"]:
                ids.add(str(r["line_id"]).strip())
        if ids:
            return ids
    if spark.catalog.tableExists(silver_arrives):
        for r in spark.table(silver_arrives).select("line_id").distinct().collect():
            if r["line_id"]:
                ids.add(str(r["line_id"]).strip())
    return ids


def project_gold_alerts(
    spark,
    *,
    now_naive: datetime,
    gold_table: str = GOLD_TABLE,
    silver_alerts_table: str = SILVER_ALERTS,
) -> list[dict]:
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
