# ADR-030: Frequency response gate: 20 observations preferred; 24h warmup guide

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** US-08 readiness

## 1. Context

Cold start makes observed frequency impossible initially. Design review asked for warmup policy vs hard sample gate.

## 2. Alternatives Considered

- **A — Time-only warmup (e.g. 24h) then always answer:** May still be under-sampled.
- **B — 24h operational guide + **20 valid observations** gate preferred; below 20 → NULL/unknown even after 24h:** Safer.
- **C — No gate:** Hallucinated headways.

## 3. Decision

Adopt **B**. Threshold may be tuned later operationally; leave as adjustable initial value.

## 4. Consequences

- **Pros:** Aligns with contract’s 20-observation idea.
- **Cons:** Early demos may say “unknown” often.

## 5. Amended / Superseded by

- None at time of writing.
