# Transformation & Mapping Spec — Bronze → Silver → Gold

**Version:** 1.1  
**Last updated:** 2026-07-16  
**Status:** Active  
**Source:** PO `docs/data-source-contract-v3.md` §2, §4, §8 notebooks; conversation agreements marked **(agreed)**

---

## 1. Purpose

How origin data becomes the tables in `03`.

Not in this document: column lists as storage contract (`03`), API field catalogue (`02`), freshness SLA numbers (`05`), product scope (`01`).

---

## 2. Pipeline (PO §8)

```
GTFS bootstrap → silver_stops_dim, silver_lines_dim, silver_stop_lines
EMT arrives  → bronze_emt_raw → silver_arrival_observations
                                    ↓
              silver_stop_lines LEFT JOIN latest observations
                                    ↓
                         gold_stop_line_eta_latest
```

| Notebook | Responsibility (PO) |
|---|---|
| bronze → silver | Enrich with GTFS, dedup |
| silver → gold | Latest rows per stop, LEFT JOIN against `silver_stop_lines` |

---

## 3. Terminus / null ETA (PO §2)

- Cabecera / origin stop: GTFS `stop_times` with `stop_sequence = 1` → `is_terminus` on `silver_stop_lines`.
- Do **not** use API `position_type_bus` (not available in this API version).
- If `eta_seconds` is null on a **terminus** stop → `origin_stop_notice = true`.
- If `eta_seconds` is null on a **non-terminus** stop → real empty → `has_upcoming_bus = false`.

---

## 4. Catalogue vs live ETA (PO §4)

LEFT JOIN live observations to `silver_stop_lines`:

| Situation | Result |
|---|---|
| Line in catalogue + ETA in poll | Show ETA |
| Line in catalogue + no ETA in poll | `has_upcoming_bus = false` |
| Line not in catalogue | Invalid question |

---

## 5. API → bronze

- One `arrives` call → one `bronze_emt_raw` row.
- Store full JSON in `payload_json`; set `endpoint`, `request_stop_id`, `api_code`, `api_description`, `ingested_at` as in `03`.
- No flatten of business arrays in bronze.

**(agreed)** Empty `Arrive: []` with success code still writes a bronze row.

---

## 6. Bronze → `silver_arrival_observations`

- Flatten each element of `data[*].Arrive[]` to one observation row.
- **(agreed)** Empty `Arrive: []` → zero new observation rows for that poll.
- Map (see also `02`): `Arrive.line` → `line_label`; `Arrive.bus` → `bus_id`; `Arrive.destination` → `destination`; `Arrive.estimateArrive` → `eta_seconds`; envelope `datetime` → `datetime_polling`.
- Dedup via `_rk` = SHA256(`stop_id + line_id + bus_id + datetime_polling`) as in PO.
- `eta_seconds` null allowed; **do not discard** the row (PO).
- **`line_id`:** not on `Arrive`; resolve by matching `Arrive.line` to `StopInfo.lines[].label` in the same payload and/or join to `silver_stop_lines` / `silver_lines_dim` (implementation; required because PO marks `line_id` NOT NULL).

**(agreed)** Text: `trim()` on padded API strings (`destination`, etc.) before persist.  
**(agreed)** Timezone: store `ingested_at` in UTC; parse envelope `datetime` to UTC (if naive, treat as Europe/Madrid then convert).  
**(agreed)** MVP does not persist `DistanceBus` / bus GPS into silver/gold (not required by user stories; not in PO silver/gold columns).

---

## 7. GTFS → dims

- Bootstrap `silver_stops_dim`, `silver_lines_dim`, `silver_stop_lines` from GTFS (PO §8, §9).
- `in_scope` from geofence in `01` **(agreed: 600 m Sol circle)**.
- `is_terminus` from `stop_sequence = 1` (PO §2).

---

## 8. Silver → gold

- Rebuild per stop from **last successful poll** only (PO §3).
- Driver: lines serving the stop from `silver_stop_lines`; LEFT JOIN latest observations (PO §4 / §8).
- Fill `has_upcoming_bus`, `origin_stop_notice`, `is_stale`, `updated_at` per PO meanings; stale threshold in `05`.

**(agreed)** After a successful poll with empty `Arrive[]`, still rebuild gold so catalogue lines get `has_upcoming_bus = false` and `updated_at` advances.

**(agreed)** `destination` when no observation: use catalogue `name_a` / `name_b` if available; else `""` (keeps PO NOT NULL without inventing SQL NULL).

---

## 9. References

- `docs/data-source-contract-v3.md` §2, §4, §8  
- `docs/02-source-contract.md`  
- `docs/03-schema-contract.md`  
- `docs/05-data-quality-operations.md`  
