# ADR-017: Bronze holds REST and RT payloads only; GTFS bootstraps Silver

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** Bronze scope, GTFS path

## 1. Context

Whether GTFS belongs in Bronze was debated. Contract puts static GTFS into Silver bootstrap.

## 2. Alternatives Considered

- **A — GTFS in Bronze then Silver:** Extra hop.
- **B — GTFS direct to Silver bootstrap; Bronze = S1 REST + S2 RT JSON:** Matches contract.
- **C — Dual-store raw `.pb` and JSON for RT:** Heavier; rejected for POC.

## 3. Decision

Adopt **B**. RT: decode `.pb` → store **JSON only** in Bronze (no dual raw `.pb` retention for POC). Calendar collected daily into Bronze as material for `day_type`.

## 4. Consequences

- **Pros:** Smaller Bronze; one RT representation.
- **Cons:** Re-decode from network if original protobuf bytes needed later.

## 5. Amended / Superseded by

- None at time of writing.
