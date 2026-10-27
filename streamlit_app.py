"""R&D value proposition explorer.

Run with: uv run streamlit run streamlit_app.py
"""

from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

import charts
import local_state
from charts import Style, compact_money
from npv import npv, periodic_rate
from rd_value import (
    COST_TYPES,
    DEFAULT_COSTS,
    DEFAULT_SCENARIOS,
    OPPORTUNITY_COST,
    WINDOWS,
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
MAX_MONTH = max(WINDOWS.values())
TEMPLATE = "Realistic"
CURRENCIES = ["€", "$", "£"]
COST_COLUMNS = ["Name", "Type", "Monthly amount", "Start month", "End month"]
MONEY_COLUMNS = ["benefit", "opportunity_cost", "deployed_cost", "direct_costs", "total_cost", "net_flow"]

st.set_page_config(page_title="R&D value proposition", page_icon=":material/science:", layout="wide")


# ---------------------------------------------------------------- defaults & state

def default_scenarios_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Scenario": [s.name for s in DEFAULT_SCENARIOS],
            "Description": [s.description for s in DEFAULT_SCENARIOS],
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
    "baseline": DEFAULT_PARAMS.count_deployed_baseline,
    "margin": int(DEFAULT_PARAMS.benefit_margin * 100),
    "rate": float(DEFAULT_PARAMS.annual_rate * 100),
    "window": "2 years",
}
# Editors render from these base tables; programmatic changes (new scenario, reset)
# replace a base table and drop the editor's pending edits.
BASE_TABLES = {"scen_base": default_scenarios_df, "opp_base": default_opportunities_df, "cost_base": default_costs_df}
EDITOR_KEYS = ["scenarios_editor", "opportunities_editor", "costs_editor"]


def reset_all() -> None:
    for key in [*WIDGET_DEFAULTS, *BASE_TABLES, *EDITOR_KEYS, "scen_latest", "opp_latest",
                "visible", "focus", "discounted", "new_name", "template"]:
        st.session_state.pop(key, None)


def unique_name(wanted: str, taken: set[str]) -> str:
    name, i = wanted, 2
    while name in taken:
        name, i = f"{wanted} ({i})", i + 1
    return name


def create_scenario() -> None:
    """Add a scenario copying the template's opportunities (callback of the create button)."""
    ss = st.session_state
    scen = ss.get("scen_latest", ss.scen_base).copy()
    opps = ss.get("opp_latest", ss.opp_base).copy()
    template = ss.get("template", TEMPLATE)
    taken = set(scen["Scenario"].dropna().astype(str))
    wanted = (ss.get("new_name") or "").strip() or f"Custom {len(taken) - len(DEFAULT_SCENARIOS) + 1}"
    name = unique_name(wanted, taken)

    new_row = pd.DataFrame([{"Scenario": name, "Description": f"Based on {template}. Edit its opportunities below."}])
    copied = opps[opps["Scenario"] == template].assign(Scenario=name)
    ss.scen_base = pd.concat([scen, new_row], ignore_index=True)
    ss.opp_base = pd.concat([opps, copied], ignore_index=True)
    for key in ["scenarios_editor", "opportunities_editor"]:
        ss.pop(key, None)
    if "visible" in ss:
        ss.visible = [*ss.visible, name]
    ss.new_name = ""
    ss.created = name


def saved_params(saved: dict) -> dict:
    """Saved parameters that still fit the widgets; anything unknown or invalid falls back to its default."""
    params = saved.get("params")
    if not isinstance(params, dict):
        return {}
    valid = {}
    for key, default in WIDGET_DEFAULTS.items():
        value = params.get(key)
        if isinstance(default, bool):
            ok = isinstance(value, bool)
        elif isinstance(default, (int, float)):
            ok = isinstance(value, (int, float)) and not isinstance(value, bool)
            value = type(default)(value) if ok else value
        else:
            ok = isinstance(value, str)
        if ok:
            valid[key] = value
    if valid.get("window") not in WINDOWS:
        valid.pop("window", None)
    if valid.get("currency") not in CURRENCIES:
        valid.pop("currency", None)
    return valid


