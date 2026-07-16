# Project Scope — EMT Madrid PoC (Sol / Gran Vía)

**Version:** 1.0  
**Last updated:** 2026-07-16  
**Status:** Active  
**Audience:** Product Owner, Data Engineer, Analytics Engineer, AI Developer

---

## 1. Purpose of this document

This document defines **what the PoC covers and why** — project boundary, user stories in scope, geofence, and explicit exclusions.

It does **not** define:

| Topic | See |
|---|---|
| API endpoints, request/response fields, auth | `docs/02-source-contract.md` |
| Table/column schemas, keys, types | `docs/03-schema-contract.md` |
| Bronze → Silver → Gold transforms | `docs/04-transformation-mapping.md` |
| Freshness SLA, retries, stale rules, load success | `docs/05-data-quality-operations.md` |
| Architecture Decision Records (ADR) | Deferred — add under `docs/ADR/` later if needed |

**Legacy references (unchanged):** frozen data contract `docs/data-source-contract-v3.md`; API JSON reference `docs/api-response-reference.md` (companion to `02-source-contract.md`).

---

## 2. Project vision

**Title:** *From live data to natural-language answers* — EMT Madrid urban mobility PoC.

**Problem:** Real-time public transport data exists (bus ETAs, stop catalogues), but answering a simple question like *“When does the M1 arrive at my stop?”* normally requires pipelines, SQL, and dashboards. This PoC collapses that chain into a conversational agent backed by governed lakehouse data.

**Target user profile:** Tourist in central Madrid (Sol / Gran Vía area) who asks in natural language without knowing internal stop codes.

**Success for the data layer:** The agent can answer grounded questions about **next bus arrivals** and **which lines serve a stop**, using only data we ingest and model — never inventing fields the API does not provide (US-04).

---

## 3. Data domain

