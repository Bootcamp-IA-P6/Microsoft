# EMT Madrid Fabric Refactoring Roadmap

**Updated:** 2026-07-29 — contract **v4.5** ([ADR-040](./adr/ADR-040-eventhouse-catalogue-sot-seed-tag-and-kusto-udf-read.md)); Phase 5 EH catalogue

## Objective

Transform the current notebook-based Spark pipeline into a modular, reusable, production-oriented architecture while minimizing risk.

Instead of rewriting the project, evolve it incrementally through independent phases.

---

# Design Principles

- Keep the medallion roles: **Bronze → Silver (by domain) → Gold**.
- Physical domain tables (contract v4.5):
  - `bronze_emt_raw`
  - `silver_arrives` (poll history + catalogue seed; ex `silver_emt`)
  - `silver_alerts` (S2 servicealerts, latest-only)
  - `gold_emt_stop_line` (Agent serving; `alert_*` columns unchanged)
- Keep the **Lakehouse** as the storage layer through Phase 0–3 (Phase 4 adds Eventhouse hot path; Phase 5 removes LH as catalogue SoT).
- Preserve functionality after every phase.
- Separate business logic from execution engine.
- Maximize code reuse.
- Replace infrastructure gradually instead of rewriting everything.
- **Arrives jobs must not overwrite Gold `alert_*`.** Alerts are a separate path (contract §4 pipeline steps 3–4).
- **Daily catalogue seed must not wipe live Gold ETA** when sharing `silver_arrives` (Phase 5).

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

See [phase4-rti.md](./phase4-rti.md). **Push only when asked.**

- [x] UDF poll + silver expand (`poll_arrives_scope`, `poll_alerts_scope`) — smoke OK (`bronze`/`silver`/`fails=0`)
- [x] Eventhouse DDL + gold KQL (`rti/kql/01`–`06`)
- [x] UDF connections + Eventstream CONNs (aliases `lhemtmadrid` / `varemtmadrid`)
- [x] Bootstrap remains Lakehouse daily
- [ ] Gold apply on schedule (`.set-or-replace gold_emt_stop_line`)
- [ ] Full-scope arrives batches + Pipeline
- [ ] Dual-run / Agent rebind; ADR-038 KQL validate

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

**Contract:** physical engine may change; Agent-facing grain and column meanings stay v4.4 unless a new ADR says otherwise. Freq = ADR-038.

---

# Phase 5 — Remove Lakehouse catalogue dependency

**Decision record:** [ADR-040](./adr/ADR-040-eventhouse-catalogue-sot-seed-tag-and-kusto-udf-read.md) · contract **v4.5**

## Goal

Move daily GTFS + S1 line-stops **bootstrap SoT** from Lakehouse `silver_arrives` into Eventhouse **`silver_arrives` (same table — no separate catalogue table)**. UDF reads scope / denorm / `line_id` list from Eventhouse only. Lakehouse becomes optional rollback, not a hot-path dependency.

## Why now (not Phase 4)

- Phase 4 driver was Spark session cost on the **hot path**. Bootstrap stayed on Lakehouse on purpose (daily, heavy GTFS; little RTI cadence win) — see [phase4-rti.md](./phase4-rti.md) out of scope “Moving bootstrap into Eventhouse”.
- Arrives wall-clock is already **≈80s+** per run; **60s cadence is not the Phase 5 success metric**.
- Remaining structural debt: dual engine for catalogue (LH write + UDF LH SQL read). Phase 5 removes that.

## Non-goals

- Sub-60s arrives (batching / parallelism — separate track).
- New physical table for catalogue (e.g. `silver_catalogue`). Prefer same `silver_arrives` grain as Lakehouse today.
- Pausing arrives for bootstrap (impossible: arrives is 24/7; bootstrap ~06:00–09:00 always overlaps).
- Merging daily bootstrap into the minute-cadence arrives/alerts **pipeline item** (keep a separate daily pipeline for failure isolation — overlap with arrives is expected).
- Changing poll `emt_record` away from `"silver_arrives"` (poll path stays as-is).

## Verified: how `emt_record` is used today (2026-07-29)

Repo audit before implement:

| Layer | Uses `emt_record`? |
|-------|-------------------|
| KQL `04` gold / `05` freq / `silver_alerts_latest` | **No** — never in `where`; gold uses `map_ok`, `datetime_polling`, `eta_*`; freq uses `bus_id` present |
| KQL `01`–`03` | Column + JSON mapping `$.emt_record` only (passthrough) |
| UDF `_send` | **No filter** — routes by **CONN** (`ARRIVES_BRONZE_*` / `ARRIVES_SILVER_*` / alerts twin), not by field value |
| Lakehouse `bootstrap_impl` / `pipeline/` | **Field absent** |
| Eventstream filter definitions | **Not in repo** — portal-owned |

