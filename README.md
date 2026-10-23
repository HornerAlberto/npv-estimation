# npv-estimation

NPV model for the value proposition of an internal R&D project at a consultancy firm.

## Quickstart

```bash
uv run streamlit run streamlit_app.py
```

Then open the **Quickstart** tab in the app, or read [docs/quickstart.md](docs/quickstart.md).

## Contents

- [docs/quickstart.md](docs/quickstart.md): how to use the app
- [docs/business-context.md](docs/business-context.md): purpose, assumptions, cost and benefit model, parameters
- [docs/scenarios.md](docs/scenarios.md): the four benefit scenarios
- `streamlit_app.py`: interactive app with three views (investment case, monthly budget, robustness), a cost editor and a scenario editor
- `rd_value.py`: monthly flow model for the R&D project (costs, benefits, payback, break-even)
- `charts.py`: Altair chart builders used by the app
- `npv.py`: NPV calculation (annual rate, per-period cash flows: year, semester, month, week)
- `npv_estimation.ipynb`: worked examples of `npv.py`

Run the tests with `uv run pytest`.
