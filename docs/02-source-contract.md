# Source Contract — EMT Madrid API & GTFS

**Version:** 1.0  
**Last updated:** 2026-07-16  
**Status:** Active  
**Audience:** Data Engineer, Analytics Engineer

---

## 1. Purpose of this document

This document defines **what origin systems provide** — endpoints, auth, request/response shapes, field meanings, GTFS files, and which raw fields are the origin of which business concepts.

It does **not** define:

| Topic | See |
|---|---|
| Project boundary, geofence, user stories | `docs/01-project-scope.md` |
| Lakehouse table/column schemas | `docs/03-schema-contract.md` |
| Flatten, joins, cast, trim, dedup, lineage | `docs/04-transformation-mapping.md` |
| Freshness SLA, retries, stale, load success | `docs/05-data-quality-operations.md` |
| Architecture Decision Records (ADR) | Deferred — add under `docs/ADR/` later if needed |

**Companion (unchanged):** detailed Spanish JSON samples and smoke-test notes live in `docs/api-response-reference.md`. This file (`02`) is the English **source of truth** for PoC ingest design; keep both aligned when the API behaviour changes.

---

## 2. Origin systems overview

| System | Role | Trust level | Refresh pattern |
|---|---|---|---|
| **EMT Madrid OpenAPI** | Live bus ETAs at a stop | Operational real-time | Continuous poll of in-scope stops |
| **EMT GTFS (CRTM)** | Static stop/line catalogue and stop↔line graph | Static reference | Bootstrap load; optional periodic refresh |

Live ingest does **not** replace the GTFS catalogue. GTFS answers “which lines serve this stop / what is the stop name?”; the API answers “what is arriving now?”.

---

## 3. EMT Madrid OpenAPI

### 3.1 Platform

