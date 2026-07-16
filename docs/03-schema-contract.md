# Schema Contract — Bronze / Silver / Gold

**Version:** 1.0  
**Last updated:** 2026-07-16  
**Status:** Active (MVP schemas for Phase 2)  
**Audience:** Data Engineer, Analytics Engineer, AI Developer

---

## 1. Purpose of this document

This document defines **what we store** — table names, columns, types, nullability, keys, grain, update mode, and examples.

It does **not** define:

| Topic | See |
|---|---|
| Project boundary, geofence, user stories | `docs/01-project-scope.md` |
| API/GTFS request-response and raw field meanings | `docs/02-source-contract.md` |
| Flatten, joins, cast, trim, row generation, lineage | `docs/04-transformation-mapping.md` |
| Freshness SLA thresholds, retries, alert policy | `docs/05-data-quality-operations.md` |
| Architecture Decision Records (ADR) | Deferred — `docs/ADR/` later if needed |

**Content source:** frozen `docs/data-source-contract-v3.md` §6–§7 (preserved; this file is the English schema home).

---

## 2. Layer summary

| Layer | Purpose | MVP tables |
|---|---|---|
| **Bronze** | Raw API responses, minimal columns around full JSON | `bronze_emt_raw` |
| **Silver** | Clean, typed observations + static dims | `silver_arrival_observations`, `silver_stops_dim`, `silver_lines_dim`, `silver_stop_lines` |
| **Gold** | Agent-ready latest state per stop+line | `gold_stop_line_eta_latest` |

**Postponed (Phase 3+, do not build in Phase 2):** `silver_incidents`, `gold_incident_line_current`, `gold_line_status_5m` — see §8.

---

## 3. Cross-cutting conventions

| Convention | Value |
|---|---|
| **Storage** | Microsoft Fabric Lakehouse (Delta tables) |
| **Timezone for timestamps** | Store pipeline and normalised snapshot times in **UTC**; see `04` §3.1 for parse rules |
| **`stop_id` type** | `INT` in lakehouse schemas (API may send string; cast in `04`) |
| **Schema evolution** | Additive columns allowed with `mergeSchema` / explicit migration; renames and type breaks require coordinated notebook/agent update + bump of this doc’s version |
| **Partitioning (PoC)** | TBD — not required for MVP volume; revisit if bronze grows large |
| **Retention (PoC)** | TBD — keep all bronze/silver history for demo unless storage forces pruning; gold is latest-state (overwrite/upsert) |

---

## 4. MVP — Bronze

### 4.1 `bronze_emt_raw`

**Grain:** one row = one successful or persisted API call response for a stop (typically one `arrives` poll).  
**Source endpoint:** `POST /v2/transport/busemtmad/stops/{stopId}/arrives/`  
**Update mode:** append  
**Dedup:** none at bronze (raw history); uniqueness not enforced  
**Primary key:** none (optional surrogate TBD)

| Column | Type | Nullable | Default | Description | Example |
|---|---|---|---|---|---|
| `ingested_at` | TIMESTAMP | NOT NULL | — | When the row was written to the lakehouse | `2026-07-15T10:19:33Z` |
| `endpoint` | STRING | NOT NULL | — | Origin tag | `"arrives"` |
| `request_stop_id` | INT | NOT NULL | — | Stop ID requested in the path | `4035` |
| `api_code` | STRING | NOT NULL | — | EMT envelope `code` | `"00"` |
| `api_description` | STRING | NULLABLE | — | EMT envelope `description` | `"Data recovered OK"` |
| `payload_json` | STRING | NOT NULL | — | Full raw JSON response (includes envelope `datetime` and `data`) | `{ "code":"00", "data":[...] }` |

**Allowed values:**

| Column | Allowed |
|---|---|
| `endpoint` | `"arrives"` for MVP continuous ingest; other tags reserved |
| `api_code` | Provider strings; `"00"` / `"01"` treated as success at login; `"00"` expected for successful arrives |

**Notes:**

