"""R&D value proposition explorer.

Run with: uv run streamlit run streamlit_app.py
"""

from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

import charts
from charts import Style, compact_money
from rd_value import (
    COST_TYPES,
    DEFAULT_COSTS,
    DEFAULT_SCENARIOS,
    OPPORTUNITY_COST,
    CostItem,
    Opportunity,
    Params,
    Scenario,
    break_even_margin,
    break_even_team_size,
    cost_breakdown,
    monthly_flows,
    npv_of,
    opportunity_cost,
    summarize,
)

QUICKSTART = Path(__file__).parent / "docs" / "quickstart.md"
MAX_SCENARIOS = 8
MAX_HORIZON = 120

st.set_page_config(page_title="R&D value proposition", page_icon=":material/science:", layout="wide")


# ---------------------------------------------------------------- defaults & state

def default_scenarios_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Scenario": [s.name for s in DEFAULT_SCENARIOS],
            "Horizon (months)": [s.horizon_months for s in DEFAULT_SCENARIOS],
        }
    )


def default_opportunities_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Scenario": s.name, "Start month": o.start_month, "Consultants": float(o.consultants)}
            for s in DEFAULT_SCENARIOS
            for o in s.opportunities
        ]
    )


def default_costs_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Name": c.name,
                "Type": c.cost_type,
                "Monthly amount": float(c.monthly_amount),
                "Start month": c.start_month,
                "End month": np.nan if c.end_month is None else float(c.end_month),
            }
            for c in DEFAULT_COSTS
        ]
    )


DEFAULT_PARAMS = Params()
WIDGET_DEFAULTS = {
    "currency": "€",
    "n_rd": int(DEFAULT_PARAMS.n_rd_consultants),
    "dedication": int(DEFAULT_PARAMS.dedication * 100),
    "billing": float(DEFAULT_PARAMS.billing_rate_monthly),
    "occupation": int(DEFAULT_PARAMS.occupation * 100),
    "margin": int(DEFAULT_PARAMS.benefit_margin * 100),
    "rate": float(DEFAULT_PARAMS.annual_rate * 100),
}
EDITOR_KEYS = ["scenarios_editor", "opportunities_editor", "costs_editor"]


def reset_all() -> None:
    for key in [*WIDGET_DEFAULTS, *EDITOR_KEYS, "visible", "focus"]:
        st.session_state.pop(key, None)


for key, value in WIDGET_DEFAULTS.items():
    st.session_state.setdefault(key, value)


# ---------------------------------------------------------------- sidebar: parameters

with st.sidebar:
    st.header("Parameters")

    st.subheader(":material/groups: R&D team", divider="gray")
    st.number_input("Consultants on R&D", min_value=0, max_value=100, step=1, key="n_rd")
    st.slider("Dedication to R&D", 0, 100, format="%d%%", key="dedication",
              help="Share of each R&D consultant's time spent on the project.")

    st.subheader(":material/payments: Billing", divider="gray")
    st.selectbox("Currency", ["€", "$", "£"], key="currency")
    st.number_input("Billing rate per consultant per month", min_value=0.0, step=500.0, format="%.0f", key="billing",
                    help="What a client pays for one full-time consultant for a month. Not the salary.")
    st.slider("Occupation KPI", 0, 100, format="%d%%", key="occupation",
              help="Share of time consultants would bill clients if they were not on R&D. Scales the opportunity cost.")

    st.subheader(":material/trending_up: Benefit", divider="gray")
    st.slider("Benefit margin", 0, 100, format="%d%%", key="margin",
              help="Share of the new billing counted as benefit. 100% = full billing; lower it to test a conservative case.")

    st.subheader(":material/percent: Discounting", divider="gray")
    st.slider("Annual discount rate (pre-tax)", 0.0, 40.0, step=0.5, format="%.1f%%", key="rate",
              help="Pre-tax hurdle rate. Converted to a monthly rate with effective compounding.")

    st.button("Reset everything", icon=":material/restart_alt:", on_click=reset_all, width="stretch")

cur = st.session_state.currency
params = Params(
    n_rd_consultants=st.session_state.n_rd,
    billing_rate_monthly=st.session_state.billing,
    occupation=st.session_state.occupation / 100,
    dedication=st.session_state.dedication / 100,
    benefit_margin=st.session_state.margin / 100,
    annual_rate=st.session_state.rate / 100,
)
style = Style(st.context.theme.type or "light", cur)


def money(v: float) -> str:
    return f"{'−' if v < 0 else ''}{cur}{abs(v):,.0f}"


