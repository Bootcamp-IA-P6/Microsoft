# EMT API — sample responses & local fetch

Reference for JSON files under `samples/`. Captured from the [EMT Swagger API](https://datos.emtmadrid.es/m360-swagger/docs) (`https://openapi.emtmadrid.es`).

## Auth note

Samples are fetched with **Basic login** (`email` + `password` in `.env`). App credentials (`EMT_CLIENT_ID` + `EMT_MADRID_PASS_KEY`) currently return login `code=84` — use Basic until EMT activates passKey.

`02_login_basic.json` stores the login response with `accessToken` redacted.

## Refresh samples locally

Requires `EMT_EMAIL` and `EMT_PASSWORD` in `.env` (never commit `.env`):

```bash
python3 scripts/fetch_emt_samples.py
```

Remove email/password from `.env` after running if you prefer.

## Files in `samples/`

| File | Endpoint | Purpose |
|------|----------|---------|
| `01_hello.json` | `GET /v1/hello` | API health check |
| `02_login_basic.json` | `GET /v1/mobilitylabs/user/login/` | Auth response shape |
| `03_stops_arroundxy_lavapies.json` | `GET /v2/transport/busemtmad/stops/arroundxy/{lon}/{lat}/{radius}/` | Stops near Lavapiés |
| `04_arrives_stop_{id}.json` | `POST /v2/transport/busemtmad/stops/{stopId}/arrives/` | Real-time arrivals (bronze source) |
| `05_stop_detail_{id}.json` | `GET /v1/transport/busemtmad/stops/{stopId}/detail/` | Stop metadata and lines |
| `06_lines_info_today.json` | `GET /v2/transport/busemtmad/lines/info/{dateRef}/` | Network line status for a date |
| `07_line_incidents_{line}.json` | `GET /v1/transport/busemtmad/lines/incidents/{lineid}/` | Incidents / delays for one line |

## How the team uses these

- **Data Engineer (Z2):** bronze raw shape, silver/gold field names, polling endpoints
- **AI Developer (Z3):** mock JSON contract aligned with gold tables
- **PO:** example questions vs fields (`estimateArrive`, `line`, `DistanceBus`, etc.)

## Related scripts

| Script | Role |
|--------|------|
| `scripts/fetch_emt_samples.py` | Regenerate all sample JSON files |
| `scripts/emt_login_check.py` | Login diagnostics (Protected vs Basic) |
| `scripts/emt_cred_inspect.py` | Check `.env` credential format (no secrets printed) |
| `scripts/test_emt_api.sh` | End-to-end smoke test (Protected login; fails with code 84 today) |

## External docs

- Swagger UI: https://datos.emtmadrid.es/m360-swagger/docs
- OpenAPI JSON: https://datos.emtmadrid.es/m360-swagger/openapi.json
- Mobility Labs (app registration): https://mobilitylabs.emtmadrid.es/