- Envelope `datetime` is **inside** `payload_json` (not a separate bronze column in the frozen contract).
- No business flatten here.

---

## 5. MVP — Silver

### 5.1 `silver_arrival_observations`

**Grain:** one row = one vehicle observation at one stop at one poll snapshot.  
**Update mode:** append (history of observations)  
**Primary key:** `_rk`  
**Dedup key:** `_rk` = SHA256(`stop_id` + `line_id` + `bus_id` + `datetime_polling`)  
**Unique:** `_rk` unique

| Column | Type | Nullable | Default | Description | Example |
|---|---|---|---|---|---|
| `_rk` | STRING | NOT NULL | — | PK hash for dedup | `a3f1…` |
| `stop_id` | INT | NOT NULL | — | Stop | `4035` |
| `line_id` | STRING | NOT NULL | — | Internal line id | `"601"` |
| `line_label` | STRING | NOT NULL | — | Public line label for users | `"M1"` |
| `bus_id` | STRING | NOT NULL | — | Vehicle identifier | `"9010"` |
| `destination` | STRING | NOT NULL | — | Destination header (D1). Always non-null after transform; empty string `""` allowed when no live text and no catalogue header | `"SOL SEVILLA"` |
| `eta_seconds` | INT | NULLABLE | — | Estimated seconds; **null allowed — row not discarded** | `524` |
| `datetime_polling` | TIMESTAMP | NOT NULL | — | Poll / snapshot time for this observation | `2026-07-15T09:53:12Z` |
| `ingested_at` | TIMESTAMP | NOT NULL | — | Lakehouse ingest time | `2026-07-15T09:53:13Z` |

**Allowed values / constraints:**

| Column | Rule |
|---|---|
| `eta_seconds` | Null permitted; if present, non-negative integer (sentinel handling → `04`) |
| `line_label` | Non-empty after normalisation |

---

### 5.2 `silver_stops_dim`

**Grain:** one row = one stop in the catalogue.  
**Source:** GTFS bootstrap (+ optional enrich).  
**Update mode:** full/partial reload on catalogue refresh (overwrite or merge by `stop_id`)  
**Primary key:** `stop_id`  
**Unique:** `stop_id`

| Column | Type | Nullable | Default | Description | Example |
|---|---|---|---|---|---|
| `stop_id` | INT | NOT NULL | — | Unique stop id | `4035` |
| `stop_name` | STRING | NULLABLE | — | Stop name | `"Mercado San Fernando"` |
| `stop_lat` | DOUBLE | NULLABLE | — | Latitude WGS84 | `40.407557` |
| `stop_lon` | DOUBLE | NULLABLE | — | Longitude WGS84 | `-3.703891` |
| `direction_text` | STRING | NULLABLE | — | Street reference (optional) | `"Embajadores frente al Nº 60"` |
| `in_scope` | BOOLEAN | NOT NULL | — | Inside Sol 600 m geofence | `true` |
| `catalog_loaded_at` | DATE | NOT NULL | — | GTFS load date | `2026-07-15` |

---

### 5.3 `silver_lines_dim`

**Grain:** one row = one line.  
**Source:** GTFS.  
**Update mode:** reload/merge on catalogue refresh  
**Primary key:** `line_id`  
**Unique:** `line_id`

| Column | Type | Nullable | Default | Description | Example |
|---|---|---|---|---|---|
| `line_id` | STRING | NOT NULL | — | Internal line code | `"601"` |
| `line_label` | STRING | NOT NULL | — | Public label | `"M1"` |
| `name_a` | STRING | NULLABLE | — | Header direction A | `"SOL SEVILLA"` |
| `name_b` | STRING | NULLABLE | — | Header direction B | `"EMBAJADORES"` |
| `in_scope` | BOOLEAN | NOT NULL | — | `true` if at least one stop is in geofence | `true` |
| `catalog_loaded_at` | DATE | NOT NULL | — | GTFS load date | `2026-07-15` |

---

### 5.4 `silver_stop_lines`

