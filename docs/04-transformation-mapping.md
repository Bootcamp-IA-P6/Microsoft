# Transformation & Mapping Spec — Bronze → Silver → Gold

**Version:** 1.0  
**Last updated:** 2026-07-16  
**Status:** Active (Phase 2 MVP)  
**Audience:** Data Engineer, Analytics Engineer

---

## 1. Purpose of this document

This document defines **how raw origin data becomes lakehouse tables** — flatten rules, joins, casts, null handling, dedup order, latest-row selection, source priority, and lineage.

It does **not** define:

| Topic | See |
|---|---|
| Project scope / geofence | `docs/01-project-scope.md` |
| API/GTFS field meanings as origin truth | `docs/02-source-contract.md` |
| Final column types / PKs as storage contract | `docs/03-schema-contract.md` |
| Retry policy, alert thresholds, load SLA numbers | `docs/05-data-quality-operations.md` |
| Architecture Decision Records (ADR) | Deferred — `docs/ADR/` later if needed |

---

## 2. Pipeline overview

```
GTFS files (bootstrap)
        │
        ▼
silver_stops_dim / silver_lines_dim / silver_stop_lines
        │
EMT POST .../arrives/ ──► bronze_emt_raw ──► silver_arrival_observations
        │                                              │
        │                                              ▼
        └────────── last successful poll per stop ──► gold_stop_line_eta_latest
                         LEFT JOIN silver_stop_lines
```

| Notebook / job (MVP) | Responsibility |
|---|---|
| Ingest | API → `bronze_emt_raw` (append) |
| Bronze → Silver | Parse JSON, type, enrich with GTFS, dedup → `silver_arrival_observations`; maintain dims |
| Silver → Gold | Latest per stop+line via catalogue LEFT JOIN → `gold_stop_line_eta_latest` |

---

## 3. Normalisation rules (apply before/at silver)

| Rule | Action |
|---|---|
| **Trim** | `trim()` on `destination`, `Direction` / `direction_text`, `address`, and other padded API strings |
| **stop_id** | Cast API string/int → lakehouse `INT` |
| **bus_id** | Always persist as `STRING` (API may send int or string) |
| **eta_seconds** | Cast to `INT` when numeric; see §6 for null / `999999` |
| **Timestamps** | See §3.1 |
| **GeoJSON** | If used later: `coordinates[0]` = lon, `[1]` = lat — **not mapped into MVP silver/gold columns** |

### 3.1 Timezone rules (PoC)

| Field | Rule |
|---|---|
| `ingested_at` | Write as **UTC** (pipeline clock) |
| `datetime_polling` | Parse envelope `datetime` from `payload_json`. If the string has `Z` or an explicit offset → convert to UTC. If **naive** (no offset) → interpret as **Europe/Madrid** local time, then store as UTC |
| `updated_at` (gold) | Prefer last successful poll snapshot time (same UTC normalisation as `datetime_polling`); else job UTC time |
| Agent display | Format to Madrid local for users; **storage remains UTC** |

Do not mix naive Madrid and UTC in the same column without documenting the assumption above.

---

## 4. API → Bronze mapping

**Input:** one HTTP response from `POST .../stops/{stopId}/arrives/`  
**Output:** one row in `bronze_emt_raw`  
**Row generation:** 1 call → 1 bronze row (even if `Arrive` is empty)

| Bronze column | Source | Rule |
|---|---|---|
| `ingested_at` | Pipeline clock | UTC now at write |
| `endpoint` | Constant | `"arrives"` |
| `request_stop_id` | Path `{stopId}` | Cast to INT |
| `api_code` | Envelope `code` | As string |
| `api_description` | Envelope `description` | As string; null if missing |
| `payload_json` | Full response body | Serialize complete JSON; **no field drop** |

**Do not** flatten `Arrive` / `StopInfo` in bronze.

**Failed HTTP / non-JSON:** do not invent a bronze business row unless ops policy says to log failures separately (`05`). Successful empty snapshot (`code: "00"`, `Arrive: []`) **does** produce a bronze row.

---

## 5. Bronze → Silver — `silver_arrival_observations`

### 5.1 JSON flatten — row generation

| Input | Output rows |
|---|---|
| `payload_json` → `data[0].Arrive[]` with N elements | **N** silver observation rows |
| `Arrive: []` (valid empty snapshot) | **0** observation rows from that poll |
| Multiple objects in `data[]` (rare) | Flatten all `Arrive` arrays found under `data[*]` |

Each `Arrive` element becomes one candidate row, then normalised and enriched.

### 5.2 Field mapping

| Silver column | Origin path | Transform |
|---|---|---|
| `stop_id` | `Arrive.stop` (fallback: `request_stop_id`) | Cast → INT |
| `line_label` | `Arrive.line` | Trim; NOT NULL |
| `bus_id` | `Arrive.bus` | Cast → STRING |
| `destination` | `Arrive.destination` | Trim; NOT NULL |
| `eta_seconds` | `Arrive.estimateArrive` | See §6 |
| `datetime_polling` | Envelope `datetime` inside `payload_json` | Parse → TIMESTAMP |
| `ingested_at` | Bronze `ingested_at` | Pass-through |
| `line_id` | Enrichment — see §5.3 | NOT NULL after enrich |
| `_rk` | Computed | SHA256(`stop_id` + `line_id` + `bus_id` + `datetime_polling`) |

