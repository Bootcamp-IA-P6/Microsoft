# ADR-025: Observed headway formula is median of successive gaps in minutes

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** US-08 metric definition

## 1. Context

Without a formula, implementers would compute incompatible averages/medians and dedupe rules.

## 2. Alternatives Considered

- **A — Mean gap:** Sensitive to outliers.
- **B — Median of successive valid observation gaps (minutes); same poll bucket + same `bus_id` counts once:** Robust POC default.
- **C — Leave unspecified:** Demo inconsistency.

## 3. Decision

Adopt **B** (OPEN-4 acceptance).

## 4. Consequences

- **Pros:** Deterministic POC metric.
- **Cons:** Not a full statistical headway model.

## 5. Amended / Superseded by

- Observation grain clarified by [ADR-038](ADR-038-observed-headway-passages-are-bus-visit-first-seen-at-stop.md) (visit first-seen at stop×line×direction; not line-pooled poll timestamps). Median-of-gaps decision here remains.
