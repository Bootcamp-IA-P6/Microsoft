# ADR-031: Semantic model, KPI, and quality logs stay outside EMT domain Gold

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** Scope boundaries, ops analytics

## 1. Context

Semantic layer is needed eventually but was explicitly not part of this schema decision pass. KPI/response-rate and US-06 quality logs were debated for Gold inclusion.

## 2. Alternatives Considered

- **A — Put KPI/quality into domain Gold:** One agent surface; pollutes domain.
- **B — Keep Semantic/KPI/quality outside EMT domain Gold; optional separate ops connection later:** Clean domain table.
- **C — Expand Semantic to read Silver:** Weakens single Gold serving intent.

## 3. Decision

Adopt **B**. Bus Data Agent reads Gold (+ future Semantic). Chat history and quality logs remain separated (Q16). Quality store may start as files; not Fabric domain schema now (Q18 out of scope).

## 4. Consequences

- **Pros:** Gold stays passenger-domain facts.
- **Cons:** Ops metrics need another dataset/dashboard.

## 5. Amended / Superseded by

- None at time of writing.
