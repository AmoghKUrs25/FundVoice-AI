from decimal import Decimal

import pytest

from app.services.portfolio_calculator import (
    calculate_holding_value,
    calculate_portfolio,
    round_money,
)


def test_calculate_holding_value():
    units = Decimal("125.500")
    nav = Decimal("80.25")

    result = calculate_holding_value(units, nav)

    assert result == Decimal("10071.375")


def test_fractional_units():
    units = Decimal("10.125")
    nav = Decimal("100.50")

    result = calculate_holding_value(units, nav)

    assert result == Decimal("1017.5625")


def test_round_money():
    result = round_money(Decimal("10077.875"))

    assert result == Decimal("10077.88")


def test_portfolio_total():
    holdings = [
        (Decimal("10"), Decimal("100")),
        (Decimal("20"), Decimal("50")),
        (Decimal("5"), Decimal("200")),
    ]

    result = calculate_portfolio(holdings)

    assert result == Decimal("3000")


def test_negative_units_are_rejected():
    with pytest.raises(ValueError):
        calculate_holding_value(
            Decimal("-10"),
            Decimal("100"),
        )


def test_negative_nav_is_rejected():
    with pytest.raises(ValueError):
        calculate_holding_value(
            Decimal("10"),
            Decimal("-100"),
        )


def test_nan_units_are_rejected():
    with pytest.raises(ValueError):
        calculate_holding_value(
            Decimal("NaN"),
            Decimal("100"),
        )


def test_non_decimal_input_is_rejected():
    with pytest.raises(TypeError):
        calculate_holding_value(10.0, Decimal("100"))

        

def test_unit_split_does_not_change_holding_value():
    # Synthetic 2-for-1 split: unit count doubles and NAV halves.
    before_units = Decimal("10")
    before_nav = Decimal("100")

    after_units = Decimal("20")
    after_nav = Decimal("50")

    before_value = calculate_holding_value(
        before_units,
        before_nav,
    )

    after_value = calculate_holding_value(
        after_units,
        after_nav,
    )

    apparent_change = after_value - before_value

    assert before_value == Decimal("1000")
    assert after_value == Decimal("1000")
    assert apparent_change == Decimal("0")
    percentage_change = (
        apparent_change / before_value
    ) * Decimal("100")

    assert percentage_change == Decimal("0")