| Item | Value |
|---|---|
| **Base URL** | `https://openapi.emtmadrid.es` |
| **Official docs** | [apidocs.emtmadrid.es](https://apidocs.emtmadrid.es/) |
| **API family used** | Bus EMT Madrid (`busemtmad`) — v1 login, v2 transport |
| **Credentials** | App registration at [mobilitylabs.emtmadrid.es](https://mobilitylabs.emtmadrid.es) — `EMT_CLIENT_ID` + `EMT_MADRID_PASS_KEY` |
| **Daily quota (verified)** | **250,000** calls/day (`apiCounter.dailyUse` on login) |

### 3.2 Endpoints in PoC scope

| Endpoint | Method | Role in PoC |
|---|---|---|
| `/v1/mobilitylabs/user/login/` | `GET` | Obtain `accessToken` |
| `/v2/transport/busemtmad/stops/{stopId}/arrives/` | `POST` | **Primary live source** — ETA snapshot per stop |
| `/v2/transport/busemtmad/stops/arroundxy/{lon}/{lat}/{radius}/` | `GET` | **Auxiliary** — discover nearby `stopId` (smoke tests / tooling); not the continuous ingest path |

### 3.3 Call cadence and limits

| Item | PoC value | Notes |
|---|---|---|
| **Planned poll interval** | ~60 s per in-scope stop | Operational enforcement → `05-data-quality-operations.md` |
| **Quota** | 250,000 calls/day | Shared across login + arrives (+ occasional arroundxy) |
| **Stops polled** | In-scope only (geofence in `01-project-scope.md`) | Full network is **not** polled |

---

## 4. Authentication — `GET /v1/mobilitylabs/user/login/`

### 4.1 Request

| Part | Value |
|---|---|
| **Path** | `/v1/mobilitylabs/user/login/` |
| **Headers** | `X-ClientId: <EMT_CLIENT_ID>`, `passKey: <EMT_MADRID_PASS_KEY>` |
| **Body** | None |

### 4.2 Success response

Success codes: **`00`** or **`01`** (`01` often means token extended / control-cache).

```json
{
  "code": "01",
  "description": "Token extend  into control-cache Data recovered OK",
  "datetime": "2026-07-15T09:53:12.086825",
  "data": [
    {
      "accessToken": "eyJ...",
      "apiCounter": {
        "current": 2358,
        "dailyUse": 250000
      }
    }
  ]
}
```

| Field | Type | Nullable | Meaning |
|---|---|---|---|
| `code` | string | no | Result code |
| `description` | string | no | Human-readable server message |
| `datetime` | string (ISO) | no | Server time when the response was generated |
| `data[0].accessToken` | string | no | Session token for subsequent calls (header `accessToken`) |
| `data[0].apiCounter.current` | integer | yes | Calls consumed today |
| `data[0].apiCounter.dailyUse` | integer | yes | Daily call limit for the app |

### 4.3 Error response (shape)

Non-success `code` (not `00`/`01`) or HTTP error. Envelope still uses `code` / `description` / `datetime` / `data` when JSON is returned. Exact error code catalogue is provider-defined; treat any non-`00`/`01` login as **failed auth**.

---

## 5. Primary live endpoint — `POST .../stops/{stopId}/arrives/`

### 5.1 Request

| Part | Value |
|---|---|
| **Path** | `/v2/transport/busemtmad/stops/{stopId}/arrives/` |
| **Path parameter** | `stopId` — EMT stop identifier (string in path, e.g. `4035`) |
| **Headers** | `accessToken: <token>`, `Content-Type: application/json` |

**MVP request body (frozen):**

```json
{
  "cultureInfo": "es",
  "Text_StopRequired_YN": "Y",
  "Text_EstimationsRequired_YN": "Y",
  "Text_LineInfoRequired_YN": "Y",
  "Text_IncidencesRequired_YN": "N"
}
```

| Field | Type | MVP value | Effect on response |
|---|---|---|---|
| `cultureInfo` | string | `"es"` | Language of texts |
| `Text_StopRequired_YN` | string | `"Y"` | Includes `StopInfo[]` |
| `Text_EstimationsRequired_YN` | string | `"Y"` | Includes `Arrive[]` |
| `Text_LineInfoRequired_YN` | string | `"Y"` | Line metadata inside `StopInfo.lines[]` |
| `Text_IncidencesRequired_YN` | string | `"N"` | No incident block (out of MVP scope) |

### 5.2 Common envelope

| Field | Type | Nullable | Meaning |
|---|---|---|---|
| `code` | string | no | `"00"` = success; other values = failure / non-OK |
| `description` | string | no | Server message (may include elapsed ms) |
| `datetime` | string (ISO) | no | **API snapshot time** — when the server generated this response (not our ingest clock) |
| `data` | array | no | Payload; usually one element for this endpoint |

**Timestamp basis:** envelope `datetime` is the EMT server instant for this snapshot. It is the origin of “when was this ETA calculated?”. Client poll start time and lakehouse `ingested_at` are **not** this field (those are pipeline times — see `03` / `04`).

### 5.3 Success response example

Full sample: `samples/04_arrives_stop_4035.json` (when present in repo).

```json
{
  "code": "00",
  "description": " Data recovered OK  (lapsed: 436 millsecs)",
  "datetime": "2026-07-15T09:53:12.732050",
  "data": [
    {
      "Arrive": [
        {
          "line": "M1",
          "stop": "4035",
          "bus": 9010,
          "destination": "SOL SEVILLA",
          "estimateArrive": 524,
          "DistanceBus": 457,
          "geometry": {
            "type": "Point",
            "coordinates": [-3.70046, 40.40782]
          }
        }
      ],
      "StopInfo": [
        {
          "stopId": "4035",
          "stopName": "Mercado San Fernando",
          "Direction": "Embajadores frente al Nº 60                            ",
          "geometry": {
            "type": "Point",
            "coordinates": [-3.70389, 40.40756]
          },
          "lines": [
            {
              "line": "601",
              "label": "M1",
              "nameA": "SOL SEVILLA",
              "nameB": "EMBAJADORES",
              "metersFromHeader": 273,
              "to": "A",
              "color": "0072ce"
            }
          ]
        }
      ]
    }
  ]
}
```

### 5.4 Array structure of `data[0]`

| Block | Type | When present | Meaning |
|---|---|---|---|
| `Arrive` | array of objects | If estimations requested | One object ≈ one vehicle approaching the stop |
| `StopInfo` | array of objects | If stop info requested | Stop metadata + lines serving the stop |

**Important:** A successful call (`code: "00"`) with **`Arrive: []`** is a **valid empty snapshot** (no buses currently estimated) — not an API error.

### 5.5 `Arrive[]` fields

| Field | Type (as observed) | Nullable | Meaning |
|---|---|---|---|
| `line` | string | no* | Public line label (what users see on the panel), e.g. `"M1"` |
| `stop` | string | no* | Stop ID where arrival is estimated |
| `bus` | integer \| string | no* | Vehicle identifier |
| `destination` | string | no* | Destination / direction header text (may have trailing spaces) |
| `estimateArrive` | integer \| string | yes / sentinel | Seconds until estimated arrival. **`999999`** = EMT convention for ETA &gt; ~45 minutes |
| `DistanceBus` | integer | yes | Metres remaining to the stop post |
| `geometry.type` | string | yes | GeoJSON type (`"Point"`) |
| `geometry.coordinates[0]` | number | yes | Bus longitude (WGS84) |
| `geometry.coordinates[1]` | number | yes | Bus latitude (WGS84) |

\*Typically present when the element exists; absences are rare and are handled in transformation (`04`).

**GeoJSON order:** always `[longitude, latitude]`.

**Fields documented by EMT as not applying to this API version (do not use as source of truth):** `positionTypeBus`, `isHead`.

### 5.6 `StopInfo[]` fields

| Field | Type | Nullable | Meaning |
|---|---|---|---|
| `stopId` | string | no* | Stop ID |
| `stopName` | string | yes | Stop display name |
| `Direction` | string | yes | Street reference (often padded with trailing spaces) |
| `geometry.type` | string | yes | GeoJSON type of the post |
| `geometry.coordinates[0]` | number | yes | Stop longitude |
| `geometry.coordinates[1]` | number | yes | Stop latitude |
| `lines` | array | yes | Lines that stop at this post |

#### `StopInfo[].lines[]`

| Field | Type | Nullable | Meaning |
|---|---|---|---|
| `line` | string | no* | **Internal** EMT line ID, e.g. `"601"` |
| `label` | string | no* | Public label; aligns with `Arrive[].line`, e.g. `"M1"` |
| `nameA` | string | yes | Header name for direction A |
| `nameB` | string | yes | Header name for direction B |
| `metersFromHeader` | integer | yes | Metres from header in this direction |
| `to` | string | yes | Direction at this stop (`"A"` or `"B"`) |
| `color` | string | yes | Line colour hex without `#` |

### 5.7 Error / non-OK response

| Situation | Typical signal |
|---|---|
| Auth expired / invalid | HTTP 401/403 or non-`00` `code` |
| Bad stop / bad request | Non-`00` `code` + description |
| Transport / timeout | No usable JSON envelope |

Exact error code table is provider-owned. For ingest, any response that is not a successful `arrives` snapshot must be treated as a **failed poll** (policy in `05`).

---

## 6. Auxiliary endpoint — `GET .../stops/arroundxy/{lon}/{lat}/{radius}/`

Used for discovery / smoke tests near a GPS point. **Not** the continuous bronze ingest path.

| Part | Value |
|---|---|
| **Path** | `/v2/transport/busemtmad/stops/arroundxy/{lon}/{lat}/{radius}/` |
| **Path parameters** | `lon`, `lat` (WGS84), `radius` (metres) |
| **Headers** | `accessToken` |

| Field | Type | Notes |
|---|---|---|
| `stopId` | integer | Same concept as string `stop` / `stopId` elsewhere — type differs by endpoint |
| `stopName` | string | Stop name |
| `address` | string | Street reference (may be padded) |
| `metersToPoint` | integer | Distance to query point |
| `geometry` | Point | Post location |
| `lines[]` | array | Similar to `StopInfo.lines` (subset of fields) |

---

## 7. Observed source quirks (API facts)

These are **properties of the origin**, not lakehouse rules. How we normalise them belongs in `04-transformation-mapping.md`.

| Quirk | Observation |
|---|---|
| Mixed numeric types | `bus`, `estimateArrive` may arrive as integer **or** string |
| Mixed stop ID types | `stopId` is integer in `arroundxy`, string in `arrives` / `StopInfo` |
| Padded text | `destination`, `Direction`, `address` often have trailing spaces |
| Long ETA sentinel | `estimateArrive = 999999` means &gt; ~45 min, not a literal 999999-second wait |
| Empty arrivals | `Arrive: []` + `code: "00"` = no buses on the way |
| Unused / N/A fields | `positionTypeBus`, `isHead` marked “No apply for this version” |

---

## 8. GTFS — static catalogue source

### 8.1 Origin

| Item | Value |
|---|---|
| **Dataset** | EMT / CRTM GTFS |
| **URL** | https://datos.crtm.es/datasets/868df0e58fca47e79b942902dffd7da0/about |
| **Role** | Bootstrap stop names, coordinates, line headers, stop↔line relationships, terminus detection |
| **Coverage** | Full EMT network for catalogue; live poll still limited to geofence |

### 8.2 Files used in PoC (minimum)

| GTFS file | Used for |
|---|---|
| `stops.txt` | `stop_id`, `stop_name`, `stop_lat`, `stop_lon` |
| `routes.txt` (and/or equivalent line tables) | Line identifiers and public labels |
| `trips.txt` | Trip ↔ route / direction |
| `stop_times.txt` | Stop sequence on trips — **terminus**: `stop_sequence = 1` as origin stop for that trip direction |

Exact column-to-table mapping → `03` / `04`. Terminus uses GTFS `stop_sequence = 1` (not API `positionTypeBus`) — see frozen contract §2 and `04`.

### 8.3 Trust boundary

| Question | Prefer |
|---|---|
| Stop name / coordinates for search (US-03) | GTFS |
| Does line L serve stop S? | GTFS stop↔line graph |
| Is stop S a line origin (terminus)? | GTFS `stop_times` (`stop_sequence = 1`) |
| ETA / vehicle / live destination now | EMT `arrives` API |

---

## 9. Origin map — business concept → raw field

| Business concept | Primary origin | Raw field(s) |
|---|---|---|
| Public line label | EMT `Arrive` | `Arrive[].line` |
| Internal line ID | EMT `StopInfo` and/or GTFS | `StopInfo.lines[].line` / GTFS route id |
| Vehicle ID | EMT `Arrive` | `Arrive[].bus` |
| Live destination text | EMT `Arrive` | `Arrive[].destination` |
| ETA (seconds) | EMT `Arrive` | `Arrive[].estimateArrive` |
| Distance to stop (metres) | EMT `Arrive` | `Arrive[].DistanceBus` (available; **not required** by MVP user stories) |
| Bus GPS | EMT `Arrive` | `Arrive[].geometry.coordinates` (available; **not required** by MVP user stories) |
| Stop ID (live) | EMT `Arrive` / `StopInfo` | `Arrive[].stop` / `StopInfo[].stopId` |
| Stop name | GTFS (primary); API optional | GTFS `stop_name`; API `StopInfo.stopName` |
| Stop coordinates | GTFS (primary) | GTFS `stop_lat` / `stop_lon` |
| Street reference | EMT `StopInfo` (optional enrich) | `StopInfo.Direction` |
| Line headers A/B | GTFS and/or `StopInfo.lines` | `nameA` / `nameB` / GTFS equivalents |
| Snapshot time | EMT envelope | top-level `datetime` |
| API call status | EMT envelope | `code`, `description` |
| In-scope flag | Derived (geofence) | Not from API — see `01-project-scope.md` |
| Terminus / origin stop | GTFS | `stop_times.stop_sequence = 1` |

---

## 10. What this source does **not** provide (MVP)

Aligned with `01-project-scope.md` out-of-scope:

- Vehicle occupancy
- Delay cause / incidents (MVP request keeps `Text_IncidencesRequired_YN: "N"`)
- Theoretical timetable as live ETA substitute
- Metro / Cercanías
- Fares / tickets

---

## 11. References

| Document | Role |
|---|---|
| `docs/api-response-reference.md` | Detailed Spanish API examples and parsing notes |
| `docs/data-source-contract-v3.md` | Frozen Phase 1 contract (legacy monolith) |
| `docs/01-project-scope.md` | Geofence, US, exclusions |
| `docs/Historias de usuario.md` | US numbering source of truth |
| `samples/*.json` | Real downloaded API payloads (when present) |