def saved_costs(saved: dict) -> pd.DataFrame | None:
    rows = saved.get("costs")
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        return None
    df = pd.DataFrame(rows, columns=COST_COLUMNS)
    df[["Name", "Type"]] = df[["Name", "Type"]].astype(object)
    return df.astype({"Monthly amount": float, "Start month": float, "End month": float})


# Restore the last saved parameters and costs once per browser session; "Reset everything"
# then goes back to the defaults (and saves them).
if "state_loaded" not in st.session_state:
    saved = local_state.load_state()
    st.session_state.update(saved_params(saved))
    costs_saved = saved_costs(saved)
    if costs_saved is not None:
        st.session_state.cost_base = costs_saved
    st.session_state.state_loaded = True

for key, value in WIDGET_DEFAULTS.items():
    st.session_state.setdefault(key, value)
for key, factory in BASE_TABLES.items():
    if key not in st.session_state:
        st.session_state[key] = factory()


# ---------------------------------------------------------------- sidebar: parameters

with st.sidebar:
    st.header("Parameters")

    st.subheader(":material/groups: R&D team", divider="gray")
    st.number_input("Consultants on R&D", min_value=0, max_value=100, step=1, key="n_rd")
    st.slider("Dedication to R&D", 0, 100, format="%d%%", key="dedication",
              help="Share of each R&D consultant's time spent on the project.")

    st.subheader(":material/payments: Billing", divider="gray")
    st.selectbox("Currency", CURRENCIES, key="currency")
    st.number_input("Billing rate per consultant per month", min_value=0.0, step=500.0, format="%.0f", key="billing",
                    help="What a client pays for one full-time consultant for a month. Not the salary.")
    st.slider("Occupation KPI", 0, 100, format="%d%%", key="occupation",
              help="Share of time consultants bill clients in the normal course of business. "
                   "Scales the opportunity cost of the R&D team and of deployed consultants.")

    st.subheader(":material/trending_up: Benefit", divider="gray")
    st.toggle("Compare deployed consultants against the occupation KPI", key="baseline",
              help="On: consultants staffed on R&D-generated work would have billed at the occupation KPI anyway, "
                   "so only billing above that baseline counts as gain. Off: their full billing counts.")
    st.slider("Benefit margin", 0, 100, format="%d%%", key="margin",
              help="Share of the full billing rate realised on R&D-generated work. 100% = full rate; "
                   "lower it to test discounts or a conservative case.")

    st.subheader(":material/percent: Discounting", divider="gray")
    st.slider("Annual discount rate (pre-tax)", 0.0, 40.0, step=0.5, format="%.1f%%", key="rate",
              help="Pre-tax hurdle rate. Converted to a monthly rate with effective compounding.")

    st.button("Reset everything", icon=":material/restart_alt:", on_click=reset_all, width="stretch")

cur = st.session_state.currency
# "$" opens math in Markdown and LaTeX; escape it wherever the currency is rendered as text.
md_cur = cur.replace("$", r"\$")
params = Params(
    n_rd_consultants=st.session_state.n_rd,
    billing_rate_monthly=st.session_state.billing,
    occupation=st.session_state.occupation / 100,
    dedication=st.session_state.dedication / 100,
    benefit_margin=st.session_state.margin / 100,
    annual_rate=st.session_state.rate / 100,
    count_deployed_baseline=st.session_state.baseline,
)
style = Style(st.context.theme.type or "light", cur)


def payback_text(month) -> str:
    """Payback month for display; summaries hold it as float or NaN once in a DataFrame."""
    return f"Month {int(month)}" if pd.notna(month) else "Not reached"


def money(v: float) -> str:
    return f"{'−' if v < 0 else ''}{md_cur}{abs(v):,.0f}"


# ---------------------------------------------------------------- page

st.title("R&D value proposition")
st.caption(
    "Net present value of an internal R&D team: forgone client billing and direct costs "
    "versus the client work the R&D generates. Change the parameters in the sidebar; "
    "edit costs and scenarios in their tabs. New here? Open **Quickstart**."
)

top = st.container(horizontal=True, vertical_alignment="bottom", gap="medium")
window_label = top.segmented_control(
    "Analysis window", list(WINDOWS), key="window", required=True,
    help="Narrow or widen the window. Every scenario is evaluated over the same window.",
)
window = WINDOWS[window_label]

