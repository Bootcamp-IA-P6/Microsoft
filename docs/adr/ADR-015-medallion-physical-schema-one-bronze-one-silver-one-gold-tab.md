# ADR-015: Medallion physical schema: one Bronze, one Silver, one Gold table

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** Fabric Lakehouse physical model

## 1. Context

POC constraint: Bronze, Silver, and Gold must each be exactly one table (three total). Stakeholders insisted on this cost constraint during design review.

## 2. Alternatives Considered

- **A — Classic multi-table medallion:** Cleaner domains; violates constraint.
- **B — 1+1+1 with denormalization / wide rows:** Fits constraint; forces trade-offs (alert/freq replication).
- **C — Renegotiate multi-table for alerts:** Preferred architecturally; rejected for POC timeline.

## 3. Decision

Adopt **B**. Semantic model and KPI stores are **out of physical schema scope** for now (needed later, not decided here). Workspace `microsoft-factoriaf5-2026`, Lakehouse `lh_emt_madrid`. Azure storage account/region remain UNVERIFIED.

## 4. Consequences

- **Pros:** Implementable under hard table cap.
- **Cons:** Line-level attributes replicated onto stop×direction rows; complexity shifts to pipeline rules.

## 5. Amended / Superseded by

- Design-review item proposing a separate current-alert table was **rejected for POC** in favor of Gold `alert_*` denormalization (ADR-025).
