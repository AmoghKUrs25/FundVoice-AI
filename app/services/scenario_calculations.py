"""Calculations for FundVoice AI synthetic test scenarios."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


CENT = Decimal("0.01")


def _number(value, field_name):
    """Convert input to a finite Decimal safely."""
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{field_name} must be a valid number.") from exc

    if not number.is_finite() or number < 0:
        raise ValueError(f"{field_name} must be finite and non-negative.")

    return number


def _money(value):
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_tc1(units, nav):
    """Calculate one synthetic holding's value: units multiplied by NAV."""
    units = _number(units, "Units")
    nav = _number(nav, "NAV")

    value = _money(units * nav)

    return {
        "scenario": "TC1",
        "status": "SYNTHETIC_TEST",
        "units": str(units),
        "nav": str(nav),
        "calculation": f"{units} x {nav}",
        "holding_value": str(value),
        "verified_portfolio_value": None,
    }


def calculate_tc2(holdings):
    """Value each synthetic holding separately using its own NAV date."""
    if len(holdings) < 2:
        raise ValueError("TC2 requires at least two holdings.")

    results = []

    for index, holding in enumerate(holdings, start=1):
        units = _number(holding.get("units"), f"Holding {index} units")
        nav = _number(holding.get("nav"), f"Holding {index} NAV")
        nav_date = str(holding.get("nav_date", "")).strip()

        if not nav_date:
            raise ValueError(f"Holding {index} needs a NAV date.")

        results.append({
            "holding": str(holding.get("name") or f"Holding {index}"),
            "units": str(units),
            "nav": str(nav),
            "nav_date": nav_date,
            "holding_value": str(_money(units * nav)),
        })

    dates_differ = len({item["nav_date"] for item in results}) > 1

    return {
        "scenario": "TC2",
        "status": "REVIEW_REQUIRED" if dates_differ else "SYNTHETIC_TEST",
        "holdings": results,
        "dates_differ": dates_differ,
        "combined_verified_portfolio_value": None if dates_differ else "NOT_VERIFIED",
    }


def calculate_tc3(before_units, before_nav, after_units, after_nav):
    """Compare values before and after a unit split."""
    before_units = _number(before_units, "Before-split units")
    before_nav = _number(before_nav, "Before-split NAV")
    after_units = _number(after_units, "After-split units")
    after_nav = _number(after_nav, "After-split NAV")

    before_value = _money(before_units * before_nav)
    after_value = _money(after_units * after_nav)
    difference = _money(after_value - before_value)

    return {
        "scenario": "TC3",
        "status": "SYNTHETIC_TEST",
        "before_value": str(before_value),
        "after_value": str(after_value),
        "difference": str(difference),
        "values_match": before_value == after_value,
        "interpretation": (
            "Values match; no arithmetic loss is shown."
            if before_value == after_value
            else "Values differ; investigate other market movements, dates, or inputs."
        ),
        "verified_portfolio_value": None,
    }
