# ADR-007: Geographic scope: Puerta del Sol geofence 600m with 52 in-scope stops

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** Geofence, catalog seed, Gold row existence

## 1. Context

Q13 initially said the disk radius existed but values were not provided. `data-source-contract-v4.md` later supplied closed operational values. Early schema left geofence UNVERIFIED.

## 2. Alternatives Considered

- **A — Leave radius UNVERIFIED:** Blocks seed sizing.
- **B — Adopt contract values (Sol 40.416729,-3.703339, 600m, 52 stops):** Aligns with prior contract.
- **C — Whole Madrid:** Too large for POC poll load.

## 3. Decision

Adopt **B**. Reflect geofence in schema/ops. Gold table contains **only** in-scope combinations — no Gold `in_scope` column (table membership is the filter).

## 4. Consequences

- **Pros:** Finite poll set (~52 stops).
- **Cons:** Outside-fence stops appear “unknown”.

## 5. Amended / Superseded by

- Supersedes Q13 “value not provided yet” for schema purposes.
- Later clarified: do not keep `in_scope` as a Gold column ([ADR-028](ADR-028-freshness-is-stale-after-180-seconds-no-gold-in-scope-column.md)).