# ---------------------------------------------------------------- page

st.title("R&D value proposition")
st.caption(
    "Net present value of an internal R&D team: forgone client billing and direct costs "
    "versus the client work the R&D generates. Change the parameters in the sidebar; "
    "edit costs and scenarios in their tabs. New here? Open **Quickstart**."
)

picker = st.container()  # scenario chips, filled once the scenario table is read

tab_case, tab_month, tab_risk, tab_costs, tab_scen, tab_guide = st.tabs(
    [
        ":material/insights: Investment case",
        ":material/calendar_month: Monthly budget",
        ":material/shield: Robustness",
        ":material/receipt_long: Costs",
        ":material/account_tree: Scenarios",
        ":material/menu_book: Quickstart",
    ]
)

# ---------------------------------------------------------------- inputs: costs & scenarios
# Editors are drawn first because every view depends on them.

with tab_costs:
    st.subheader("Direct monthly costs")
    st.markdown(
        "Everything the R&D costs **apart from consultants' time** (that is the opportunity cost, "
        "set in the sidebar). Add a row per cost. Leave **End month** empty for costs that run "
        "for the whole horizon; set start = end for a one-off cost."
    )
    costs_df = st.data_editor(
        default_costs_df(),
        key="costs_editor",
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "Name": st.column_config.TextColumn("Name", required=True, width="medium"),
            "Type": st.column_config.SelectboxColumn("Type", options=COST_TYPES, required=True, default="Other"),
            "Monthly amount": st.column_config.NumberColumn(f"Monthly amount ({cur})", min_value=0.0, step=100.0, format="localized", required=True),
            "Start month": st.column_config.NumberColumn("Start month", min_value=1, max_value=MAX_HORIZON, step=1, default=1, required=True),
            "End month": st.column_config.NumberColumn("End month", min_value=1, max_value=MAX_HORIZON, step=1, help="Empty = until the end of the horizon."),
        },
        alt="Editable list of direct monthly R&D costs",
    )

with tab_scen:
    st.subheader("Scenarios")
    st.markdown(
        "Each scenario has a horizon and a list of **opportunities**: client work the R&D generates. "
        "From its start month on, an opportunity bills its consultants full time until the end of the "
        "horizon, and opportunities add up. Add rows to create new scenarios or opportunities."
    )
    left, right = st.columns(2)
    with left:
        scen_df = st.data_editor(
            default_scenarios_df(),
            key="scenarios_editor",
            num_rows="dynamic",
            hide_index=True,
            column_config={
                "Scenario": st.column_config.TextColumn("Scenario", required=True, width="medium"),
                "Horizon (months)": st.column_config.NumberColumn("Horizon (months)", min_value=1, max_value=MAX_HORIZON, step=1, default=12, required=True),
            },
            alt="Editable list of scenarios and their horizons",
        )
    scenario_names = list(dict.fromkeys(str(n).strip() for n in scen_df["Scenario"].dropna() if str(n).strip()))
    with right:
        opp_df = st.data_editor(
            default_opportunities_df(),
            key="opportunities_editor",
            num_rows="dynamic",
            height=420,
            hide_index=True,
            column_config={
                "Scenario": st.column_config.SelectboxColumn("Scenario", options=scenario_names, required=True, width="medium"),
                "Start month": st.column_config.NumberColumn("Start month", min_value=1, max_value=MAX_HORIZON, step=1, default=1, required=True,
                                                             help="First month in which these consultants bill."),
                "Consultants": st.column_config.NumberColumn("Consultants", min_value=0.0, step=1.0, default=1.0, required=True),
            },
            alt="Editable list of opportunities per scenario",
        )


def build_costs(df: pd.DataFrame) -> tuple[CostItem, ...]:
    items = []
    for _, r in df.dropna(subset=["Monthly amount"]).iterrows():
        start = int(r["Start month"]) if pd.notna(r["Start month"]) else 1
        end = int(r["End month"]) if pd.notna(r["End month"]) else None
        items.append(
            CostItem(
                name=str(r["Name"]) if pd.notna(r["Name"]) else "Unnamed cost",
                cost_type=r["Type"] if r["Type"] in COST_TYPES else "Other",
                monthly_amount=float(r["Monthly amount"]),
                start_month=start,
                end_month=end,
            )
        )
    return tuple(items)