**Grain:** one row = one (stop, line, direction) service relationship (+ terminus flag).  
**Source:** GTFS (`trips` / `stop_times`).  
**Update mode:** reload/merge on catalogue refresh  
**Primary key:** composite — (`stop_id`, `line_id`, `direction_id`)  
**Unique:** same composite

| Column | Type | Nullable | Default | Description | Example |
|---|---|---|---|---|---|
| `stop_id` | INT | NOT NULL | — | Stop | `4035` |
| `line_id` | STRING | NOT NULL | — | Line serving the stop | `"601"` |
| `line_label` | STRING | NOT NULL | — | Public label | `"M1"` |
| `is_terminus` | BOOLEAN | NOT NULL | — | `true` if `stop_sequence = 1` for that trip direction | `false` |
| `direction_id` | INT | NOT NULL | — | GTFS direction `0` or `1` | `0` |
| `catalog_loaded_at` | DATE | NOT NULL | — | GTFS load date | `2026-07-15` |

**Allowed values:**

| Column | Allowed |
|---|---|
| `direction_id` | `0`, `1` (GTFS) |
| `is_terminus` | `true` / `false` |

---

## 6. MVP — Gold

### 6.1 `gold_stop_line_eta_latest`

**Grain:** one row = latest agent-facing state for a **(stop_id, line_id)** pair that serves the stop (from catalogue).  
**Consumers:** agent / US-01, US-02 (and stop resolution via dims for US-03).  
**Update mode:** upsert / rebuild from last successful poll per stop (see `04` / `05`)  
**Primary key:** (`stop_id`, `line_id`)  
**Unique:** (`stop_id`, `line_id`)

| Column | Type | Nullable | Default | Description | Example |
|---|---|---|---|---|---|
| `stop_id` | INT | NOT NULL | — | Queried stop | `4035` |
| `line_id` | STRING | NOT NULL | — | Line | `"601"` |
| `line_label` | STRING | NOT NULL | — | Public label | `"M1"` |
| `destination` | STRING | NOT NULL | — | For D1 destination match. Always non-null; may be `""` if no observation and no catalogue header fallback | `"SOL SEVILLA"` |
| `eta_seconds` | INT | NULLABLE | — | Live ETA; null when `has_upcoming_bus = false` | `184` |
| `has_upcoming_bus` | BOOLEAN | NOT NULL | — | Distinguishes “no bus now” vs “line does not serve stop” | `true` |
| `origin_stop_notice` | BOOLEAN | NOT NULL | — | `true` if stop is terminus and ETA is uncertain | `false` |
| `is_stale` | BOOLEAN | NOT NULL | — | `true` if last successful poll exceeds freshness rule | `false` |
| `updated_at` | TIMESTAMP | NOT NULL | — | When this gold row was last refreshed | `2026-07-15T09:53:12Z` |

**Semantics (schema-level only):**

| Situation | Expected shape |
|---|---|
| Line in catalogue + ETA present | `has_upcoming_bus = true`, `eta_seconds` set |
| Line in catalogue + no ETA in last poll | `has_upcoming_bus = false`, `eta_seconds` null |
| Line not in catalogue for stop | **No gold row** — invalid question at agent layer |

How rows are produced (LEFT JOIN, empty `Arrive`, etc.) → `04-transformation-mapping.md`.  
Numeric thresholds for `is_stale` → `05-data-quality-operations.md`.

**Open product grain (tracked, not changed here):** whether gold keeps only the next bus per line or multiple vehicles — PO decision (U02-2). Current frozen contract grain is **per stop+line**.

---

## 7. Table inventory (MVP)

| Table | Layer | PK | Update mode | Build in Phase 2? |
|---|---|---|---|---|
| `bronze_emt_raw` | Bronze | — | append | Yes |
| `silver_arrival_observations` | Silver | `_rk` | append | Yes |
| `silver_stops_dim` | Silver | `stop_id` | reload/merge | Yes |
| `silver_lines_dim` | Silver | `line_id` | reload/merge | Yes |
| `silver_stop_lines` | Silver | (`stop_id`,`line_id`,`direction_id`) | reload/merge | Yes |
| `gold_stop_line_eta_latest` | Gold | (`stop_id`,`line_id`) | upsert/rebuild | Yes |