**Not mapped into MVP silver observations:** `DistanceBus`, bus `geometry` (available in API; out of MVP schema).

### 5.3 `line_id` enrichment (source priority)

`Arrive` does **not** carry internal `line_id`. Resolve in this order:

| Priority | Method | Join / match key |
|---|---|---|
| **1** | Same-response `StopInfo.lines[]` | Match `Arrive.line` = `lines[].label` → take `lines[].line` |
| **2** | `silver_stop_lines` | Match (`stop_id`, `line_label`) → `line_id` |
| **3** | `silver_lines_dim` | Match `line_label` → `line_id` (weaker if labels collide) |

If still unresolved after priority 1–3 → **quarantine** row (do not write to silver fact); log for ops (`05`). Do not invent `line_id`.

### 5.4 Dedup order

1. Build candidate rows for the poll.  
2. Compute `_rk`.  
3. If `_rk` already exists in `silver_arrival_observations` → **skip insert** (idempotent).  
4. Otherwise append.

### 5.5 Lineage (bronze ↔ silver)

| Approach | Rule |
|---|---|
| **MVP** | Trace via (`stop_id`, `datetime_polling` ≈ envelope datetime, `ingested_at`) back to bronze `payload_json` |
| **Optional later** | Add `bronze_row_id` / UUID on bronze and carry into silver — schema change in `03` |

---

## 6. NULL and sentinel handling (`eta_seconds`)

| Case | Action in silver |
|---|---|
| Missing `estimateArrive` | `eta_seconds = null` — **keep row** |
| Empty / non-numeric after cast fail | Quarantine or null per notebook policy; prefer quarantine if bus/line otherwise valid is ambiguous — default: **null + keep** if other keys OK |
| `estimateArrive = 999999` | Treat as **> 45 min** sentinel. MVP options: keep as `999999` **or** map to null with a flag — **decision TBD**; until decided, **persist `999999` as INT** and document in agent semantics that it means “far” |
| Null at terminus vs non-terminus | Interpreted in **gold** via `is_terminus` / `origin_stop_notice` (§8), not by dropping silver rows |

---

## 7. GTFS → Silver dimensions

### 7.1 `silver_stops_dim`

| Column | GTFS / rule |
|---|---|
| `stop_id` | `stops.stop_id` → INT |
| `stop_name` | `stops.stop_name` |
| `stop_lat` / `stop_lon` | `stops.stop_lat` / `stops.stop_lon` |
| `direction_text` | Optional enrich from first in-scope `StopInfo.Direction` (trim); else null |
| `in_scope` | Haversine/circle test vs Sol geofence (`01-project-scope.md`) |
| `catalog_loaded_at` | Load date |

**Update:** bootstrap full load; refresh replaces/merges on `stop_id`.

### 7.2 `silver_lines_dim`

| Column | GTFS / rule |
|---|---|
| `line_id` / `line_label` | From routes (and EMT naming conventions as in GTFS) |
| `name_a` / `name_b` | Route / trip headsign headers as available in GTFS |
| `in_scope` | `true` if ≥1 related stop has `in_scope = true` |
| `catalog_loaded_at` | Load date |

### 7.3 `silver_stop_lines`

| Column | Rule |
|---|---|
| `stop_id`, `line_id`, `line_label` | From GTFS trip/stop_times/routes graph |
| `direction_id` | GTFS `direction_id` (0/1) |
| `is_terminus` | `true` if any trip for that stop+line+direction has `stop_sequence = 1` |
| `catalog_loaded_at` | Load date |

**Join type for building graph:** inner joins across GTFS files as needed to produce the relationship set; orphan stops without trips may be omitted from `silver_stop_lines` but can still exist in `silver_stops_dim`.

---

## 8. Silver → Gold — `gold_stop_line_eta_latest`

### 8.1 Driver set

**Base:** catalogue rows for the stop from `silver_stop_lines` (distinct `stop_id`, `line_id`, `line_label`).

**Join type:** catalogue **LEFT JOIN** latest live ETA observations for that stop.

This preserves lines that serve the stop even when the poll returned no bus for that line.

### 8.2 Latest observation selection

For a given `stop_id` after a successful poll:

1. Take silver observations for that `stop_id` with `datetime_polling` equal to the **latest successful poll snapshot** for that stop (envelope datetime of the last good bronze arrives).  
2. Per `line_id` (or `line_label` if needed), pick the observation with **minimum `eta_seconds`** among non-null ETAs; if all null, keep a null ETA representative if any observation exists.  
3. If PO later chooses “all buses” grain (U02-2), this step changes — current contract grain is **one gold row per stop+line**.

### 8.3 Column derivation

