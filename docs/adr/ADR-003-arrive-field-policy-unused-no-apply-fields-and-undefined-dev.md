# ADR-003: Arrive field policy: unused No-apply fields and undefined deviation

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** Arrive ingestion, Gold/Silver column selection, agent answers

## 1. Context

Live Arrive samples include `positionTypeBus`, `isHead`, and `deviation`. Official docs mark some as No apply; `deviation` has no field-list definition (examples only). Product risk: agents treating junk fields as facts.

## 2. Alternatives Considered

- **A — Store and expose all observed fields:** Complete raw fidelity; unsafe semantics.
- **B — Mark No-apply as unused; mark undefined as meaning-unknown / unusable:** Honest contract.
- **C — Drop fields silently without documentation:** Easy to forget why.

## 3. Decision

Adopt **B**:
- `positionTypeBus`, `isHead`: **unused** (apidocs No apply; isHead also No apply in swagger).
- `deviation`: **meaning unknown / must not be used** (not in apidocs field list nor swagger schema).
Document classification in §5 as closed observation / unused / meaning-unknown — not open “maybe later” items.

## 4. Consequences

- **Pros:** Prevents hallucinated interpretations in US answers.
- **Cons:** Some numeric fields in payloads are ignored by design.

## 5. Amended / Superseded by

- Amended by [ADR-039](ADR-039-gold-exposes-stop-and-live-bus-coordinates-for-map.md): Arrive **`geometry`** (GeoJSON Point) is **in use** for live bus lat/lon. Unused list above (`positionTypeBus`, `isHead`, `deviation`) **unchanged**.
