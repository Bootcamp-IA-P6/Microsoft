# ADR-008: Timezone Europe/Madrid for calendar day type and alert activity

- **Date:** 2026-07-20
- **Author:** Mirae Kang
- **Status:** Accepted
- **Components affected:** day_type, alert active_period, agent defaults

## 1. Context

Answers depend on “today” and whether an alert is active now. Server UTC vs Madrid local can disagree near midnight.

## 2. Alternatives Considered

- **A — UTC everywhere:** Simple; wrong local service day.
- **B — Europe/Madrid (Q24=A):** Matches EMT operations.

## 3. Decision

Adopt **B**. Agent must use Gold `day_type` rather than inventing weekday math. Alert activity compares `active_period` to `now(Europe/Madrid)`.

## 4. Consequences

- **Pros:** Consistent day windows for frequency.
- **Cons:** Pipeline must set timezone explicitly in Fabric notebooks.

## 5. Amended / Superseded by

- None at time of writing.