def build_scenarios(scen: pd.DataFrame, opps: pd.DataFrame) -> list[Scenario]:
    scenarios = []
    for name in scenario_names:
        horizon = scen.loc[scen["Scenario"].astype(str).str.strip() == name, "Horizon (months)"].iloc[0]
        horizon = int(horizon) if pd.notna(horizon) else 12
        rows = opps[(opps["Scenario"] == name)].dropna(subset=["Start month", "Consultants"])
        scenarios.append(
            Scenario(
                name=name,
                horizon_months=max(1, min(horizon, MAX_HORIZON)),
                opportunities=tuple(Opportunity(int(r["Start month"]), float(r["Consultants"])) for _, r in rows.iterrows()),
            )
        )
    return scenarios


costs = build_costs(costs_df)
scenarios = build_scenarios(scen_df, opp_df)
all_names = [s.name for s in scenarios]

if not scenarios:
    st.warning("Add at least one scenario in the **Scenarios** tab.", icon=":material/warning:")
    st.stop()

# Scenario picker, shared by the views. Colours stay tied to each scenario's position in the full list.
visible = picker.pills(
    "Scenarios to show",
    all_names,
    selection_mode="multi",
    default=all_names[:MAX_SCENARIOS],
    key="visible",
)
visible = [n for n in all_names if n in (visible or [])][:MAX_SCENARIOS]
if not visible:
    picker.info("Select at least one scenario above.", icon=":material/info:")
    st.stop()
shown = [s for s in scenarios if s.name in visible]

summaries = pd.DataFrame([summarize(s, params, costs) for s in shown])

# ---------------------------------------------------------------- view 1: investment case

with tab_case:
    st.subheader("Is it worth it?")
    positive = summaries[summaries["npv"] > 0]
    worst = summaries.loc[summaries["npv"].idxmin()]
    if len(positive) == len(summaries):
        verdict = (
            f"All {len(summaries)} scenarios create value. The weakest, **{worst['scenario']}**, "
            f"has an NPV of **{money(worst['npv'])}**"
            + (f" and pays back in month {worst['payback_month']}." if worst["payback_month"] else ".")
        )
        st.success(verdict, icon=":material/check_circle:")
    elif positive.empty:
        st.error(f"No scenario creates value with these parameters. Best NPV: **{money(summaries['npv'].max())}**.",
                 icon=":material/cancel:")
    else:
        st.warning(
            f"{len(positive)} of {len(summaries)} scenarios create value. "
            f"**{worst['scenario']}** loses **{money(-worst['npv'])}** in present value.",
            icon=":material/warning:",
        )

    cols = st.columns(len(shown), border=True)
    for col, (_, s) in zip(cols, summaries.iterrows()):
        with col:
            st.markdown(f"**{s['scenario']}**")
            st.caption(f"{s['horizon_months']}-month horizon")
            st.metric("NPV", compact_money(s["npv"], cur), help="Present value of benefits minus all costs, discounted monthly.")
            st.metric("Discounted payback", f"Month {s['payback_month']}" if s["payback_month"] else "Not reached",
                      help="First month after which cumulative discounted value stays at or above zero.")
            st.metric("Peak funding need", compact_money(s["max_funding_need"], cur),
                      help="The deepest point of cumulative discounted value: how much the firm carries before payback.")
            st.metric("Consultants billing at the end", f"{s['final_consultants_staffed']:g}",
                      help="Consultants staffed on R&D-generated work in the last month.")

    with st.container(border=True):
        st.markdown("**When does it pay back?** Cumulative discounted value by month")
        cum = pd.concat([monthly_flows(s, params, costs).assign(scenario=s.name) for s in shown], ignore_index=True)
        st.altair_chart(charts.cumulative_value(cum, all_names, style), alt="Cumulative discounted value per scenario by month")
        st.caption("Below zero, the project is still being funded; the crossing point is the discounted payback.")
    with st.container(border=True):
        st.markdown("**Where does the value come from?** Present value of benefits vs costs")
        st.altair_chart(charts.value_bridge(summaries, visible, style), alt="Present value of benefits and costs per scenario, with NPV")
        st.caption("Bars to the right are benefits, to the left costs; the tick marks the NPV.")
    st.caption(
        ":material/info: Scenarios with different horizons are not directly comparable: "
        "a 36-month scenario has more time to recover its costs."
    )

# ---------------------------------------------------------------- view 2: monthly budget

