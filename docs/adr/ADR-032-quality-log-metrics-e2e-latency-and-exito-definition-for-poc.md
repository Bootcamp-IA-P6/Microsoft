# ADR-032: Quality-log metrics: E2E latency and éxito definition for POC

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** US-06 measurement (non-domain)

## 1. Context

Need definitions even though storage is out of schema scope.

## 2. Alternatives Considered

- **A — Backend-only latency:** Misses UX.
- **B — E2E latency (send→display); éxito = correct answer OR correct refusal OR correct ask-back; hallucination/wrong/silence/timeout = failure (Q19/Q20):** Product-true.
- **C — Count any non-empty reply as success:** Inflates quality.

## 3. Decision

Adopt **B**. PII/retention for POC: keep raw indefinitely (Q21=C).

## 4. Consequences

- **Pros:** Clear scoring.
- **Cons:** Long POC retention of transcripts.

## 5. Amended / Superseded by

- None at time of writing.
