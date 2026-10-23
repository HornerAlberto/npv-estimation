# Business context and methodology

## Purpose

Build the value proposition for an **internal R&D project** at a consultancy firm.
The question is whether dedicating consultants and budget to R&D creates more value
than keeping those consultants on client work. The answer is expressed as a **net
present value (NPV)** of monthly flows, evaluated under several benefit scenarios
(see [scenarios.md](scenarios.md)).

## Perspective and key assumptions

- **Internal budget view, pre-tax.** Everything is calculated as the budget of an
  internal team. Taxes are ignored.
  - This is defensible for a go/no-go decision: with a flat tax rate *t* on both costs
    and benefits, after-tax NPV = (1 − t) × pre-tax NPV, so the sign (the decision)
    does not change.
  - Consistency rule: pre-tax flows must be discounted with a **pre-tax** rate.
  - Not modelled, but worth mentioning as upside: **R&D tax credits/deductions**, which
    would make the project more attractive than the pre-tax view shows.
- **Incremental (economic) flows, not accounting cash flows.** The largest cost is
  revenue the firm gives up (opportunity cost), not money it pays out. In project
  appraisal this still counts, because every incremental effect of the decision is
  included. In the write-up, describe the flows as *net incremental flows* and state
  that the opportunity cost is forgone billing.

## Monthly flow model

For each month *t* = 1 … horizon:

```
net_flow(t) = benefit(t) − monthly_investment − opportunity_cost
```

There is no flow at t = 0 (CF₀ = 0).

### Costs (constant, every month of the horizon)

1. **Opportunity cost of the R&D team.** The consultants on R&D could otherwise be
   billing clients.

   ```
   opportunity_cost = n_rd_consultants × billing_rate_monthly × occupation × dedication
   ```

   - `billing_rate_monthly` is the **billing rate** (what clients pay per consultant per
     month), not the salary. Salaries are paid either way, so they are not incremental.
     Do not add salaries on top of forgone billing; that would double-count.
     - Exception: if people are *hired* for the R&D team, their cost is their salary
       (there is no forgone billing).
   - `occupation` = **0.73**, the firm's occupation KPI. Without the R&D project,
     consultants would only bill about 73% of their time, so this avoids overstating
     the loss.
   - `dedication` = share of each R&D consultant's time spent on R&D (1.0 = full time).
   - Optional refinement: if client projects carry variable costs (travel,
     subcontractors), the forgone amount is billing minus those costs.

2. **Monthly investment.** Direct R&D operating costs **other than consultants' time**,
   e.g. software licences and cloud computing resources.

### Benefits

The R&D work generates new client **opportunities**. Each opportunity has a start month
and a number of full-time consultants staffed on it.

```
benefit(t) = billing_rate_monthly × benefit_margin × Σ consultants of opportunities active in month t
```

- Opportunities are **additive and persistent**: once one starts, it stays active until
  the end of the horizon, and later opportunities add to it.
- Benefits are at **full billing** (`benefit_margin` = 1.0, no occupation factor). This
  assumes the new work is staffed from bench time or new hires, so its revenue is
  genuinely new.
- `benefit_margin` is a parameter for sensitivity analysis. A reviewer could argue that
  consultants staffed on the new work would otherwise have billed other clients, so only
  part of the revenue is incremental; lowering the margin tests that. **This is the
  assumption most likely to be challenged in the value proposition.**

## Discounting

- Uses `npv.py` with the textbook formula: NPV = Σ CFₜ / (1 + r_p)ᵗ, with CF₀ at t = 0
  undiscounted (this differs from Excel's `NPV()`, which discounts the first value).
- The discount rate is **annual** (pre-tax hurdle rate) and converted to the period
  length with effective compounding: r_p = (1 + r_annual)^(1/n) − 1.
- Periods: year (n = 1), semester (n = 2), month (n = 12), week (n = 52). The R&D
  model uses months.

### Why timing matters

If costs and benefits were constant from month 1, NPV = monthly net flow × annuity
factor, and the discount rate could never change the decision. NPV only adds
information because benefits arrive later than costs (costs start in month 1, benefits
only once opportunities appear). Discounting is what penalises waiting for them.

## Parameters

| Parameter | Meaning | Default / example |
|---|---|---|
| `n_rd_consultants` | Consultants working on R&D | to be provided |
| `billing_rate_monthly` | Billing per full-time consultant per month | to be provided |
| `occupation` | Occupation KPI | 0.73 |
| `dedication` | Share of R&D consultants' time on R&D | 1.0 |
| `monthly_investment` | Direct R&D operating costs (licences, cloud) | to be provided |
| `opportunities` | List of (start month, consultants) | per scenario |
| `horizon_months` | Analysis window | 12 or 36 (per scenario) |
| `benefit_margin` | Share of new billing counted as benefit | 1.0 |
| `annual_rate` | Pre-tax annual discount rate | to be provided |

## Implementation

- `npv.py`: NPV with the `"month"` period (n = 12).
- `rd_value.py`: `monthly_flows(...)` returns benefit, opportunity cost, direct costs,
  net flow and discounting per month; `summarize(...)` adds payback and peak funding
  need; break-even benefit margin and team size. The four scenarios are defined as data.
- Direct costs are a list of items (name, type, monthly amount, start and end month), so
  they can be broken down by type.
- `streamlit_app.py`: interactive app; see [quickstart.md](quickstart.md).
