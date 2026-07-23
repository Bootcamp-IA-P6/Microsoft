# ADR-038: Observed headway observations are bus-visit first-seen at stop×line×direction

- **Date:** 2026-07-23
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** US-08 / `freq_*` in `nb_poll_and_transform`; clarifies [ADR-025](ADR-025-observed-headway-formula-is-median-of-successive-gaps-in-min.md)

## 1. Context

ADR-025 chose median of successive observation gaps but left “observation” underspecified. The Phase 0 implementation pooled unique `datetime_polling` per `line_id`×window across all stops. Sequential multi-stop polling produced sub-minute gaps (e.g. 0.33 min) — poll-loop spacing, not bus headway.

## 2. Alternatives Considered

- **A — Keep line-level poll-timestamp gaps:** Wrong product meaning.
- **B — One timestamp per Pipeline run then gap:** Yields poll cadence, not headway.
- **C — Observation = first sighting of each bus visit at `stop_id`×`line_id`×`direction_id`; gaps within that grain; pool to `line_id`×window median; sample size = observation count:** Matches US-08; keeps ADR-024 line-level Gold columns.

## 3. Decision

Adopt **C**.

Rules:

1. Valid sighting row: `silver_arrives` with `bus_id IS NOT NULL`, `map_ok=true`, `direction_id` set, `day_type` in `LA|SA|FE`.
2. Same `(stop, line, direction, bus, window)` ordered by `datetime_polling`: a **new visit** starts on the first sighting or when the gap since the previous sighting of that bus is **≥ 20 minutes**.
3. **Observation** (for headway / `freq_sample_size_*`) = `datetime_polling` of the first row of each visit. Same `bus_id` polled every 2 minutes during one visit still counts as **one** observation. Different `bus_id`s = different observations.
4. Within `(stop, line, direction, window)`, sort observations → successive gaps (minutes). Keep gaps in **[1, 60]** minutes.
5. Pool kept gaps for `line_id`×window → **median** → `freq_observed_*_min` (replicated on Gold per [ADR-024](ADR-024-observed-frequency-aggregation-grain-is-line-id-plus-day-typ.md)).
6. `freq_sample_size_*` = count of those **observaciones válidas**. Gate **&lt; 20 → NULL** ([ADR-030](ADR-030-frequency-response-gate-20-observations-preferred-24h-warmup.md)). Terminology stays “observaciones” ([ADR-023](ADR-023-gold-frequency-windows-weekday-weekend-with-sample-sizes-no-.md)); this ADR only defines how one observation is counted.

## 4. Consequences

- **Pros:** Headway-like values; no Gold schema change.
- **Cons:** POC thresholds (20 / 1–60 min / 20 min visit break) are heuristic.

## 5. Amended / Superseded by

- Amends observation definition of [ADR-025](ADR-025-observed-headway-formula-is-median-of-successive-gaps-in-min.md) (median-of-gaps kept).
- Clarifies observation counting for [ADR-023](ADR-023-gold-frequency-windows-weekday-weekend-with-sample-sizes-no-.md).
