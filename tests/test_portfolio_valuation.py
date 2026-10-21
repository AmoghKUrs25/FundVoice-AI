
from datetime import date, datetime, timezone
from decimal import Decimal

from app.models.nav import NAVEvidence, NAVRecord
from app.models.portfolio import Holding, PortfolioStatement
from app.models.verification import VerificationStatus
from app.services.portfolio_valuation import (
    value_portfolio,
    verified_portfolio_valuation,
)


VALUATION_DATE = date(2026, 10, 16)


def create_portfolio():
    return PortfolioStatement(
        portfolio_id="P001",
        valuation_date=VALUATION_DATE,
        holdings=[
            Holding(
                holding_id="H001",
                scheme_name="Example Equity Fund",
                units=Decimal("10"),
            )
        ],
    )


def create_nav_record(
    nav_date=VALUATION_DATE,
    nav=Decimal("100"),
    source_url="https://example.com/nav",
    evidence_text="Example Equity Fund NAV: 100 dated 16-Oct-2026",
):
    evidence = NAVEvidence(
        evidence_id="E001",
        source_url=source_url,
        retrieved_at=datetime.now(timezone.utc),
        evidence_text=evidence_text,
    )

    return NAVRecord(
        scheme_name="Example Equity Fund",
        nav_date=nav_date,
        nav=nav,
        evidence=evidence,
    )


def test_valid_portfolio_is_valued():
    result = verified_portfolio_valuation(
        create_portfolio(),
        [create_nav_record()],
    )

    assert result["status"] == VerificationStatus.VERIFIED.value
    assert result["valuation"]["total_value"] == Decimal("1000.00")


def test_missing_nav_prevents_valuation():
    result = verified_portfolio_valuation(
        create_portfolio(),
        [],
    )

    assert result["status"] == VerificationStatus.REVIEW_REQUIRED.value
    assert result["valuation"] is None


def test_wrong_date_prevents_valuation():
    wrong_date_nav = create_nav_record(
        nav_date=date(2026, 10, 17),
    )

    result = verified_portfolio_valuation(
        create_portfolio(),
        [wrong_date_nav],
    )

    assert result["status"] == VerificationStatus.REVIEW_REQUIRED.value
    assert result["valuation"] is None


def test_duplicate_nav_records_prevent_valuation():
    result = verified_portfolio_valuation(
        create_portfolio(),
        [
            create_nav_record(),
            create_nav_record(),
        ],
    )

    assert result["status"] == VerificationStatus.REVIEW_REQUIRED.value
    assert result["valuation"] is None


def test_direct_valuation_rejects_missing_nav():
    try:
        value_portfolio(create_portfolio(), [])
    except ValueError as exc:
        assert "Expected exactly one matching NAV" in str(exc)
    else:
        raise AssertionError("Expected missing NAV to be rejected")