tab_case, tab_month, tab_risk, tab_costs, tab_scen, tab_check, tab_guide = st.tabs(
    [
        ":material/insights: Investment case",
        ":material/calendar_month: Monthly budget",
        ":material/shield: Robustness",
        ":material/receipt_long: Costs",
        ":material/account_tree: Scenarios",
        ":material/function: Validation",
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
        "for the whole window; set start = end for a one-off cost."
    )
    costs_df = st.data_editor(
        st.session_state.cost_base,
        key="costs_editor",
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "Name": st.column_config.TextColumn("Name", required=True, width="medium"),
            "Type": st.column_config.SelectboxColumn("Type", options=COST_TYPES, required=True, default="Other"),
            # The label leaves out the currency: changing the column config would drop the edits.
            "Monthly amount": st.column_config.NumberColumn("Monthly amount", help="In the currency chosen in the sidebar.", min_value=0.0, step=100.0, format="localized", required=True),
            "Start month": st.column_config.NumberColumn("Start month", min_value=1, max_value=MAX_MONTH, step=1, default=1, required=True),
            "End month": st.column_config.NumberColumn("End month", min_value=1, max_value=MAX_MONTH, step=1, help="Empty = until the end of the window."),
        },
        alt="Editable list of direct monthly R&D costs",
    )
    st.caption(":material/save: Costs and sidebar parameters are saved on this computer and restored next time you open the app.")

local_state.save_state(
    {key: st.session_state[key] for key in WIDGET_DEFAULTS},
    costs_df[COST_COLUMNS].to_dict("records"),
)

