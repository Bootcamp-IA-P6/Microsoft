# ADR-018: Bronze contract: UUID ingest_id and no enforced column types

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** Bronze table contract

## 1. Context

Team agreed not to force NOT NULL/types on Bronze for POC. `ingest_id` usefulness vs weight was debated.

## 2. Alternatives Considered

- **A — Strict typed Bronze:** Better DQ early; slows iteration.
- **B — Soft schema + UUID `ingest_id` for lineage:** Traceable; light.
- **C — No ingest_id:** Minimal; weaker replay/debug.

## 3. Decision

Adopt **B**. Use UUID `ingest_id`. Do not enforce types/NOT NULL by contract on Bronze.

## 4. Consequences

- **Pros:** Fast POC ingestion; correlatable batches.
- **Cons:** More cleaning burden on Silver.

## 5. Amended / Superseded by

- None at time of writing.