| Aspect | Decision |
|---|---|
| **Primary live source** | EMT Madrid OpenAPI — `POST .../stops/{stopId}/arrives/` (real-time ETAs) |
| **Static catalogue** | EMT GTFS ([CRTM dataset](https://datos.crtm.es/datasets/868df0e58fca47e79b942902dffd7da0/about)) — stop names, line headers, stop↔line relationships |
| **Storage pattern** | Microsoft Fabric Lakehouse — bronze / silver / gold (Phase 2) |
| **API quota (planning)** | 250,000 calls/day (verified via login `apiCounter.dailyUse`) |

**Principle:** Full-network GTFS for **search and reference**; live polling only for **in-scope stops** inside the geofence (see §4).

---

## 4. Geofence — operational zone (decided)

**Source of truth for the PoC zone.** (An ADR may be added later under `docs/ADR/` if the team wants a formal decision record; not required for Phase 2.)

| Parameter | Value |
|---|---|
| **Center** | Puerta del Sol |
| **Latitude** | 40.416729 |
| **Longitude** | -3.703339 |
| **Method** | Circular radius (not polygon) |
| **Radius** | **600 m** |

### Rationale (summary)

A **600 m** radius is roughly **10 minutes on foot** and covers main tourist interest points around Sol:

- Gran Vía (towards Callao)
- Alcalá
- Sevilla
- Tirso de Molina
- Plaza Mayor

### Implications for the PoC

- Stops with `in_scope = true` are those whose coordinates fall inside this circle (plus explicit validation of the resulting stop list).
- Live ingest polls **in-scope stops only** — not the full EMT network.
- Stops/lines outside the geofence remain in GTFS catalogue (`in_scope = false`) but are **not** continuously polled.
- Exact stop count and final `scope_stop_ids` list are a **developer deliverable** (derived from GTFS + geofence query); this document fixes the rule, not the final ID list.

---

## 5. User stories — data-relevant scope

Source: `docs/Historias de usuario.md`. Mapping to data/agent phases.

| ID | Summary | Data layer role | MVP? |
|---|---|---|---|
| **US-01** | ETA for line X at stop Y; error if line does not serve stop | `gold_stop_line_eta_latest` + `silver_stop_lines` validation | Yes |
| **US-02** | All lines + ETAs at stop Y; explicit message if none | Same gold; `has_upcoming_bus = false` when catalogued but no ETA | Yes |
| **US-03** | Resolve stop by street/place name, not numeric code | `silver_stops_dim` (GTFS); agent disambiguation | Yes (catalog) |
| **US-04** | Do not invent unavailable data | Out-of-scope matrix (§6); agent prompt (Phase 3+) | Yes (rules) |
| **US-05** | Simple chat UI | No data schema — frontend Phase 5 | No (data) |
| **US-06** | Ingest interchangeable (Fabric Eventstream vs Kafka) | Bronze portable; downstream unchanged | Phase 2 infra |
| **US-07** | Minimal interaction log (5 fields) | Separate log table — Phase 5 | No (MVP data) |

### Product decision D1 (destination match)

Match user destination against **line header names** (`name_a` / `name_b` in catalogue, `destination` in live ETA) — **no routing** to intermediate non-terminal stops. Routing to arbitrary stops is out of scope.

### Open product items (not blocking scope doc)

From user stories and frozen contract — tracked in implementation/decisions, not redefined here:

- US-01/US-02: gold grain (one row per line vs all buses in snapshot) — PO pending.
- US-03: ambiguous name → ask user vs auto-pick — agent behaviour.

---

## 6. Out of scope (US-04 alignment)

The agent and pipeline **must not** imply data exists for:

| Excluded | Notes |
|---|---|
| **Incidents / delay causes** | Postponed Phase 3+; MVP request keeps incidents off |
| **Vehicle occupancy** | Not in API for this PoC |
| **Intermediate-stop routing** | Only terminal/header destination match (D1) |
| **Theoretical schedules** | Real-time ETAs only |
| **Fares, tickets, payments** | — |
| **Metro, Cercanías, other operators** | EMT bus only |
| **Voice input** | Phase 6 idea — not MVP |
| **Stops/lines outside geofence** | Catalogue only; no live poll (`in_scope = false`) |

If the user asks for excluded information, the system responds that the data is **not available** — never guesses (US-04).

---

## 7. Phase alignment (roadmap summary)

Aligned with `docs/Roadmap y pasos detallados.md` and frozen contract §8.  
**Sync note (roadmap):** AI work (Z3) can start on **mock gold** before real Z2 data; real validation needs `gold_stop_line_eta_latest`.

| Roadmap phase | Focus | Data-layer status for this PoC |
|---|---|---|
| **0 — Setup (Z1)** | Tenant, capacity, workspace | Infra (out of these contracts) |
| **1 — Data source** | Domain chosen (EMT) | Closed — frozen `docs/data-source-contract-v3.md`; structured in `docs/` |
| **2 — Ingest → model (Z2)** | Live data → consultable gold | **Current** — bronze/silver/gold + polling |
| **3 — Basic agent (Z3, mock first)** | Agent on simulated gold shape | Consumes gold schema from `03` |
| **4–5 — MCP + supervisor + frontend** | E2E chat (+ map/feedback ideas) | Needs real gold from Phase 2 |
| **6 — Extension (optional)** | Alerts, voice, ranking, anomalies | Out of MVP data scope |
| **Close A/B** | QA + README/blog/slides | After Phase 5 |

### Phase 2 (Z2) MVP — data deliverables (scope only)

- Bronze: raw `arrives` responses for in-scope stops
- Silver: typed observations + GTFS dimensions (`stops`, `lines`, `stop_lines`)
- Gold: latest ETA per stop+line for agent consumption
- Continuous polling (~60 s per in-scope stop — operational detail in `05-data-quality-operations.md`)
- Documented layer schemas (this `docs/` set) for the AI Developer

**Postponed schemas** (defined for reference only, **not built in Phase 2**): `silver_incidents`, `gold_incident_line_current`, `gold_line_status_5m`.  
(Incidents are **not** HU US-05 — US-05 is the chat UI; see `docs/Historias de usuario.md`.)

---

## 8. Documentation map (`docs/`)

| File | Role |
|---|---|
| `01-project-scope.md` (this) | Boundary, users, geofence, exclusions, phases |
| `02-source-contract.md` | EMT API + GTFS as origin systems |
| `03-schema-contract.md` | Bronze/silver/gold table definitions |
| `04-transformation-mapping.md` | How raw data becomes tables |
| `05-data-quality-operations.md` | Freshness, failures, validation |
| `ADR/` | Deferred — create later if formal ADRs are needed |

---

## 9. Pending deliverables (developer)

These do not change scope rules; they operationalize them:

- [ ] Compute and freeze `scope_stop_ids` from GTFS + §4 geofence
- [ ] Document final in-scope stop count
- [ ] GTFS bootstrap script (`silver_stop_lines` with `is_terminus`)
- [ ] Validate `stop_sequence = 1` terminus logic on local GTFS

---

## 10. References

| Document | Use |
|---|---|
| `docs/data-source-contract-v3.md` | Frozen Phase 1 contract (superseded structurally by `docs/`, content preserved) |
| `docs/api-response-reference.md` | Spanish API JSON samples (companion to `02`) |
| `docs/Historias de usuario.md` | User stories US-01–US-07 (**US number source of truth**) |
| `docs/Resumen-Del dato vivo a respuesta en lenguaje natural.md` | Project summary and roles |
| `docs/Roadmap y pasos detallados.md` | Phase / pairing roadmap |
| `docs/factoriaF52026_abstract.md` | PoC context (Microsoft × Factoría F5) |

---

## Appendix A — Changes from data-source-contract v2 → v3

Preserved from PO frozen contract §0 (`docs/data-source-contract-v3.md`).  
**Clarification:** row 2’s legacy label “US-05” meant **incident tables postponed**, which conflicts with HU **US-05 = chat UI**. In these structured docs (`01`–`05`), incidents stay Phase 3+ / out of MVP data; chat remains HU US-05 (frontend).

| # | Change |
|---|---|
| 1 | Reintroduced `silver_arrival_observations`, `silver_stops_dim`, `silver_lines_dim` (needed for MVP) |
| 2 | `silver_incidents` and `gold_incident_line_current` confirmed as **postponed** (not MVP; legacy text said “US-05”) |
| 3 | `gold_line_status_5m` confirmed as **postponed** (operational aggregates, Phase 3+) |
| 4 | Replaced `position_type_bus` logic (not in API v2) with `is_terminus` from GTFS (`stop_sequence = 1` in `stop_times.txt`) |
| 5 | Explicit phased build plan (Phase 2 MVP vs Phase 3+) |
