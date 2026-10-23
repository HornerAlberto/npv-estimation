import pytest

from npv import npv, npv_table, periodic_rate


def test_annual_npv_matches_hand_calculation():
    # -1000 + 300/1.1 + 400/1.1^2 + 500/1.1^3
    assert npv(0.10, [-1000, 300, 400, 500]) == pytest.approx(-21.0368, abs=1e-4)


def test_single_cash_flow_is_not_discounted():
    assert npv(0.10, [-1000]) == -1000


def test_zero_rate_is_plain_sum():
    assert npv(0.0, [-100, 50, 60], period="week") == pytest.approx(10)


@pytest.mark.parametrize(("period", "n"), [("year", 1), ("semester", 2), ("month", 12), ("week", 52)])
def test_periodic_rate_compounds_back_to_annual(period, n):
    assert (1 + periodic_rate(0.10, period)) ** n == pytest.approx(1.10)


def test_periods_are_consistent_across_frequencies():
    # 100 received after one year, expressed in each period length
    yearly = npv(0.10, [0, 100], period="year")
    semester = npv(0.10, [0, 0, 100], period="semester")
    weekly = npv(0.10, [0] * 52 + [100], period="week")
    assert semester == pytest.approx(yearly)
    assert weekly == pytest.approx(yearly)


def test_table_rows():
    rows = npv_table(0.10, [-1000, 300, 400], period="semester")
    assert [row["period"] for row in rows] == [0, 1, 2]
    assert [row["years"] for row in rows] == [0, 0.5, 1]
    assert rows[0]["discount_factor"] == 1
    assert rows[2]["discount_factor"] == pytest.approx(1 / 1.10)
    assert rows[2]["present_value"] == pytest.approx(400 / 1.10)
    assert sum(r["present_value"] for r in rows) == pytest.approx(
        npv(0.10, [-1000, 300, 400], period="semester")
    )


def test_empty_cash_flows_raise():
    with pytest.raises(ValueError):
        npv(0.10, [])


def test_rate_at_or_below_minus_one_raises():
    with pytest.raises(ValueError):
        npv(-1, [100])


def test_unknown_period_raises():
    with pytest.raises(ValueError):
        npv(0.10, [100], period="day")
