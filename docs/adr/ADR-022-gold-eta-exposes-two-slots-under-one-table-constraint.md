# ADR-022: Gold ETA exposes two slots under one-table constraint

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** Gold columns, US-01/02

## 1. Context

Same stop×line Arrive can return up to two buses (verified, e.g. stop 86 line 27). One Gold table forbids a child bus table.

## 2. Alternatives Considered

- **A — Only nearest bus:** Simple; hides second bus shown in official app.
- **B — `eta_seconds_1`/`bus_id_1` and `eta_seconds_2`/`bus_id_2`:** Matches API reality under 1-table rule.
- **C — Array/JSON bus list column:** Flexible; weaker for SQL agents.

## 3. Decision

Adopt **B** (team agreement after design review; option B). Slot 1 is the sooner vehicle.

## 4. Consequences

- **Pros:** Matches passenger-visible two-bus ETA.
- **Cons:** Fixed cardinality; third bus would be dropped.

## 5. Amended / Superseded by

- None at time of writing.
