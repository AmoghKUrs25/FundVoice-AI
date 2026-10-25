
from datetime import date
from decimal import Decimal

from app.models.nav import NAVEvidence, NAVRecord
from app.models.portfolio import Holding, PortfolioStatement
from app.models.verification import VerificationStatus


def test_tc2_mixed_dates_block_verified_total():
    valuation_date = date(2026, 10, 22)

    portfolio = PortfolioStatement(
        portfolio_id="TC2-P001",
        valuation_date=valuation_date,
        holdings=[
            Holding(
                holding_id="H001",
                scheme_name="Synthetic Fund A",
                units=Decimal("10"),
            ),
            Holding(
                holding_id="H002",
                scheme_name="Synthetic Fund B",
                units=Decimal("20"),
            ),
        ],
    )

    def make_nav(scheme, nav, nav_date, evidence_id):
        return NAVRecord(
            scheme_name=scheme,
            nav=Decimal(nav),
            nav_date=nav_date,
            evidence=NAVEvidence(
                evidence_id=evidence_id,
                source_url="https://example.com/synthetic-nav",
                retrieved_at="2026-10-23T00:00:00Z",
                evidence_text=f"Synthetic NAV for {scheme}",
            ),
        )

    nav_records = [
        make_nav(
            "Synthetic Fund A",
            "100",
            date(2026, 10, 22),
            "TC2-E001",
        ),
        make_nav(
            "Synthetic Fund B",
            "50",
            date(2026, 10, 21),
            "TC2-E002",
        ),
    ]

    from app.verification.engine import verify_portfolio

    verification = verify_portfolio(portfolio, nav_records)

    verified = (
        verification.status == VerificationStatus.VERIFIED
    )

    assert verification.status == VerificationStatus.REVIEW_REQUIRED
    assert verified is False
    assert any(
    issue.code == "NAV_DATE_MISMATCH"
    for issue in verification.issues
)

def test_dashboard_source_contains_mixed_date_safeguards():
    with open("app/ui/dashboard.py", encoding="utf-8") as file:
        source = file.read()

    assert "Verified portfolio value" in source
    assert "A verified portfolio value is not available." in source
    assert "Dated NAV Observations" in source
    assert "Different dates must not be combined into a " in source