**Eventstreams (portal):** `es_emt_arrives`, `es_emt_arrives_silver`, `es_emt_alerts`, `es_emt_alerts_silver`.

Implications for Phase 5:

1. Adding `emt_record = "silver_arrives_seed"` does **not** break existing KQL consumers (they ignore the field).
2. **Still must** add Gold exclude (**P5.2**) before seeds land — otherwise `max(datetime_polling)` treats seeds as latest polls.
3. Portal: confirm `es_emt_arrives_silver` → `silver_arrives` has **no** hard filter `emt_record == "silver_arrives"` only; if it does, allow-list `"silver_arrives_seed"`. If no filter (schema mapping only), seed JSON with the same silver columns lands as-is.
4. Seeds use **`es_emt_arrives_silver`** (same silver mapping as arrives polls). Do not send seeds to bronze or alerts streams.

## Locked design decisions

| Decision | Choice |
|----------|--------|
| Catalogue table | Same EH `silver_arrives` (no second table) |
| Seed vs poll discriminator | **`emt_record = "silver_arrives_seed"`** for seeds only; polls keep **`"silver_arrives"`** |
| Empty Arrive[] polls | Stay `"silver_arrives"` (heartbeat ≠ catalogue) |
| EH seed refresh | Append new `catalog_loaded_at`; **no** broad DELETE of null-shaped rows |
| Gold latest | Exclude `emt_record == "silver_arrives_seed"` (defense A; optional C) — **required even though no KQL uses the field today** |
| Catalogue / scope read | Tagged seeds only + `max(catalog_loaded_at)` (defense B) |
| Hot-path LH | Remove after cutover (`lhemtmadrid` / `LH_SQL_DB` gone from UDF) |
| Bootstrap runner | Spark-free notebook `nb_bootstrap_eh_silver` + `bootstrap_seed` / `bootstrap_eh_impl`; daily Fabric Pipeline; send = **requests+SAS** |
| UDF Event Hub send | **requests+SAS** (HTTP timeout); Variable Library for CONN / Query URI / SPN |
| Seed ingest path | **`es_emt_arrives_silver`** (or KQL ingest) → table `silver_arrives`; never bronze / alerts ES |

---

## Implementation plan (ordered)

### P5.0 — Preconditions (Phase 4 leftovers)

Do not start catalogue cutover until these are true enough for dual-run:

- [ ] EH `silver_arrives` / `silver_alerts` / `gold_emt_stop_line` receiving live data
- [ ] Gold apply on a schedule (or reliable manual apply for smoke)
- [x] Repo: KQL/UDF do not filter on `emt_record` (verified 2026-07-29)
- [ ] Portal: inspect `es_emt_arrives_silver` → EH destination — note any `emt_record` filter; if present, plan allow-list for `silver_arrives_seed`

### P5.1 — Contract of the seed row (docs + constants)

- [x] Document allowed `emt_record` values: `bronze` · `silver_arrives` · **`silver_arrives_seed`** · `silver_alerts` · gold patches ([phase4-rti.md](./phase4-rti.md) §3)
- [x] Seed grain unchanged: one row per in-scope `(stop_id, line_id, direction_id)` with `bus_id` / `eta_seconds` / `destination` null; denorm + `catalog_loaded_at` + `day_type` + `map_ok=true`
- [x] `_rk` remains distinct from polls (`rti/lib/bootstrap_seed.py` + UDF `emit_seed_smoke_from_lh`)
- [x] Touch: [phase4-rti.md](./phase4-rti.md) Steps C–G; [ADR-040](./adr/ADR-040-eventhouse-catalogue-sot-seed-tag-and-kusto-udf-read.md); contract v4.5

### P5.2 — KQL defenses **before** writing seeds to EH

Ship query rules first so accidental seed ingest cannot wipe ETA.

- [x] `gold_arrives_stage`: `coalesce(emt_record,"") != "silver_arrives_seed"` before latest poll (`rti/kql/04`)
- [x] `freq_by_line_adr038`: explicit seed exclude (`rti/kql/05`)
- [x] `silver_arrives_catalogue_latest()` helper (`rti/kql/02`)
- [ ] Fabric: paste `02` → `05` → `04`, gold apply, ETA smoke ([phase4-rti.md](./phase4-rti.md) Step A)
- [ ] Optional: one hand seed row → confirm Gold ETA unchanged

