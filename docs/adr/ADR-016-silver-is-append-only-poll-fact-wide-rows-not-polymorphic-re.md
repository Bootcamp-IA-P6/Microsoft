# ADR-016: silver_arrives is append-only poll fact wide rows not polymorphic record_type

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted (amended 2026-07-23)
- **Components affected:** Silver arrives table, US-08 history

## 1. Context

Initial internal draft used a polymorphic Silver (`record_type`, `is_current`) for stops/routes/alerts. The contract models Arrive poll history for observed frequency. Table was named `silver_emt`; renamed to `silver_arrives` under ADR-037.

## 2. Alternatives Considered

- **A — Polymorphic Silver master:** Flexible; weak for headway history.
- **B — Poll fact wide row append-only with `_rk` SHA256:** Enables observed frequency.
- **C — Separate history table:** Clean; originally broke 1-Silver rule.

## 3. Decision

Adopt **B**. Table name: **`silver_arrives`** (was `silver_emt`). Grain conceptually `(stop_id, line_id, direction_id)` per poll; `_rk` includes bus_id and polling timestamp. Rows without bus (`bus_id`/`eta` NULL) are still stored. **No alert columns** on this table — alerts live in `silver_alerts` ([ADR-037](ADR-037-silver-split-into-silver-arrives-and-silver-alerts.md)).

## 4. Consequences

- **Pros:** US-08 computable; idempotent reloads via `_rk`; clear domain boundary vs alerts.
- **Cons:** Wide denormalized catalog fields on every poll row; rename must propagate in code/docs.

## 5. Amended / Superseded by

- Supersedes early `silver_emt_record` / `record_type` design.
- Amended by [ADR-037](ADR-037-silver-split-into-silver-arrives-and-silver-alerts.md) (rename + alerts out of band).
