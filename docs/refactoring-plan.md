# EMT Madrid Fabric Refactoring Roadmap

**Updated:** 2026-07-23 — aligned with contract **v4.3** ([data-source-contract-v4.md](./data-source-contract-v4.md), [ADR-037](adr/ADR-037-silver-split-into-silver-arrives-and-silver-alerts.md))

## Objective

Transform the current notebook-based Spark pipeline into a modular, reusable, production-oriented architecture while minimizing risk.

Instead of rewriting the project, evolve it incrementally through independent phases.

---

# Design Principles

- Keep the medallion roles: **Bronze → Silver (by domain) → Gold**.
- Physical domain tables (contract v4.3):
  - `bronze_emt_raw`
  - `silver_arrives` (poll history + catalogue seed; ex `silver_emt`)
  - `silver_alerts` (S2 servicealerts, latest-only)
  - `gold_emt_stop_line` (Agent serving; `alert_*` columns unchanged)
- Keep the **Lakehouse** as the storage layer through Phase 0–3 (Phase 4 may add Eventhouse).
- Preserve functionality after every phase.
- Separate business logic from execution engine.
- Maximize code reuse.
- Replace infrastructure gradually instead of rewriting everything.
- **Arrives jobs must not overwrite Gold `alert_*`.** Alerts are a separate path (contract §4 pipeline steps 3–4).

---

# Phase 0 — Baseline (current / target “notebook complete”)

Phase 0 is the **stable base branch** for everything that follows. It is *not* optional debt.

## Goal

Contract v4.3 Lakehouse ingestion running in Fabric with paste notebooks (no Environment / no Git↔Fabric sync required).

## Architecture

```text
[1× / migrate]  nb_create_tables
[1× / daily]    nb_bootstrap_gtfs_silver  → seed silver_arrives

[recurring]     nb_poll_and_transform
                  S1 arrives → bronze → append silver_arrives
                  → MERGE gold (ETA / freq / stale only — NOT alert_*)

[recurring]     nb_alerts_silver_gold
                  S2 servicealerts → bronze → upsert silver_alerts
                  → MERGE gold alert_* only (by line_id)
```

```text
Pipeline(s) → Notebook(s) → Spark → Lakehouse tables (v4.3)
```

## Deliverables (Phase 0 complete)

- [x] Tables + migrate `silver_emt` → `silver_arrives` (data preserved)
- [x] `silver_alerts` DDL
- [x] Arrives poll + transform notebooks on `silver_arrives`
- [x] Arrives Gold MERGE does **not** clear `alert_*`
- [x] `nb_alerts_silver_gold` (full S2 → silver_alerts → gold `alert_*`)
- [x] Ops guide lists both recurring notebooks / schedules
- [x] Freq headway = visit first-seen observations ([ADR-038](./adr/ADR-038-observed-headway-passages-are-bus-visit-first-seen-at-stop.md)); contract v4.3.1

SoT paste notebooks: `notebooks/nb_*.py` · guide: [manual-lakehouse-ingestion.md](./manual-lakehouse-ingestion.md)

## Problems still accepted in Phase 0

- Spark cold start
- Large paste notebooks
- Logic coupled to Spark
- Hard to unit-test / reuse outside Fabric

Later phases remove these without changing the **v4.3 table contracts** unless an ADR says otherwise.

---

# Phase 1 — Spark Performance Optimization

## refer

https://community.fabric.microsoft.com/t5/Fabric-Updates-Blog/How-does-Fabric-make-Spark-Notebooks-Instant/ba-p/5172419

## Goal

Improve execution speed **without** changing architecture or schemas.

Base = **Phase 0** (v4.3 tables, arrives + alerts notebooks).

## Tasks

