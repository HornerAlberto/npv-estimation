# Benefit scenarios

Benefits are analysed in four scenarios: two over a short window (1 year) and two over
a three-year window. See [business-context.md](business-context.md) for the benefit
formula and assumptions.

All opportunities are **additive and persistent** (they stay active until the end of the
horizon). Costs (opportunity cost of the R&D team + monthly investment) apply in every
month of each horizon.

## Definitions

1. **Short window (12 months).** After four months, the R&D finds an opportunity and
   4 consultants are allocated to it. Benefits are zero for the first four months and
   4 × full-time billing for the last 8 months.
2. **Short window (12 months).** After three months, an opportunity onboards 3 full-time
   consultants. Then, at month 6, a strong opportunity onboards 7 more.
3. **Three years (36 months).** Scenario 1, plus a new opportunity for 5 consultants in
   the second year and another for 4 in the third year.
4. **Three years (36 months).** Scenario 2, plus a new opportunity for 9 consultants in
   the second year and another for 5 in the third year.

Opportunities in the second and third years start in the **first month** of that year
(months 13 and 25).

## Opportunities as data

| Scenario | Horizon | Opportunities (start month: consultants) |
|---|---|---|
| 1 | 12 | m5: 4 |
| 2 | 12 | m4: 3, m6: 7 |
| 3 | 36 | m5: 4, m13: 5, m25: 4 |
| 4 | 36 | m4: 3, m6: 7, m13: 9, m25: 5 |

## Consultants billing on R&D-generated work, by month

| Scenario | 1–3 | 4 | 5 | 6–12 | 13–24 | 25–36 |
|---|---|---|---|---|---|---|
| 1 | 0 | 0 | 4 | 4 | – | – |
| 2 | 0 | 3 | 3 | 10 | – | – |
| 3 | 0 | 0 | 4 | 4 | 9 | 13 |
| 4 | 0 | 3 | 3 | 10 | 19 | 24 |

## Open question

**Start-month convention.** In scenario 1, "after four months" means billing starts in
month 5 (the first four months are zero), and "after three months" in scenario 2 was
read the same way (month 4). The second opportunity in scenario 2 was confirmed as
**month 6**, which follows a different convention (by the scenario 1 rule it would be
month 7). Confirm whether month 6 is intended.
