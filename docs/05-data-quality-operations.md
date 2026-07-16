# Data Quality & Operations Contract

**Version:** 1.0  
**Last updated:** 2026-07-16  
**Status:** Active (Phase 2 MVP)  
**Audience:** Data Engineer, Analytics Engineer, AI Developer, Scrum Master

---

## 1. Purpose of this document

This document defines **when data is healthy**, how fresh it must be, what happens on failure, and how we test loads.

It does **not** define:

| Topic | See |
|---|---|
| Project scope / geofence | `docs/01-project-scope.md` |
| API/GTFS payloads | `docs/02-source-contract.md` |
| Table schemas | `docs/03-schema-contract.md` |
| Flatten / join / mapping logic | `docs/04-transformation-mapping.md` |

**Preserved from frozen contract:** freshness 3× interval, gold only from last successful poll, Phase 2 acceptance criteria (`docs/data-source-contract-v3.md` §3, §8).

---

## 2. Operating parameters (MVP)

| Parameter | Value | Notes |
|---|---|---|
| **Poll interval (normal)** | 60 seconds per in-scope stop | Target cadence |
| **Stale multiplier** | 3× interval | → ~**180 seconds** (~3 min) |
| **API daily quota** | 250,000 calls/day | Shared budget; watch login counter |
| **Geofence** | Sol, 600 m circle | Only `in_scope` stops polled |
| **Incidents in request** | Off (`N`) | Not part of MVP ops |

---

## 3. Definitions — success and failure

### 3.1 Successful poll (per stop)

All of the following:

1. HTTP call to `arrives` completes without transport timeout/error.  
2. Response JSON parses.  
3. Envelope `code` indicates success for arrives (typically `"00"`).  
4. One row is appended to `bronze_emt_raw` with full `payload_json`.  

**Empty `Arrive: []` with `code: "00"` counts as a successful poll** (valid “no buses now” snapshot).

### 3.2 Failed poll (per stop)

Any of:

- HTTP error / timeout / no response  
- Non-parseable body  
- Non-success envelope `code` for arrives  
- Auth failure (login) preventing the call  

Failed polls **do not** advance “last successful poll” for that stop.

### 3.3 Successful load (pipeline level)

For Phase 2 acceptance, a **load cycle** is successful when:

| Stage | Required |
|---|---|
| Bronze | Successful poll row written for the stop(s) under test |
| Silver | Dims present; observations written when `Arrive` non-empty; empty Arrive → 0 new observations OK |
| Gold | Rebuilt for that stop from last successful poll + catalogue LEFT JOIN (including empty Arrive case) |

Agent answers from **gold** (and dims), never by scraping bronze JSON at query time.

---

## 4. Freshness SLA

### 4.1 Gold rebuild rule

- Rebuild `gold_stop_line_eta_latest` for a stop **only** from that stop’s **last successful poll**.  
- Failed polls leave previous gold rows in place; set/keep `is_stale` per §4.2.

### 4.2 Stale flag

| Condition | Action |
|---|---|
| `now - last_successful_poll_ts(stop) > 3 × poll_interval` | Set `is_stale = true` on gold rows for that stop |
| Within threshold | `is_stale = false` |

With 60 s interval → stale after **> 180 s** without a successful poll.

**Agent behaviour:** if `is_stale = true`, communicate that data may be outdated (“dato desactualizado”), in addition to any ETA / `has_upcoming_bus` content.

### 4.3 End-to-end freshness target

| Target | Metric |
|---|---|
| Gold reflects last successful poll | Within **60 seconds** of that poll completing (Phase 2 acceptance) |

---

## 5. Completeness criteria

| Check | Expectation |
|---|---|
| **In-scope coverage** | Every `in_scope` stop is polled on the schedule (no silent drop from the poll list) |
| **Catalogue** | `silver_stops_dim` / `silver_lines_dim` / `silver_stop_lines` loaded before relying on gold LEFT JOIN |
| **Gold line coverage** | For each polled stop, gold contains one row per catalogue line serving that stop (after rebuild) |
| **Empty snapshot** | Completeness ≠ “has buses”; empty Arrive still requires bronze + gold rebuild |

**Completeness rate (PoC):** TBD numeric SLO; for MVP, track manually: % of scheduled polls that succeed per hour.

---

## 6. Duplicate tolerance

| Layer | Rule |
|---|---|
| Bronze | Duplicates allowed (raw history); no uniqueness SLA |
| Silver observations | `_rk` unique — duplicate inserts skipped (`04`) |
| Gold | One row per (`stop_id`, `line_id`) — upsert/rebuild |

**Duplicate allowance:** silver duplicate attempt rate should trend to ~0 after idempotent write; any `_rk` collision from clock skew is logged, not double-counted as two facts.

---

## 7. NULL tolerance

| Field / case | Tolerance |
|---|---|
| `eta_seconds` null on silver | **Allowed** — do not drop row |
| `eta_seconds` null on gold with `has_upcoming_bus = false` | **Expected** |
| Null `destination` after trim | **Not allowed** on silver NOT NULL columns — quarantine (`04`) |
| Quarantine rate | TBD; investigate if > small share of Arrive elements fail enrich |

---

## 8. API failure — retry

