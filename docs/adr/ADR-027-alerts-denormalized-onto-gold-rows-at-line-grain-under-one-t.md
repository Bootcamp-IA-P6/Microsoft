# ADR-027: Alerts denormalized onto Gold rows at line grain

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted (amended 2026-07-23)
- **Components affected:** Gold alert_* columns, US-07, silver_alerts

## 1. Context

Alerts are line-scoped; Gold grain is stop×line×direction. Under the original 1+1+1 cap, a separate **Gold** current-alert table was forbidden, so `alert_*` were denormalized onto Gold. PO later allowed a **Silver** alerts table while keeping Gold columns ([ADR-037](ADR-037-silver-split-into-silver-arrives-and-silver-alerts.md)).

## 2. Alternatives Considered

- **A — Separate Gold alert current table:** Clean; rejected for POC Agent contract / table cap.
- **B — `alert_*` on Gold replicated per `line_id`:** Fits single Gold table; non-stop semantics must be explicit.
- **C — Omit alerts from Gold:** Breaks US-07 serving.
- **D — Remove Gold `alert_*` and join `silver_alerts` at serve time:** Rejected by PO (opción B); keep columns.

## 3. Decision

Adopt **B** (unchanged for Gold shape). **Amendment:** pipeline path is

```text
S2 → bronze_emt_raw → silver_alerts (latest-only, typed) → MERGE gold alert_* by line_id
```

- Sole Gold alert input = `silver_alerts` (do not re-parse Bronze in the Gold job for alerts).
- `alert_active` computed at Gold assemble with `now` vs `active_period` (Europe/Madrid); Silver stores periods/texts/`line_id`, not a durable `alert_active` fact.
- Failed line mapping: `map_ok=false` stays in Silver; excluded from Gold MERGE.

## 4. Consequences

- **Pros:** US-07 still answerable from Gold alone; Agent/Semantic unchanged; parse/map owned in Silver.
- **Cons:** Same alert text repeated on many Gold rows; must not claim stop-level disruption; Silver↔Gold sync discipline required.

## 5. Amended / Superseded by

- Amended by [ADR-037](ADR-037-silver-split-into-silver-arrives-and-silver-alerts.md).
- Original note “Silver alert columns abandoned for POC” applied to the **poll** Silver only; superseded for a dedicated `silver_alerts` table.
