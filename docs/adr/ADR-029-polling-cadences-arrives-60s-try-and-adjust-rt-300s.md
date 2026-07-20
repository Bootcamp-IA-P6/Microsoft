# ADR-029: Polling cadences: arrives ~60s try-and-adjust; RT 300s

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** Ingestion schedules

## 1. Context

Arrives ideally every 60s but may not hold under load (~52 stops). RT has no strong reason to match 60s and rate limits are unknown.

## 2. Alternatives Considered

- **A — Both at 60s:** Fresh alerts; heavier / unnecessary for RT.
- **B — Arrives ideal 60s (monitor); RT 300s (~5×):** Pragmatic.
- **C — Leave both UNVERIFIED forever:** Blocks ops planning.

## 3. Decision

Adopt **B**. Keep arrives performance as watch item; do not pretend final production interval is proven.

## 4. Consequences

- **Pros:** Clear POC targets.
- **Cons:** Stale=180s assumes ~60s arrives.

## 5. Amended / Superseded by

- None at time of writing.