| Step | MVP policy |
|---|---|
| Login failure | Retry with backoff (e.g. 1s, 2s, 4s); max **3** attempts per job run; then fail the run |
| Single stop `arrives` failure | Retry that stop up to **2** extra times with short backoff; then mark poll failed for that stop |
| Partial round failure | Other stops continue; do not block whole round on one stop |
| Quota exhaustion | Stop polling; alert; do not hammer the API |

Exact backoff library is implementation detail; behaviour above is the contract.

---

## 9. Poll failure handling

| On failure | Behaviour |
|---|---|
| Bronze | No success row (or optional failure log table — TBD) |
| Silver | No new observations from that attempt |
| Gold | **Keep last good gold**; recompute `is_stale` from time since last success |
| Agent | May still answer from last gold; must honour `is_stale` |

**Do not** wipe gold on a single failed poll.

---

## 10. Data loss detection

| Signal | Meaning |
|---|---|
| Gap in bronze `ingested_at` for an in-scope stop ≫ interval | Missed polls |
| Gold `updated_at` stuck while clock advances | Rebuild not running or all polls failing |
| Silver quarantine spike | Mapping / API shape change |
| Login `apiCounter.current` flat while job “runs” | Job not actually calling API |

MVP: detect via notebook summary metrics + manual Fabric table checks. Automated alerts optional (§11).

---

## 11. Alert conditions (PoC)

Minimum useful alerts (Teams / email / log — choose one):

| Condition | Severity |
|---|---|
| Login fails after retries | High |
| Success rate &lt; 80% of scheduled polls in a 15 min window | High |
| Any in-scope stop stale (`is_stale`) for &gt; 10 min continuous | Medium |
| Daily calls &gt; 80% of 250k | Medium |
| Quarantine count &gt; threshold (TBD) in one run | Medium |

Full observability stack is out of scope; US-07 covers interaction logs later, not ingest alerts.

---

## 12. Backfill

| Case | Policy |
|---|---|
| Missed polls (downtime) | **No historical ETA backfill** — live API cannot recreate past snapshots |
| After outage | Resume polling; gold updates from new successful polls |
| GTFS catalogue | Re-run bootstrap/reload; dims refresh; gold rebuild on next successful polls |
| Corrupt bronze row | Exclude from silver; optional delete/flag; no synthetic repair of `payload_json` |

---

## 13. Use of last successful data

| Layer | On failure / gap |
|---|---|
| Gold | **Yes** — serve last successful rebuild |
| Agent | **Yes** — with `is_stale` disclosure when applicable |
| Bronze/silver history | Append-only; gaps remain visible as missing timestamps |

---

## 14. Testing methods

### 14.1 Phase 2 acceptance (from frozen contract)

- [ ] **30+ minutes** continuous polling without failures  
- [ ] Gold reflects within **60 s** of last successful poll  
- [ ] Manual validation: US-01 / US-02 answers correct **from gold**

### 14.2 Recommended checks (Data Engineer)

| Test | How |
|---|---|
| Smoke auth + arrives | `scripts/test_emt_api.py` / `.sh` |
| Empty Arrive handling | Poll a quiet stop/time; assert bronze row + gold `has_upcoming_bus = false` |
| Catalogue miss | Ask agent/line not in `silver_stop_lines` → invalid, not fake ETA |
| Stale simulation | Pause poller &gt; 180 s; assert `is_stale = true` |
| Idempotent silver | Re-process same bronze payload; no duplicate `_rk` |
| Geofence | Spot-check `in_scope` vs 600 m Sol radius |

### 14.3 AI Developer checks

| Test | Expectation |
|---|---|
| US-01 | ETA or explicit “line does not serve stop” |
| US-02 | List with ETAs or explicit “no buses now” |
| Stale | User-visible outdated warning when `is_stale` |
| US-04 | No invented occupancy / incidents / metro |

---

## 15. Load success checklist (per demo / daily)

1. Login OK; quota remaining healthy.  
2. Bronze receiving rows for all in-scope stops.  
3. Silver dims loaded; observations incrementing when buses present.  
4. Gold `updated_at` moving; `is_stale` false under normal polling.  
5. Spot-check one US-01 and one US-02 question against official EMT app (tolerance: small ETA drift expected).

---

## 16. Open items

| ID | Topic | Owner |
|---|---|---|
| Q-1 | Numeric completeness SLO (% polls OK / hour) | Data Engineer + SM |
| Q-2 | Failure log table vs log-only | Data Engineer |
| Q-3 | Alert channel (Teams / email) | Team |
| Q-4 | Exact login/arrives success `code` matrix if provider docs expand | Data Engineer |

---

## 17. References

| Document | Role |
|---|---|
| `docs/data-source-contract-v3.md` | Frozen freshness + acceptance criteria |
| `docs/04-transformation-mapping.md` | Empty poll → gold rebuild mechanics |
| `docs/03-schema-contract.md` | `is_stale`, `has_upcoming_bus` columns |
| `docs/01-project-scope.md` | In-scope stops / exclusions |
| `docs/02-source-contract.md` | Quota, empty Arrive semantics |
| `docs/Historias de usuario.md` | US acceptance language |
| `docs/Roadmap y pasos detallados.md` | Z2 deliverable: consultable gold + documented schemas |
