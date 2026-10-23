from dataclasses import replace

import pytest

from npv import npv
from rd_value import (
    DEFAULT_SCENARIOS,
    OPPORTUNITY_COST,
    CostItem,
    Opportunity,
    Params,
    Scenario,
    break_even_margin,
    break_even_team_size,
    consultants_staffed,
    cost_breakdown,
    monthly_flows,
    npv_of,
    opportunity_cost,
    summarize,
)

PARAMS = Params(
    n_rd_consultants=3,
    billing_rate_monthly=10_000,
    occupation=0.73,
    dedication=1.0,
    benefit_margin=1.0,
    annual_rate=0.12,
)
COSTS = (CostItem("Cloud", "Cloud computing", 1_000),)
S1, S2, S3, S4 = DEFAULT_SCENARIOS


def staffing(scenario):
    return [consultants_staffed(scenario, m) for m in range(1, scenario.horizon_months + 1)]


def test_opportunity_cost_formula():
    assert opportunity_cost(PARAMS) == pytest.approx(3 * 10_000 * 0.73)
    assert opportunity_cost(replace(PARAMS, dedication=0.5)) == pytest.approx(10_950)


def test_scenario_staffing_timelines():
    assert staffing(S1) == [0] * 4 + [4] * 8
    assert staffing(S2) == [0] * 3 + [3] * 2 + [10] * 7
    assert staffing(S3) == [0] * 4 + [4] * 8 + [9] * 12 + [13] * 12
    assert staffing(S4) == [0] * 3 + [3] * 2 + [10] * 7 + [19] * 12 + [24] * 12


def test_monthly_flows_columns_and_values():
    df = monthly_flows(S1, PARAMS, COSTS)
    assert len(df) == 12
    assert df["month"].tolist() == list(range(1, 13))
    month5 = df.iloc[4]
    assert month5["benefit"] == 40_000
    assert month5["total_cost"] == pytest.approx(21_900 + 1_000)
    assert month5["net_flow"] == pytest.approx(40_000 - 22_900)


def test_npv_matches_npv_module_with_monthly_period():
    df = monthly_flows(S2, PARAMS, COSTS)
    expected = npv(0.12, [0, *df["net_flow"]], period="month")
    assert npv_of(S2, PARAMS, COSTS) == pytest.approx(expected)
    assert df["cumulative_pv"].iloc[-1] == pytest.approx(expected)


def test_cost_item_window():
    item = CostItem("Course", "Training", 500, start_month=3, end_month=4)
    assert [item.amount_in(m) for m in range(1, 7)] == [0, 0, 500, 500, 0, 0]


def test_cost_breakdown_totals_match_flows():
    costs = (*COSTS, CostItem("Course", "Training", 500, start_month=3, end_month=4))
    breakdown = cost_breakdown(S1, PARAMS, costs)
    flows = monthly_flows(S1, PARAMS, costs)
    assert breakdown["amount"].sum() == pytest.approx(flows["total_cost"].sum())
    assert set(breakdown["cost_type"]) == {OPPORTUNITY_COST, "Cloud computing", "Training"}


def test_summary_pv_components_add_up_to_npv():
    s = summarize(S3, PARAMS, COSTS)
    assert s["pv_benefit"] - s["pv_opportunity_cost"] - s["pv_direct_costs"] == pytest.approx(
        s["npv"]
    )
    assert s["final_consultants_staffed"] == 13


def test_payback_month():
    # Costs 100/month, benefit 300 from month 3: cumulative -100, -200, 0, ... at 0% rate
    scenario = Scenario("t", 6, (Opportunity(3, 3),))
    params = Params(1, 100, 1.0, 1.0, 1.0, 0.0)
    s = summarize(scenario, params, ())
    assert s["payback_month"] == 3
    assert s["max_funding_need"] == pytest.approx(200)


def test_no_payback_when_npv_negative():
    scenario = Scenario("t", 6, ())
    assert summarize(scenario, PARAMS, COSTS)["payback_month"] is None


def test_break_even_margin_gives_zero_npv():
    m = break_even_margin(S1, PARAMS, COSTS)
    assert npv_of(S1, replace(PARAMS, benefit_margin=m), COSTS) == pytest.approx(0, abs=1e-6)


def test_break_even_team_size_gives_zero_npv():
    n = break_even_team_size(S4, PARAMS, COSTS)
    assert npv_of(S4, replace(PARAMS, n_rd_consultants=n), COSTS) == pytest.approx(0, abs=1e-6)


def test_break_even_margin_none_without_benefit():
    assert break_even_margin(Scenario("t", 6, ()), PARAMS, COSTS) is None