with tab_month:
    st.subheader("What does each month cost and return?")
    focus = st.segmented_control("Scenario", visible, default=visible[0], key="focus", required=True)
    focus = focus if focus in visible else visible[0]
    scenario = next(s for s in shown if s.name == focus)
    flows = monthly_flows(scenario, params, costs)
    breakdown = cost_breakdown(scenario, params, costs)

    positive_months = flows.loc[flows["net_flow"] > 0, "month"]
    with st.container(horizontal=True):
        st.metric("Monthly cost (month 1)", compact_money(flows["total_cost"].iloc[0], cur), border=True,
                  help="Opportunity cost plus direct costs in the first month.")
        st.metric("Opportunity cost per month", compact_money(opportunity_cost(params), cur), border=True,
                  help="R&D consultants × billing rate × occupation × dedication.")
        st.metric("First month with positive net flow", f"Month {positive_months.iloc[0]}" if not positive_months.empty else "None", border=True)
        st.metric("Benefit in the last month", compact_money(flows["benefit"].iloc[-1], cur), border=True)

    with st.container(border=True):
        st.markdown(f"**Monthly flows: {focus}**")
        st.altair_chart(charts.monthly_budget(flows, breakdown, style), alt=f"Monthly benefit, costs by type and net flow for {focus}")
        st.caption("Bars above zero are new billing; bars below are costs stacked by type. The line is the net flow.")

    left, right = st.columns([2, 3])
    with left, st.container(border=True):
        st.markdown("**Leverage:** consultants the R&D puts to work")
        st.altair_chart(charts.staffing(flows, params.n_rd_consultants * params.dedication, style),
                        alt="R&D team size versus consultants billing on generated work")
    with right, st.container(border=True):
        st.markdown("**Month by month**")
        table = flows[["month", "consultants_staffed", "benefit", "opportunity_cost", "direct_costs", "net_flow", "present_value", "cumulative_pv"]]
        st.dataframe(
            table.round(0).assign(consultants_staffed=table["consultants_staffed"]),
            hide_index=True,
            height=260,
            column_config={
                "month": st.column_config.NumberColumn("Month", format="%d"),
                "consultants_staffed": st.column_config.NumberColumn("Consultants billing", format="%.1f"),
                "benefit": st.column_config.NumberColumn(f"Benefit ({cur})", format="localized"),
                "opportunity_cost": st.column_config.NumberColumn(f"Opportunity cost ({cur})", format="localized"),
                "direct_costs": st.column_config.NumberColumn(f"Direct costs ({cur})", format="localized"),
                "net_flow": st.column_config.NumberColumn(f"Net flow ({cur})", format="localized"),
                "present_value": st.column_config.NumberColumn(f"Present value ({cur})", format="localized"),
                "cumulative_pv": st.column_config.NumberColumn(f"Cumulative PV ({cur})", format="localized"),
            },
            alt=f"Monthly flows for {focus}",
        )
        st.download_button("Download CSV", table.to_csv(index=False), file_name="monthly_flows.csv", mime="text/csv",
                           icon=":material/download:")

# ---------------------------------------------------------------- view 3: robustness

with tab_risk:
    st.subheader("What has to be true?")
    st.markdown(
        "How far can the key assumptions move before the project stops creating value? "
        "The dashed line marks the current setting."
    )

    margins = np.arange(0, 101, 5)
    rates = np.arange(0, 41, 2)
    margin_df = pd.DataFrame(
        [{"scenario": s.name, "margin": m, "npv": npv_of(s, replace(params, benefit_margin=m / 100), costs)} for s in shown for m in margins]
    )
    rate_df = pd.DataFrame(
        [{"scenario": s.name, "rate": r, "npv": npv_of(s, replace(params, annual_rate=r / 100), costs)} for s in shown for r in rates]
    )

    left, right = st.columns(2)
    with left, st.container(border=True):
        st.markdown("**How much of the new billing must be real?** NPV vs benefit margin")
        st.altair_chart(charts.sensitivity(margin_df, "margin", "Benefit margin", params.benefit_margin * 100, all_names, style),
                        alt="NPV per scenario as the benefit margin varies")
    with right, st.container(border=True):
        st.markdown("**How demanding can the hurdle rate be?** NPV vs annual discount rate")
        st.altair_chart(charts.sensitivity(rate_df, "rate", "Annual discount rate", params.annual_rate * 100, all_names, style),
                        alt="NPV per scenario as the discount rate varies")

    with st.container(border=True):
        st.markdown("**Break-even points**")
        rows = []
        for s in shown:
            m = break_even_margin(s, params, costs)
            n = break_even_team_size(s, params, costs)
            rows.append(
                {
                    "Scenario": s.name,
                    "NPV": round(npv_of(s, params, costs)),
                    "Break-even benefit margin": m,
                    "Safety buffer": None if m is None else params.benefit_margin - m,
                    "Max R&D team size": n,
                }
            )
        st.dataframe(
            pd.DataFrame(rows),
            hide_index=True,
            column_config={
                "NPV": st.column_config.NumberColumn(f"NPV ({cur})", format="localized"),
                "Break-even benefit margin": st.column_config.NumberColumn(
                    format="percent", help="Share of the new billing that must be real for NPV = 0. Above 100% means it cannot break even."),
                "Safety buffer": st.column_config.NumberColumn(
                    format="percent", help="Current benefit margin minus the break-even margin. Negative = currently losing value."),
                "Max R&D team size": st.column_config.NumberColumn(
                    format="%.1f", help="R&D consultants (at the current dedication) the scenario can carry before NPV turns negative."),
            },
            alt="Break-even benefit margin and maximum R&D team size per scenario",
        )
        st.caption(
            "NPV is linear in both the benefit margin and the team size, so each break-even point is exact. "
            "Taxes are ignored: with a flat tax rate both benefits and costs shrink proportionally, so the sign of the NPV does not change."
        )

