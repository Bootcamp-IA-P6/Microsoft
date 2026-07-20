# ADR-033: US-03 name resolution may stay outside Gold; no schema change for POC

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** US-03, app/agent search

## 1. Context

Coverage review marked US-03 as YES (indirect). Question: is that a blocker?

## 2. Alternatives Considered

- **A — Add dedicated search table/index in medallion:** Better search; breaks 1+1+1 or bloats Gold.
- **B — App/Agent resolves name→`stop_id` via GTFS(+enrich) or Gold `stop_name`, then query Gold:** No schema change.

## 3. Decision

Adopt **B**. POC feasible without schema change.

## 4. Consequences

- **Pros:** Keeps Gold grain clean.
- **Cons:** Search quality depends on app/agent layer.

## 5. Amended / Superseded by

- None at time of writing.