with tab_scen:
    st.subheader("Scenarios")
    st.markdown(
        "Each scenario is a list of **opportunities**: client work the R&D generates. "
        "From its start month on, an opportunity bills its consultants full time until the end of the "
        "window, and opportunities add up. The window (1, 2 or 3 years) is chosen at the top of the page."
    )
    scen_df = st.data_editor(
        st.session_state.scen_base,
        key="scenarios_editor",
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "Scenario": st.column_config.TextColumn("Scenario", required=True, width="medium"),
            "Description": st.column_config.TextColumn("Description", width="large"),
        },
        alt="Editable list of scenarios and their descriptions",
    )
    st.session_state.scen_latest = scen_df
    scenario_names = list(dict.fromkeys(str(n).strip() for n in scen_df["Scenario"].dropna() if str(n).strip()))

    with st.container(border=True):
        st.markdown(f"**New scenario.** Start from a copy of an existing scenario, {TEMPLATE} by default, then edit its opportunities.")
        with st.container(horizontal=True, vertical_alignment="bottom"):
            st.text_input("Name", key="new_name", placeholder="e.g. Custom 1")
            template_options = scenario_names or [TEMPLATE]
            st.selectbox("Based on", template_options,
                         index=template_options.index(TEMPLATE) if TEMPLATE in template_options else 0, key="template")
            st.button("Create scenario", icon=":material/add:", on_click=create_scenario, type="primary", key="create")
        if "created" in st.session_state:
            st.success(f"Created **{st.session_state.pop('created')}**. Its opportunities are in the table below.",
                       icon=":material/check_circle:")

    opp_df = st.data_editor(
        st.session_state.opp_base,
        key="opportunities_editor",
        num_rows="dynamic",
        hide_index=True,
        height=420,
        column_config={
            "Scenario": st.column_config.SelectboxColumn("Scenario", options=scenario_names, required=True, width="medium"),
            "Start month": st.column_config.NumberColumn("Start month", min_value=1, max_value=MAX_MONTH, step=1, default=1, required=True,
                                                         help="First month in which these consultants bill."),
            "Consultants": st.column_config.NumberColumn("Consultants", min_value=0.0, step=1.0, default=1.0, required=True),
        },
        alt="Editable list of opportunities per scenario",
    )
    st.session_state.opp_latest = opp_df


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
        desc = scen.loc[scen["Scenario"].astype(str).str.strip() == name, "Description"].iloc[0]
        rows = opps[(opps["Scenario"] == name)].dropna(subset=["Start month", "Consultants"])
        scenarios.append(
            Scenario(
                name=name,
                horizon_months=window,
                opportunities=tuple(Opportunity(int(r["Start month"]), float(r["Consultants"])) for _, r in rows.iterrows()),
                description=str(desc) if pd.notna(desc) else "",
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
visible = top.pills(
    "Scenarios to show",
    all_names,
    selection_mode="multi",
    default=all_names[:MAX_SCENARIOS],
    key="visible",
)
visible = [n for n in all_names if n in (visible or [])][:MAX_SCENARIOS]
if not visible:
    st.info("Select at least one scenario at the top.", icon=":material/info:")
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
            f"All {len(summaries)} scenarios create value over {window_label}. The weakest, **{worst['scenario']}**, "
            f"has an NPV of **{money(worst['npv'])}**"
            + (f" and pays back in month {int(worst['payback_month'])}." if pd.notna(worst["payback_month"]) else ".")
        )
        st.success(verdict, icon=":material/check_circle:")
    elif positive.empty:
        st.error(f"No scenario creates value over {window_label} with these parameters. "
                 f"Best NPV: **{money(summaries['npv'].max())}**.", icon=":material/cancel:")
    else:
        st.warning(
            f"{len(positive)} of {len(summaries)} scenarios create value over {window_label}. "
            f"**{worst['scenario']}** loses **{money(-worst['npv'])}** in present value.",
            icon=":material/warning:",
        )

    cols = st.columns(len(shown), border=True)
    for col, scenario, (_, s) in zip(cols, shown, summaries.iterrows()):
        with col:
            st.markdown(f"**{s['scenario']}**")
            st.caption(scenario.description or "No description.")
            st.metric("NPV", compact_money(s["npv"], cur), help="Present value of benefits minus all costs, discounted monthly.")
            st.metric("Discounted payback", payback_text(s["payback_month"]),
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

# ---------------------------------------------------------------- view 2: monthly budget

with tab_month:
    st.subheader("What does each month cost and return?")
    with st.container(horizontal=True, vertical_alignment="bottom", gap="medium"):
        focus = st.segmented_control("Scenario", visible, default=visible[0], key="focus", required=True)
        discounted = st.toggle("Discounted cash flows", key="discounted",
                               help="Show every amount as a present value (discounted to today). "
                                    "The bars then add up to the NPV.")
    focus = focus if focus in visible else visible[0]
    scenario = next(s for s in shown if s.name == focus)
    if scenario.description:
        st.caption(scenario.description)
    flows = monthly_flows(scenario, params, costs)
    breakdown = cost_breakdown(scenario, params, costs)

    view, view_breakdown = flows, breakdown
    if discounted:
        view = flows.copy()
        view[MONEY_COLUMNS] = flows[MONEY_COLUMNS].mul(flows["discount_factor"], axis=0)
        view_breakdown = breakdown.merge(flows[["month", "discount_factor"]], on="month")
        view_breakdown["amount"] = view_breakdown["amount"] * view_breakdown["discount_factor"]
    pv = "PV of " if discounted else ""

    positive_months = flows.loc[flows["net_flow"] > 0, "month"]
    with st.container(horizontal=True):
        st.metric("PV of cost in month 1" if discounted else "Cost in month 1", compact_money(view["total_cost"].iloc[0], cur), border=True,
                  help="R&D team opportunity cost plus direct costs in the first month.")
        st.metric("First month with positive net flow", f"Month {positive_months.iloc[0]}" if not positive_months.empty else "None", border=True,
                  help="The first month in which new billing beats all costs, including the deployed consultants' baseline.")
        st.metric("PV of net flow in the last month" if discounted else "Net flow in the last month", compact_money(view["net_flow"].iloc[-1], cur), border=True)
        st.metric("NPV" if discounted else "Sum of net flows (undiscounted)",
                  compact_money(view["net_flow"].sum(), cur), border=True,
                  help="Sum of the monthly net flows shown in the chart.")

    with st.container(border=True):
        st.markdown(f"**{'Discounted monthly' if discounted else 'Monthly'} flows: {focus}**")
        st.altair_chart(charts.monthly_budget(view, view_breakdown, style, "Present value per month" if discounted else "Per month"),
                        alt=f"Monthly benefit, costs by type and net flow for {focus}")
        baseline_note = (
            f" Below zero also sits the **deployed consultants' baseline**: the {params.occupation:.0%} of their billing "
            "they would have produced anyway. The net line is above zero only when the new work beats that baseline."
            if params.count_deployed_baseline else
            " The deployed consultants' baseline is switched off in the sidebar, so their full billing counts as gain."
        )
        st.markdown(
            "Bars above zero are billing on R&D-generated work; below zero, the R&D team's forgone billing and direct "
            "costs, stacked by type." + baseline_note + " The line is the net flow."
            + (" Amounts are discounted to today." if discounted else "")
        )

    left, right = st.columns([2, 3])
    with left, st.container(border=True):
        st.markdown("**Leverage:** consultants the R&D puts to work")
        st.altair_chart(charts.staffing(flows, params.n_rd_consultants * params.dedication, style),
                        alt="R&D team size versus consultants billing on generated work")
    with right, st.container(border=True):
        st.markdown(f"**Month by month**{' (present values)' if discounted else ''}")
        table = view[["month", "consultants_staffed", "benefit", "opportunity_cost", "deployed_cost", "direct_costs", "net_flow", "cumulative_pv"]]
        st.dataframe(
            table.round(0).assign(consultants_staffed=table["consultants_staffed"]),
            hide_index=True,
            height=260,
            column_config={
                "month": st.column_config.NumberColumn("Month", format="%d"),
                "consultants_staffed": st.column_config.NumberColumn("Consultants billing", format="%.1f"),
                "benefit": st.column_config.NumberColumn(f"{pv}Benefit ({cur})", format="localized"),
                "opportunity_cost": st.column_config.NumberColumn(f"{pv}R&D team cost ({cur})", format="localized"),
                "deployed_cost": st.column_config.NumberColumn(f"{pv}Deployed baseline ({cur})", format="localized"),
                "direct_costs": st.column_config.NumberColumn(f"{pv}Direct costs ({cur})", format="localized"),
                "net_flow": st.column_config.NumberColumn(f"{pv}Net flow ({cur})", format="localized"),
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
        st.markdown("**How much of the billing rate must be realised?** NPV vs benefit margin")
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
                    format="percent", help="Share of the billing rate that must be realised for NPV = 0. Above 100% means it cannot break even."),
                "Safety buffer": st.column_config.NumberColumn(
                    format="percent", help="Current benefit margin minus the break-even margin. Negative = currently losing value."),
                "Max R&D team size": st.column_config.NumberColumn(
                    format="%.1f", help="R&D consultants (at the current dedication) the scenario can carry before NPV turns negative. Negative = it cannot break even even without a team."),
            },
            alt="Break-even benefit margin and maximum R&D team size per scenario",
        )
        st.caption(
            "NPV is linear in both the benefit margin and the team size, so each break-even point is exact. "
            "Taxes are ignored: with a flat tax rate both benefits and costs shrink proportionally, so the sign of the NPV does not change."
        )

# ---------------------------------------------------------------- costs: totals & visuals

with tab_costs:
    window_scenario = Scenario("costs", window, ())
    direct_total = sum(c.amount_in(m) for c in costs for m in range(1, window + 1))
    st.dataframe(
        pd.DataFrame(
            [{
                "Total": f"Total ({len(costs)} costs)",
                "Monthly amount": round(sum(c.monthly_amount for c in costs)),
                "Month 1": round(sum(c.amount_in(1) for c in costs)),
                "Window": round(direct_total),
            }]
        ),
        hide_index=True,
        column_config={
            "Total": st.column_config.TextColumn(" ", width="medium"),
            "Monthly amount": st.column_config.NumberColumn(f"Monthly amounts ({cur})", format="localized",
                                                            help="Sum of the monthly amounts of all costs."),
            "Month 1": st.column_config.NumberColumn(f"Active in month 1 ({cur})", format="localized",
                                                     help="Costs actually running in the first month."),
            "Window": st.column_config.NumberColumn(f"Total over {window_label} ({cur})", format="localized",
                                                    help="Every cost over its active months within the window."),
        },
        alt="Totals of the direct monthly costs",
    )

    include_opp = st.toggle("Include R&D team time (opportunity cost)", value=False,
                            help="Off by default so the direct cost types are readable; R&D team time usually dwarfs them.")
    breakdown_all = cost_breakdown(window_scenario, params, costs)
    if not include_opp:
        breakdown_all = breakdown_all[breakdown_all["cost_type"] != OPPORTUNITY_COST]

    opp_total = opportunity_cost(params) * window
    with st.container(horizontal=True):
        st.metric("Direct costs in month 1", compact_money(sum(c.amount_in(1) for c in costs), cur), border=True)
        st.metric("R&D team opportunity cost per month", compact_money(opportunity_cost(params), cur), border=True)
        st.metric(f"Total over {window_label}", compact_money(breakdown_all["amount"].sum(), cur), border=True,
                  help="Direct costs, plus R&D team time if included above.")
        st.metric("R&D team time share", f"{opp_total / (opp_total + direct_total):.0%}" if opp_total + direct_total else "0%",
                  border=True, help="Share of R&D team time in all R&D costs (team time + direct costs).")

    if breakdown_all.empty:
        st.info("No costs to show. Add a row above or turn on R&D team time.", icon=":material/info:")
    else:
        left, right = st.columns([3, 2])
        with left, st.container(border=True):
            st.markdown(f"**Monthly costs by type** over {window_label}")
            st.altair_chart(charts.costs_over_time(breakdown_all, style), alt="Monthly costs stacked by type")
        with right, st.container(border=True):
            st.markdown("**Total by type**")
            st.altair_chart(charts.costs_by_type(breakdown_all, style), alt="Total cost per type over the window")
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
                alt="Total cost per item over the window",
            )

