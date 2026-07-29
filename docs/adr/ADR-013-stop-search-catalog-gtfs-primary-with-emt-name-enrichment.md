# ADR-013: Stop search catalog: GTFS primary with EMT name enrichment

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** US-03, catalog snapshot

## 1. Context

Users ask by street/stop name, not stop code. `stop_desc` is empty in GTFS.

## 2. Alternatives Considered

- **A — EMT-only names:** Incomplete catalog vs GTFS.
- **B — GTFS `stops` primary + EMT name/address enrichment (Q08=C):** Best coverage.
- **C — Live arroundxy only:** Needs coordinates; returns NO data sometimes.

## 3. Decision

Adopt **B**. Catalog refresh daily (Q11=B). Street/area names: never single-guess; return candidates and ask back (Q09=D).

## 4. Consequences

- **Pros:** Disambiguation-safe UX.
- **Cons:** Search UX lives partly outside Gold (ADR-034).

## 5. Amended / Superseded by

- None at time of writing.
