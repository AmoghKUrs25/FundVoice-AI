
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.portfolio import (
    Holding,
    PortfolioStatement,
)
from app.models.nav import (
    NAVEvidence,
    NAVRecord,
)


def test_valid_holding():
    holding = Holding(
        holding_id="H001",
        scheme_name="Example Equity Fund",
        units=Decimal("125.500"),
    )

    assert holding.units == Decimal("125.500")


def test_negative_units_rejected():
    with pytest.raises(ValidationError):
        Holding(
            holding_id="H001",
            scheme_name="Example Equity Fund",
            units=Decimal("-10"),
        )


def test_duplicate_holding_ids_rejected():
    with pytest.raises(ValidationError):
        PortfolioStatement(
            portfolio_id="P001",
            valuation_date=date(2026, 10, 16),
            holdings=[
                Holding(
                    holding_id="H001",
                    scheme_name="Fund A",
                    units=Decimal("10"),
                ),
                Holding(
                    holding_id="H001",
                    scheme_name="Fund B",
                    units=Decimal("20"),
                ),
            ],
        )


def test_valid_nav_record():
    evidence = NAVEvidence(
        evidence_id="E001",
        source_url="https://example.com/nav",
        retrieved_at=datetime.now(timezone.utc),
        evidence_text="Example Equity Fund NAV: 80.25",
    )

    record = NAVRecord(
        scheme_name="Example Equity Fund",
        nav_date=date(2026, 10, 16),
        nav=Decimal("80.25"),
        evidence=evidence,
    )

    assert record.nav == Decimal("80.25")
    assert record.nav_date == date(2026, 10, 16)


def test_zero_nav_rejected():
    evidence = NAVEvidence(
        evidence_id="E002",
        source_url="https://example.com/nav",
        retrieved_at=datetime.now(timezone.utc),
        evidence_text="Example NAV evidence",
    )

    with pytest.raises(ValidationError):
        NAVRecord(
            scheme_name="Example Equity Fund",
            nav_date=date(2026, 10, 16),
            nav=Decimal("0"),
            evidence=evidence,
        )


def test_timezone_required_for_retrieval_time():
    with pytest.raises(ValidationError):
        NAVEvidence(
            evidence_id="E003",
            source_url="https://example.com/nav",
            retrieved_at=datetime(2026, 10, 19, 10, 0),
            evidence_text="Example NAV evidence",
        )