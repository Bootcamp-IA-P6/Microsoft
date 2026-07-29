# ADR-005: Source taxonomy: S1 REST only, S2 RT servicealerts, S3 GTFS

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** All docs, pipeline labeling, Bronze source_system

## 1. Context

Service Alerts protobuf is served from an EMT host URL but is the Mobility Database mdb-3102 producer. Early docs incorrectly labeled RT as part of S1 (EMT OpenAPI), mixing REST product APIs with the RT feed.

## 2. Alternatives Considered

- **A — S1 = EMT host everything (REST + RT):** Matches hostname; confuses SoT ownership.
- **B — S1 = EMT OpenAPI REST only; S2 = mdb-3102 GTFS-RT proto (+ catalog meta); S3 = GTFS static:** Matches product roles.

## 3. Decision

Adopt **B**. Producer URL may live on `openapi.emtmadrid.es`, but alert **payload SoT** is S2. MDB Catalog API JSON body is not SoT.

## 4. Consequences

- **Pros:** Clear SoT for US-07 vs REST ETA.
- **Cons:** Readers must not equate hostname with source id.

## 5. Amended / Superseded by

- Amends earlier `us-source-comparison` / reference wording that bundled RT under S1.
- Schema taxonomy updated after this correction (see ADR-015+).
