# Phase 4 — Real-Time Intelligence (EMT Madrid)

**Branch:** `feat/fabric-phase4`  
**Contract:** [data-source-contract-v4.md](./data-source-contract-v4.md) **v4.4** (map coords on Gold/Silver)  
**Rollback:** Lakehouse Phase 0–3 (`pipeline/` + notebooks) until Agent cutover.

## Status (workspace progress)

| Step | Status |
|------|--------|
| UDF `udf-emt-ingest` + libraries (`requests`, `azure-eventhub`) | Done |
| UDF connections (`lhemtmadrid`, `varemtmadrid`) | Done |
| Eventstream CONNs filled; alerts + arrives smoke | Done (e.g. `bronze=1 silver=4 fails=0`) |
| Eventhouse tables from `rti/kql/01`–`04` | Done (paste) |
| Separate ES destinations so bronze ≠ silver schema mix | Confirm in your workspace |
| **Gold map coords** (`stop_lat/lon`, `bus_lat_1/2`, `bus_lon_1/2`) | **Repo ready — paste UDF + KQL `02`/`04`, then re-poll + gold apply** |
| Gold `.set-or-replace` on a schedule | **Next** |
| Full-scope arrives (all catalogue stops, batched) | **Next** |
| Pipeline schedule + dual-run / Agent rebind | Later |
| Lakehouse arrives/gold parity for map cols | Later (EH is Agent SoT) |
| Contract v4.4 column bump (docs) | Done |

Bootstrap / GTFS stays **Lakehouse daily** (not UDF).

---

## Topology

```text
Daily:  nb_bootstrap_gtfs_silver  →  Lakehouse silver_arrives (catalogue)
                                    └── UDF reads via SQL connection
                                        (includes stop_lat / stop_lon from GTFS)

Hot path:
  udf-emt-ingest
    poll_arrives_scope  → Eventstream(s) → bronze_emt_raw + silver_arrives
                          (silver adds bus_lat / bus_lon from Arrive.geometry)
    poll_alerts_scope   → Eventstream(s) → bronze_emt_raw + silver_alerts
  Eventhouse KQL
    gold_emt_stop_line_build → .set-or-replace gold_emt_stop_line
    (gold exposes stop_* + bus_*_1/2 for 3D map)
  → Data Agent / frontend map (after cutover)
```

Arrives must not clear `alert_*`; alerts must not clear ETA/freq (same ownership as Lakehouse MERGEs).

---

## Map coordinates (A + B)

Serving columns on Eventhouse `gold_emt_stop_line` (grain unchanged: `stop_id` × `line_id` × `direction_id`):

| Column | Source | Notes |
|--------|--------|-------|
| `stop_lat`, `stop_lon` | Silver catalogue (GTFS denorm via LH bootstrap → UDF expand) | Static-ish; same value on all rows of a stop |
| `bus_lat_1`, `bus_lon_1` | Arrive `geometry` for ETA slot 1 (`bus_id_1`) | Live; NULL if no bus / bad geometry |
| `bus_lat_2`, `bus_lon_2` | Arrive `geometry` for ETA slot 2 (`bus_id_2`) | Live; NULL if only one bus |

**API shape (verified live):** GeoJSON Point, `coordinates = [lon, lat]`.

```json
{ "type": "Point", "coordinates": [-3.70199, 40.40533] }
```

UDF/`rti/lib` parse: `bus_lon = coordinates[0]`, `bus_lat = coordinates[1]`. Do not swap.

Silver also stores per-bus `bus_lat` / `bus_lon` so KQL gold can rank by ETA and pick slots 1/2.

**Deploy order (EH only — skip Lakehouse for this):**

1. Paste updated [`rti/udf/udf_emt_ingest.py`](../rti/udf/udf_emt_ingest.py) into Fabric UDF and publish.  
2. Paste [`rti/kql/02_silver_arrives.kql`](../rti/kql/02_silver_arrives.kql) (adds `bus_lat`/`bus_lon` + JSON mapping).  
3. Paste [`rti/kql/04_gold_emt_stop_line.kql`](../rti/kql/04_gold_emt_stop_line.kql) (DDL + `gold_arrives_stage` / build).  
4. Run `poll_arrives_scope` (new silver rows carry bus coords; old rows stay NULL).  
5. `.set-or-replace gold_emt_stop_line <| gold_emt_stop_line_build(900)`

Smoke:

```kusto
gold_emt_stop_line
| where has_upcoming_bus
| project stop_id, line_id, stop_lat, stop_lon,
    bus_id_1, bus_lat_1, bus_lon_1, bus_id_2, bus_lat_2, bus_lon_2
| take 20
```

Expect Sol-area lat ≈ `40.41`, lon ≈ `-3.70`. If `bus_id_1` is set, `bus_lat_1` should usually be set too.

---

## Fabric object names

| Object | Name / note |
|--------|-------------|
| UDF | `udf-emt-ingest` |
| UDF Lakehouse SQL alias | `lhemtmadrid` (`@udf.connection` must match portal) |
| UDF Variable Library alias | `varemtmadrid` |
| Eventhouse / DB | `eh_emt_madrid` / `db_emt` (adjust if yours differ) |
| Tables | `bronze_emt_raw`, `silver_arrives`, `silver_alerts`, `gold_emt_stop_line` |
| Eventstreams | Prefer **separate** bronze vs silver streams (or filter by `emt_record`). Mixing silver JSON into `bronze_emt_raw` mapping → null columns. |

Paste target: [`rti/udf/udf_emt_ingest.py`](../rti/udf/udf_emt_ingest.py)  
KQL: [`rti/kql/`](../rti/kql/) (`01`…`06`)

