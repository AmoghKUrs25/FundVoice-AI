from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable


# Monetary values are displayed to two decimal places.
MONEY_PRECISION = Decimal("0.01")


def calculate_holding_value(
    units: Decimal,
    nav: Decimal,
) -> Decimal:
    """
    Calculate the value of one mutual fund holding.

    Formula:
        Holding Value = Units * NAV

    Returns the unrounded Decimal result.
    """

    if not isinstance(units, Decimal):
        raise TypeError("Units must be a Decimal value.")

    if not isinstance(nav, Decimal):
        raise TypeError("NAV must be a Decimal value.")

    if not units.is_finite() or not nav.is_finite():
        raise ValueError("Units and NAV must be finite numbers.")

    if units < Decimal("0"):
        raise ValueError("Units cannot be negative.")

    if nav < Decimal("0"):
        raise ValueError("NAV cannot be negative.")

    return units * nav


def round_money(amount: Decimal) -> Decimal:
    """
    Round a monetary amount to two decimal places
    using the ROUND_HALF_UP policy.
    """

    if not isinstance(amount, Decimal):
        raise TypeError("Amount must be a Decimal value.")

    if not amount.is_finite():
        raise ValueError("Amount must be a finite number.")

    return amount.quantize(
        MONEY_PRECISION,
        rounding=ROUND_HALF_UP,
    )


def calculate_portfolio(
    holdings: Iterable[tuple[Decimal, Decimal]],
) -> Decimal:
    """
    Calculate the total value of multiple holdings.

    Each holding is represented as:
        (units, nav)

    The total is calculated before rounding.
    """

    total = Decimal("0")

    for units, nav in holdings:
        total += calculate_holding_value(units, nav)

    return total