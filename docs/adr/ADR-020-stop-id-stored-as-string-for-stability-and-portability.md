# ADR-020: stop_id stored as string for stability and portability

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** Identifiers across layers

## 1. Context

GTFS and EMT samples use string ids like `"86"`. Integer typing was considered for compactness.

## 2. Alternatives Considered

- **A — Integer stop_id:** Compact; brittle with leading zeros / non-numeric ids.
- **B — String stop_id:** Stable across systems; slightly wider.

## 3. Decision

Adopt **B**, citing identifier stability and portability to other systems.

## 4. Consequences

- **Pros:** Safer joins with GTFS text ids.
- **Cons:** Minor storage/index width.

## 5. Amended / Superseded by

- None at time of writing.