| Gold column | Rule |
|---|---|
| `stop_id`, `line_id`, `line_label` | From catalogue side of LEFT JOIN |
| `destination` | From matched observation (trimmed). If no observation: catalogue header fallback — prefer `name_a` / `name_b` by known direction; if direction unknown use `name_a`; if still missing use **`""`**. Never SQL NULL (keeps `03` NOT NULL). |
| `eta_seconds` | From matched observation; **null** if no upcoming bus |
| `has_upcoming_bus` | `true` if matched observation has usable ETA (non-null; and not treated as absent); else `false` |
| `origin_stop_notice` | `true` if `is_terminus` for that stop+line(+direction) **and** ETA is null / uncertain; else `false` |
| `is_stale` | Computed from age of last successful poll vs interval rule — formula in `05`; gold stores the boolean |
| `updated_at` | Timestamp of gold rebuild (typically last successful poll datetime or job time — prefer poll snapshot time for consistency) |

### 8.4 Semantic matrix (must match frozen contract)

| Situation | Gold result |
|---|---|
| Line in catalogue + ETA in poll | Row with ETA; `has_upcoming_bus = true` |
| Line in catalogue + no ETA in poll | Row; `has_upcoming_bus = false`; `eta_seconds` null |
| Line not in catalogue | **No gold row** — agent rejects question |

### 8.5 Empty `Arrive[]` poll

| Step | Behaviour |
|---|---|
| Bronze | 1 row written (`payload_json` with empty `Arrive`) |
| Silver observations | 0 new observation rows |
| Gold | Still **rebuild** for that `stop_id` from catalogue LEFT JOIN → all serving lines get `has_upcoming_bus = false`, `updated_at` refreshed |

Gold must not depend on reading bronze JSON at query time; empty polls still advance freshness via rebuild.

### 8.6 Rebuild trigger

Gold for a stop is rebuilt **only from the last successful poll** for that stop (frozen rule). Failed polls do not move `updated_at` forward (`05` for failure definition).

---

## 9. Source conflict priority

| Conflict | Winner |
|---|---|
| Stop name GTFS vs `StopInfo.stopName` | **GTFS** for dim; API optional enrich only if GTFS missing |
| Stop coordinates | **GTFS** |
| Internal `line_id` | StopInfo match → else `silver_stop_lines` → else `silver_lines_dim` (§5.3) |
| Live ETA vs any static schedule | **API Arrive only** (no theoretical schedule in MVP) |
| Terminus detection | **GTFS** `stop_sequence = 1` only (not API `positionTypeBus`); see frozen contract §2 |

---

## 10. Missing fields & parse failures

| Event | Action |
|---|---|
| Required `Arrive` keys missing (`line`, `bus`, `stop`) | **Quarantine** — do not write silver observation |
| `line_id` unresolved | **Quarantine** (§5.3) |
| Malformed `payload_json` | Skip silver for that bronze row; flag in ops (`05`) |
| Partial `StopInfo` | Observations may still load via GTFS enrich; dim enrich optional |
| Unexpected extra JSON fields | Ignore (forward-compatible) |

**Quarantine store (PoC):** TBD table or log path; minimum is notebook error log + skip. Prefer not to silently drop without log.

---

## 11. Fields explicitly not transformed (MVP)

| API / concept | Reason |
|---|---|
| `DistanceBus`, bus GPS | Not in MVP schema / user stories |
| Incidents blocks | Request flag `N`; postponed tables |
| `positionTypeBus`, `isHead` | Not applicable in API v2 |
| Occupancy | Not provided |

---

## 12. Mapping quick reference (API → silver)

| API field | Silver target |
|---|---|
| Envelope `datetime` | `datetime_polling` |
| Envelope `code` / `description` | Bronze only (`api_code` / `api_description`) |
| `Arrive.line` | `line_label` |
| `Arrive.stop` | `stop_id` |
| `Arrive.bus` | `bus_id` |
| `Arrive.destination` | `destination` |
| `Arrive.estimateArrive` | `eta_seconds` |
| `StopInfo.lines[].line` | `line_id` (enrich) |
| `StopInfo.lines[].label` | Match key to `Arrive.line` |
| `StopInfo.Direction` | Optional → `silver_stops_dim.direction_text` |

---

## 13. Open items (do not block Phase 2 start)

| ID | Topic | Owner |
|---|---|---|
| T-1 | Persist `999999` vs map to null | Data Engineer + PO |
| T-3 | Quarantine table vs log-only | Data Engineer |
| T-4 | Carry `bronze_row_id` into silver | Optional enhancement |
| U02-2 | One gold row per line vs all vehicles | PO |

**Closed:** T-2 destination fallback — observation → `name_a`/`name_b` → `""` (see §8.3).

---

## 14. References

| Document | Role |
|---|---|
| `docs/02-source-contract.md` | Raw fields and quirks |
| `docs/03-schema-contract.md` | Target tables |
| `docs/05-data-quality-operations.md` | Stale formula, success/failure of polls |
| `docs/data-source-contract-v3.md` | Frozen §2–§4 business rules preserved here in English |
| `docs/api-response-reference.md` | JSON examples |
