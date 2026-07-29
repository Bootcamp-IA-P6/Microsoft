# ADR-014: Ask-back rules for missing direction and ambiguous place names

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** Agent dialog, US-01/03

## 1. Context

Direction and place names are often underspecified. Guessing causes wrong ETA rows.

## 2. Alternatives Considered

- **A — Infer silently:** Smooth UX; high error rate.
- **B — Ask back when direction unknown (Q02=D) and for street/area names (Q09=D):** Safer.

## 3. Decision

Adopt **B**. Peak/off-peak labels are **not** used (Q28). When user names weekday/weekend, use the matching frequency window columns.

## 4. Consequences

- **Pros:** Fewer wrong-direction answers.
- **Cons:** Extra turn in conversation.

## 5. Amended / Superseded by

- None at time of writing.
