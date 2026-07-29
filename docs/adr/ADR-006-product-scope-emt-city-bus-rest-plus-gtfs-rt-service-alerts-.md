# ADR-006: Product scope: EMT city bus REST plus GTFS-RT service alerts only

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** Product boundary, US-04 refusals, pipeline sources

## 1. Context

User stories cover bus ETA, lines at a stop, name search, disruptions, and observed frequency. Metro and third-party modes are out of scope.

## 2. Alternatives Considered

- **A — Bus + metro + other modes:** Broader; no verified metro SoT in this project.
- **B — EMT city bus (S1 REST) + Service Alerts (S2) only (Q12=B):** Matches verified sources.

## 3. Decision

Adopt **B**. Out-of-scope questions must be refused explicitly (no invention). Control sentences for US-04 live in an **external** sheet (Q15=B), not in Fabric domain tables.

## 4. Consequences

- **Pros:** Honest coverage boundary for the agent.
- **Cons:** Many tourist questions will be refused by design.

## 5. Amended / Superseded by

- None at time of writing.
