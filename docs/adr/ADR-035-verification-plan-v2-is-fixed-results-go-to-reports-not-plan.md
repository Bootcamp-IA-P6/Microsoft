# ADR-035: Verification plan v2 is fixed; results go to reports not plan edits

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** emt-data-reference verification process

## 1. Context

After fixing Arrive usage issues, the verification plan was rewritten mid-flight, which defeated the point of a fixed plan.

## 2. Alternatives Considered

- **A — Edit the plan whenever results surprise us:** Circular.
- **B — Freeze plan v2; write PASS/FAIL/OPEN only to `verification-report.md`; change `emt-data-reference.md` only on FAIL:** Disciplined.

## 3. Decision

Adopt **B**. L0 dual official → L1 doc↔raw → L2/L3 counts/crosswalk → L4 live → L5 fix-or-report.

## 4. Consequences

- **Pros:** Auditable verification.
- **Cons:** Plan gaps require a new versioned plan, not silent edits.

## 5. Amended / Superseded by

- None at time of writing.
