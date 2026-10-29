# Quickstart

This app estimates the **net present value (NPV)** of an internal R&D team. It weighs the client billing the firm gives up, plus direct R&D costs, against the client work the R&D generates. Methodology: `docs/business-context.md`. Scenarios: `docs/scenarios.md`.

## Run it

```bash
uv run streamlit run streamlit_app.py
```

The app opens at http://localhost:8501. Every change recalculates instantly.

## 1. Set the parameters (sidebar)

| Parameter | What it means | Default |
|---|---|---|
| Consultants on R&D | People on the R&D team | 3 |
| Dedication to R&D | Share of their time on R&D | 100% |
| Currency | Display only | € |
| Billing rate per consultant per month | What a client pays for one full-time consultant for a month (**not** the salary) | 12,000 |
| Occupation KPI | Share of time consultants bill clients in the normal course of business | 73% |
| Compare deployed consultants against the occupation KPI | Count what consultants staffed on new work would have billed anyway (see below) | On |
| Benefit margin | Share of the full billing rate realised on the new work | 100% |
| Annual discount rate | Pre-tax hurdle rate, converted to a monthly rate | 12% |

Two opportunity costs are counted:

- **R&D team time:** R&D consultants × billing rate × occupation × dedication, every month.
- **Deployed consultants' baseline:** consultants staffed on R&D-generated work would have billed at the occupation KPI anyway. With 4 consultants on a new project, the comparison is against those 4 billing at 73%, so only billing above that baseline is a gain. The toggle turns this off.

The defaults are placeholders: replace them with your firm's figures.

At the top of the page, **Analysis window** switches between **1 year**, **2 years** and **3 years**. Every scenario is evaluated over the same window.

## 2. Add your monthly costs (Costs tab)

List everything the R&D costs **apart from consultants' time**, such as licences and cloud computing.

- **Add a cost:** click the **+** below the table and fill in name, type, monthly amount and start month.
- **End month:** leave it empty for a cost that runs for the whole window. Set start = end for a one-off cost.
- **Delete a cost:** select the row and press the delete icon.
- **Totals row:** below the table, the sum of the monthly amounts, the costs active in month 1 and the total over the window.
- The charts show monthly costs **stacked by type** and the **total per type**. Toggle *Include R&D team time* to see how much of the cost is forgone billing.

Types: Licences, Cloud computing, Tools & equipment, Training, External services, Other.

## 3. Review or create scenarios (Scenarios tab)

A scenario is a description plus a list of **opportunities**: client work the R&D generates, given as a start month and a number of consultants. There are three: **Pessimistic**, **Realistic** and **Optimistic**. Their descriptions are shown on the Investment case cards and in the Scenarios tab; details are in `docs/scenarios.md`.

- From its start month on, an opportunity bills its consultants **full time until the end of the window**, and opportunities **add up**.
- **New scenario:** type a name, keep *Based on: Realistic* (or pick another), and press **Create scenario**. It copies that scenario's opportunities, which you can then edit in the opportunities table.
- Edit any scenario's description or opportunities directly in the tables.
- The chart below the tables shows the staffing each scenario produces.

## 4. Read the three views

Pick which scenarios to show with the chips at the top of the page.

### Investment case: *is it worth it?*
- **Verdict banner:** how many scenarios create value, and the weakest one.
- **Cards per scenario:**
  - NPV.
  - Discounted payback: the month after which cumulative value stays positive.
  - Peak funding need: how much the firm carries before payback.
  - Consultants billing at the end.
- **Cumulative discounted value:** where each line crosses zero is its payback. Hover to compare scenarios month by month.
- **Value bridge:** the present value of benefits (right) against R&D team time, the deployed consultants' baseline and direct costs (left), with the NPV marked.

### Monthly budget: *what does each month cost and return?*
- Choose one scenario. Its description is shown below the selector.
- The main chart shows the benefit above zero, costs **stacked by type** below zero (including the deployed consultants' baseline), and the net flow as a line. The net flow is above zero only when the new work beats what those consultants would have billed anyway.
- **Discounted cash flows:** turn this on to show every amount as a present value. The bars then add up to the NPV.
- **Leverage** compares the R&D team size with the consultants it puts to work on client projects.
- The table shows every month in full. **Download CSV** exports it.

### Robustness: *what has to be true?*
- **NPV vs benefit margin:** how much of the full billing rate must be realised on the new work for the project to pay off.
- **NPV vs discount rate:** how demanding the hurdle rate can be.
- **Break-even table:**
  - Break-even benefit margin.
  - Safety buffer: the current margin minus the break-even margin.
  - Maximum R&D team size before NPV turns negative.

### Validation: *how is the NPV calculated?*
- A step-by-step, formula-style check of the **Realistic** scenario with the current parameters:
  1. The monthly discount rate.
  2. The cash flow formula.
  3. The discounted cash flow in the last month of each year (months 12, 24 and 36).
  4. The full NPV sum.
- A cross-check confirms that the independent `npv()` function, the sum of discounted flows and the Investment case figure agree.

## Tips

- **Conservative case:** lower the *Benefit margin* (for example to 90%) to test discounts or slower ramp-up on new work.
- **Partial dedication:** set *Dedication* below 100% if the R&D team keeps some client work.
- **1, 2 or 3 years:** opportunities take time to arrive, so the 1-year window is a much harder test. Compare scenarios over the same window.
- **Your inputs are saved:** the sidebar parameters, the analysis window and the cost table are saved in `.local/state.json` (git-ignored) and restored the next time you open the app. Edits to costs immediately update every view.
- **Start over:** **Reset everything** in the sidebar restores all defaults, including the cost and scenario tables, and overwrites the saved state.

## Assumptions to keep in mind

- **Pre-tax.** This is an internal budget view. A flat tax shrinks benefits and costs alike, so it does not change whether NPV is positive. R&D tax credits would be extra upside.
- **Opportunity cost uses billing, not salary.** Salaries are paid either way, so they are not incremental.
- **Monthly discounting at the end of each month.** There is no flow at month 0.
- **Open question:** in Realistic, the second opportunity starts in month 6 as stated. By the Pessimistic convention it would be month 7. You can switch it in the Scenarios tab.
