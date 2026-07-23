# ADR-033: US-03 name resolution may stay outside Gold; no schema change for POC

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** US-03, app/agent search

## 1. Context

Coverage review marked US-03 as YES (indirect). Question: is that a blocker?

## 2. Alternatives Considered

- **A — Add dedicated search table/index in medallion:** Better search; adds tables or bloats Gold (originally also broke hard 1+1+1).
- **B — App/Agent resolves name→`stop_id` via GTFS(+enrich) or Gold `stop_name`, then query Gold:** No schema change.

## 3. Decision

Adopt **B**. POC feasible without schema change.

## 4. Consequences

- **Pros:** Keeps Gold grain clean.
- **Cons:** Search quality depends on app/agent layer.

## 5. Amended / Superseded by

- Table-cap wording in alt A: hard 1+1+1 later amended by [ADR-037](ADR-037-silver-split-into-silver-arrives-and-silver-alerts.md) / [ADR-015](ADR-015-medallion-physical-schema-one-bronze-one-silver-one-gold-tab.md); **US-03 decision B unchanged** (still no dedicated search table in medallion for POC).
