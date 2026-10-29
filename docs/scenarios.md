# Benefit scenarios

There are three scenarios: **pessimistic**, **realistic** and **optimistic**. Each one can
be evaluated over a **1-year or 2-year window**, chosen in the app. See
[business-context.md](business-context.md) for the benefit formula and assumptions.

All opportunities are **additive and persistent**: once one starts, it stays active until
the end of the window, and later opportunities add to it. Costs (the R&D team's
opportunity cost and the monthly direct costs) apply in every month of the window.

## Definitions

1. **Pessimistic.** After four months, the R&D finds an opportunity and 4 consultants are
   allocated to it. In the second year, a new opportunity adds 5 consultants.
2. **Realistic.** After three months, an opportunity onboards 3 full-time consultants.
   Then, at month 6, a strong opportunity onboards 7 more. In the second year, a new
   opportunity adds 9 consultants.
3. **Optimistic** (created for the app as an upside case). The R&D pays off earlier and
   bigger: 4 consultants from month 3 and 8 more from month 6. The second year brings an
   opportunity for 10 consultants at its start and another for 5 at mid-year.

Second-year opportunities start in the **first month** of that year (month 13), except
the optimistic mid-year one (month 19).

The pessimistic and realistic scenarios merge the four original scenarios: original
scenarios 1 and 3 became the pessimistic one, and 2 and 4 the realistic one. The
year-3 opportunities were dropped because the window is now at most two years.

## Opportunities as data

| Scenario | Opportunities (start month: consultants) |
|---|---|
| Pessimistic | m5: 4, m13: 5 |
| Realistic | m4: 3, m6: 7, m13: 9 |
| Optimistic | m3: 4, m6: 8, m13: 10, m19: 5 |

With a 1-year window, opportunities starting after month 12 do not count.

## Consultants billing on R&D-generated work, by month

| Scenario | 1–2 | 3 | 4 | 5 | 6–12 | 13–18 | 19–24 |
|---|---|---|---|---|---|---|---|
| Pessimistic | 0 | 0 | 0 | 4 | 4 | 9 | 9 |
| Realistic | 0 | 0 | 3 | 3 | 10 | 19 | 19 |
| Optimistic | 0 | 4 | 4 | 4 | 12 | 22 | 27 |

## New scenarios

The app can create a new scenario as a copy of an existing one (realistic by default).
Its opportunities can then be edited.

## Open question

**Start-month convention.** In the pessimistic scenario, "after four months" means billing
starts in month 5 (the first four months are zero). "After three months" in the realistic
scenario was read the same way (month 4). The realistic scenario's second opportunity was
confirmed as **month 6**, which follows a different convention: by the pessimistic rule it
would be month 7. Confirm whether month 6 is intended.
