
from typing import Any
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


ONES = [
    "zero", "one", "two", "three", "four", "five",
    "six", "seven", "eight", "nine", "ten", "eleven",
    "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen",
]

TENS = [
    "", "", "twenty", "thirty", "forty", "fifty",
    "sixty", "seventy", "eighty", "ninety",
]


def _under_thousand_words(number: int) -> str:
    """Convert a number from 0 to 999 into words."""
    if number < 20:
        return ONES[number]

    if number < 100:
        tens, remainder = divmod(number, 10)
        return TENS[tens] + (
            f"-{ONES[remainder]}" if remainder else ""
        )

    hundreds, remainder = divmod(number, 100)
    result = f"{ONES[hundreds]} hundred"

    if remainder:
        result += f" {_under_thousand_words(remainder)}"

    return result


def _integer_to_words(number: int) -> str:
    """Convert a non-negative integer using Indian number groups."""
    if number < 0:
        return "minus " + _integer_to_words(-number)

    if number < 1000:
        return _under_thousand_words(number)

    groups = [
        (10**7, "crore"),
        (10**5, "lakh"),
        (1000, "thousand"),
    ]

    parts = []
    remaining = number

    for divisor, label in groups:
        group = remaining // divisor

        if group:
            parts.append(
                f"{_integer_to_words(group)} {label}"
            )
            remaining %= divisor

    if remaining:
        parts.append(_under_thousand_words(remaining))

    return " ".join(parts)


def _format_currency_for_speech(value: Any) -> str:
    """Speak a currency amount as rupees and paise."""
    try:
        amount = Decimal(str(value))

        if not amount.is_finite():
            return "an unavailable amount"

        amount = amount.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        if amount < 0:
            return "minus " + _format_currency_for_speech(-amount)

        rupees = int(amount)
        paise = int((amount - Decimal(rupees)) * 100)

        parts = [
            f"{_integer_to_words(rupees)} rupees"
        ]

        if paise:
            parts.append(f"{_integer_to_words(paise)} paise")

        return " and ".join(parts)

    except (InvalidOperation, ValueError, TypeError):
        return "an unavailable amount"


def _format_nav_for_speech(value: Any) -> str:
    """Speak NAV with its decimal digits preserved."""
    try:
        amount = Decimal(str(value))

        if not amount.is_finite():
            return "an unavailable NAV"

        text = format(amount, "f")

        if text.startswith("-"):
            sign = "minus "
            text = text[1:]
        else:
            sign = ""

        if "." not in text:
            return sign + _integer_to_words(int(text))

        integer_part, fractional_part = text.split(".", 1)

        integer_words = _integer_to_words(int(integer_part))
        decimal_words = " ".join(ONES[int(digit)] for digit in fractional_part)

        return f"{sign}{integer_words} point {decimal_words}"

    except (InvalidOperation, ValueError, TypeError):
        return "an unavailable NAV"


def _get_field(item: Any, field: str, default: Any = None) -> Any:
    """Read a field from a dictionary or object."""
    if isinstance(item, dict):
        return item.get(field, default)

    return getattr(item, field, default)


def prepare_voice_report(
    report: str | None,
    human_review_required: bool = False,
) -> str:
    """Prepare a safe, readable text version of a portfolio report."""
    if human_review_required:
        return (
            "Your portfolio report requires human review. "
            "Some information could not be verified. "
            "Please review the unresolved items before relying "
            "on a valuation."
        )

    if not report or not report.strip():
        return (
            "A portfolio report is not available yet. "
            "Please run the portfolio verification workflow first."
        )

    return " ".join(report.split())


def _get_verification_status(result: dict[str, Any]) -> str | None:
    """Extract verification status from the workflow result."""
    verification = result.get("verification")

    if verification is None:
        return result.get("verification_status")

    status = _get_field(verification, "status")

    if status is None:
        return None

    return str(getattr(status, "value", status))


