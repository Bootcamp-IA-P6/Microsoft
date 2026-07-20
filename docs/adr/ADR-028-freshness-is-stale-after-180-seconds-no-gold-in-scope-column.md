# ADR-028: Freshness is_stale after 180 seconds; no Gold in_scope column

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** Gold serving flags

## 1. Context

Agent needs to know if ETA is stale. Geofence membership could be a column or implied by table contents.

## 2. Alternatives Considered

- **A — `in_scope` boolean on Gold:** Explicit; redundant if table is filtered.
- **B — No `in_scope` column; `is_stale = (now - updated_at) > 180s` assuming 60s×3:** Simpler Gold.

## 3. Decision

Adopt **B**. If poll interval changes, adjust documentation (and threshold) accordingly.

## 4. Consequences

- **Pros:** Narrower Gold contract.
- **Cons:** Stale threshold coupled to intended poll cadence.

## 5. Amended / Superseded by

- None at time of writing.
