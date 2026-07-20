# ADR-027: Alerts denormalized onto Gold rows at line grain under one-table rule

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** Gold alert_* columns, US-07

## 1. Context

Alerts are line-scoped; Gold grain is stop×line×direction. A separate current-alert table would violate 1+1+1.

## 2. Alternatives Considered

- **A — Separate alert current table:** Clean; forbidden for POC.
- **B — `alert_*` on Gold replicated per `line_id` with explicit non-stop semantics warning:** Fits constraint.
- **C — Omit alerts from Gold:** Breaks US-07 serving.

## 3. Decision

Adopt **B**. Silver alert columns abandoned for POC (would dirty poll fact).

## 4. Consequences

- **Pros:** US-07 answerable from Gold alone.
- **Cons:** Same alert text repeated on many rows; must not claim stop-level disruption.

## 5. Amended / Superseded by

- None at time of writing.
