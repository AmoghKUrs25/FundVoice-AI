from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.models.nav import NAVEvidence, NAVRecord
from app.models.portfolio import Holding, PortfolioStatement
from app.services.portfolio_valuation import value_portfolio


def make_nav(scheme_name, nav, nav_date, evidence_id):
    evidence = NAVEvidence(
        evidence_id=evidence_id,
        source_url="https://example.com/nav",
        retrieved_at=datetime.now(timezone.utc),
        evidence_text=(
            f"{scheme_name} NAV {nav} dated {nav_date}"
        ),
    )

    return NAVRecord(
        scheme_name=scheme_name,
        nav=Decimal(nav),
        nav_date=nav_date,
        evidence=evidence,
    )


def test_mixed_nav_dates_do_not_produce_combined_valuation():
    portfolio = PortfolioStatement(
        portfolio_id="TC2-001",
        valuation_date=date(2026, 10, 22),
        holdings=[
            Holding(
                holding_id="H001",
                scheme_name="Example Equity Fund",
                units=Decimal("10"),
            ),
            Holding(
                holding_id="H002",
                scheme_name="Example Debt Fund",
                units=Decimal("20"),
            ),
        ],
    )

    nav_records = [
        make_nav(
            "Example Equity Fund",
            "100",
            date(2026, 10, 22),
            "E001",
        ),
        make_nav(
            "Example Debt Fund",
            "50",
            date(2026, 10, 21),
            "E002",
        ),
    ]

    with pytest.raises(ValueError, match="Expected exactly one matching NAV"):
        value_portfolio(portfolio, nav_records)

        
def test_mixed_nav_dates_preserve_each_date_and_block_total():
    from datetime import date, datetime, timezone
    from decimal import Decimal

    import pytest

    from app.models.nav import NAVEvidence, NAVRecord
    from app.models.portfolio import Holding, PortfolioStatement
    from app.services.portfolio_valuation import value_portfolio

    def make_nav(scheme_name, nav, nav_date, evidence_id):
        evidence = NAVEvidence(
            evidence_id=evidence_id,
            source_url="https://example.com/nav",
            retrieved_at=datetime.now(timezone.utc),
            evidence_text=f"{scheme_name} NAV {nav} dated {nav_date}",
        )
        return NAVRecord(
            scheme_name=scheme_name,
            nav=Decimal(nav),
            nav_date=nav_date,
            evidence=evidence,
        )

    date_one = date(2026, 10, 22)
    date_two = date(2026, 10, 21)

    portfolio = PortfolioStatement(
        portfolio_id="TC2-002",
        valuation_date=date_one,
        holdings=[
            Holding(
                holding_id="H001",
                scheme_name="Example Equity Fund",
                units=Decimal("10"),
            ),
            Holding(
                holding_id="H002",
                scheme_name="Example Debt Fund",
                units=Decimal("20"),
            ),
        ],
    )

    records = [
        make_nav("Example Equity Fund", "100", date_one, "E001"),
        make_nav("Example Debt Fund", "50", date_two, "E002"),
    ]

    # Both observations retain their actual dates and evidence.
    assert records[0].nav_date == date_one
    assert records[1].nav_date == date_two
    assert records[0].evidence.evidence_id == "E001"
    assert records[1].evidence.evidence_id == "E002"

    # The system must not produce a combined same-date valuation.
    with pytest.raises(ValueError, match="Expected exactly one matching NAV"):
        value_portfolio(portfolio, records)

