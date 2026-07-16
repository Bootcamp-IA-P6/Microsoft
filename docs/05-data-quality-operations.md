# Data Quality & Operations Contract

**Version:** 1.1  
**Last updated:** 2026-07-16  
**Status:** Active  
**Source:** PO `docs/data-source-contract-v3.md` §3 and §8 (acceptance), plus conversation clarifications noted below

---

## 1. Purpose

When data is considered fresh / usable for the agent, and Phase 2 acceptance checks.

Not in this document: schemas (`03`), transforms (`04`), API field catalogue (`02`), product scope (`01`).

---

## 2. Freshness (PO §3)

- Gold is rebuilt **only from** the last **successful** polling round per stop.
- If the last successful poll for a stop is older than **3× the normal interval** (~3 minutes when polling every **60 s**), set `is_stale = true` and the agent communicates that the data is outdated (“dato desactualizado”).

---

## 3. Successful poll (conversation clarification of PO)

Aligned with `02` / empty-snapshot behaviour:

- A poll that returns EMT success with **`Arrive: []`** is a **valid successful snapshot** (no buses now), not a failure.
- Failed HTTP / non-success envelope does **not** advance “last successful poll”; gold keeps the previous successful rebuild and may become stale per §2.

Agent reads **gold** (and catalogue dims), not bronze JSON at query time.

---

## 4. Phase 2 acceptance criteria (PO §8)

- [ ] 30+ minutes of continuous polling without failures  
- [ ] Gold reflected within 60 s of the last successful poll  
- [ ] Manual validation: US-01 / US-02 questions answered correctly from gold  

---

## 5. References

- `docs/data-source-contract-v3.md` §3, §8  
- `docs/03-schema-contract.md` — `is_stale`, `has_upcoming_bus`  
- `docs/04-transformation-mapping.md` — empty poll → gold rebuild  
- `docs/01-project-scope.md` — in-scope stops  
