# ADR-039: Gold exposes stop and live bus coordinates for map serving

- **Date:** 2026-07-28
- **Author:** Mirae Kang (record)
- **Decision owner:** Jonathan Brasales (PO)
- **Status:** Accepted
- **Components affected:** `silver_arrives`, `gold_emt_stop_line`, Phase 4 Eventhouse / UDF, frontend 3D map; contract v4.4

## 1. Context

The 3D map needed stop and approaching-bus positions. Gold already exposed ETA slots (`eta_seconds_1/2`, `bus_id_1/2`) under [ADR-022](ADR-022-gold-eta-exposes-two-slots-under-one-table-constraint.md) but **no coordinates**. The frontend used a static mock (`geoData.ts`). Live Arrive payloads include GeoJSON `geometry` (Point, `coordinates` = `[lon, lat]`), verified on production samples. Silver already denormalizes GTFS `stop_lat` / `stop_lon`.

## 2. Alternatives Considered

- **A — Frontend mock only** (approximate stop points / sketched lines): Fast; not real-time; not reusable by Agent/Semantic.
- **B — Expose real coords on Gold:** `stop_lat`/`stop_lon` from Silver (GTFS denorm); `bus_lat_1/2`·`bus_lon_1/2` from Arrive `geometry`, aligned with ETA slots 1/2. Keep one Gold table and grain.
- **C — Separate map table or opaque GeoJSON blob column:** Flexible; weaker for SQL Agent and duplicate serving surface.

## 3. Decision

Adopt **B** (PO: Jonathan Brasales).

Rules:

1. **Stop coords:** project existing Silver `stop_lat`/`stop_lon` onto Gold (same denorm pattern as `stop_name`).
2. **Bus coords:** parse Arrive `geometry` → Silver `bus_lat`/`bus_lon` per poll row; Gold slots `_1`/`_2` follow the same vehicles as `bus_id_1/2` / `eta_seconds_1/2`.
3. **Coordinate order:** GeoJSON `[lon, lat]` — do not swap.
4. **NULL:** missing/invalid geometry → `bus_lat_*`/`bus_lon_*` NULL; ETA/`bus_id_*` may still be set.
5. **Grain / ownership unchanged:** PK `(stop_id, line_id, direction_id)`; arrives path owns ETA+map bus cols; alerts path does not clear them.
6. **Serving SoT:** Eventhouse Gold first ([phase4-rti.md](../phase4-rti.md)); Lakehouse column parity optional/later.
7. **Arrive field policy:** `geometry` is **in use**. `deviation` / `positionTypeBus` / `isHead` remain unused per [ADR-003](ADR-003-arrive-field-policy-unused-no-apply-fields-and-undefined-dev.md).

## 4. Consequences

- **Pros:** Map and Agent share one serving table; no mock as SoT; fits ADR-022 two-slot model.
- **Cons:** Schema bump (contract v4.4); Eventhouse `.create-merge` appends columns — rebuild Gold if `project` order differs; old Silver rows lack `bus_*` until re-poll.

## 5. Amended / Superseded by

- Extends [ADR-022](ADR-022-gold-eta-exposes-two-slots-under-one-table-constraint.md) (coords on the same slots).
- Clarifies [ADR-003](ADR-003-arrive-field-policy-unused-no-apply-fields-and-undefined-dev.md): `geometry` allowed; unused list unchanged.
- Column list: [data-source-contract-v4.md](../data-source-contract-v4.md) v4.4.
