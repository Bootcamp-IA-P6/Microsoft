# ADR-016: Silver is append-only poll fact wide rows not polymorphic record_type

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** Silver table design, US-08 history

## 1. Context

Initial internal draft used a polymorphic Silver (`record_type`, `is_current`) for stops/routes/alerts. `data-source-contract-v4.md` models Silver as Arrive poll history for observed frequency.

## 2. Alternatives Considered

- **A — Polymorphic Silver master:** Flexible; weak for headway history.
- **B — Poll fact wide row append-only with `_rk` SHA256 (contract §5):** Enables observed frequency.
- **C — Separate history table:** Clean; breaks 1-table rule.

## 3. Decision

Adopt **B**. Grain conceptually `(stop_id, line_id, direction_id)` per poll; `_rk` includes bus_id and polling timestamp. Rows without bus (`bus_id`/`eta` NULL) are still stored. No Silver alert columns for POC.

## 4. Consequences

- **Pros:** US-08 becomes computable; idempotent reloads via `_rk`.
- **Cons:** Wide denormalized catalog fields on every poll row.

## 5. Amended / Superseded by

- Supersedes early `silver_emt_record` / `record_type` design.
