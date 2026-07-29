# ADR-036: No peak or off-peak labels; no daily total vehicle counts in scope

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** US-08 product language

## 1. Context

AC text mentioned peak-style demos; APIs do not provide reliable peak bands. Daily totals are not available without heavy aggregation and were declined.

## 2. Alternatives Considered

- **A — Speak peak/off-peak using guessed windows:** Friendly; unverified.
- **B — Forbid peak labels; answer with day-type frequency windows only; do not promise daily totals:** Honest.

## 3. Decision

Adopt **B**.

## 4. Consequences

- **Pros:** Avoids fabricated timetable structure.
- **Cons:** Less “tourery” wording in demos.

## 5. Amended / Superseded by

- None at time of writing.
