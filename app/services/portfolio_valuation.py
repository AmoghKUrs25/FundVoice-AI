from app.models.verification import VerificationStatus
from app.verification.engine import verify_portfolio
from decimal import Decimal

from app.models.nav import NAVRecord
from app.models.portfolio import Holding, PortfolioStatement
from app.services.portfolio_calculator import (
    calculate_holding_value,
    round_money,
)


def value_holding(
    holding: Holding,
    nav_record: NAVRecord,
    valuation_date,
) -> dict:
    """
    Value a holding only when its NAV date matches
    the portfolio valuation date.
    """

    if nav_record.nav_date != valuation_date:
        raise ValueError(
            "NAV date does not match the requested valuation date."
        )

    if (
        nav_record.scheme_name.casefold()
        != holding.scheme_name.casefold()
    ):
        raise ValueError(
            "NAV scheme does not match the portfolio holding."
        )

    exact_value = calculate_holding_value(
        holding.units,
        nav_record.nav,
    )

    return {
        "holding_id": holding.holding_id,
        "scheme_name": holding.scheme_name,
        "units": holding.units,
        "nav": nav_record.nav,
        "nav_date": nav_record.nav_date,
        "value": round_money(exact_value),
        "evidence_id": nav_record.evidence.evidence_id,
        "source_url": nav_record.evidence.source_url,
    }


def value_portfolio(
    portfolio: PortfolioStatement,
    nav_records: list[NAVRecord],
) -> dict:
    """
    Produce a portfolio valuation using dated NAV records.

    Each holding must have exactly one matching NAV record.
    """

    results = []

    for holding in portfolio.holdings:
        matching_records = [
            record
            for record in nav_records
            if (
                record.scheme_name.casefold()
                == holding.scheme_name.casefold()
                and record.nav_date == portfolio.valuation_date
            )
        ]

        if len(matching_records) != 1:
            raise ValueError(
                f"Expected exactly one matching NAV for "
                f"{holding.scheme_name} on "
                f"{portfolio.valuation_date}; "
                f"found {len(matching_records)}."
            )

        results.append(
            value_holding(
                holding,
                matching_records[0],
                portfolio.valuation_date,
            )
        )

    total = sum(
        (item["value"] for item in results),
        Decimal("0"),
    )

    return {
        "portfolio_id": portfolio.portfolio_id,
        "valuation_date": portfolio.valuation_date,
        "holdings": results,
        "total_value": round_money(total),
    }
def verified_portfolio_valuation(
    portfolio: PortfolioStatement,
    nav_records: list[NAVRecord],
) -> dict:
    """
    Verify a portfolio before calculating its valuation.

    Returns a review result without calculating a valuation
    when the required checks do not pass.
    """

    verification = verify_portfolio(
        portfolio,
        nav_records,
    )

    if verification.status != VerificationStatus.VERIFIED:
        return {
            "portfolio_id": portfolio.portfolio_id,
            "valuation_date": portfolio.valuation_date,
            "status": verification.status.value,
            "issues": [
                issue.model_dump(mode="json")
                for issue in verification.issues
            ],
            "valuation": None,
        }

    valuation = value_portfolio(
        portfolio,
        nav_records,
    )

    return {
        "portfolio_id": portfolio.portfolio_id,
        "valuation_date": portfolio.valuation_date,
        "status": verification.status.value,
        "issues": [],
        "valuation": valuation,
    }

def calculate_portfolio_valuation(
    portfolio: PortfolioStatement,
    nav_records: list[NAVRecord],
) -> dict:
    """
    Compatibility wrapper for the agent workflow.

    Delegates valuation to the existing value_portfolio()
    function, preserving the current valuation logic.
    """
    return value_portfolio(portfolio, nav_records)