---

## UDF functions (as in repo / Fabric)

| Function | Role |
|----------|------|
| `ping` | Runtime smoke (no Eventstream) |
| `poll_arrives_scope` | Catalogue scope from LH SQL → EMT arrives → bronze + silver (+ optional gold patch CONN) |
| `poll_alerts_scope` | GTFS-RT protobuf decode → bronze + silver_alerts |

### Parameters (`poll_arrives_scope`)

| Param | Use |
|-------|-----|
| `stopIdsCsv` | Empty = all catalogue `stop_id`s. Smoke: `"2711"` |
| `batchOffset` / `batchLimit` | Chunk full scope if UDF times out (e.g. limit 40) |
| `clientId` / `passKey` | Optional if Variable Library connection works |

### EMT arrives codes (important)

| `api_code` | Meaning | UDF |
|------------|---------|-----|
| `00` | OK with estimations | Success → bronze/silver |
| `01` | OK, **no estimations** (e.g. night) | Success → bronze (empty Arrive; silver may seed catalogue grains) |
| `80`–`90` (auth set) | Token / auth | Re-login + retry; else fail with `detail=[…]` |

Return example when healthy:

`scope_total=1 batch=1 offset=0 bronze=1 silver=4 gold_patches=4(local) fails=0`

`gold_patches=N(local)` means gold rows were computed in-process; they are only sent if `GOLD_PATCH_CONN` is set. Otherwise apply gold in Eventhouse (below).

### Lakehouse SQL quirks

- Portal Lakehouse connection → runtime type is **`FabricLakehouseClient`**. Use **`connectToSql()`**, not `.connect()` (that is for `FabricSqlConnection` only).
- Catalogue filter uses **`map_ok = 1`** (T-SQL/ODBC). Do not use `true`.
- Three-part SQL uses **Lakehouse item name** `LH_SQL_DB` (default `lh_emt_madrid`), **not** connection alias `lhemtmadrid`.

### Event Hub log noise

`Connection state changed: … OPENED … CLOSE` lines from `azure-eventhub` are **normal** for a successful send. Not an error by themselves.

---

## Repo map

| Path | Fabric? | Role |
|------|---------|------|
| `rti/udf/udf_emt_ingest.py` | Paste into UDF | Production poll + silver expand (incl. geometry → bus_lat/lon) |
| `rti/kql/01`–`06` | Paste into Eventhouse | DDL, gold build, freq notes, apply |
| `rti/lib/` | No | Spark-free ports (mirrored inside UDF) |
| `rti/ingest/` | No | Laptop JSONL only |
| `pipeline/` + `notebooks/` | Lakehouse | Bootstrap + rollback |

---

## What to do next

### 1. Deploy map-coords patch (if not already)

See **Map coordinates** deploy order above. Re-paste UDF + `02` + `04`, poll, gold apply.

### 2. Verify Eventhouse rows

```kusto
bronze_emt_raw
| where resource_kind == "arrives"
| take 5

silver_arrives
| where stop_id == "2711"
| project stop_id, bus_id, eta_seconds, bus_lat, bus_lon, stop_lat, stop_lon, datetime_polling
| take 10
```

If bronze columns are null again: Eventstream destination mapping / wrong table / silver mixed into bronze stream.  
If silver `bus_lat` stays null after a fresh poll: UDF not republished, or Eventstream still using old JSON mapping without `bus_lat`/`bus_lon`.

### 3. Gold (Eventhouse)

After silver has data, run once:

```kusto
// from rti/kql/04 + 06
.set-or-replace gold_emt_stop_line <| gold_emt_stop_line_build(900)
```

Then:

```kusto
gold_emt_stop_line | take 20
```

Wire this on a timer (Pipeline KQL activity) after arrives/alerts UDF steps.

### 4. Full-scope arrives

- Leave `stopIdsCsv` empty.
- If timeout: loop `batchOffset=0,40,80…` with `batchLimit=40`.
- Expect many `01` at night — still `fails=0` if treated as OK; ETA appears when buses run.

### 5. Pipeline sketch

```text
~1 min:  poll_arrives_scope (batches) → gold apply
~5 min:  poll_alerts_scope → gold apply
daily:   Lakehouse bootstrap (unchanged)
```

### 6. Cutover

1. Dual-run EH gold vs Lakehouse gold (ETA, `alert_active`, freq; map cols are EH-first).  
2. Rebind Agent → EH `gold_emt_stop_line`.  
3. Stop Spark arrives/alerts schedules; **keep bootstrap**.

---

## Lessons learned (ops)

1. UDF **Manage connections** must include Lakehouse + Variable Library; aliases must match code.  
2. Do **not** land silver-shaped events on a bronze-only JSON mapping (null columns).  
3. Alerts full protobuf in `payload` can be huge — prefer separate silver stream; watch EH column size limits.  
4. `from __future__ import annotations` breaks Fabric UDF IntelliSense/runtime annotation checks — do not use.  
5. Arrives `api=01 No estimations found` is not a credential bug.  
6. After adding silver columns, **re-apply** the JSON ingestion mapping (`silver_arrives_json`) or new fields never land.

---

## Out of scope / follow-ups

- Full ADR-038 freq in KQL (`05_freq_adr038.kql` — validate before trusting).  
- Semantic Model.  
- Moving bootstrap into Eventhouse.  
- Formal contract v4.x column list for map coords + Lakehouse arrives transform parity.  
- Using `StopInfo.geometry` instead of GTFS for stop coords (optional; catalogue already has stop_lat/lon).