**Exit:** Gold safe under seed-shaped rows even if bootstrap is not live yet.

### P5.3 — Eventstream / ingest path for seeds

- [ ] Default path: **`es_emt_arrives_silver`** same JSON mapping as poll silver → `silver_arrives` (column set identical)
- [ ] Alternate: KQL `.ingest` / queued ingest if ES batch size awkward for full morning seed
- [ ] Portal allow-list if filtered; if unfiltered, no ES change beyond sending new events
- [ ] Do **not** send seeds to `es_emt_arrives`, `es_emt_alerts`, or `es_emt_alerts_silver`
- [ ] UDF poll path: leave `emt_record: "silver_arrives"` unchanged in `udf_emt_ingest` / `arrives_expand`

**Exit:** A hand-sent seed JSON with `emt_record=silver_arrives_seed` appears in EH `silver_arrives`.

### P5.4 — Bootstrap writer → EH

Port Lakehouse `bootstrap_impl` behaviour without Spark-on-hot-path dependency:

- [x] Reuse logic: GTFS zip → geofence → S1 line_stops / calendar / labels → seed dicts (`rti/lib/bootstrap_seed.py`; LH SoT still `bootstrap_impl.py` for rollback)
- [x] Emit rows with **`emt_record: "silver_arrives_seed"`** + existing silver columns (`bus_lat`/`bus_lon` null OK)
- [x] **No** LH-style `DELETE WHERE bus_id IS NULL AND …` on EH (documented + code)
- [x] Notebook [`nb_bootstrap_eh_silver`](../notebooks/nb_bootstrap_eh_silver.py) + [`bootstrap_eh_impl`](../pipeline/orchestrator/bootstrap_eh_impl.py) (no Spark write to LH)
- [ ] Fabric: upload Files/python + run notebook smoke then full (Step D) — **portal pending**
- [ ] Bronze optional: line_stops/calendar raw can still go `bronze_emt_raw` via `es_emt_arrives` if useful for audit; GTFS zip still **not** Bronze ([ADR-017](adr/ADR-017-bronze-holds-rest-and-rt-payloads-only-gtfs-bootstraps-silve.md))

**Exit:** Morning-sized seed batch lands in EH; `count where emt_record=="silver_arrives_seed"` ≈ in-scope grains; `catalog_loaded_at` = run day.

### P5.5 — UDF catalogue read from Eventhouse

- [x] Repo: `_load_scope_and_catalogue_eh` via **Kusto REST** (`EH_QUERY_URI` + SPN in Variable Library); functions `poll_arrives_scope_eh` / `poll_alerts_scope_eh` (LH variants kept for dual-run)
- [x] Scope + denorm: **only** `emt_record == "silver_arrives_seed"` and `catalog_loaded_at == max(catalog_loaded_at)` (and `map_ok`)
- [x] Dual-run: Pipeline stays on `poll_*_scope` until Step E; then switch to `*_eh` (LH connection optional for rollback)
- [x] Mid-bootstrap: readers use `max(catalog_loaded_at)` — previous day until new batch completes; **do not** pause arrives ([phase4-rti.md](./phase4-rti.md) Step E)
- [ ] Fabric: VL (`EH_QUERY_URI` + SPN + ES CONN) + UDF paste (`requests` only; no `azure-eventhub`/`azure-identity`) + Pipeline → `poll_*_scope_eh` — **portal in progress**

**Exit:** Hot-path Pipeline calls `poll_*_scope_eh` with **no** Lakehouse catalogue read.

### P5.6 — Daily Fabric Pipeline