def prepare_voice_report_from_result(
    result: dict[str, Any],
) -> str:
    """Generate a natural spoken summary from a workflow result."""

    if result.get("human_review_required", False):
        return prepare_voice_report(
            report=result.get("report"),
            human_review_required=True,
        )

    verification_status = _get_verification_status(result)

    # Preserve compatibility with report-only results.
    if verification_status is None:
        return prepare_voice_report(report=result.get("report"))

    if verification_status != "VERIFIED":
        return (
            "Your portfolio valuation has not been fully verified. "
            "I cannot announce holding values as confirmed. "
            "Please review the verification results on the dashboard."
        )

    portfolio = result.get("portfolio")
    valuation = result.get("valuation")

    total_value = _get_field(valuation, "total_value")

    if total_value is None:
        total_value = result.get("total_value")

    if portfolio is None or total_value is None:
        return (
            "The portfolio details or valuation total are missing. "
            "Please review the workflow result before relying on "
            "the spoken valuation."
        )

    try:
        total = Decimal(str(total_value))

        if not total.is_finite() or total < 0:
            raise InvalidOperation

    except (InvalidOperation, ValueError, TypeError):
        return (
            "The portfolio total is invalid. "
            "Please review the dashboard before relying on this report."
        )

    portfolio_date = _get_field(portfolio, "valuation_date")
    holdings = _get_field(portfolio, "holdings", [])
    nav_records = result.get("nav_records", [])

    if not isinstance(holdings, (list, tuple)):
        return "The portfolio holdings could not be read. Please review the dashboard."

    if not isinstance(nav_records, (list, tuple)):
        return "The NAV records could not be read. Please review the dashboard."

    nav_by_scheme = {}

    for record in nav_records:
        scheme_name = _get_field(record, "scheme_name", "")
        key = str(scheme_name).strip().casefold()

        if key:
            nav_by_scheme[key] = record

    calculated_holdings = []

    for holding in holdings:
        scheme_name = _get_field(
            holding, "scheme_name", "Unnamed scheme"
        )
        units_value = _get_field(holding, "units", 0)

        nav_record = nav_by_scheme.get(
            str(scheme_name).strip().casefold()
        )

        if nav_record is None:
            return (
                f"Matching NAV evidence is missing for {scheme_name}. "
                "Please review the dashboard before relying on "
                "the spoken breakdown."
            )

        nav = _get_field(nav_record, "nav")
        nav_date = _get_field(nav_record, "nav_date")

        if (
            portfolio_date is None
            or nav_date is None
            or str(nav_date) != str(portfolio_date)
        ):
            return (
                "A holding's NAV date does not match the portfolio "
                "valuation date. I cannot announce the detailed "
                "valuation as confirmed. Please review the dashboard."
            )

        if nav is None:
            return f"The NAV for {scheme_name} is unavailable. Please review the dashboard."

        try:
            units = Decimal(str(units_value))
            nav_amount = Decimal(str(nav))

            if (
                not units.is_finite()
                or not nav_amount.is_finite()
                or units < 0
                or nav_amount < 0
            ):
                raise InvalidOperation

            holding_value = (units * nav_amount).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )

        except (InvalidOperation, ValueError, TypeError):
            return f"The units or NAV for {scheme_name} are invalid. Please review the dashboard."

        calculated_holdings.append({
            "scheme_name": str(scheme_name),
            "units": units,
            "nav": nav_amount,
            "nav_date": nav_date,
            "current_value": holding_value,
        })

    calculated_total = sum(
        (item["current_value"] for item in calculated_holdings),
        Decimal("0.00"),
    )

    if calculated_total != total.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    ):
        return (
            "The holding values do not reconcile with the verified "
            "portfolio total. I cannot announce the detailed "
            "valuation as confirmed. Please review the dashboard."
        )

    spoken_parts = [
        "Your mutual fund portfolio report is ready.",
        "Your verified portfolio value is "
        f"{_format_currency_for_speech(total)}.",
        f"Your portfolio contains {len(holdings)} holdings.",
    ]

    if calculated_holdings:
        largest = max(
            calculated_holdings,
            key=lambda item: item["current_value"],
        )

        largest_allocation = (
            largest["current_value"] / total * Decimal("100")
        ).quantize(Decimal("0.01")) if total > 0 else Decimal("0.00")

        spoken_parts.append(
            f"Your largest holding by current value is "
            f"{largest['scheme_name']}, worth "
            f"{_format_currency_for_speech(largest['current_value'])}, "
            f"representing {_format_nav_for_speech(largest_allocation)} "
            "percent of your portfolio."
        )

    for item in calculated_holdings:
        allocation = (
            item["current_value"] / total * Decimal("100")
        ).quantize(Decimal("0.01")) if total > 0 else Decimal("0.00")

        spoken_parts.append(
            f"{item['scheme_name']}. "
            f"Units held: {_format_nav_for_speech(item['units'])}. "
            f"NAV: {_format_nav_for_speech(item['nav'])}. "
            f"Current value: "
            f"{_format_currency_for_speech(item['current_value'])}. "
            f"Portfolio allocation: "
            f"{_format_nav_for_speech(allocation)} percent. "
            f"NAV date: {item['nav_date']}."
        )

    spoken_parts.append(
        "Allocation percentages describe your current portfolio "
        "distribution and are not investment recommendations. "
        "Mutual fund values can change with market movements."
    )

    return " ".join(spoken_parts)
