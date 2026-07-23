# ADR-015: Medallion physical schema: Bronze one, Silver per domain, Gold one

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted (amended 2026-07-23)
- **Components affected:** Fabric Lakehouse physical model

## 1. Context

POC originally required Bronze, Silver, and Gold to each be exactly one table (three total). Stakeholders insisted on that cost constraint during design review. Later PO approved a Silver domain split for arrives vs alerts ([ADR-037](ADR-037-silver-split-into-silver-arrives-and-silver-alerts.md)).

## 2. Alternatives Considered

- **A — Classic multi-table medallion:** Cleaner domains; originally rejected under hard 1+1+1.
- **B — 1+1+1 with denormalization / wide rows:** Original POC decision.
- **C — Renegotiate multi-table for alerts:** Preferred architecturally; deferred then accepted via ADR-037.

## 3. Decision

**Original (2026-07-20):** Adopt **B** (1 Bronze + 1 Silver + 1 Gold).

**Amendment (2026-07-23, ADR-037):** Cap becomes:

| Layer | Physical tables |
|-------|-----------------|
| Bronze | **1** — `bronze_emt_raw` |
| Silver | **1 per domain** — currently `silver_arrives` + `silver_alerts` |
| Gold | **1** — `gold_emt_stop_line` |

Medallion remains the **role** split (raw / conformed fact / serving), not “exactly one table per layer.” Semantic model and KPI stores stay **out of physical EMT domain schema** ([ADR-031](ADR-031-semantic-model-kpi-and-quality-logs-stay-outside-emt-domain-.md)). Workspace `microsoft-factoriaf5-2026`, Lakehouse `lh_emt_madrid`. Azure storage account/region remain UNVERIFIED.

## 4. Consequences

- **Pros:** Domain grains (poll vs alert) no longer forced into one Silver; Gold Agent contract can stay single-table.
- **Cons:** More than three Delta tables; pipeline must not treat “Silver” as one object.

## 5. Amended / Superseded by

- Amended by [ADR-037](ADR-037-silver-split-into-silver-arrives-and-silver-alerts.md).
- Design-review item for a separate **Gold** current-alert table remains rejected for POC in favor of Gold `alert_*` denormalization ([ADR-027](ADR-027-alerts-denormalized-onto-gold-rows-at-line-grain-under-one-t.md)); what is now allowed is a **Silver** alerts table feeding those columns.
