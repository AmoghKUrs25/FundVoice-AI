
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.services.voice_report import (
    prepare_voice_report,
    prepare_voice_report_from_result,
)


def test_verified_report_is_prepared_for_speech():
    text = prepare_voice_report(
        "Portfolio verified. Total value is ₹10,071.38.",
        human_review_required=False,
    )

    assert text == "Portfolio verified. Total value is ₹10,071.38."


def test_human_review_prevents_normal_report_from_being_spoken():
    text = prepare_voice_report(
        "Portfolio value is ₹10,071.38.",
        human_review_required=True,
    )

    assert "requires human review" in text
    assert "₹10,071.38" not in text


def test_empty_report_returns_safe_message():
    text = prepare_voice_report(None)

    assert "report is not available" in text


def test_result_wrapper_uses_report():
    result = {
        "report": "Portfolio verified.",
        "human_review_required": False,
    }

    assert prepare_voice_report_from_result(result) == "Portfolio verified."


def test_result_wrapper_handles_review_required():
    result = {
        "report": "Unverified report.",
        "human_review_required": True,
    }

    text = prepare_voice_report_from_result(result)

    assert "requires human review" in text
    assert "Unverified report" not in text


def make_verified_result(
    total_value="1000.00",
    nav_date=date(2026, 10, 21),
):
    """Create a small, verified portfolio for safety tests."""

    valuation_date = date(2026, 10, 21)

    holding = SimpleNamespace(
        holding_id="H001",
        scheme_name="Example Equity Fund",
        units=Decimal("10"),
    )

    nav_record = SimpleNamespace(
        scheme_name="Example Equity Fund",
        nav_date=nav_date,
        nav=Decimal("100.00"),
    )

    portfolio = SimpleNamespace(
        portfolio_id="TEST001",
        valuation_date=valuation_date,
        holdings=[holding],
    )

    valuation = SimpleNamespace(
        total_value=Decimal(total_value),
    )

    verification = SimpleNamespace(status="VERIFIED")

    return {
        "portfolio": portfolio,
        "valuation": valuation,
        "verification": verification,
        "verification_status": "VERIFIED",
        "nav_records": [nav_record],
        "human_review_required": False,
        "report": "Example portfolio report.",
    }


def test_unverified_result_does_not_announce_valuation():
    result = make_verified_result()
    result["verification"] = SimpleNamespace(status="FAILED")
    result["verification_status"] = "FAILED"

    text = prepare_voice_report_from_result(result)

    assert "not been fully verified" in text
    assert "1000.00 rupees" not in text


def test_nav_date_mismatch_blocks_detailed_valuation():
    result = make_verified_result(
        nav_date=date(2026, 10, 20),
    )

    text = prepare_voice_report_from_result(result)

    assert "NAV date does not match" in text
    assert "Current value:" not in text


def test_total_mismatch_blocks_detailed_valuation():
    # Ten units × NAV of 100 = 1,000, not 900.
    result = make_verified_result(total_value="900.00")

    text = prepare_voice_report_from_result(result)

    assert "do not reconcile" in text
    assert "Current value:" not in text


def test_verified_result_includes_holding_and_allocation():
    result = make_verified_result()

    text = prepare_voice_report_from_result(result)

    assert "verified portfolio value is one thousand rupees" in text
    assert "portfolio contains 1 holdings" in text
    assert "Example Equity Fund" in text
    assert "Current value: one thousand rupees" in text
    assert (
        "Portfolio allocation: one hundred point zero zero percent"
        in text
    )


def test_human_review_blocks_detailed_valuation():
    result = make_verified_result()
    result["human_review_required"] = True

    text = prepare_voice_report_from_result(result)

    assert "requires human review" in text
    assert "Current value:" not in text


from app.services.voice_report import (
    _format_currency_for_speech,
    _format_nav_for_speech,
)



def test_currency_speech_uses_rupees_and_paise():
    assert _format_currency_for_speech("23698.26") == (
        "twenty-three thousand six hundred ninety-eight rupees "
        "and twenty-six paise"
    )



def test_nav_speech_preserves_decimal_digits():
    assert _format_nav_for_speech("2144.266") == (
        "two thousand one hundred forty-four point "
        "two six six"
    )


def test_currency_speech_handles_zero():
    assert _format_currency_for_speech("0.00") == "zero rupees"