---

## 8. POSTPONED schemas (Phase 3+ — do not build in Phase 2)

Defined for reference only. Activation depends on product stories / ops need.

### 8.1 `silver_incidents` (POSTPONED — Phase 3+; incidents / delay causes — **not** HU US-05)

HU **US-05** is the chat UI (`docs/Historias de usuario.md`). Incident tables are postponed product scope, not that story.

| Column | Type | Nullable | Description | Example |
|---|---|---|---|---|
| `line_id` | STRING | NOT NULL | Affected line | `"601"` |
| `incident_guid` | STRING | NOT NULL | Unique incident id | `"…"` |
| `title` | STRING | NULLABLE | Title | `"Desvío…"` |
| `description` | STRING | NULLABLE | Detail | `"…"` |
| `cause` | STRING | NULLABLE | Cause class | `"04 - Manifestación"` |
| `effect` | STRING | NULLABLE | Effect class | `"05 - Desvío programado"` |
| `valid_from` | TIMESTAMP | NULLABLE | Start | — |
| `valid_to` | TIMESTAMP | NULLABLE | End | — |
| `snapshot_ts` | TIMESTAMP | NOT NULL | Poll time | — |

**PK (proposed):** (`incident_guid`, `snapshot_ts`) — TBD at activation.

### 8.2 `gold_incident_line_current` (POSTPONED — Phase 3+; not HU US-05)

| Column | Type | Nullable | Description |
|---|---|---|---|
| `line_id` | STRING | NOT NULL | Line |
| `incident_guid` | STRING | NOT NULL | Incident id |
| `title` | STRING | NULLABLE | Title |
| `cause` | STRING | NULLABLE | Cause |
| `effect` | STRING | NULLABLE | Effect |
| `is_active_now` | BOOLEAN | NOT NULL | `true` if now ∈ [`valid_from`, `valid_to`] |
| `snapshot_ts` | TIMESTAMP | NOT NULL | Refresh time |

### 8.3 `gold_line_status_5m` (POSTPONED — operational aggregates)

| Column | Type | Nullable | Description |
|---|---|---|---|
| `window_start` | TIMESTAMP | NOT NULL | Window start (e.g. 10:15:00) |
| `line_label` | STRING | NOT NULL | Line label |
| `observations` | INT | NOT NULL | Rows in window |
| `avg_eta_seconds` | DOUBLE | NULLABLE | Mean ETA |
| `p50_eta_seconds` | DOUBLE | NULLABLE | p50 ETA |
| `p90_eta_seconds` | DOUBLE | NULLABLE | p90 ETA |
| `avg_deviation_min` | DOUBLE | NULLABLE | Mean deviation vs theoretical (if available) |

---

## 9. Schema change rules

1. **Additive** nullable columns: allowed; document in changelog of this file.  
2. **Tightening nullability** or **type changes**: breaking — require coordinated notebook/agent update + version bump of this doc.  
3. **Renames / drops**: breaking — same as (2).  
4. **Postponed tables** move to MVP only via explicit scope change in `01-project-scope.md` and checklist update here.  
5. Frozen legacy text remains in `docs/data-source-contract-v3.md` until the team retires it; **`docs/03` wins** for new work if they diverge. Formal ADRs under `docs/ADR/` are optional/deferred.

---

## 10. References

| Document | Role |
|---|---|
| `docs/data-source-contract-v3.md` | Frozen Phase 1 monolith (source of these schemas) |
| `docs/02-source-contract.md` | Origin of fields |
| `docs/04-transformation-mapping.md` | How tables are populated |
| `docs/05-data-quality-operations.md` | Stale thresholds, load success criteria |
| `docs/01-project-scope.md` | MVP vs postponed product scope |