- [x] Reduce Spark jobs (skip pipeline `count`/`display` unless `verbose_display`)
- [x] Remove unnecessary `collect()` (gold = latest poll join only; no full `silver_arrives` collect)
- [x] Freq: visit first-seen observations via Spark ([ADR-038](adr/ADR-038-observed-headway-passages-are-bus-visit-first-seen-at-stop.md)); exact `statistics.median` on gap values
- [x] Incremental cutoff = one agg instead of two
- [x] Timing logs: `[phase1 timing] HTTP …` vs transform laps (separate wall-clock drivers)
- [x] Fix silver append path: `cache` → `count` → `write` (no `take`+`write` double join)
- [ ] Evaluate **Starter Pool** in Fabric UI (this is what [Instant notebooks](https://community.fabric.microsoft.com/t5/Fabric-Updates-Blog/How-does-Fabric-make-Spark-Notebooks-Instant/ba-p/5172419) actually changes — **not** notebook code)
- [ ] Measure startup vs execution on real Pipeline runs (compare before/after paste)

## Code changes (paste SoT)

- `notebooks/nb_poll_and_transform.py`
- `notebooks/nb_alerts_silver_gold.py`
- Ops: [manual-lakehouse-ingestion.md](./manual-lakehouse-ingestion.md) § Phase 1

## Notes

- Instant / cold-start: enable **default Starter Pool** (avoid custom pool / Environment that forces on-demand ~minutes). Code cannot fix session spin-up.
- End-to-end wall time is often dominated by **HTTP arrives poll**, not Spark transform — check timing lines separately.
- Phase 1 code wins grow as `silver_arrives` history grows (latest-only gold path).

## Deliverables

- Faster **transform** portion as history grows; clearer HTTP vs Spark timing
- Same outputs (`silver_arrives`, `silver_alerts`, `gold_emt_stop_line`) incl. exact freq median
- Zero architectural / schema changes

---

# Phase 2 — Modular Spark Architecture

## Goal

Separate business logic into reusable Python modules.

Notebooks become thin orchestrators only, e.g.:

```python
import sys
_FILES_PY = "/lakehouse/default/Files/python"
if _FILES_PY not in sys.path:
    sys.path.insert(0, _FILES_PY)

from pipeline.orchestrator.run_arrives import run_arrives
from pipeline.orchestrator.run_alerts import run_alerts
```

**Deploy:** upload repo `pipeline/` → Lakehouse `Files/python/pipeline/` (no Environment / whl — Instant-friendly).  
**Schema:** unchanged (v4.3.1 tables).

## Status

- [x] `pipeline/` package under repo root
- [x] Thin paste notebooks (`nb_create_tables`, `nb_bootstrap_gtfs_silver`, `nb_poll_and_transform`, `nb_alerts_silver_gold`)
- [x] Arrives / alerts / bootstrap / create orchestrators
- [x] Freq remains ADR-038 (`pipeline.aggregate.frequency`)
- [ ] Fabric: upload `Files/python/pipeline/` + re-paste thin notebooks + smoke

## Proposed Structure

```text
pipeline/
    config/
        settings.py
        constants.py          # table names: bronze_emt_raw, silver_arrives, …
    common/                   # datetime, keys, delta_retry, http_retry, …
    ingestion/
        emt_client.py         # S1 REST
        gtfs_rt_client.py     # S2 servicealerts
        gtfs_static.py
        bronze_writer.py
        arrives_ingest.py
        alerts_ingest.py
    transform/
        arrives_normalize.py  # (logic lives in aggregate/arrives_transform for now)
        alerts_normalize.py
        enrich.py
    aggregate/
        frequency.py          # ADR-038
        arrives_transform.py  # silver + gold arrives MERGE
        alerts_project.py
        alerts_transform.py   # silver_alerts + gold alert_* MERGE
    validation/
        schema.py
        quality.py
    orchestrator/
        run_arrives.py
        run_alerts.py
        run_bootstrap.py
        run_create_tables.py
        bootstrap_impl.py
```

## Responsibilities

| Area | Owns |
|------|------|
| ingestion | Auth, S1/S2 HTTP, bronze append |
| transform | Parse, normalize, map to `silver_arrives` / `silver_alerts` |
| aggregate | Freq, latest ETA, alert projection, **separate** Gold MERGEs |
| validation | Schema / quality |
| orchestrator | Order only — thin notebooks call these |

Do **not** merge arrives + alerts into one Gold overwrite that resets the other domain’s columns.

## Deliverables

- [x] Thin notebooks (arrives / alerts / bootstrap / create)
- [x] Reusable modules under `pipeline/`
- [x] Better testing and Git history surface (modules vs mega-notebooks)
- [ ] Fabric smoke after Files upload

---

# Phase 3 — Serverless Ingestion

## Goal

Remove **external API** calls from the Spark **transform** hot path.

Spark starts from Bronze, not from EMT/GTFS-RT HTTP.

## Status (repo)

- [x] Split orchestrators: `run_arrives_ingest` / `run_arrives_transform`, `run_alerts_ingest_only` / `run_alerts_transform_only`
- [x] Alerts transform can reload latest bronze `servicealerts` payload (no in-session HTTP required)
- [x] Notebooks: `nb_ingest_*` + `nb_transform_*` (combined notebooks kept as fallback)
- [x] Docs: manual guide Phase 3 topology
- [ ] Fabric: rewire Pipelines to ingest → transform
- [ ] Optional later: replace ingest notebooks with Fabric User Data Function

## Current (Phase 0–2)

```text
Notebook → Spark → EMT / GTFS-RT API → Bronze → Silver → Gold
```

## Target (Phase 3 POC)

```text
Fabric Pipeline
  → nb_ingest_arrives / nb_ingest_alerts   # HTTP → bronze (UDF-equivalent for now)
  → nb_transform_arrives / nb_transform_alerts  # Spark: bronze → silver → gold (no HTTP)
```

Aspirational:

```text
Fabric Pipeline
  → User Data Function
      → S1 / S2 → Bronze
  → Spark transform only
      → silver_* → gold_*
```

Keep **two ingestion cadences**:

- Arrives ~60s (POC may be slower)
- Alerts ~300s

## Benefits

- Spark transform independent of external I/O / SSL flakiness
- Reusable ingestion entrypoints
- Ready for Eventstream (Phase 4)

**Schema:** unchanged (v4.3.1).

---

# Phase 4 — Replace Spark Execution

## Goal

Replace Spark transforms with Real-Time Intelligence where it fits.

Business logic stays conceptually the same; engine changes.

**Why now:** Lakehouse notebook ingest/transform wall-clock (session + HTTP) is too slow for target cadences. Phase 3 split was structural prep; Phase 4 removes Spark from the hot path.

## Branch

`feat/fabric-phase4` (from Phase 3). Lakehouse Phase 0–3 path remains rollback until Agent is re-pointed and validated.

## Status

- [ ] Decide Eventhouse / Eventstream workspace objects (names, retention)
- [ ] Ingest: UDF (or non-Spark poller) → Eventstream → EH bronze-equivalent
- [ ] Map `pipeline/` domains to KQL / MVs (see table below)
- [ ] Gold serving grain = today’s `gold_emt_stop_line` (Agent-compatible)
- [ ] Keep arrives vs alerts column ownership (no cross-wipe)
- [ ] Dual-run / cutover plan vs Lakehouse gold
- [ ] Agent rebind smoke (ETA + US-07 alerts + US-08 freq)

## Target sketch

```text
Ingestion (UDF / poller)
  → Eventstream
  → Eventhouse
       Bronze raw
       Silver: silver_arrives-equivalent / silver_alerts-equivalent
       Gold: MV or serving table (same Agent grain as gold_emt_stop_line)
  → Data Agent
```

Domain split **must** survive the move:

| Today (Lakehouse) | Future (conceptual) | Phase 2–3 code SoT |
|-------------------|---------------------|--------------------|
| `silver_arrives` | Arrives fact / history in EH | `arrives_ingest` + `arrives_transform` / `frequency` |
| `silver_alerts` | Alerts latest snapshot in EH | `alerts_ingest` + `alerts_transform` / `alerts_project` |
| `gold_emt_stop_line` | Serving view/table for Agent | gold arrives MERGE + gold alerts MERGE (separate) |

```text
arrives_normalize / frequency / latest  → KQL / Materialized Views
alerts_normalize / alerts_project       → Dedicated KQL (or update policies)
```

**Contract:** physical engine may change; Agent-facing grain and column meanings stay v4.3.1 unless a new ADR says otherwise. Freq = ADR-038.

---

# Final Architecture (aspirational)

```text
Fabric Pipeline
  → User Data Function(s)     # S1 + S2 ingestion, separate cadences
  → Eventstream
  → Eventhouse
  → KQL / Materialized Views  # silver_arrives + silver_alerts domains
  → Gold serving
  → (optional) Semantic Model
  → AI / Data Agent
```

Lakehouse Phase 0–2 remains the rollback and Agent-proven path until Phase 4 is validated.

---

# Success Criteria

## Phase 0

- Contract v4.3 tables in use
- Arrives and alerts paths both live
- Gold `alert_*` not wiped by arrives jobs
- Agent can use `gold_emt_stop_line`

## Phase 1

- Faster Spark execution
- Same functionality and schemas

## Phase 2

- Modular architecture
- Thin notebooks
- Reusable modules; arrives/alerts orchestration split

## Phase 3

- Spark **transform** no longer calls external APIs on the hot path
- Clear separation ingestion vs transform (notebooks + orchestrators)
- Combined notebooks optional fallback only

## Phase 4

- Spark replaced (or bypassed) by Eventstream/Eventhouse for hot path
- Minimal rewrite of domain logic
- `silver_arrives` / `silver_alerts` semantics preserved