def test_missing_verification_blocks_detailed_voice_report():
    result = make_verified_result()

    # Simulate a workflow that failed before verification could run.
    result.pop("verification", None)
    result.pop("verification_status", None)
    result["human_review_required"] = True
    result["valuation"] = None
    result["report"] = "Human review required: NAV retrieval failed."

    text = prepare_voice_report_from_result(result)

    assert "requires human review" in text
    assert "Current value:" not in text
    assert "1000.00 rupees" not in text

    
def test_negative_nav_blocks_detailed_voice_report():
    result = make_verified_result()

    result["nav_records"][0].nav = Decimal("-100.00")

    text = prepare_voice_report_from_result(result)

    assert "NAV" in text
    assert "invalid" in text
    assert "Current value:" not in text


def test_zero_value_portfolio_does_not_divide_by_zero():
    result = make_verified_result(total_value="0.00")

    result["portfolio"].holdings[0].units = Decimal("0")
    result["nav_records"][0].nav = Decimal("100.00")

    text = prepare_voice_report_from_result(result)

    assert "verified portfolio value is zero rupees" in text
    assert "Current value: zero rupees" in text
    assert "Portfolio allocation: zero point zero zero percent" in text


def test_multiple_holdings_have_correct_allocation_percentages():
    result = make_verified_result(total_value="2000.00")

    second_holding = SimpleNamespace(
        holding_id="H002",
        scheme_name="Second Equity Fund",
        units=Decimal("10"),
    )

    second_nav = SimpleNamespace(
        scheme_name="Second Equity Fund",
        nav_date=date(2026, 10, 21),
        nav=Decimal("100.00"),
    )

    result["portfolio"].holdings.append(second_holding)
    result["nav_records"].append(second_nav)
    result["valuation"].total_value = Decimal("2000.00")

    text = prepare_voice_report_from_result(result)

    assert "portfolio contains 2 holdings" in text
    assert "Example Equity Fund" in text
    assert "Second Equity Fund" in text
    assert "Current value: one thousand rupees" in text
    assert "Portfolio allocation: fifty point zero zero percent" in text


def test_missing_nav_for_one_of_multiple_holdings_blocks_report():
    result = make_verified_result()

    second_holding = SimpleNamespace(
        holding_id="H002",
        scheme_name="Second Equity Fund",
        units=Decimal("10"),
    )

    result["portfolio"].holdings.append(second_holding)

    # NAV evidence exists only for the first holding.
    text = prepare_voice_report_from_result(result)

    assert "Matching NAV evidence is missing for Second Equity Fund" in text
    assert "Current value:" not in text

def test_conflicting_duplicate_nav_records_block_voice_report():
    result = make_verified_result()

    conflicting_nav = SimpleNamespace(
        scheme_name="Example Equity Fund",
        nav_date=date(2026, 10, 21),
        nav=Decimal("110.00"),
    )

    result["nav_records"].append(conflicting_nav)

    text = prepare_voice_report_from_result(result)

    assert "do not reconcile" in text
    assert "Current value:" not in text


def test_non_finite_nav_blocks_detailed_voice_report():
    result = make_verified_result()

    result["nav_records"][0].nav = Decimal("NaN")

    text = prepare_voice_report_from_result(result)

    assert "invalid" in text
    assert "Current value:" not in text


def test_missing_portfolio_blocks_detailed_voice_report():
    result = make_verified_result()
    result["portfolio"] = None

    text = prepare_voice_report_from_result(result)

    assert "portfolio details or valuation total are missing" in text
    assert "Current value:" not in text


def test_missing_valuation_total_blocks_detailed_voice_report():
    result = make_verified_result()
    result["valuation"].total_value = None

    text = prepare_voice_report_from_result(result)

    assert "portfolio details or valuation total are missing" in text
    assert "Current value:" not in text


def test_unit_split_is_not_reported_as_a_loss():
    # Before a synthetic 2-for-1 unit split:
    # 10 units × ₹100 NAV = ₹1,000.
    before_value = Decimal("10") * Decimal("100")

    # After the split:
    # 20 units × ₹50 NAV = ₹1,000.
    after_value = Decimal("20") * Decimal("50")

    assert before_value == Decimal("1000")
    assert after_value == Decimal("1000")
    assert after_value - before_value == Decimal("0")

    # The voice reporter describes the current verified value,
    # not a loss based merely on the unit count changing.
    result = make_verified_result(total_value="1000.00")
    result["portfolio"].holdings[0].units = Decimal("20")
    result["nav_records"][0].nav = Decimal("50.00")

    text = prepare_voice_report_from_result(result)

    assert "verified portfolio value is one thousand rupees" in text
    assert "Current value: one thousand rupees" in text
    assert "loss" not in text.lower()

