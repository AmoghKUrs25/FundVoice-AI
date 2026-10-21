from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.nav import NAVEvidence, NAVRecord
from app.models.portfolio import Holding, PortfolioStatement
from app.models.verification import VerificationStatus
from app.verification.engine import verify_portfolio

VALUATION_DATE = date(2026, 10, 16)


def create_portfolio():
    return PortfolioStatement(
        portfolio_id="P001",
        valuation_date=VALUATION_DATE,
        holdings=[
            Holding(
                holding_id="H001",
                scheme_name="Example Equity Fund",
                units=Decimal("125.500"),
            )
        ],
    )


def create_nav_record(
    nav_date=VALUATION_DATE,
    nav=Decimal("80.25"),
):
    evidence = NAVEvidence(
        evidence_id="E001",
        source_url="https://example.com/nav",
        retrieved_at=datetime.now(timezone.utc),
        evidence_text=(
            "Example Equity Fund NAV: 80.25 "
            "dated 16-Oct-2026"
        ),
    )

    return NAVRecord(
        scheme_name="Example Equity Fund",
        nav_date=nav_date,
        nav=nav,
        evidence=evidence,
    )


def test_correct_nav_is_verified():
    result = verify_portfolio(
        create_portfolio(),
        [create_nav_record()],
    )

    assert result.status == VerificationStatus.VERIFIED
    assert result.issues == []


def test_different_nav_date_requires_review():
    result = verify_portfolio(
        create_portfolio(),
        [
            create_nav_record(
                nav_date=date(2026, 10, 17)
            )
        ],
    )

    assert result.status == VerificationStatus.REVIEW_REQUIRED
    assert result.issues[0].code == "NAV_DATE_MISMATCH"


def test_missing_nav_requires_review():
    result = verify_portfolio(
        create_portfolio(),
        [],
    )

    assert result.status == VerificationStatus.REVIEW_REQUIRED
    assert result.issues[0].code == "NAV_NOT_FOUND"


def test_duplicate_matching_navs_require_review():
    result = verify_portfolio(
        create_portfolio(),
        [
            create_nav_record(),
            create_nav_record(),
        ],
    )

    assert result.status == VerificationStatus.REVIEW_REQUIRED
    assert result.issues[0].code == "AMBIGUOUS_NAV"


def test_zero_units_are_not_rejected_as_invalid():
    portfolio = PortfolioStatement(
        portfolio_id="P002",
        valuation_date=VALUATION_DATE,
        holdings=[
            Holding(
                holding_id="H002",
                scheme_name="Example Equity Fund",
                units=Decimal("0"),
            )
        ],
    )

    result = verify_portfolio(
        portfolio,
        [create_nav_record()],
    )

    assert result.status == VerificationStatus.VERIFIED

    
def test_missing_source_url_requires_review():
    portfolio = create_portfolio()
    nav_record = create_nav_record()
    nav_record.evidence.source_url = "   "

    result = verify_portfolio(portfolio, [nav_record])

    assert result.status == VerificationStatus.REVIEW_REQUIRED
    assert result.issues[0].code == "MISSING_SOURCE_URL"


def test_missing_evidence_text_requires_review():
    portfolio = create_portfolio()
    nav_record = create_nav_record()
    nav_record.evidence.evidence_text = "   "

    result = verify_portfolio(portfolio, [nav_record])

    assert result.status == VerificationStatus.REVIEW_REQUIRED
    assert result.issues[0].code == "MISSING_EVIDENCE_TEXT"



def test_negative_units_are_rejected_by_holding_model():
    with pytest.raises(ValidationError):
        Holding(
            holding_id="H003",
            scheme_name="Example Equity Fund",
            units=Decimal("-1"),
        )


