# ADR-002: Require both apidocs and m360 swagger for Arrive field semantics

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** EMT OpenAPI interpretation, Arrive field usage, verification plan

## 1. Context

Arrive responses contain fields such as `positionTypeBus`, `isHead`, and `deviation`. apidocs and m360-swagger disagree or omit definitions. Using only swagger produced incorrect “used” markings and hallucinations.

## 2. Alternatives Considered

- **A — Trust swagger only:** Convenient; wrong for No-apply fields.
- **B — Trust apidocs only:** Misses swagger-only wording and conflicts.
- **C — Always cross-check both official sources (L0):** Extra work; conflict-aware.

## 3. Decision

Adopt **C**. Verification plan v2 makes dual official docs mandatory. Conflicts are recorded side-by-side. Official `No apply for this version` means **do not use** even if values appear in live payloads.

## 4. Consequences

- **Pros:** Stops inventing meanings; aligns usage flags with vendor docs.
- **Cons:** Compare JSON and L0 checks must be refreshed when official docs change.

## 5. Amended / Superseded by

- Supersedes earlier single-source Arrive usage notes from early verification runs.
- Formalized in verification plan v2 (`doc_verification_plan_v2`).
