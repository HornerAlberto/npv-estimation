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
| Occupation KPI | Share of time consultants would bill if they were not on R&D | 73% |
| Benefit margin | Share of the new billing counted as benefit | 100% |
| Annual discount rate | Pre-tax hurdle rate, converted to a monthly rate | 12% |

The **opportunity cost** per month is consultants × billing rate × occupation × dedication. The defaults are placeholders: replace them with your firm's figures.

## 2. Add your monthly costs (Costs tab)

List everything the R&D costs **apart from consultants' time**, such as licences and cloud computing.

- **Add a cost:** click the **+** below the table and fill in name, type, monthly amount and start month.
- **End month:** leave it empty for a cost that runs for the whole horizon. Set start = end for a one-off cost.
- **Delete a cost:** select the row and press the delete icon.
- The charts show monthly costs **stacked by type** and the **total per type**. Toggle *Include consultant time* to see how much of the cost is forgone billing.

Types: Licences, Cloud computing, Tools & equipment, Training, External services, Other.

## 3. Review or create scenarios (Scenarios tab)

A scenario is a **horizon** plus a list of **opportunities**: client work the R&D generates, given as a start month and a number of consultants.

- From its start month on, an opportunity bills its consultants **full time until the end of the horizon**, and opportunities **add up**.
- Edit the four default scenarios, or add a row in the left table to create a new one, then give it opportunities in the right table.
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
- **Value bridge:** the present value of benefits (right) against consultant time and direct costs (left), with the NPV marked.

### Monthly budget: *what does each month cost and return?*
- Choose one scenario.
- The main chart shows the benefit above zero, costs **stacked by type** below zero, and the net flow as a line.
- **Leverage** compares the R&D team size with the consultants it puts to work on client projects.
- The table shows every month in full. **Download CSV** exports it.

### Robustness: *what has to be true?*
- **NPV vs benefit margin:** how much of the new billing must be genuinely new for the project to pay off.
- **NPV vs discount rate:** how demanding the hurdle rate can be.
- **Break-even table:**
  - Break-even benefit margin.
  - Safety buffer: the current margin minus the break-even margin.
  - Maximum R&D team size before NPV turns negative.

## Tips

- **Conservative case:** lower the *Benefit margin* (for example to 50%). This tests the objection that consultants staffed on the new work would have billed other clients anyway.
- **Partial dedication:** set *Dedication* below 100% if the R&D team keeps some client work.
- **Comparing horizons:** a 36-month scenario has more time to recover its costs than a 12-month one, so compare like with like.
- **Start over:** **Reset everything** in the sidebar restores all defaults, including the cost and scenario tables.

## Assumptions to keep in mind

- **Pre-tax.** This is an internal budget view. A flat tax shrinks benefits and costs alike, so it does not change whether NPV is positive. R&D tax credits would be extra upside.
- **Opportunity cost uses billing, not salary.** Salaries are paid either way, so they are not incremental.
- **Monthly discounting at the end of each month.** There is no flow at month 0.
- **Open question:** the second opportunity in scenario 2 starts in month 6 as stated. By the scenario 1 convention it would be month 7. You can switch it in the Scenarios tab.
