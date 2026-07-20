# ADR-021: line_id vs line_label and failed Arrive label resolution excludes Gold

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** Joins, Arrive mapping

## 1. Context

Arrive `line` is passenger label form (`"27"`), while internal id is `"027"`. `label=001` maps to `line=361`, not `line=001`.

## 2. Alternatives Considered

- **A — Join on Arrive.line string as-is:** Breaks on padding/label collisions.
- **B — `line_id` internal join key + `line_label` display; master lookup; `map_ok=false` excludes Gold:** Safe.

## 3. Decision

Adopt **B**. Failed label→`line_id` resolve must not merge into Gold.

## 4. Consequences

- **Pros:** Prevents wrong-line ETA.
- **Cons:** Requires maintained label master.

## 5. Amended / Superseded by

- None at time of writing.
