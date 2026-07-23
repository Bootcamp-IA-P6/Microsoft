# ADR-012: Frequency SoT is observed Silver polls with no planned fallback

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** US-08, Gold freq_* columns

## 1. Context

US-08 asks how often a line runs. Candidates: EMT Frequency* on lines info, GTFS frequencies.txt, or headways observed from Arrive polls. An intermediate idea was “observed first, else planned API”.

## 2. Alternatives Considered

- **A — Planned Frequency* / GTFS frequencies as SoT:** Immediate answers; not “observed”.
- **B — Observed first, planned fallback:** Always answers; mixes meanings.
- **C — Observed only; if insufficient samples → unknown (align `data-source-contract-v4.md`):** Honest; cold start.

## 3. Decision

Adopt **C** (final). Planned Frequency* and GTFS frequencies are **not** SoT. No fallback when samples are insufficient.

## 4. Consequences

- **Pros:** Single meaning of “frequency”; matches refuse-if-unknown ethos.
- **Cons:** Needs warmup / sample gate ([ADR-030](ADR-030-frequency-response-gate-20-observations-preferred-24h-warmup.md)).

## 5. Amended / Superseded by

- History: User first considered PO + API fallback, then explicitly chose **observed-only / say unknown**, aligning with the user story and contract.
- Early schema draft that used planned Frequency* is superseded.
- Poll history table renamed `silver_emt` → `silver_arrives` ([ADR-037](ADR-037-silver-split-into-silver-arrives-and-silver-alerts.md)); frequency SoT unchanged.
