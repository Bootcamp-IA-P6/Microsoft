# ADR-026: Map Arrive destination to direction_id; require path mapping at seed

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** Silver poll write path, catalog seed

## 1. Context

Arrive has no direction field, but Gold/Silver grain requires `direction_id`. Seed uses EMT path 1/2.

## 2. Alternatives Considered

- **A — Write ETA into both directions:** Wrong.
- **B — Map `destination` ≈ `name_b` → 0, ≈ `name_a` → 1; on failure do not blind-update both; seed path 1→0, path 2→1 (OPEN-1, OPEN-3):** Aligns §4.6.

## 3. Decision

Adopt **B**.

## 4. Consequences

- **Pros:** Closes poll→Gold direction hole.
- **Cons:** Needs string normalization care (accents/case) at implementation time.

## 5. Amended / Superseded by

- None at time of writing.
