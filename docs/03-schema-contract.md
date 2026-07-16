# Schema Contract — Bronze / Silver / Gold

**Version:** 1.1  
**Last updated:** 2026-07-16  
**Status:** Active  
**Source of truth for column lists:** frozen `docs/data-source-contract-v3.md` §6–§7  
**Language:** English translation of the PO schemas (no extra constraints beyond that document)

---

## 1. Purpose

What we **store**: table and column names, and only the types / restrictions that appear in the PO contract.

Not in this document: API payloads (`02`), transforms (`04`), freshness ops (`05`), project scope (`01`).

---

## 2. MVP tables (Phase 2)

| Layer | Tables |
|---|---|
| Bronze | `bronze_emt_raw` |
| Silver | `silver_arrival_observations`, `silver_stops_dim`, `silver_lines_dim`, `silver_stop_lines` |
| Gold | `gold_stop_line_eta_latest` |

Postponed (not built in Phase 2): §7.

---

## 3. Bronze — `bronze_emt_raw`

Raw response of `POST /v2/transport/busemtmad/stops/{stopId}/arrives/`, complete, without transformation.

| Field | Description |
|---|---|
| `ingested_at` | Ingestion timestamp |
| `endpoint` | Response type tag (`arrives`, `lines_info`, etc.) |
| `request_stop_id` | `stop_id` consulted |
| `api_code`, `api_description` | EMT status envelope |
| `payload_json` | Full raw JSON response |

*(PO contract lists fields and descriptions only — no types or nullability.)*

---

## 4. Silver — `silver_arrival_observations`

| Column | Type | Restriction | Description |
|---|---|---|---|
| `_rk` | STRING | PRIMARY KEY | SHA256 hash of `stop_id + line_id + bus_id + datetime_polling` for dedup |
| `stop_id` | INT | NOT NULL | Stop |
| `line_id` | STRING | NOT NULL | Line |
| `line_label` | STRING | NOT NULL | Line label for the user |
| `bus_id` | STRING | NOT NULL | Vehicle identifier |
| `destination` | STRING | NOT NULL | Destination header (used in D1) |
| `eta_seconds` | INT | NULLABLE | Estimated seconds — null allowed, **row is not discarded** |
| `datetime_polling` | TIMESTAMP | NOT NULL | Exact poll time |
| `ingested_at` | TIMESTAMP | NOT NULL | Ingestion time in Fabric |

---

## 5. Silver — `silver_stops_dim`

Static stop catalogue (GTFS bootstrap).

| Column | Type | Description |
|---|---|---|
| `stop_id` | INT | Unique identifier |
| `stop_name` | STRING | Stop name (e.g. "Mercado San Fernando") |
| `stop_lat` | DOUBLE | Latitude |
| `stop_lon` | DOUBLE | Longitude |
| `direction_text` | STRING | Street / direction (optional) |
| `in_scope` | BOOLEAN | `true` if inside the Sol/Gran Vía geofence |
| `catalog_loaded_at` | DATE | GTFS load date |

---

## 6. Silver — `silver_lines_dim`

Static line catalogue (GTFS).

| Column | Type | Description |
|---|---|---|
| `line_id` | STRING | Line code (e.g. "001") |
| `line_label` | STRING | Display label (e.g. "M1") |
| `name_a` | STRING | Destination direction A |
| `name_b` | STRING | Destination direction B |
| `in_scope` | BOOLEAN | `true` if at least one stop is inside the geofence |
| `catalog_loaded_at` | DATE | GTFS load date |

---

## 7. Silver — `silver_stop_lines`

Static line↔stop relationship + terminus flag (GTFS).

| Column | Type | Description |
|---|---|---|
| `stop_id` | INT | Stop |
| `line_id` | STRING | Line serving that stop |
| `line_label` | STRING | Line label |
| `is_terminus` | BOOLEAN | `true` if `stop_sequence = 1` in trips/stop_times (origin / header) |
| `direction_id` | INT | Direction (0 or 1 in GTFS) |
| `catalog_loaded_at` | DATE | GTFS load date |

---

## 8. Gold — `gold_stop_line_eta_latest`

Final view for agent queries (US-01, US-02, US-03).

| Column | Type | Restriction | Description |
|---|---|---|---|
| `stop_id` | INT | NOT NULL | Stop consulted |
| `line_id` | STRING | NOT NULL | Line |
| `line_label` | STRING | NOT NULL | Line label |
| `destination` | STRING | NOT NULL | Used for D1 match |
| `eta_seconds` | INT | NULLABLE | Live ETA — null if `has_upcoming_bus = false` |
| `has_upcoming_bus` | BOOLEAN | NOT NULL | Distinguishes “no bus now” vs “line does not serve stop” |
| `origin_stop_notice` | BOOLEAN | NOT NULL | `true` if stop is terminus and ETA is uncertain |
| `is_stale` | BOOLEAN | NOT NULL | `true` if last poll exceeds 3× normal interval |
| `updated_at` | TIMESTAMP | NOT NULL | Refresh timestamp |

### Business meaning (from PO §4)

| Situation | Result |
|---|---|
| Line in catalogue + ETA in poll | Show ETA |
| Line in catalogue + no ETA in poll | `has_upcoming_bus = false` |
| Line not in catalogue | Invalid question (line does not serve that stop) |

---

## 9. Postponed schemas (Phase 3+, not MVP)

Defined for reference; **not built in Phase 2**.

> **HU note:** PO v3 labels some of these “US-05”. In `docs/Historias de usuario.md`, **US-05 is the chat UI**. These tables are postponed incident / aggregate work, not that story.

### `silver_incidents` (postponed)

| Column | Type | Description |
|---|---|---|
| `line_id` | STRING | Affected line |
| `incident_guid` | STRING | Unique incident id |
| `title` | STRING | Title |
| `description` | STRING | Detail |
| `cause` | STRING | Cause class (e.g. "04 - Manifestación") |
| `effect` | STRING | Effect class (e.g. "05 - Desvío programado") |
| `valid_from` | TIMESTAMP | Start |
| `valid_to` | TIMESTAMP | End |
| `snapshot_ts` | TIMESTAMP | Poll timestamp |

### `gold_incident_line_current` (postponed)

| Column | Type | Description |
|---|---|---|
| `line_id` | STRING | Line |
| `incident_guid` | STRING | Incident id |
| `title` | STRING | Title |
| `cause`, `effect` | STRING | Classification |
| `is_active_now` | BOOLEAN | `true` if `now()` is between `valid_from` and `valid_to` |
| `snapshot_ts` | TIMESTAMP | Refresh timestamp |

### `gold_line_status_5m` (postponed — operational aggregates)

| Column | Type | Description |
|---|---|---|
| `window_start` | TIMESTAMP | Window start (e.g. 10:15:00) |
| `line_label` | STRING | Line |
| `observations` | INT | Row count in window |
| `avg_eta_seconds`, `p50_eta_seconds`, `p90_eta_seconds` | DOUBLE | ETA percentiles |
| `avg_deviation_min` | DOUBLE | Mean deviation vs theoretical schedule (if available) |

---

## 10. References

- `docs/data-source-contract-v3.md` §6–§7  
- `docs/01-project-scope.md` — geofence / MVP scope  
- `docs/04-transformation-mapping.md` — how rows are built  
- `docs/05-data-quality-operations.md` — stale / acceptance  
