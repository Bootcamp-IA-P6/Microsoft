# Source Contract — EMT Madrid API & GTFS

**Version:** 1.2  
**Last updated:** 2026-07-17  
**Status:** Active  
**Sources:** PO `docs/data-source-contract-v3.md` (§1 catalogue URL, §10 request body, 250k limit); companion `docs/api-response-reference.md` for JSON shapes

### Changelog 1.1 → 1.2

| # | Change |
|---|---|
| 1 | §4 request body: removed `Text_LineInfoRequired_YN` — not in official EMT API docs ([apidocs.emtmadrid.es](https://apidocs.emtmadrid.es/)); introduced by mistake in internal scripts. Line metadata in `StopInfo.lines[]` is obtained via `Text_StopRequired_YN: "Y"`. |

---

## 1. Purpose

What **origin systems** provide (EMT API + GTFS): endpoints, auth, request body, response shape, field meaning.

Not in this document: lakehouse schemas (`03`), transforms (`04`), freshness SLA (`05`), product scope (`01`).

---

## 2. Origin systems (PO)

| System | Role |
|---|---|
| EMT OpenAPI | Live arrivals — `POST .../stops/{stopId}/arrives/` |
| GTFS (CRTM) | Static catalogue — https://datos.crtm.es/datasets/868df0e58fca47e79b942902dffd7da0/about |

**(agreed)** Daily call limit used in planning: **250,000** / day (login `apiCounter.dailyUse`).

---

## 3. Authentication

- `GET /v1/mobilitylabs/user/login/`
- Headers: `X-ClientId`, `passKey`
- Success codes: `00` or `01` (from observed API / `api-response-reference.md`)
- Returns `accessToken` for later calls

---

## 4. Primary live endpoint

`POST /v2/transport/busemtmad/stops/{stopId}/arrives/`  
Headers: `accessToken`, `Content-Type: application/json`

### Request body (PO §10 / agreed)

```json
{
  "cultureInfo": "es",
  "Text_StopRequired_YN": "Y",
  "Text_EstimationsRequired_YN": "Y",
  "Text_IncidencesRequired_YN": "N"
}
```

| Field | MVP value | Effect |
|---|---|---|
| `cultureInfo` | `"es"` | Language of texts |
| `Text_StopRequired_YN` | `"Y"` | Stop metadata in response |
| `Text_EstimationsRequired_YN` | `"Y"` | Arrival estimates (ETA) |
| `Text_IncidencesRequired_YN` | `"N"` | No incidents (out of MVP; PO §5) |

### Envelope

| Field | Meaning |
|---|---|
| `code` | Result code (`"00"` = success for arrives) |
| `description` | Server message |
| `datetime` | Server time when the response was generated (API snapshot time) |
| `data` | Payload array |

### `data[0]` blocks (from API reference)

| Block | Meaning |
|---|---|
| `Arrive` | Estimated arrivals; **`[]` = no buses on the way, not an error** when `code` is success |
| `StopInfo` | Stop metadata + `lines[]` when stop/line flags are `Y` |

Detail field lists and examples: `docs/api-response-reference.md` (keep in sync).  
PO does not require DistanceBus / bus GPS in lakehouse MVP tables (`03`).

### Fields not to use as source of truth

Per API docs / PO §2: `positionTypeBus` (and similar N/A fields) — terminus comes from GTFS instead.

---

## 5. GTFS files used (PO §2 / §9)

Minimum for MVP catalogue + terminus:

| File | Use |
|---|---|
| `stops.txt` | Stop id, name, coordinates |
| `routes.txt` (and related) | Line ids / labels |
| `trips.txt` | Trip ↔ route / direction |
| `stop_times.txt` | `stop_sequence = 1` → terminus / origin |

---

## 6. Auxiliary endpoint (not continuous ingest)

`GET /v2/transport/busemtmad/stops/arroundxy/{lon}/{lat}/{radius}/` — discovery / smoke tests only (`api-response-reference.md`). Not the bronze continuous path (PO: bronze = `arrives`).

---

## 7. References

- `docs/data-source-contract-v3.md`  
- `docs/api-response-reference.md`  
- `docs/01-project-scope.md`  
- `docs/03-schema-contract.md`  