- [x] Guide: `pl_emt_bootstrap_daily` in [phase4-rti.md](./phase4-rti.md) Step F (schedule ~06:00–09:00 Madrid) — separate from arrives/alerts
- [ ] Fabric: create pipeline Notebook → Wait → optional gold apply — **portal pending** (notebook: **no `%pip`**; Spark runtime `requests`)
- [x] Arrives/alerts schedule **keeps running** through that window (documented Do-not #6)
- [ ] Alerts on bootstrap failure (pager/email) — stale catalogue is worse than overlapping writers

**Exit:** One unattended morning run while arrives is live; Gold ETA continuous; scope refreshes after seed visible.

### P5.7 — Cutover & rollback

- [x] Dual-run procedure documented ([phase4-rti.md](./phase4-rti.md) Steps E–G)
- [ ] Stop LH `nb_bootstrap_gtfs_silver` schedule when EH seeds trusted — **portal pending**
- [x] Rollback: re-enable LH bootstrap + `poll_*_scope`; Gold seed-exclude filters can stay (harmless)
- [x] Update [phase4-rti.md](./phase4-rti.md) Steps A–G; [agent-eventhouse-cutover-context.md](./agent-eventhouse-cutover-context.md) topology note
- [ ] [dfd-erd.md](./dfd-erd.md) topology refresh (optional polish)

---

## Status (checklist rollup)

- [ ] P5.0 Phase 4 EH hot path ready; portal `es_emt_arrives_silver` filter check
- [x] P5.0 repo audit: KQL/UDF ignore `emt_record` for logic
- [x] P5.1 Seed `emt_record` contract documented ([ADR-040](./adr/ADR-040-eventhouse-catalogue-sot-seed-tag-and-kusto-udf-read.md), contract v4.5)
- [ ] P5.2 KQL Gold/freq exclude `silver_arrives_seed` — **repo done**; Fabric paste + smoke pending
- [x] P5.2 repo: `02` catalogue helper + `04`/`05` seed exclude
- [ ] P5.3 `es_emt_arrives_silver` / ingest accepts seed tag into `silver_arrives` (Step B/C portal)
- [x] P5.4 Bootstrap writer → EH **repo done**; Fabric Step D pending
- [x] P5.5 UDF catalogue from EH **repo done**; Fabric Step E pending
- [ ] P5.6 Daily bootstrap pipeline (guide ready; Fabric Step F pending)
- [ ] P5.7 Cutover: stop LH schedule after dual-run trust (Step G)

---

## Target sketch

```text
Daily pl_emt_bootstrap_daily (~06–09 Europe/Madrid):
  bootstrap → es_emt_arrives_silver (or KQL ingest)
    → silver_arrives rows with emt_record=silver_arrives_seed

Hot path (existing ES):
  UDF reads catalogue FROM EH (seed tag + max catalog_loaded_at)
    → es_emt_arrives / es_emt_arrives_silver
    → es_emt_alerts / es_emt_alerts_silver
  KQL gold build: latest excludes silver_arrives_seed
  → gold_emt_stop_line → Agent / map
```

## Same table: override risk (summary)

Unprotected seed append with `datetime_polling=now` can steal Gold `max(datetime_polling)` → ETA null until next poll. **Mitigation = P5.2 + tagged seeds (P5.1/P5.4), not schedule isolation.**

Poll fact rows are **not** overwritten in place (different `_rk`). Concurrent arrives + bootstrap is the normal case.

## Concurrent with 24/7 arrives

| Pattern | Verdict |
|---------|---------|
| Pause arrives for bootstrap | **Rejected** — not operable |
| Separate daily *pipeline item* | **Yes** — ops isolation only |
| Tag + Gold exclude + catalogue max(date) | **Required** |
| LH broad DELETE of null-shaped rows | **Do not port to EH**; fix LH rollback if still used |

Mid-bootstrap: UDF may briefly see previous `catalog_loaded_at` until the new seed batch is fully queryable — acceptable.

---

# Final Architecture (aspirational)

```text
Fabric Pipeline (arrives/alerts)     Fabric Pipeline (daily)
  → UDF                                → bootstrap
  → es_emt_arrives                     → es_emt_arrives_silver
  → es_emt_arrives_silver                (emt_record=silver_arrives_seed)
  → es_emt_alerts
  → es_emt_alerts_silver
  → Eventhouse
       bronze_emt_raw
       silver_arrives   # polls + seeds (discriminated by emt_record)
       silver_alerts
       gold_emt_stop_line      # latest ignores seeds
  → (optional) Semantic Model
  → AI / Data Agent
```

Lakehouse remains rollback until Phase 4 Agent cutover **and** Phase 5 catalogue cutover are validated. After Phase 5, hot path needs **no** Lakehouse connection.

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

## Phase 5

- Catalogue SoT = EH `silver_arrives` seeds with `emt_record=silver_arrives_seed`
- Poll path still emits `emt_record=silver_arrives` unchanged
- UDF hot path runs **without** Lakehouse connection
- Morning bootstrap safe while arrives runs 24/7 (no pause)
- Gold ETA not cleared by seed append (KQL exclude verified **before** seed writer)
- Daily `pl_emt_bootstrap_daily`; existing arrives/alerts schedule keeps running
- LH daily bootstrap schedule stopped after cutover
