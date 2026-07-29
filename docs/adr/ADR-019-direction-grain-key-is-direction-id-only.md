# ADR-019: Direction grain key is direction_id only

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** Silver/Gold PK, mapping notes

## 1. Context

EMT exposes path 1/2 and A/B; GTFS exposes `direction_id`. Early schema used `direction_path`. Contract uses `direction_id`.

## 2. Alternatives Considered

- **A — Persist path and letter as columns:** Verbose.
- **B — PK/grain = `direction_id` only; path/A-B as mapping notes:** Minimal schema.
- **C — Composite of all three:** Redundant.

## 3. Decision

Adopt **B**. Document mapping (§4.6). If GTFS `direction_id` is globally empty at bootstrap → fail-fast.

## 4. Consequences

- **Pros:** One join key.
- **Cons:** Requires reliable path↔id mapping at seed and poll ([ADR-026](ADR-026-map-arrive-destination-to-direction-id-require-path-mapping-.md)).

## 5. Amended / Superseded by

- Supersedes `direction_path` / `direction_code` as schema columns.
