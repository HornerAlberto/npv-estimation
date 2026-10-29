"""Altair chart builders for the Streamlit app.

Colours follow the entity, never its rank: every scenario, cost type and
benefit keeps the same colour in every chart. The categorical palette is the
reference palette, used in its validated slot order, except slot 2: orange was
replaced with a metallic steel blue (light #3e5874, dark #9db0c4). Against slot 1
(blue) it keeps an OKLab distance >= 15 for normal vision and >= 13 under
simulated colour blindness, in both modes.
"""

import altair as alt
import pandas as pd

from rd_value import COST_TYPES, DEPLOYED_COST, OPPORTUNITY_COST

CATEGORICAL = {
    "light": ["#2a78d6", "#3e5874", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"],
    "dark": ["#3987e5", "#9db0c4", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"],
}
# Tint of slot 2 for the deployed consultants' baseline: same kind of cost as the
# R&D team's time, so the same hue family, distinct in lightness.
DEPLOYED_TINT = {"light": "#a9bccf", "dark": "#46607c"}
INK = {
    "light": {"primary": "#0b0b0b", "secondary": "#52514e", "muted": "#898781", "surface": "#fcfcfb"},
    "dark": {"primary": "#f0efec", "secondary": "#c3c2b7", "muted": "#898781", "surface": "#1a1a19"},
}

BENEFIT = "Benefit (new billing)"
DIRECT_COSTS = "Direct costs (all types)"
NET = "Net flow"
RD_TEAM = "R&D team (FTE)"
GENERATED = "Consultants billing on generated work"


class Style:
    """Colours and number formats for one theme mode and currency."""

    def __init__(self, mode: str, currency: str):
        self.mode = "dark" if mode == "dark" else "light"
        self.palette = CATEGORICAL[self.mode]
        self.ink = INK[self.mode]
        self.currency = currency

    # Benefit is slot 1; R&D team time slot 2 (deployed baseline its tint); direct cost types slots 3-8.
    def component_scale(self, components: list[str] | None = None) -> alt.Scale:
        mapping = {BENEFIT: self.palette[0], OPPORTUNITY_COST: self.palette[1], DEPLOYED_COST: DEPLOYED_TINT[self.mode]}
        mapping.update(zip(COST_TYPES, self.palette[2:]))
        mapping[DIRECT_COSTS] = self.ink["muted"]
        domain = components or list(mapping)
        return alt.Scale(domain=domain, range=[mapping[c] for c in domain])

    def scenario_scale(self, names: list[str]) -> alt.Scale:
        # Beyond eight scenarios colours repeat; the app caps the selection at eight.
        colors = [self.palette[i % len(self.palette)] for i in range(len(names))]
        return alt.Scale(domain=names, range=colors)

    def money_axis(self, title: str | None = None) -> alt.Axis:
        sym = self.currency
        return alt.Axis(
            title=title,
            labelExpr=f"(datum.value < 0 ? '−' : '') + '{sym}' + format(abs(datum.value), '~s')",
        )

    def money_tooltip(self, field: str, title: str) -> alt.Tooltip:
        return alt.Tooltip(field, title=f"{title} ({self.currency})", format=",.0f")


def _zero_rule(style: Style) -> alt.Chart:
    return (
        alt.Chart(pd.DataFrame({"y": [0]}))
        .mark_rule(color=style.ink["muted"], strokeWidth=1)
        .encode(y="y:Q")
    )


def cumulative_value(df: pd.DataFrame, names: list[str], style: Style) -> alt.LayerChart:
    """Cumulative discounted value per scenario. df: month, scenario, cumulative_pv."""
    color = alt.Color("scenario:N", scale=style.scenario_scale(names), legend=alt.Legend(title=None, orient="bottom", labelLimit=320, columns=2))
    x = alt.X("month:Q", title="Month", axis=alt.Axis(tickMinStep=1), scale=alt.Scale(domain=[1, int(df["month"].max())], nice=False))
    base = alt.Chart(df).encode(
        x=x,
        y=alt.Y("cumulative_pv:Q", axis=style.money_axis("Cumulative discounted value")),
        color=color,
    )
    hover = alt.selection_point(fields=["month"], nearest=True, on="pointerover", empty=False, clear="pointerout")
    lines = base.mark_line(strokeWidth=2, interpolate="linear")
    points = base.mark_point(filled=True, size=70, stroke=style.ink["surface"], strokeWidth=2).encode(
        opacity=alt.condition(hover, alt.value(1), alt.value(0)),
        tooltip=[
            alt.Tooltip("scenario:N", title="Scenario"),
            alt.Tooltip("month:Q", title="Month"),
            style.money_tooltip("cumulative_pv:Q", "Cumulative value"),
        ],
    ).add_params(hover)
    rule = (
        alt.Chart(df)
        .mark_rule(color=style.ink["muted"], strokeDash=[3, 3])
        .encode(x=x)
        .transform_filter(hover)
    )
    last = df.loc[df.groupby("scenario")["month"].idxmax()].copy()
    last["label"] = last["scenario"].str.split(".").str[0].map(lambda n: f"S{n}")
    end_dot = alt.Chart(last).mark_point(filled=True, size=60, stroke=style.ink["surface"], strokeWidth=2).encode(
        x=x, y="cumulative_pv:Q", color=color
    )
    end_label = alt.Chart(last).mark_text(align="left", dx=8, fontSize=12, color=style.ink["secondary"]).encode(
        x=x, y="cumulative_pv:Q", text="label:N"
    )
    return alt.layer(_zero_rule(style), lines, rule, points, end_dot, end_label).properties(height=360)


def value_bridge(summaries: pd.DataFrame, names: list[str], style: Style) -> alt.LayerChart:
    """Present value of benefits vs costs per scenario, with the NPV marked."""
    rows = []
    for _, s in summaries.iterrows():
        rows += [
            {"scenario": s["scenario"], "component": BENEFIT, "value": s["pv_benefit"], "order": 0},
            {"scenario": s["scenario"], "component": OPPORTUNITY_COST, "value": -s["pv_opportunity_cost"], "order": 1},
            {"scenario": s["scenario"], "component": DEPLOYED_COST, "value": -s["pv_deployed_cost"], "order": 2},
            {"scenario": s["scenario"], "component": DIRECT_COSTS, "value": -s["pv_direct_costs"], "order": 3},
        ]
    df = pd.DataFrame(rows)
    df = df[df["value"] != 0]
    components = [c for c in [BENEFIT, OPPORTUNITY_COST, DEPLOYED_COST, DIRECT_COSTS] if c in set(df["component"])]
    y = alt.Y("scenario:N", sort=names, title=None, axis=alt.Axis(labelLimit=220))
    bars = alt.Chart(df).mark_bar(height=22, stroke=style.ink["surface"], strokeWidth=2).encode(
        y=y,
        x=alt.X("value:Q", axis=style.money_axis("Present value"), scale=alt.Scale(domain=[float(df["value"].min()) * 1.1, float(df["value"].max()) * 1.15])),
        color=alt.Color("component:N", scale=style.component_scale(components), legend=alt.Legend(title=None, orient="bottom", labelLimit=320, columns=2)),
        order=alt.Order("order:Q"),
        tooltip=[alt.Tooltip("scenario:N", title="Scenario"), alt.Tooltip("component:N", title="Component"), style.money_tooltip("value:Q", "Present value")],
    )
    npv = summaries[["scenario", "npv"]].copy()
    npv["label"] = npv["npv"].map(lambda v: "NPV " + compact_money(v, style.currency))
    tick = alt.Chart(npv).mark_tick(color=style.ink["primary"], thickness=3, size=30).encode(
        y=y, x="npv:Q", tooltip=[alt.Tooltip("scenario:N", title="Scenario"), style.money_tooltip("npv:Q", "NPV")]
    )
    label = alt.Chart(npv).mark_text(align="left", dx=6, dy=-16, fontSize=12, fontWeight="bold", color=style.ink["primary"]).encode(
        y=y, x="npv:Q", text="label:N"
    )
    return alt.layer(bars, tick, label).properties(height=max(160, 70 * len(names)))


def monthly_budget(flows: pd.DataFrame, breakdown: pd.DataFrame, style: Style, y_title: str = "Per month") -> alt.LayerChart:
    """Benefit above zero, costs stacked by type below zero, net flow as a line.

    Pass discounted flows and breakdown to show present values instead.
    """
    by_type = breakdown.groupby(["month", "cost_type"], as_index=False)["amount"].sum()
    bars_df = pd.concat(
        [
            pd.DataFrame({"month": flows["month"], "component": BENEFIT, "value": flows["benefit"]}),
            pd.DataFrame({"month": by_type["month"], "component": by_type["cost_type"], "value": -by_type["amount"]}),
        ],
        ignore_index=True,
    )
    present = set(by_type["cost_type"])
    components = [BENEFIT, *[c for c in [OPPORTUNITY_COST, DEPLOYED_COST, *COST_TYPES] if c in present]]
    order_map = {c: i for i, c in enumerate(components)}
    bars_df["order"] = bars_df["component"].map(order_map)
    x = alt.X("month:O", title="Month", axis=alt.Axis(labelAngle=0, labelOverlap=True))
    bars = alt.Chart(bars_df).mark_bar(stroke=style.ink["surface"], strokeWidth=1).encode(
        x=x,
        y=alt.Y("value:Q", axis=style.money_axis(y_title)),
        color=alt.Color("component:N", scale=style.component_scale(components), legend=alt.Legend(title=None, orient="bottom", labelLimit=320, columns=2)),
        order=alt.Order("order:Q"),
        tooltip=[alt.Tooltip("month:O", title="Month"), alt.Tooltip("component:N", title="Component"), style.money_tooltip("value:Q", "Amount")],
    )
    net = alt.Chart(flows.assign(series=NET)).encode(x=x, y="net_flow:Q")
    net_line = net.mark_line(color=style.ink["primary"], strokeWidth=2)
    net_points = net.mark_point(filled=True, size=40, color=style.ink["primary"]).encode(
        tooltip=[alt.Tooltip("month:O", title="Month"), style.money_tooltip("net_flow:Q", "Net flow")]
    )
    return alt.layer(bars, _zero_rule(style), net_line, net_points).properties(height=380)


def staffing(flows: pd.DataFrame, rd_fte: float, style: Style) -> alt.LayerChart:
    """R&D team size vs consultants billing on work the R&D generated."""
    df = pd.concat(
        [
            pd.DataFrame({"month": flows["month"], "series": GENERATED, "consultants": flows["consultants_staffed"]}),
            pd.DataFrame({"month": flows["month"], "series": RD_TEAM, "consultants": rd_fte}),
        ],
        ignore_index=True,
    )
    scale = alt.Scale(domain=[GENERATED, RD_TEAM], range=[style.palette[0], style.palette[1]])
    return (
        alt.Chart(df)
        .mark_line(strokeWidth=2, interpolate="step-after", point=alt.OverlayMarkDef(filled=True, size=30))
        .encode(
            x=alt.X("month:Q", title="Month", axis=alt.Axis(tickMinStep=1)),
            y=alt.Y("consultants:Q", title="Consultants"),
            color=alt.Color("series:N", scale=scale, legend=alt.Legend(title=None, orient="bottom", labelLimit=320, columns=1)),
            tooltip=[alt.Tooltip("series:N", title="Series"), alt.Tooltip("month:Q", title="Month"), alt.Tooltip("consultants:Q", title="Consultants", format=",.1f")],
        )
        .properties(height=260)
    )


def sensitivity(df: pd.DataFrame, x_field: str, x_title: str, current: float, names: list[str], style: Style) -> alt.LayerChart:
    """NPV per scenario as one input varies. df: scenario, x_field, npv. x in percent."""
    color = alt.Color("scenario:N", scale=style.scenario_scale(names), legend=alt.Legend(title=None, orient="bottom", labelLimit=320, columns=2))
    lines = alt.Chart(df).mark_line(strokeWidth=2, point=alt.OverlayMarkDef(filled=True, size=25)).encode(
        x=alt.X(f"{x_field}:Q", title=x_title, axis=alt.Axis(labelExpr="datum.value + '%'")),
        y=alt.Y("npv:Q", axis=style.money_axis("NPV")),
        color=color,
        tooltip=[alt.Tooltip("scenario:N", title="Scenario"), alt.Tooltip(f"{x_field}:Q", title=x_title, format=".1f"), style.money_tooltip("npv:Q", "NPV")],
    )
    now = alt.Chart(pd.DataFrame({"x": [current], "label": ["current"]}))
    now_rule = now.mark_rule(color=style.ink["muted"], strokeDash=[4, 4]).encode(x="x:Q")
    now_text = now.mark_text(align="left", dx=4, y=8, color=style.ink["secondary"], fontSize=11).encode(x="x:Q", text="label:N")
    return alt.layer(_zero_rule(style), lines, now_rule, now_text).properties(height=300)


def costs_over_time(breakdown: pd.DataFrame, style: Style) -> alt.Chart:
    """Monthly costs stacked by type."""
    by_type = breakdown.groupby(["month", "cost_type"], as_index=False)["amount"].sum()
    components = [c for c in [OPPORTUNITY_COST, *COST_TYPES] if c in set(by_type["cost_type"])]
    by_type["order"] = by_type["cost_type"].map({c: i for i, c in enumerate(components)})
    return (
        alt.Chart(by_type)
        .mark_bar(stroke=style.ink["surface"], strokeWidth=1)
        .encode(
            x=alt.X("month:O", title="Month", axis=alt.Axis(labelAngle=0, labelOverlap=True)),
            y=alt.Y("amount:Q", axis=style.money_axis("Per month")),
            color=alt.Color("cost_type:N", scale=style.component_scale(components), legend=alt.Legend(title=None, orient="bottom", labelLimit=320, columns=2)),
            order=alt.Order("order:Q"),
            tooltip=[alt.Tooltip("month:O", title="Month"), alt.Tooltip("cost_type:N", title="Type"), style.money_tooltip("amount:Q", "Amount")],
        )
        .properties(height=320)
    )


def costs_by_type(breakdown: pd.DataFrame, style: Style) -> alt.LayerChart:
    """Total cost per type over the horizon, largest first."""
    totals = breakdown.groupby("cost_type", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
    totals["label"] = totals["amount"].map(lambda v: compact_money(v, style.currency))
    components = totals["cost_type"].tolist()
    y = alt.Y("cost_type:N", sort=components, title=None, scale=alt.Scale(paddingInner=0.35), axis=alt.Axis(labelLimit=240, labelOverlap=False))
    bars = alt.Chart(totals).mark_bar(cornerRadiusEnd=4).encode(
        y=y,
        x=alt.X("amount:Q", axis=style.money_axis("Total over horizon")),
        color=alt.Color("cost_type:N", scale=style.component_scale(components), legend=None),
        tooltip=[alt.Tooltip("cost_type:N", title="Type"), style.money_tooltip("amount:Q", "Total")],
    )
    labels = alt.Chart(totals).mark_text(align="left", dx=6, fontSize=12, color=style.ink["secondary"]).encode(
        y=y, x="amount:Q", text="label:N"
    )
    return alt.layer(bars, labels).properties(height=alt.Step(36))


def compact_money(value: float, currency: str) -> str:
    sign = "−" if value < 0 else ""
    v = abs(value)
    if v >= 1e6:
        text = f"{v / 1e6:,.2f}M"
    elif v >= 1e3:
        text = f"{v / 1e3:,.1f}k"
    else:
        text = f"{v:,.0f}"
    return f"{sign}{currency}{text}"


def scenario_staffing(df: pd.DataFrame, names: list[str], style: Style) -> alt.FacetChart:
    """Consultants billing on generated work: one small panel per scenario, shared axes.

    Small multiples, because scenarios that share opportunities draw identical lines
    that would hide each other on a single chart.
    """
    shown = [n for n in names if n in set(df["scenario"])]
    return (
        alt.Chart(df)
        .mark_area(line={"strokeWidth": 2}, interpolate="step-after", opacity=0.25)
        .encode(
            x=alt.X("month:Q", title="Month", axis=alt.Axis(tickMinStep=1), scale=alt.Scale(domain=[1, int(df["month"].max())], nice=False)),
            y=alt.Y("consultants:Q", title="Consultants billing"),
            color=alt.Color("scenario:N", scale=style.scenario_scale(names), legend=None),
            tooltip=[alt.Tooltip("scenario:N", title="Scenario"), alt.Tooltip("month:Q", title="Month"), alt.Tooltip("consultants:Q", title="Consultants", format=",.1f")],
        )
        .properties(width=420, height=140)
        .facet(facet=alt.Facet("scenario:N", sort=shown, title=None, header=alt.Header(labelFontSize=12, labelAnchor="start")), columns=2)
    )
