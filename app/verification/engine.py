from decimal import Decimal

from app.models.nav import NAVRecord
from app.models.portfolio import PortfolioStatement
from app.models.verification import (
    VerificationIssue,
    VerificationResult,
    VerificationStatus,
)


def verify_portfolio(
    portfolio: PortfolioStatement,
    nav_records: list[NAVRecord],
) -> VerificationResult:
    """
    Verify whether every portfolio holding has exactly one
    matching NAV record for the requested valuation date.

    This verifies data consistency and evidence presence.
    It does not independently authenticate the source.
    """

    issues: list[VerificationIssue] = []
    checks_passed: list[str] = []

    if not portfolio.holdings:
        return VerificationResult(
            portfolio_id=portfolio.portfolio_id,
            status=VerificationStatus.FAILED,
            issues=[
                VerificationIssue(
                    code="EMPTY_PORTFOLIO",
                    message="The portfolio contains no holdings.",
                )
            ],
        )

    checks_passed.append("PORTFOLIO_NOT_EMPTY")

    for holding in portfolio.holdings:
        if not holding.units.is_finite() or holding.units < Decimal("0"):
            issues.append(
                VerificationIssue(
                    code="INVALID_UNITS",
                    message="Holding units are invalid.",
                    holding_id=holding.holding_id,
                )
            )
            continue

        same_scheme_records = [
            record
            for record in nav_records
            if record.scheme_name.casefold()
            == holding.scheme_name.casefold()
        ]

        matching_records = [
            record
            for record in same_scheme_records
            if record.nav_date == portfolio.valuation_date
        ]

        if not matching_records:
            if same_scheme_records:
                available_dates = sorted(
                    {record.nav_date.isoformat()
                     for record in same_scheme_records}
                )

                issues.append(
                    VerificationIssue(
                        code="NAV_DATE_MISMATCH",
                        message=(
                            "No NAV matches the requested valuation date. "
                            f"Available NAV dates: {', '.join(available_dates)}."
                        ),
                        holding_id=holding.holding_id,
                    )
                )
            else:
                issues.append(
                    VerificationIssue(
                        code="NAV_NOT_FOUND",
                        message=(
                            "No NAV record was found for this fund."
                        ),
                        holding_id=holding.holding_id,
                    )
                )

            continue

        if len(matching_records) > 1:
            issues.append(
                VerificationIssue(
                    code="AMBIGUOUS_NAV",
                    message=(
                        "Multiple NAV records match this fund and date."
                    ),
                    holding_id=holding.holding_id,
                )
            )
            continue

        nav_record = matching_records[0]

        if (
            nav_record.nav <= Decimal("0")
            or not nav_record.nav.is_finite()
        ):
            issues.append(
                VerificationIssue(
                    code="INVALID_NAV",
                    message="The matching NAV is invalid.",
                    holding_id=holding.holding_id,
                )
            )
            continue

        evidence = nav_record.evidence

        if not evidence.source_url.strip():
            issues.append(
                VerificationIssue(
                    code="MISSING_SOURCE_URL",
                    message="The NAV source URL is missing.",
                    holding_id=holding.holding_id,
                )
            )
            continue

        if not evidence.evidence_text.strip():
            issues.append(
                VerificationIssue(
                    code="MISSING_EVIDENCE_TEXT",
                    message="The supporting NAV evidence is missing.",
                    holding_id=holding.holding_id,
                )
            )
            continue

        checks_passed.append(
            f"NAV_DATE_MATCH:{holding.holding_id}"
        )
        checks_passed.append(
            f"NAV_SCHEME_MATCH:{holding.holding_id}"
        )
        checks_passed.append(
            f"NAV_EVIDENCE_PRESENT:{holding.holding_id}"
        )

    if not issues:
        status = VerificationStatus.VERIFIED
    elif any(
        issue.code in {
            "INVALID_UNITS",
            "INVALID_NAV",
            "EMPTY_PORTFOLIO",
        }
        for issue in issues
    ):
        status = VerificationStatus.FAILED
    else:
        status = VerificationStatus.REVIEW_REQUIRED

    return VerificationResult(
        portfolio_id=portfolio.portfolio_id,
        status=status,
        checks_passed=checks_passed,
        issues=issues,
    )