# ---------------------------------------------------------------- costs: visuals

with tab_costs:
    horizon = max(s.horizon_months for s in shown)
    horizon_scenario = Scenario("costs", horizon, ())
    include_opp = st.toggle("Include consultant time (opportunity cost)", value=False,
                            help="Off by default so the direct cost types are readable; consultant time usually dwarfs them.")
    breakdown_all = cost_breakdown(horizon_scenario, params, costs)
    if not include_opp:
        breakdown_all = breakdown_all[breakdown_all["cost_type"] != OPPORTUNITY_COST]

    direct_month1 = sum(c.amount_in(1) for c in costs)
    total = breakdown_all["amount"].sum()
    opp_total = opportunity_cost(params) * horizon
    with st.container(horizontal=True):
        st.metric("Direct costs per month (month 1)", compact_money(direct_month1, cur), border=True)
        st.metric("Opportunity cost per month", compact_money(opportunity_cost(params), cur), border=True)
        st.metric(f"Total over {horizon} months", compact_money(total, cur), border=True)
        st.metric("Consultant time share", f"{opp_total / (opp_total + sum(c.amount_in(m) for c in costs for m in range(1, horizon + 1))):.0%}"
                  if opp_total else "0%", border=True, help="Share of all costs that is forgone billing.")

    if breakdown_all.empty:
        st.info("No costs to show. Add a row above or turn on consultant time.", icon=":material/info:")
    else:
        left, right = st.columns([3, 2])
        with left, st.container(border=True):
            st.markdown(f"**Monthly costs by type** (longest selected horizon: {horizon} months)")
            st.altair_chart(charts.costs_over_time(breakdown_all, style), alt="Monthly costs stacked by type")
        with right, st.container(border=True):
            st.markdown("**Total by type**")
            st.altair_chart(charts.costs_by_type(breakdown_all, style), alt="Total cost per type over the horizon")
        with st.expander("Costs by item"):
            items = breakdown_all.groupby(["cost_type", "item"], as_index=False)["amount"].sum().sort_values("amount", ascending=False).round(0)
            st.dataframe(
                items,
                hide_index=True,
                column_config={
                    "cost_type": "Type",
                    "item": "Item",
                    "amount": st.column_config.NumberColumn(f"Total ({cur})", format="localized"),
                },
                alt="Total cost per item over the horizon",
            )

# ---------------------------------------------------------------- scenarios: preview

with tab_scen:
    with st.container(border=True):
        st.markdown("**Consultants billing on generated work**, per scenario")
        staffing_df = pd.DataFrame(
            [{"scenario": s.name, "month": m, "consultants": sum(o.consultants for o in s.opportunities if o.start_month <= m)}
             for s in shown for m in range(1, s.horizon_months + 1)]
        )
        st.altair_chart(charts.scenario_staffing(staffing_df, all_names, style), alt="Consultants billing on generated work by scenario")
    st.caption(
        ":material/help: Open question: the second opportunity in scenario 2 starts in month 6 as stated. "
        "By the scenario 1 convention (\"after N months\" = month N+1) it would be month 7. Change it above to compare."
    )

# ---------------------------------------------------------------- quickstart

with tab_guide:
    st.markdown(QUICKSTART.read_text(encoding="utf-8"))
