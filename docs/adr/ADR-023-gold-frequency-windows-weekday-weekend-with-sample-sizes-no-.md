# ADR-023: Gold frequency windows weekday/weekend with sample sizes; no freq_window_desc

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** Gold freq_* , US-08

## 1. Context

Need agent-readable frequency without peak labels. Debated whether `freq_sample_size` and `freq_window_desc` belong on Gold given Semantic is out of scope and Data Agent typically sees Gold(+Semantic).

## 2. Alternatives Considered

- **A — Only `freq_observed_minutes`:** Minimal; no trust signal.
- **B — Weekday/weekend observed minutes + sample sizes on Gold; no free-text `freq_window_desc`; use `day_type` codes:** Agent-complete on Gold.
- **C — Compute sample size only in notebooks:** Invisible to Gold-only agent.

## 3. Decision

Adopt **B**. Columns: `freq_observed_weekday_min`, `freq_observed_weekend_min`, `freq_sample_size_weekday`, `freq_sample_size_weekend`. `day_type` is one of `LA` | `SA` | `FE`. No daily total trip counts. Sample size = valid observations (`bus_id IS NOT NULL`), not daily vehicle count.

## 4. Consequences

- **Pros:** Agent can refuse when sample_size < 20; day type is coded.
- **Cons:** Extra columns; two sample counters to maintain.

## 5. Amended / Superseded by

- History: User first argued sample_size could be queried ad hoc / via Semantic; then accepted Gold columns because Fabric Data Agent is Gold(+Semantic)-centric and Semantic is not in scope yet.
- `freq_window_desc` considered then rejected in favor of `day_type` enum.
