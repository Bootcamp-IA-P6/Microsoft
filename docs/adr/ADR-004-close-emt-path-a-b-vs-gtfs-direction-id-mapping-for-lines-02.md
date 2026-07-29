# ADR-004: Close EMT path A/B vs GTFS direction_id mapping for lines 027 and 014

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** Direction mapping, seed, Arrive→direction assignment

## 1. Context

EMT uses path `/stops/{1|2}/` and letters A/B; GTFS uses `direction_id` 0/1. The mapping was left open because it had not been measured, not because it was impossible.

## 2. Alternatives Considered

- **A — Leave OPEN until full network enumeration:** Safest globally; blocks schema grain.
- **B — Measure two lines (027, 014) and close scope:** Enough for POC mapping rules.
- **C — Invent 1:1 equality path=GTFS:** Fast; empirically false (path `1` ↔ GTFS `0`).

## 3. Decision

Adopt **B**. Verified pattern (§4.6): path `…/stops/1/` → `direction_id=0`; letter B on that path matches 0; A matches 1. Full-network enumeration is **out of document scope**. Direction OPEN in §5 closed after two-line confirmation.

## 4. Consequences

- **Pros:** Unblocks Gold grain and seed rules.
- **Cons:** Other lines assumed to follow 027/014 pattern until proven otherwise.

## 5. Amended / Superseded by

- None at time of writing.
