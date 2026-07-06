# Issue #2 — EMT Madrid Bus API Research

**Issue:** #2 — Research and document the EMT Madrid API  
**Scope:** `fuente`  
**Status:** completed (2026-07-06)  
**Author:** Data Engineer  

Deliverable for Issue #2 (data source research). Documents the **bus** API before designing ingestion (Z2).  
For a file-by-file guide to `samples/`, see [emt-api-samples.md](./emt-api-samples.md).

---

## 1. Executive summary

The **EMT Madrid Mobility Labs** REST API exposes urban transport data as **JSON** at `https://openapi.emtmadrid.es`. Production authentication uses **Protected login** (`X-ClientId` + `passKey`) registered at [Mobility Labs](https://mobilitylabs.emtmadrid.es/). After login, an `accessToken` must be sent on every data call.

We manually tested (curl and repo scripts) the core bus endpoints. Arrival data (`arrives`) is **live**: it includes ETA in seconds, distance to the bus, and vehicle GPS position, with a server timestamp.

Section §5 lists **bus-related endpoints only** (OpenAPI Block 3 — BUSEMTMAD), plus auth and health check.

---

## 2. Official documentation

| Resource | URL |
|----------|-----|
| Swagger UI (recommended) | https://datos.emtmadrid.es/m360-swagger/docs |
| OpenAPI 3.1 (machine-readable) | https://datos.emtmadrid.es/m360-swagger/openapi.json |
| Mobility Labs portal (app registration) | https://mobilitylabs.emtmadrid.es/ |
| Open data dataset | https://datos.emtmadrid.es/dataset/tiempo-real-para-autobuses-de-emt |

**API base URL:** `https://openapi.emtmadrid.es`

---

## 3. Authentication

### 3.1 Flow (required before any data endpoint)

```
1. GET /v3/mobilitylabs/user/login/   (OpenAPI current; /v1/.../login/ also works in practice)
   Headers: X-ClientId + passKey  (Protected)  OR  email + password  (Basic)
2. Response → data[0].accessToken
3. All subsequent calls:
   Header: accessToken: <token>
```

### 3.2 Supported methods (Block 1 — User identity)

| Method | Headers | Use in this project |
|--------|---------|---------------------|
| **Protected** | `X-ClientId` + `passKey` | **Production / ingestion** — app registered in Mobility Labs |
| Basic | `email` + `password` | Local fallback (lower quota) |
| Advanced | email + password + ClientId (+ passKey) | Diagnostics; not needed in the pipeline |

### 3.3 Team credentials

- Register an application in Mobility Labs → `x-ClientId` (UUID, 36 chars) + `passKey` (hex, 128 chars).
- Variables in `.env` (do not commit): `EMT_CLIENT_ID`, `EMT_MADRID_PASS_KEY` — see `.env.example`.
- Project app: `microsoft-factoriaf5-2026`.

### 3.4 Login codes observed

| code | Observed meaning |
|------|------------------|
| `00` / `01` | Login OK (`01` = existing session extended) |
| `84` | Protected credentials rejected (seen before app activation) |
| `89` | ClientId sent without passKey in the same request |

> The API **does not publish** an official error-code catalog; only success (`00`) is documented.

### 3.5 curl example (Protected)

```bash
curl -sS -X GET "https://openapi.emtmadrid.es/v3/mobilitylabs/user/login/" \
  -H "X-ClientId: ${EMT_CLIENT_ID}" \
  -H "passKey: ${EMT_MADRID_PASS_KEY}"
```

> Repo scripts currently call `/v1/mobilitylabs/user/login/`; both paths accept the same headers and return the same envelope.

Example payload (token redacted): [`samples/02_login_protected.json`](../samples/02_login_protected.json)

---

## 4. Rate limits

| Login mode | `apiCounter.dailyUse` | Notes |
|------------|----------------------|-------|
| Basic (email/password) | 20,000 hits/day | Generic account |
| **Protected (app)** | **250,000 hits/day** | Confirmed with active app login |

- Current counter on each login: `apiCounter.current`.
- The token is extended automatically on each API call (`tokenSecExpiration` ~86400 s).
- **No** public per-second rate-limit documentation; we assume respectful polling (≥30–60 s between cycles per stop).

### 4.1 Ingestion estimate (Z2 reference)

| Scenario | Calculation | Hits/day |
|----------|-------------|----------|
| 40 stops × poll every 60 s | 40 × (86400/60) | ~57,600 |
| + lines/info 1×/hour | 24 | negligible |
| + incidents 10 lines × 1×/5 min | ~2,880 | marginal |

**Conclusion:** with Protected app credentials (250k/day) there is headroom for ~40 stops at 60 s intervals. Reduce stops or increase the interval if more sources are added.

---

## 5. Bus endpoints (BUSEMTMAD)

Source: [OpenAPI 3.1](https://datos.emtmadrid.es/m360-swagger/openapi.json) — Block 3 only.  
All bus paths require `accessToken` (see §3).

| Role | Meaning |
|------|---------|
| **Ingest** | Bronze polling target (Z2) |
| **Dimension** | Catalog / low-frequency refresh |
| **Setup** | Once at pipeline configuration |

### 5.1 Auth and health (prerequisites)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v3/mobilitylabs/user/login/` | GET | Obtain `accessToken` (OpenAPI current) |
| `/v1/mobilitylabs/user/login/` | GET | Same; used by repo scripts |
| `/v1/hello` | GET | Health check without auth — sample: [`01_hello.json`](../samples/01_hello.json) |

### 5.2 Real time

| Endpoint | Method | Returns | Live | Role |
|----------|--------|---------|------|------|
| `/v2/transport/busemtmad/stops/{stopId}/arrives/{lineArrive}/` | POST | ETA, bus ID, distance, bus GPS, incidents per line | **Yes** | **Ingest** |
| `/v2/transport/busemtmad/stops/{stopId}/arrives/` | POST | Same, all lines at stop (**tested in repo**) | **Yes** | **Ingest** |
| `/v2/transport/busemtmad/lines/info/{dateref}/` | GET | All lines status for date | Daily snapshot | **Ingest** |
| `/v1/transport/busemtmad/lines/incidents/{lineid}/` | GET | Incidents / delays per line (RSS-style `item[]`) | **Yes** | **Ingest** |

`lineArrive` filters by public line label (e.g. `M1`); omit it or use the trailing `/arrives/` path for all lines.

### 5.3 Stops — search and catalog

| Endpoint | Method | Returns | Live | Role |
|----------|--------|---------|------|------|
| `/v2/transport/busemtmad/stops/arroundxy/{longitude}/{latitude}/{radius}/` | GET | Stops near coordinates | Catalog | **Setup** |
| `/v2/transport/busemtmad/stops/arroundstop/{stopId}/{radius}/` | GET | Stops near another stop | Catalog | Dimension |
| `/v1/transport/busemtmad/stops/arroundstreet/{namePlace}/{number}/{radius}/` | GET | Stops near a street address | Catalog | Setup |
| `/v1/transport/busemtmad/stops/list/` | POST | Filtered stop listing | Static | Dimension |
| `/v1/transport/busemtmad/stops/{stopId}/detail/` | GET | Name, address, GPS, lines, frequencies | Semi-static | **Dimension** |

### 5.4 Lines — catalog, geometry, schedules

| Endpoint | Method | Returns | Live | Role |
|----------|--------|---------|------|------|
| `/v1/transport/busemtmad/lines/groups/` | GET | Line groups and subgroups | Static | Dimension |
| `/v1/transport/busemtmad/lines/{labelId}/route/` | GET | Route geometry and stop sequence | Static | Dimension |
| `/v1/transport/busemtmad/lines/{lineId}/stops/{direction}/` | GET | Ordered stops on a line (A or B) | Static | Dimension |
| `/v1/transport/busemtmad/lines/{lineId}/info/{dateref}/` | GET | Single-line detail + timetable | Daily | Dimension |
| `/v1/transport/busemtmad/lines/{lineId}/timetable/` | GET | First/last service times | Static | Reference |
| `/v1/transport/busemtmad/lines/{lineId}/trips/{dateRef}/` | GET | Planned trips for a date | Static | Reference |
| `/v1/transport/busemtmad/calendar/{startdate}/{enddate}/` | GET | Service calendar (LA/SA/FE, strikes) | Static | Dimension |

### 5.5 Trip planning (optional)

| Endpoint | Method | Returns | Live | Role |
|----------|--------|---------|------|------|
| `/v1/transport/busemtmad/travelplan/` | POST | Bus/walk itinerary with ETA and GeoJSON route | On demand | Reference |

Not required for Issue #2 AC; documented because it is part of the bus API surface.

### 5.6 Ingestion priority (Z2 preview)

| Priority | Endpoint | Interval (suggested) |
|----------|----------|---------------------|
| P0 | `POST …/stops/{stopId}/arrives/` | 30–60 s per stop |
| P1 | `GET …/lines/info/{dateref}/` | 1×/day or 1×/hour |
| P1 | `GET …/lines/incidents/{lineid}/` | 1×/5 min per watched line |
| P2 | `GET …/stops/{stopId}/detail/` | 1×/day |
| P2 | `GET …/stops/arroundxy/…` | Once at setup |

### 5.7 Test area

**Lavapiés** (Madrid): coordinates `-3.7030, 40.4088`, radius 200 m.  
Stops captured: **4035** (Mercado San Fernando), **4045** (Lavapiés). Main line in samples: **601** (label **M1**).

---

## 6. Response format

- **Format:** JSON only (no XML on the endpoints we tested).
- **Common envelope:**

```json
{
  "code": "00",
  "description": "...",
  "datetime": "2026-07-06T10:19:32.088161",
  "data": [ ... ]
}
```

| code (data) | Usual meaning |
|-------------|---------------|
| `00` | OK |
| `01` | OK with notice (e.g. no estimations at that moment) |

### 6.1 Key fields — `arrives` (bronze / gold)

Inside `data[].Arrive[]`:

| Field | Type | Description |
|-------|------|-------------|
| `estimateArrive` | int | Seconds until estimated arrival |
| `DistanceBus` | int | Meters from bus to stop |
| `geometry` | GeoJSON Point | Current bus position |
| `bus` | int | Vehicle identifier |
| `line` / `destination` | string | Line and destination |
| `deviation` | int | Deviation from schedule |

### 6.2 Required body — POST arrives

```json
{
  "cultureInfo": "es",
  "Text_StopRequired_YN": "Y",
  "Text_EstimationsRequired_YN": "Y",
  "Text_IncidencesRequired_YN": "Y",
  "DateTime_Referenced_Incidencies_YYYYMMDD": "20260706"
}
```

---

## 7. Confirmation: live data (not static/batch)

### 7.1 Evidence in real payload

File: [`samples/04_arrives_stop_4035.json`](../samples/04_arrives_stop_4035.json)

- **Server timestamp:** `2026-07-06T10:19:32.088161`
- **Bus 9012:** `estimateArrive: 184`, `DistanceBus: 230`, GPS coordinates distinct from the stop
- **Bus 9016:** `estimateArrive: 904`, `DistanceBus: 305` — second vehicle at the same stop

This shows **dynamic service state**, not a static dump.

### 7.2 Contrast with static endpoints

| Type | Behaviour |
|------|-----------|
| `arrives` | Changes between calls (ETA, bus position) |
| `timetable` / `calendar` | Same result for a `lineId`/date until the schedule changes |
| `lines/info/{date}` | Daily snapshot; refreshed via the date in the path |

### 7.3 How to reproduce the verification

```bash
# 1. Login + end-to-end smoke test
./scripts/test_emt_api.sh

# 2. Regenerate all samples
python3 scripts/fetch_emt_samples.py

# 3. Compare two back-to-back arrives calls (ETAs should differ)
#    → use the same stopId and accessToken twice
```

---

## 8. Real examples saved in the repo

| File | Endpoint tested |
|------|-----------------|
| [`samples/01_hello.json`](../samples/01_hello.json) | Health check |
| [`samples/02_login_protected.json`](../samples/02_login_protected.json) | Protected login |
| [`samples/03_stops_arroundxy_lavapies.json`](../samples/03_stops_arroundxy_lavapies.json) | Stops near Lavapiés |
| [`samples/04_arrives_stop_4035.json`](../samples/04_arrives_stop_4035.json) | Live arrivals — stop 4035 |
| [`samples/04_arrives_stop_4045.json`](../samples/04_arrives_stop_4045.json) | Live arrivals — stop 4045 |
| [`samples/05_stop_detail_4035.json`](../samples/05_stop_detail_4035.json) | Stop detail 4035 |
| [`samples/05_stop_detail_4045.json`](../samples/05_stop_detail_4045.json) | Stop detail 4045 |
| [`samples/06_lines_info_today.json`](../samples/06_lines_info_today.json) | All lines for the day |
| [`samples/07_line_incidents_601.json`](../samples/07_line_incidents_601.json) | Incidents for line 601 |

Regenerate: `python3 scripts/fetch_emt_samples.py` (requires `.env` with app credentials).

---

## 9. Implications for Z2 (ingestion)

Brief preview — full pipeline design is out of scope for Issue #2.

1. **HTTP poller** → Protected login → loop `arrives` over a set of `stopId` values.
2. **Bronze:** raw JSON + metadata (`ingested_at`, `stop_id`, `endpoint`).
3. **Silver:** flatten `Arrive[]` into rows (`stop_id`, `line`, `bus_id`, `estimate_arrive_sec`, `distance_m`, `bus_lat`, `bus_lon`, `snapshot_ts`).
4. **Gold:** per-line aggregates (average delay, ranking).
5. **Dimensions:** `stop/detail`, `lines/info`, `calendar` — daily or at setup.

---

## 10. Acceptance criteria — checklist

| Criterion | Status | Where |
|-----------|--------|-------|
| Document with relevant endpoint(s) | ✅ | §5 (bus API) |
| Auth documented | ✅ | §3 |
| Rate limit documented | ✅ | §4 |
| Real example payload | ✅ | §8 + `samples/` |
| Response format (JSON) | ✅ | §6 |
| Confirmed **live** endpoint (not static only) | ✅ | §7 |
| Manual tests (curl/scripts) | ✅ | §3.5, §7.3, `scripts/` |

---

## 11. Internal references

- [emt-api-samples.md](./emt-api-samples.md) — guide to `samples/` files
- Scripts: `scripts/fetch_emt_samples.py`, `scripts/test_emt_api.sh`, `scripts/emt_login_check.py`
