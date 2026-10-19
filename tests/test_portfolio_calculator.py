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