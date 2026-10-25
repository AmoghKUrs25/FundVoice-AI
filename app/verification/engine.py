
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urlparse

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
    Verify NAV data and the presence of its supporting evidence.

    Checks scheme name, valuation date, NAV value, evidence ID,
    HTTP/HTTPS source URL, evidence text, and retrieval timestamp.

    This checks consistency and evidence metadata presence.
    It does not independently authenticate the source.
    """

    issues: list[VerificationIssue] = []
    checks_passed: list[str] = []

    # 1. Validate the portfolio.
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

    # 2. Verify each holding independently.
    for holding in portfolio.holdings:
        if (
            not holding.units.is_finite()
            or holding.units < Decimal("0")
        ):
            issues.append(
                VerificationIssue(
                    code="INVALID_UNITS",
                    message="Holding units are invalid.",
                    holding_id=holding.holding_id,
                )
            )
            continue

        checks_passed.append(f"UNITS_VALID:{holding.holding_id}")

        # 3. Find records matching the scheme name.
        same_scheme_records = [
            record
            for record in nav_records
            if record.scheme_name.strip().casefold()
            == holding.scheme_name.strip().casefold()
        ]

        if not same_scheme_records:
            issues.append(
                VerificationIssue(
                    code="NAV_NOT_FOUND",
                    message=(
                        "No NAV record was found for "
                        "the requested fund."
                    ),
                    holding_id=holding.holding_id,
                )
            )
            continue

        # 4. Match the requested valuation date.
        matching_records = [
            record
            for record in same_scheme_records
            if record.nav_date == portfolio.valuation_date
        ]

        if not matching_records:
            available_dates = sorted(
                {
                    record.nav_date.isoformat()
                    for record in same_scheme_records
                }
            )

            issues.append(
                VerificationIssue(
                    code="NAV_DATE_MISMATCH",
                    message=(
                        "No NAV matches the requested valuation "
                        f"date {portfolio.valuation_date.isoformat()}. "
                        "Available NAV dates: "
                        f"{', '.join(available_dates)}."
                    ),
                    holding_id=holding.holding_id,
                )
            )
            continue

        checks_passed.append(
            f"NAV_DATE_MATCH:{holding.holding_id}"
        )

        # 5. Reject duplicate matching records.
        if len(matching_records) > 1:
            issues.append(
                VerificationIssue(
                    code="AMBIGUOUS_NAV",
                    message=(
                        "Multiple NAV records match this fund "
                        "and valuation date."
                    ),
                    holding_id=holding.holding_id,
                )
            )
            continue

        nav_record = matching_records[0]

        checks_passed.append(
            f"NAV_SCHEME_MATCH:{holding.holding_id}"
        )

        # 6. Validate the NAV value.
        if (
            not nav_record.nav.is_finite()
            or nav_record.nav <= Decimal("0")
        ):
            issues.append(
                VerificationIssue(
                    code="INVALID_NAV",
                    message=(
                        "The matching NAV must be a finite, "
                        "positive number."
                    ),
                    holding_id=holding.holding_id,
                )
            )
            continue

        checks_passed.append(
            f"NAV_VALUE_VALID:{holding.holding_id}"
        )

        # 7. Validate evidence ID.
        evidence = nav_record.evidence

        if not evidence.evidence_id.strip():
            issues.append(
                VerificationIssue(
                    code="MISSING_EVIDENCE_ID",
                    message="The NAV evidence identifier is missing.",
                    holding_id=holding.holding_id,
                )
            )
            continue

        # 8. Validate the source URL.
        source_url = evidence.source_url.strip()

        try:
            parsed_url = urlparse(source_url)
            valid_url = (
                parsed_url.scheme in {"http", "https"}
                and bool(parsed_url.netloc)
                and bool(parsed_url.hostname)
            )
        except (ValueError, TypeError):
            valid_url = False

        if not valid_url:
            issues.append(
                VerificationIssue(
                    code="INVALID_SOURCE_URL",
                    message=(
                        "The NAV source URL must be a valid "
                        "HTTP or HTTPS URL."
                    ),
                    holding_id=holding.holding_id,
                )
            )
            continue

        # 9. Validate supporting evidence text.
        if not evidence.evidence_text.strip():
            issues.append(
                VerificationIssue(
                    code="MISSING_EVIDENCE_TEXT",
                    message=(
                        "The supporting NAV evidence text is missing."
                    ),
                    holding_id=holding.holding_id,
                )
            )
            continue

        # 10. Validate retrieval timestamp.
        retrieved_at = evidence.retrieved_at

        if not isinstance(retrieved_at, datetime):
            issues.append(
                VerificationIssue(
                    code="MISSING_RETRIEVAL_TIMESTAMP",
                    message=(
                        "The NAV retrieval timestamp is missing "
                        "or invalid."
                    ),
                    holding_id=holding.holding_id,
                )
            )
            continue

        if (
            retrieved_at.tzinfo is None
            or retrieved_at.utcoffset() is None
        ):
            issues.append(
                VerificationIssue(
                    code="INVALID_RETRIEVAL_TIMESTAMP",
                    message=(
                        "The NAV retrieval timestamp must include "
                        "timezone information."
                    ),
                    holding_id=holding.holding_id,
                )
            )
            continue

        retrieved_at_utc = retrieved_at.astimezone(timezone.utc)

        if retrieved_at_utc > datetime.now(timezone.utc):
            issues.append(
                VerificationIssue(
                    code="FUTURE_RETRIEVAL_TIMESTAMP",
                    message=(
                        "The NAV retrieval timestamp cannot be "
                        "in the future."
                    ),
                    holding_id=holding.holding_id,
                )
            )
            continue

        checks_passed.append(
            f"NAV_EVIDENCE_VALID:{holding.holding_id}"
        )

    # 11. Determine the overall verification status.
    if not issues:
        status = VerificationStatus.VERIFIED
    elif any(
        issue.code in {
            "EMPTY_PORTFOLIO",
            "INVALID_UNITS",
            "INVALID_NAV",
        }
        for issue in issues
    ):
        status = VerificationStatus.FAILED
    else:
        status = VerificationStatus.REVIEW_REQUIRED

    # 12. Return the structured verification result.
    return VerificationResult(
        portfolio_id=portfolio.portfolio_id,
        status=status,
        checks_passed=checks_passed,
        issues=issues,
    )
