# ADR-001: Single consolidated EMT data reference before extraction decisions

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** Documentation, source-of-truth process

## 1. Context

Three overlapping data sources (EMT OpenAPI, Mobility Database GTFS-RT feed mdb-3102, GTFS static) share concepts such as stops and disruptions. Before choosing sources for user stories or designing a Fabric schema, the project needed one verified reference of endpoints, fields, samples, and cross-mappings. Multiple fragmented docs were hard to maintain and invited invented fields.

## 2. Alternatives Considered

- **A — Multiple topic docs in parallel:** Fast to draft; high drift risk.
- **B — One consolidated reference (`emt-data-reference.md`) verified against raw samples:** Slower upfront; single place for claims.
- **C — Jump straight to extraction / schema:** Faster short-term; decisions without verified facts.

## 3. Decision

Adopt **alternative B**: maintain one consolidated [`emt-data-reference.md`](../emt-data-reference.md) grounded in `docs/samples/raw/`, dual official docs, and live checks. Extraction decisions and schema design come after verification. Do not invent undocumented fields.

## 4. Consequences

- **Pros:** Shared factual baseline; verification layers (L0–L5) can assert against one document.
- **Cons / Trade-offs:** Large document; verification cost on every material change.

## 5. Amended / Superseded by

- None at time of writing.
