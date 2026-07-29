# ADR-011: Disruption SoT is GTFS-RT servicealerts not Arrive Incident

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** US-07, Bronze/Gold alerts

## 1. Context

Disruptions appear both as Arrive `Incident` JSON and as GTFS-RT Service Alerts. Team agreement (Q22) selected RT as product SoT.

## 2. Alternatives Considered

- **A — Arrive Incident body:** Already in arrives poll; stop-level temptation; not chosen SoT.
- **B — S2 `servicealerts/proto` only:** Matches team agreement; unauthenticated 200 verified.
- **C — Merge both:** Double maintenance; conflict risk.

## 3. Decision

Adopt **B**. RT `informed_entity.stop_id` is always empty → **must not** join alerts to stops. Active = `active_period` vs now. Inactive → alert text NULL / hidden.

## 4. Consequences

- **Pros:** One disruption SoT; avoids Incident schema coupling.
- **Cons:** Line-level attribution only; stop-specific disruption UX limited.

## 5. Amended / Superseded by

- None at time of writing.
