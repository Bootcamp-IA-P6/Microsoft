# Project Scope — EMT Madrid PoC (Sol / Gran Vía)

**Version:** 1.1  
**Last updated:** 2026-07-16  
**Status:** Active  
**Sources:** PO `docs/data-source-contract-v3.md`; HU `docs/Historias de usuario.md`; geofence **(agreed)**; roadmap `docs/Roadmap y pasos detallados.md`

---

## 1. Purpose

What the PoC covers: zone, users, inclusions / exclusions, phases.

Not in this document: API details (`02`), schemas (`03`), transforms (`04`), freshness ops (`05`).

---

## 2. Domain (PO §1)

- **Live source:** EMT Madrid bus arrivals API  
- **Catalogue:** GTFS from CRTM (link in PO §1)  
- **Profile:** tourist  
- **API quota (agreed / PO):** **250,000** calls/day  

Live polling only for **in-scope** stops; full GTFS for catalogue / search.

---

## 3. Geofence **(agreed — replaces PO “~700 m or polygon TBD”)**

| Parameter | Value |
|---|---|
| Center | Puerta del Sol |
| Latitude | 40.416729 |
| Longitude | -3.703339 |
| Method | Circular radius |
| Radius | **600 m** |

Rationale (team): ~10 min walk; covers Gran Vía (to Callao), Alcalá, Sevilla, Tirso de Molina, Plaza Mayor.

`in_scope = true` for stops inside this circle. Exact `scope_stop_ids` list = developer deliverable (PO §9).

---

## 4. MVP functionality (PO §1 + HU numbering)

PO text mixed US labels; **US numbers follow** `docs/Historias de usuario.md`:

| ID | Need | Data |
|---|---|---|
| US-01 | ETA for line X at stop Y; error if line does not serve stop | gold + `silver_stop_lines` |
| US-02 | All lines + ETAs at stop Y; explicit if none | same gold / `has_upcoming_bus` |
| US-03 | Resolve stop by street/place name | `silver_stops_dim` |
| US-04 | Do not invent missing data | out-of-scope list |
| D1 (PO) | Match destination to line headers only — no routing to intermediate stops | `destination` / `name_a` / `name_b` |

US-05 (chat UI), US-06 (ingest portability), US-07 (interaction log): see HU — not MVP lakehouse schemas except US-06 implies portable bronze.

---

## 5. Out of scope (PO §5)

- Incidents / delay causes in MVP (postponed)  
- Routing to intermediate non-header stops  
- Vehicle occupancy  
- Fares, tickets, payments  
- Metro, Cercanías, other operators  
- Theoretical schedules (real-time only)  
- Stops/lines outside geofence (`in_scope = false`) — catalogue only, no live poll  
- Voice (Phase 6 idea)

---

## 6. Phases (PO §8 + roadmap)

| Phase | Data relevance |
|---|---|
| 1 | Source contract — frozen v3; this `docs/01`–`05` set |
| 2 (Z2) | Bronze / silver / gold + continuous `arrives` polling (~60 s) |
| 3+ | Agent; incidents / aggregates if activated; frontend later |

**Build in Phase 2 (PO):** `bronze_emt_raw`, four silver tables, `gold_stop_line_eta_latest`.  
**Postponed:** `silver_incidents`, `gold_incident_line_current`, `gold_line_status_5m`.

> PO v3 called postponed incidents “US-05”; HU **US-05 = chat**. Incidents remain postponed / not that HU.

Roadmap note: agent can start on mock gold; real validation needs Phase 2 gold.

---

## 7. Pending (PO §9)

- [ ] Exact geofence stop list / count — Developer  
- [ ] GTFS bootstrap + `is_terminus` — Developer  
- [ ] Confirm `stop_sequence` on local GTFS — Developer  

---

## 8. Document map

| File | Role |
|---|---|
| `01-project-scope.md` | This file |
| `02-source-contract.md` | EMT + GTFS origin |
| `03-schema-contract.md` | Tables (PO schemas) |
| `04-transformation-mapping.md` | How tables are filled |
| `05-data-quality-operations.md` | Freshness / acceptance |
| `data-source-contract-v3.md` | Frozen PO monolith (kept) |

ADR folder: deferred if needed later.

---

## Appendix — PO v2 → v3 changelog (PO §0)

| # | Change |
|---|---|
| 1 | Reintroduced `silver_arrival_observations`, `silver_stops_dim`, `silver_lines_dim` |
| 2 | `silver_incidents` / `gold_incident_line_current` postponed (legacy label “US-05” in PO) |
| 3 | `gold_line_status_5m` postponed |
| 4 | Terminus via GTFS `stop_sequence = 1`, not `position_type_bus` |
| 5 | Explicit Phase 2 vs Phase 3+ plan |
