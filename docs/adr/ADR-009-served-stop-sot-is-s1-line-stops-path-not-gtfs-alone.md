# ADR-009: Served-stop SoT is S1 line stops path not GTFS alone

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** Catalog seed, Gold row existence, US-01 not-served answers

## 1. Context

Need a rule for “line does not serve this stop”. GTFS stop_times and EMT line-stops can diverge. Empty Arrive must not alone prove not-served.

## 2. Alternatives Considered

- **A — GTFS-only not-served:** Convenient; can false-negative vs EMT.
- **B — S1 `GET …/lines/{lineId}/stops/{direction}/` membership (Q01=B):** Matches operational EMT path.
- **C — Empty Arrive ⇒ not served:** Wrong (temporary no estimation).

## 3. Decision

Adopt **B**. Catalog seed and Gold row presence must align with S1 line-stops SoT. GTFS may denormalize names/coords only.

## 4. Consequences

- **Pros:** Not-served answers track EMT.
- **Cons:** Daily seed must call line-stops for in-scope lines/directions.

## 5. Amended / Superseded by

- None at time of writing.
