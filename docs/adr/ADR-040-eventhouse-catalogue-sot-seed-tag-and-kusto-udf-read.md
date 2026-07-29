# ADR-040: Eventhouse catalogue SoT — seed tag, Gold exclude, Kusto UDF read

- **Date:** 2026-07-29
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** `silver_arrives` (EH), Gold/freq KQL, UDF `udf-emt-ingest`, daily bootstrap notebook, Variable Library; contract **v4.5**; [phase4-rti.md](../phase4-rti.md) Phase 5

## 1. Context

Phase 4 moved the **hot path** (arrives/alerts poll → Eventstream → Eventhouse Gold) off Spark. Catalogue (scope stops + denorm grains) still lived on **Lakehouse** `silver_arrives` seeds, so the UDF kept a Lakehouse SQL connection solely for bootstrap rows. That left a dual-engine dependency: daily LH bootstrap write + UDF LH read, while polls already landed in Eventhouse.

Phase 5 goal: catalogue **SoT = Eventhouse** same physical table `silver_arrives` (no second catalogue table). Arrives stays 24/7; morning bootstrap always overlaps.

## 2. Alternatives Considered

- **A — Keep Lakehouse catalogue forever:** Zero migration; permanent dual SoT and LH connection on every poll.
- **B — New EH table `silver_catalogue`:** Cleaner separation; extra schema, ingest, and Agent surface.
- **C — Same EH `silver_arrives` + tagged seeds + query defenses:** One table; needs Gold/freq to ignore seeds and catalogue reads to use tag + `max(catalog_loaded_at)`.
- **D — Pause arrives during bootstrap:** Schedule isolation; **not operable** (arrives is continuous; bootstrap window always overlaps).
- **E — UDF catalogue via Eventhouse SQL / OneLake shortcut (`ehemtmadrid`):** Attractive if portal shortcut exists; blocked/unavailable in this workspace → use **Kusto REST** (`Query URI` + SPN) instead.

## 3. Decision

Adopt **C** + **E (Kusto REST)**. Reject **D**. Defer **B**.

Rules:

1. **Catalogue table:** Eventhouse `silver_arrives` only (same grain as poll facts). Lakehouse seeds remain rollback until cutover trust ([phase4-rti.md](../phase4-rti.md) Step G).
2. **Discriminator:** bootstrap / smoke seeds use **`emt_record = "silver_arrives_seed"`**. Live polls keep **`emt_record = "silver_arrives"`** (including empty Arrive[] heartbeats).
3. **Seed shape:** unchanged catalogue grain — one row per in-scope `(stop_id, line_id, direction_id)` with `bus_id` / `eta_seconds` / `destination` null; denorm + `catalog_loaded_at` + `day_type` + `map_ok=true`; distinct `_rk`.
4. **Ingest path for seeds:** **`es_emt_arrives_silver` only** (same silver mapping as poll silver). Never bronze or alerts Eventstreams.
5. **EH refresh:** append new `catalog_loaded_at`; **do not** port Lakehouse-style broad DELETE of null-shaped rows.
6. **Gold / freq:** exclude `emt_record == "silver_arrives_seed"` before `max(datetime_polling)` / headway observations (`rti/kql/04`, `05`). Required before large seed loads.
7. **Catalogue / scope read:** tagged seeds only + `catalog_loaded_at == max(catalog_loaded_at)` (+ `map_ok`) via helper `silver_arrives_catalogue_latest()` (`rti/kql/02`).
8. **UDF read path:** Kusto REST `POST {EH_QUERY_URI}/v1/rest/query` with Entra SPN from Variable Library (`FABRIC_TENANT_ID`, `FABRIC_SP_CLIENT_ID`, `FABRIC_SP_CLIENT_SECRET`). No Lakehouse shortcut required for cutover. Functions: `poll_*_scope_eh`; LH `poll_*_scope` kept for dual-run / rollback.
9. **Secrets / Eventstream SAS:** prefer Variable Library (`EH_QUERY_URI`, `ARRIVES_*_CONN`, …); UDF code constants may stay empty.
10. **Event Hub send (UDF + bootstrap notebook):** **`requests` + SAS** with HTTP timeout. Do **not** rely on `azure.eventhub` in Fabric UDF/notebook (hang / cold-start). Pipeline notebooks must **not** use `%pip` (disabled by default → `MagicUsageError`).
11. **Concurrency:** do **not** pause arrives for bootstrap; separate daily pipeline item (`pl_emt_bootstrap_daily`) for ops isolation only.
12. **Serving SoT:** Eventhouse Gold remains Agent/map SoT ([ADR-039](ADR-039-gold-exposes-stop-and-live-bus-coordinates-for-map.md)); catalogue SoT joins it on EH.

## 4. Consequences

- **Pros:** Single engine for poll + catalogue; no LH on hot path after cutover; seed tag is explicit and queryable; Gold protected under overlap.
- **Cons:** Extra Kusto + SPN latency vs LH SQL (~seconds); portal must allow-list seed `emt_record` if Eventstream filters polls only; Fabric cutover (pipelines, stop LH bootstrap schedule) is ops work beyond repo.
- **Ops guide:** [phase4-rti.md](../phase4-rti.md) Steps A–G; roadmap [refactoring-plan.md](../refactoring-plan.md) Phase 5.

## 5. Amended / Superseded by

- Extends [ADR-016](ADR-016-silver-is-append-only-poll-fact-wide-rows-not-polymorphic-re.md) (same table also holds tagged catalogue seeds on Eventhouse).
- Does not change Bronze GTFS rule ([ADR-017](ADR-017-bronze-holds-rest-and-rt-payloads-only-gtfs-bootstraps-silve.md)): GTFS still bootstraps Silver; target store for hot catalogue is Eventhouse.
- Does not change Gold grain or `alert_*` ownership ([ADR-015](ADR-015-medallion-physical-schema-one-bronze-one-silver-one-gold-tab.md), [ADR-027](ADR-027-alerts-denormalized-onto-gold-rows-at-line-grain-under-one-t.md)).
