# ADR-024: Observed frequency aggregation grain is line_id plus day-type window

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** US-08 computation, Gold freq_* replication

## 1. Context

After choosing observed frequency, grain was still ambiguous: per stop×line×direction vs per line×window.

## 2. Alternatives Considered

- **A — Aggregate per Gold grain (stop×line×direction):** Fine-grained; slow to reach 20 samples.
- **B — Aggregate per `line_id` + window; replicate values to all Gold rows of that line (like alerts):** Faster warmup; line-level meaning.

## 3. Decision

Adopt **B** (OPEN-2 acceptance).

## 4. Consequences

- **Pros:** Shared sample pool per line; consistent answers across stops.
- **Cons:** Stop-specific headway differences are hidden.

## 5. Amended / Superseded by

- None at time of writing.
