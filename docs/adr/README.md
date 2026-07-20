# Architecture Decision Records (ADR)

Decisions from the EMT Madrid Fabric medallion schema conversation (2026-07-20).

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-001](ADR-001-single-consolidated-emt-data-reference-before-extraction-dec.md) | Single consolidated EMT data reference before extraction decisions | Accepted |
| [ADR-002](ADR-002-require-both-apidocs-and-m360-swagger-for-arrive-field-seman.md) | Require both apidocs and m360 swagger for Arrive field semantics | Accepted |
| [ADR-003](ADR-003-arrive-field-policy-unused-no-apply-fields-and-undefined-dev.md) | Arrive field policy: unused No-apply fields and undefined deviation | Accepted |
| [ADR-004](ADR-004-close-emt-path-a-b-vs-gtfs-direction-id-mapping-for-lines-02.md) | Close EMT path A/B vs GTFS direction_id mapping for lines 027 and 014 | Accepted |
| [ADR-005](ADR-005-source-taxonomy-s1-rest-only-s2-rt-servicealerts-s3-gtfs.md) | Source taxonomy: S1 REST only, S2 RT servicealerts, S3 GTFS | Accepted |
| [ADR-006](ADR-006-product-scope-emt-city-bus-rest-plus-gtfs-rt-service-alerts-.md) | Product scope: EMT city bus REST plus GTFS-RT service alerts only | Accepted |
| [ADR-007](ADR-007-geographic-scope-puerta-del-sol-geofence-600m-with-52-in-sco.md) | Geographic scope: Puerta del Sol geofence 600m with 52 in-scope stops | Accepted |
| [ADR-008](ADR-008-timezone-europe-madrid-for-calendar-day-type-and-alert-activ.md) | Timezone Europe/Madrid for calendar day type and alert activity | Accepted |
| [ADR-009](ADR-009-served-stop-sot-is-s1-line-stops-path-not-gtfs-alone.md) | Served-stop SoT is S1 line stops path not GTFS alone | Accepted |
| [ADR-010](ADR-010-eta-sot-is-post-arrives-only.md) | ETA SoT is POST arrives only | Accepted |
| [ADR-011](ADR-011-disruption-sot-is-gtfs-rt-servicealerts-not-arrive-incident.md) | Disruption SoT is GTFS-RT servicealerts not Arrive Incident | Accepted |
| [ADR-012](ADR-012-frequency-sot-is-observed-silver-polls-with-no-planned-fallb.md) | Frequency SoT is observed Silver polls with no planned fallback | Accepted |
| [ADR-013](ADR-013-stop-search-catalog-gtfs-primary-with-emt-name-enrichment.md) | Stop search catalog: GTFS primary with EMT name enrichment | Accepted |
| [ADR-014](ADR-014-ask-back-rules-for-missing-direction-and-ambiguous-place-nam.md) | Ask-back rules for missing direction and ambiguous place names | Accepted |
| [ADR-015](ADR-015-medallion-physical-schema-one-bronze-one-silver-one-gold-tab.md) | Medallion physical schema: one Bronze, one Silver, one Gold table | Accepted |
| [ADR-016](ADR-016-silver-is-append-only-poll-fact-wide-rows-not-polymorphic-re.md) | Silver is append-only poll fact wide rows not polymorphic record_type | Accepted |
| [ADR-017](ADR-017-bronze-holds-rest-and-rt-payloads-only-gtfs-bootstraps-silve.md) | Bronze holds REST and RT payloads only; GTFS bootstraps Silver | Accepted |
| [ADR-018](ADR-018-bronze-contract-uuid-ingest-id-and-no-enforced-column-types.md) | Bronze contract: UUID ingest_id and no enforced column types | Accepted |
| [ADR-019](ADR-019-direction-grain-key-is-direction-id-only.md) | Direction grain key is direction_id only | Accepted |
| [ADR-020](ADR-020-stop-id-stored-as-string-for-stability-and-portability.md) | stop_id stored as string for stability and portability | Accepted |
| [ADR-021](ADR-021-line-id-vs-line-label-and-failed-arrive-label-resolution-exc.md) | line_id vs line_label and failed Arrive label resolution excludes Gold | Accepted |
| [ADR-022](ADR-022-gold-eta-exposes-two-slots-under-one-table-constraint.md) | Gold ETA exposes two slots under one-table constraint | Accepted |
| [ADR-023](ADR-023-gold-frequency-windows-weekday-weekend-with-sample-sizes-no-.md) | Gold frequency windows weekday/weekend with sample sizes; no freq_window_desc | Accepted |
| [ADR-024](ADR-024-observed-frequency-aggregation-grain-is-line-id-plus-day-typ.md) | Observed frequency aggregation grain is line_id plus day-type window | Accepted |
| [ADR-025](ADR-025-observed-headway-formula-is-median-of-successive-gaps-in-min.md) | Observed headway formula is median of successive gaps in minutes | Accepted |
| [ADR-026](ADR-026-map-arrive-destination-to-direction-id-require-path-mapping-.md) | Map Arrive destination to direction_id; require path mapping at seed | Accepted |
| [ADR-027](ADR-027-alerts-denormalized-onto-gold-rows-at-line-grain-under-one-t.md) | Alerts denormalized onto Gold rows at line grain under one-table rule | Accepted |
| [ADR-028](ADR-028-freshness-is-stale-after-180-seconds-no-gold-in-scope-column.md) | Freshness is_stale after 180 seconds; no Gold in_scope column | Accepted |
| [ADR-029](ADR-029-polling-cadences-arrives-60s-try-and-adjust-rt-300s.md) | Polling cadences: arrives ~60s try-and-adjust; RT 300s | Accepted |
| [ADR-030](ADR-030-frequency-response-gate-20-observations-preferred-24h-warmup.md) | Frequency response gate: 20 observations preferred; 24h warmup guide | Accepted |
| [ADR-031](ADR-031-semantic-model-kpi-and-quality-logs-stay-outside-emt-domain-.md) | Semantic model, KPI, and quality logs stay outside EMT domain Gold | Accepted |
| [ADR-032](ADR-032-quality-log-metrics-e2e-latency-and-exito-definition-for-poc.md) | Quality-log metrics: E2E latency and éxito definition for POC | Accepted |
| [ADR-033](ADR-033-us-03-name-resolution-may-stay-outside-gold-no-schema-change.md) | US-03 name resolution may stay outside Gold; no schema change for POC | Accepted |
| [ADR-034](ADR-034-documentation-language-team-agreement-not-stakeholder-approv.md) | Documentation language: team agreement not stakeholder-approval theater | Accepted |
| [ADR-035](ADR-035-verification-plan-v2-is-fixed-results-go-to-reports-not-plan.md) | Verification plan v2 is fixed; results go to reports not plan edits | Accepted |
| [ADR-036](ADR-036-no-peak-or-off-peak-labels-no-daily-total-vehicle-counts-in-.md) | No peak or off-peak labels; no daily total vehicle counts in scope | Accepted |

Author on all records: **Mirae Kang**.
