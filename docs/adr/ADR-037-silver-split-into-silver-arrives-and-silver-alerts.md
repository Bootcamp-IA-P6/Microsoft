# ADR-037: Silver split into silver_arrives and silver_alerts

- **Date:** 2026-07-23
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** Lakehouse physical schema, US-07 pipeline, ADR-015/016/027, data-source-contract

## 1. Context

Arrive polls (~60s, stop×line×direction) and S2 servicealerts (~300s, line/alert) share neither grain nor cadence. Under ADR-015’s 1+1+1 cap, alerts skipped Silver and projected from Bronze onto Gold `alert_*` (ADR-027). PO approved separating Silver by domain while keeping the Gold serving contract.

Proposal: [proposal-silver-arrives-alerts-split.md](../proposal-silver-arrives-alerts-split.md) (KO) / [.es.md](../proposal-silver-arrives-alerts-split.es.md).

## 2. Alternatives Considered

- **A — Keep 1+1+1; alerts Bronze→Gold only:** Minimal tables; mixes skip-Silver alerts with poll-fact Silver.
- **B — `silver_arrives` + `silver_alerts`; Gold `alert_*` unchanged:** Domain split; Agent contract stable.
- **C — Split Silver and remove Gold `alert_*` (join at serve time):** Cleaner Gold; breaks Agent/Semantic contract.

## 3. Decision

Adopt **B** (PO 2026-07-23).

| Decision | Choice |
|----------|--------|
| Physical Silver | `silver_arrives` (rename of `silver_emt` poll fact) + **`silver_alerts` (new)** |
| Table cap | ADR-015 amended: **1 Bronze + 1 Silver per domain + 1 Gold** |
| Alerts grain / PK | **A-1:** one row = `alert_id` × `line_id`; `_rk = SHA256(alert_id \| line_id \| snapshot_at)` |
| Alerts history | **latest-only** (current snapshot; no append history for POC) |
| `alert_active` | Computed at **Gold assemble** with `now ∈ active_period` (Europe/Madrid). Silver stores periods/texts/`line_id` only |
| Line map failure | **`map_ok` gate:** keep failed rows in Silver/log; MERGE to Gold only if `map_ok=true`; no guessed `line_id` |
| Gold | **Option A:** keep `alert_*` columns; sole input = `silver_alerts` (no Bronze re-parse for alerts) |
| Anti dual-truth | Alerts job: Silver upsert and Gold `alert_*` MERGE in the **same run**; arrives job must not touch `alert_*` |
| Naming | Prefer **`alerts`**, never `incidents` (Arrive Incident ≠ disruption SoT — ADR-011) |

**Common constraints (not optional):** no join on RT `stop_id` for Gold alert semantics; replicate `alert_*` by `line_id` onto stop×direction rows.

## 4. Consequences

- **Pros:** Medallion roles stay; domains not polymorphic; Agent/mock/US-07 contract unchanged; alert parse/map owned in Silver.
- **Cons:** +1 physical table and pipeline branch; rename `silver_emt` → `silver_arrives` must propagate; not a latency win.

## 5. Amended / Superseded by

- Amends [ADR-015](ADR-015-medallion-physical-schema-one-bronze-one-silver-one-gold-tab.md) (table cap).
- Amends [ADR-016](ADR-016-silver-is-append-only-poll-fact-wide-rows-not-polymorphic-re.md) (table name = `silver_arrives`; alerts out of poll fact).
- Amends [ADR-027](ADR-027-alerts-denormalized-onto-gold-rows-at-line-grain-under-one-t.md) (Gold `alert_*` kept; source = `silver_alerts`).
- Contract: `data-source-contract-v4.md` → **4.3**.