# ---------------------------------------------------------------- scenarios: preview

with tab_scen:
    with st.container(border=True):
        st.markdown(f"**Consultants billing on generated work**, per scenario, over {window_label}")
        staffing_df = pd.DataFrame(
            [{"scenario": s.name, "month": m, "consultants": sum(o.consultants for o in s.opportunities if o.start_month <= m)}
             for s in shown for m in range(1, window + 1)]
        )
        st.altair_chart(charts.scenario_staffing(staffing_df, all_names, style), alt="Consultants billing on generated work by scenario")
    st.caption(
        ":material/help: Open question: in Realistic, the second opportunity starts in month 6 as stated. "
        "By the Pessimistic convention (\"after N months\" = month N+1) it would be month 7. Change it above to compare."
    )

# ---------------------------------------------------------------- validation

def tex_num(v: float, decimals: int = 0) -> str:
    """A number for LaTeX, with thousands separators that don't add math spacing."""
    return f"{v:,.{decimals}f}".replace(",", "{,}")


def tex_money(v: float) -> str:
    return rf"\text{{{md_cur}}}\,{tex_num(v)}"


with tab_check:
    st.subheader("How the NPV is calculated")
    check_scenario = next((s for s in scenarios if s.name == TEMPLATE), scenarios[0])
    if check_scenario.name != TEMPLATE:
        st.info(f"No scenario named {TEMPLATE}; showing **{check_scenario.name}** instead.", icon=":material/info:")
    st.markdown(
        f"A step-by-step check of the NPV for **{check_scenario.name}** over **{window_label}**, "
        "using the current sidebar parameters and costs."
    )
    vf = monthly_flows(check_scenario, params, costs)
    r_m = periodic_rate(params.annual_rate, "month")
    bill, occ = params.billing_rate_monthly, params.occupation

    with st.container(border=True):
        st.markdown("**1. Monthly discount rate** (effective compounding of the annual rate)")
        st.latex(rf"r_m = (1 + r)^{{1/12}} - 1 = (1 + {params.annual_rate:.4f})^{{1/12}} - 1 = {r_m:.6f}")

    with st.container(border=True):
        st.markdown("**2. Monthly net cash flow**")
        st.latex(r"CF_t = B_t - OC_{\text{team}} - OC_{\text{deployed},\,t} - D_t")
        st.latex(
            rf"B_t = N_t \times \text{{rate}} \times \text{{margin}} = N_t \times {tex_money(bill)} \times {params.benefit_margin:.2f}"
        )
        st.latex(
            rf"OC_{{\text{{team}}}} = n_{{R\&D}} \times \text{{rate}} \times \text{{occupation}} \times \text{{dedication}}"
            rf" = {params.n_rd_consultants:g} \times {tex_money(bill)} \times {occ:.2f} \times {params.dedication:.2f}"
            rf" = {tex_money(opportunity_cost(params))}"
        )
        if params.count_deployed_baseline:
            st.latex(
                rf"OC_{{\text{{deployed}},\,t}} = N_t \times \text{{rate}} \times \text{{occupation}} = N_t \times {tex_money(bill)} \times {occ:.2f}"
            )
        else:
            st.latex(r"OC_{\text{deployed},\,t} = 0 \quad \text{(baseline switched off in the sidebar)}")
        st.caption(
            "N_t: consultants billing on R&D-generated work in month t. "
            "D_t: direct costs active in month t (Costs tab)."
        )

    with st.container(border=True):
        st.markdown("**3. Discounted cash flow in the last month of each year**")
        for t in range(12, window + 1, 12):
            row = vf.iloc[t - 1]
            st.markdown(f"*Month {t}*: end of year {t // 12}, N = {row['consultants_staffed']:g} consultants")
            st.latex(
                rf"CF_{{{t}}} = {tex_money(row['benefit'])} - {tex_money(row['opportunity_cost'])}"
                rf" - {tex_money(row['deployed_cost'])} - {tex_money(row['direct_costs'])} = {tex_money(row['net_flow'])}"
            )
            st.latex(
                rf"PV_{{{t}}} = \frac{{CF_{{{t}}}}}{{(1 + r_m)^{{{t}}}}}"
                rf" = \frac{{{tex_money(row['net_flow'])}}}{{(1 + {r_m:.6f})^{{{t}}}}}"
                rf" = {tex_money(row['net_flow'])} \times {row['discount_factor']:.6f} = {tex_money(row['present_value'])}"
            )

    total = float(vf["present_value"].sum())
    with st.container(border=True):
        st.markdown(f"**4. NPV: the sum of every month's discounted cash flow** (CF₀ = 0, amounts in {md_cur})")
        terms = [rf"\frac{{{tex_num(r['net_flow'])}}}{{(1+r_m)^{{{int(r['month'])}}}}}" for _, r in vf.iterrows()]
        lines = [" + ".join(terms[i:i + 4]) for i in range(0, len(terms), 4)]
        body = r" \\ &\quad + ".join(lines)
        st.latex(
            rf"\begin{{aligned}} NPV &= \sum_{{t=1}}^{{{window}}} \frac{{CF_t}}{{(1 + r_m)^t}} \\"
            rf" &= {body} \\ &= {tex_money(total)} \end{{aligned}}"
        )

    independent = npv(params.annual_rate, [0.0, *vf["net_flow"]], period="month")
    reported = summarize(check_scenario, params, costs)["npv"]
    matches = abs(independent - total) < 0.01 and abs(reported - total) < 0.01
    message = (
        f"Cross-check: npv.py = **{money(independent)}**, sum of discounted flows = **{money(total)}**, "
        f"Investment case = **{money(reported)}**."
    )
    if matches:
        st.success(message + " They match.", icon=":material/check_circle:")
    else:
        st.error(message + " They do not match.", icon=":material/error:")

    with st.expander("All months"):
        st.dataframe(
            vf[["month", "consultants_staffed", "net_flow", "discount_factor", "present_value", "cumulative_pv"]]
            .round({"net_flow": 0, "present_value": 0, "cumulative_pv": 0, "discount_factor": 6}),
            hide_index=True,
            column_config={
                "month": st.column_config.NumberColumn("Month", format="%d"),
                "consultants_staffed": st.column_config.NumberColumn("N (consultants)", format="%.1f"),
                "net_flow": st.column_config.NumberColumn(f"CF ({cur})", format="localized"),
                "discount_factor": st.column_config.NumberColumn("Discount factor", format="%.6f"),
                "present_value": st.column_config.NumberColumn(f"PV ({cur})", format="localized"),
                "cumulative_pv": st.column_config.NumberColumn(f"Cumulative PV ({cur})", format="localized"),
            },
            alt=f"Monthly cash flows and discount factors for {check_scenario.name}",
        )

# ---------------------------------------------------------------- quickstart

with tab_guide:
    st.markdown(QUICKSTART.read_text(encoding="utf-8"))
