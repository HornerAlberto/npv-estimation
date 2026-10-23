"""Net present value (NPV) calculation.

Cash flows are given one per period, starting at t=0 (undiscounted).
The discount rate is always annual and is converted to the chosen period
length using effective compounding: r_p = (1 + annual_rate) ** (1 / n) - 1.
"""

from collections.abc import Sequence
from typing import Literal

Period = Literal["year", "semester", "month", "week"]

PERIODS_PER_YEAR: dict[str, int] = {
    "year": 1,
    "semester": 2,
    "month": 12,
    "week": 52,
}


def periodic_rate(annual_rate: float, period: Period = "year") -> float:
    """Convert an effective annual rate to the equivalent rate per period."""
    if annual_rate <= -1:
        raise ValueError(f"annual_rate must be greater than -1, got {annual_rate}")
    if period not in PERIODS_PER_YEAR:
        raise ValueError(
            f"period must be one of {list(PERIODS_PER_YEAR)}, got {period!r}"
        )
    return (1 + annual_rate) ** (1 / PERIODS_PER_YEAR[period]) - 1


def npv_table(
    annual_rate: float, cash_flows: Sequence[float], period: Period = "year"
) -> list[dict[str, float]]:
    """Per-period discounting breakdown.

    Each row has: period, years, cash_flow, discount_factor, present_value.
    """
    if len(cash_flows) == 0:
        raise ValueError("cash_flows must contain at least one value")
    rate = periodic_rate(annual_rate, period)
    n = PERIODS_PER_YEAR[period]
    rows = []
    for t, cash_flow in enumerate(cash_flows):
        discount_factor = 1 / (1 + rate) ** t
        rows.append(
            {
                "period": t,
                "years": t / n,
                "cash_flow": cash_flow,
                "discount_factor": discount_factor,
                "present_value": cash_flow * discount_factor,
            }
        )
    return rows


def npv(
    annual_rate: float, cash_flows: Sequence[float], period: Period = "year"
) -> float:
    """Net present value: sum of CF_t / (1 + r_p) ** t, with CF_0 at t=0."""
    return sum(row["present_value"] for row in npv_table(annual_rate, cash_flows, period))
