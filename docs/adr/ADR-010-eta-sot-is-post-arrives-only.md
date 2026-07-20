# ADR-010: ETA SoT is POST arrives only

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** ETA pipeline, US-01/02

## 1. Context

Multiple sources exist for schedules; only Arrive estimates are real-time ETAs usable for the stories.

## 2. Alternatives Considered

- **A — GTFS stop_times as ETA:** Not real-time.
- **B — S1 `POST …/stops/{stopId}/arrives/` only:** Verified path (`arrivals` is 404).
- **C — Blend schedule + Arrive:** Ambiguous provenance.

## 3. Decision

Adopt **B**. Request body uses `Text_IncidencesRequired_YN=N` (alerts come from S2). Do not send unused DateTime incidence fields when incidences are N.

## 4. Consequences

- **Pros:** Single ETA provenance.
- **Cons:** Depends on EMT availability and rate limits.

## 5. Amended / Superseded by

- None at time of writing.
