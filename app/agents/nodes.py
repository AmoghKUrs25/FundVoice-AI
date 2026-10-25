
"""LangGraph nodes for the FundVoiceAI portfolio workflow."""

import asyncio
from datetime import datetime, timezone
from typing import Any

from app.agents.state import FundVoiceState
from app.models.verification import VerificationStatus
from app.services.nav_retriever import (
    AMFI_NAV_URL,
    NAVRetrievalError,
    fetch_nav_history,
    get_fund_house_id,
    parse_nav_csv,
)
from app.services.portfolio_valuation import value_portfolio
from app.storage.audit_repository import AuditRepository
from app.verification.engine import verify_portfolio


def add_audit_event(
    state: FundVoiceState,
    event_type: str,
    details: dict[str, Any],
) -> list[dict[str, Any]]:
    """Append a timestamped event to the workflow's audit history."""

    events = list(state.get("audit_events", []))
    events.append(
        {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details,
        }
    )
    return events


def build_nav_evidence_audit(
    nav_records: list[Any],
) -> list[dict[str, Any]]:
    """Prepare NAV evidence metadata for persistent audit storage."""

    evidence_items = []

    for record in nav_records:
        evidence = record.evidence
        retrieved_at = getattr(evidence, "retrieved_at", None)

        evidence_items.append(
            {
                "scheme_name": record.scheme_name,
                "nav_date": record.nav_date.isoformat(),
                "nav": str(record.nav),
                "evidence_id": evidence.evidence_id,
                "source_url": evidence.source_url,
                "retrieved_at": (
                    retrieved_at.isoformat()
                    if isinstance(retrieved_at, datetime)
                    else None
                ),
            }
        )

    return evidence_items


def validate_portfolio_node(
    state: FundVoiceState,
) -> dict[str, Any]:
    """Check whether a portfolio is available for processing."""

    portfolio = state.get("portfolio")

    if portfolio is None:
        errors = list(state.get("errors", []))
        errors.append("Portfolio data is missing.")

        return {
            "errors": errors,
            "human_review_required": True,
            "next_action": "human_review",
            "audit_events": add_audit_event(
                state,
                "portfolio_validation_failed",
                {"reason": "Portfolio data is missing."},
            ),
        }

    return {
        "errors": [],
        "human_review_required": False,
        "next_action": "retrieve_nav",
        "audit_events": add_audit_event(
            state,
            "portfolio_validation_passed",
            {"portfolio_id": portfolio.portfolio_id},
        ),
    }


def retrieve_nav_node(
    state: FundVoiceState,
) -> dict[str, Any]:
    """Retrieve exact-date NAV records for all portfolio holdings."""

    portfolio = state.get("portfolio")

    if portfolio is None:
        errors = list(state.get("errors", []))
        errors.append("Portfolio is missing.")

        return {
            "errors": errors,
            "valuation": None,
            "human_review_required": True,
            "next_action": "human_review",
            "audit_events": add_audit_event(
                state,
                "nav_retrieval_failed",
                {"reason": "Cannot retrieve NAV without a portfolio."},
            ),
        }

    supplied_records = state.get("nav_records", [])

    if supplied_records:
        return {
            "nav_records": supplied_records,
            "errors": [],
            "retry_count": state.get("retry_count", 0),
            "human_review_required": False,
            "next_action": "verify_nav",
            "audit_events": add_audit_event(
                state,
                "nav_records_reused",
                {
                    "record_count": len(supplied_records),
                    "source": "existing_workflow_state",
                },
            ),
        }

    valuation_date = portfolio.valuation_date
    previous_retry_count = state.get("retry_count", 0)

    retrieved_records = []
    retrieval_errors = []

    # Cache fetched data and metadata once per fund house.
    csv_by_fund_house = {}

    for holding in portfolio.holdings:
        try:
            fund_house_id = get_fund_house_id(holding.scheme_name)

            if fund_house_id not in csv_by_fund_house:
                csv_text = asyncio.run(
                    fetch_nav_history(
                        start_date=valuation_date,
                        end_date=valuation_date,
                        fund_house_id=fund_house_id,
                    )
                )

                # This is the configured URL, not necessarily a redirected URL.
                csv_by_fund_house[fund_house_id] = {
                    "text": csv_text,
                    "source_url": AMFI_NAV_URL,
                    "retrieved_at": datetime.now(timezone.utc),
                }

            fetch_result = csv_by_fund_house[fund_house_id]

            requested_nav_name = holding.scheme_name
            if holding.plan and holding.option:
                requested_nav_name = (
                    f"{holding.scheme_name} - "
                    f"{holding.plan} - {holding.option}"
                )

            record = parse_nav_csv(
                csv_text=fetch_result["text"],
                requested_scheme_name=requested_nav_name,
                requested_date=valuation_date,
                source_url=fetch_result["source_url"],
                retrieved_at=fetch_result["retrieved_at"],
            )

            retrieved_records.append(record)

        except (NAVRetrievalError, ValueError) as exc:
            retrieval_errors.append(
                f"{holding.scheme_name}: {exc}"
            )

        except Exception as exc:
            retrieval_errors.append(
                f"{holding.scheme_name}: "
                f"Unexpected retrieval error: {exc}"
            )

    if retrieval_errors:
        next_retry_count = previous_retry_count + 1

        if next_retry_count < 2:
            return {
                "nav_records": retrieved_records,
                "errors": retrieval_errors,
                "retry_count": next_retry_count,
                "valuation": None,
                "human_review_required": False,
                "next_action": "retry_nav",
                "audit_events": add_audit_event(
                    state,
                    "nav_retrieval_retry",
                    {
                        "attempt": next_retry_count,
                        "errors": retrieval_errors,
                    },
                ),
            }

        return {
            "nav_records": retrieved_records,
            "errors": retrieval_errors,
            "retry_count": next_retry_count,
            "valuation": None,
            "human_review_required": True,
            "next_action": "human_review",
            "audit_events": add_audit_event(
                state,
                "nav_retrieval_failed",
                {
                    "reason": (
                        "NAV retrieval failed after the "
                        "permitted attempts."
                    ),
                    "errors": retrieval_errors,
                },
            ),
        }

    return {
        "nav_records": retrieved_records,
        "errors": [],
        "retry_count": previous_retry_count,
        "human_review_required": False,
        "next_action": "verify_nav",
        "audit_events": add_audit_event(
            state,
            "nav_retrieval_succeeded",
            {
                "record_count": len(retrieved_records),
                "valuation_date": str(valuation_date),
            },
        ),
    }


def verify_nav_node(
    state: FundVoiceState,
) -> dict[str, Any]:
    """Verify NAV records and persist the verification audit."""

    portfolio = state.get("portfolio")
    nav_records = state.get("nav_records", [])

    if portfolio is None:
        errors = list(state.get("errors", []))
        errors.append("Portfolio is missing.")

        return {
            "verification": None,
            "valuation": None,
            "errors": errors,
            "human_review_required": True,
            "next_action": "human_review",
            "audit_events": add_audit_event(
                state,
                "verification_failed",
                {
                    "status": "FAILED",
                    "reason": "Portfolio is missing.",
                    "checks_passed": [],
                    "checks_failed": [
                        {
                            "code": "PORTFOLIO_NOT_FOUND",
                            "message": (
                                "No portfolio was supplied "
                                "for verification."
                            ),
                        }
                    ],
                    "human_review_required": True,
                },
            ),
        }

    # First, run the actual verification.
    verification = verify_portfolio(portfolio, nav_records)

    checks_passed = list(verification.checks_passed)

    checks_failed = [
        {
            "code": issue.code,
            "message": issue.message,
            "holding_id": issue.holding_id,
        }
        for issue in verification.issues
    ]

    human_review_required = (
        verification.status != VerificationStatus.VERIFIED
    )

    event_type = (
        "portfolio_verification_completed"
        if not human_review_required
        else "verification_requires_review"
    )

    # Preserve the verification event in workflow state.
    audit_events = add_audit_event(
        state,
        event_type,
        {
            "portfolio_id": portfolio.portfolio_id,
            "status": verification.status.value,
            "checks_passed": checks_passed,
            "checks_failed": checks_failed,
            "human_review_required": human_review_required,
        },
    )

    # Persist the verification result and NAV evidence in SQLite.
    try:
        repository = AuditRepository()

        repository.record_verification(
            run_id=str(
                state.get("run_id")
                or portfolio.portfolio_id
            ),
            portfolio_id=portfolio.portfolio_id,
            verification_status=verification.status.value,
            checks_passed=checks_passed,
            issues=checks_failed,
            nav_evidence=build_nav_evidence_audit(nav_records),
        )

    except Exception as exc:
        # Make persistence failure visible; do not pretend that
        # the database write succeeded.
        audit_events = add_audit_event(
            {
                **state,
                "audit_events": audit_events,
            },
            "audit_persistence_failed",
            {
                "portfolio_id": portfolio.portfolio_id,
                "operation": "record_verification",
                "error": str(exc),
            },
        )

    errors = list(state.get("errors", []))

    if human_review_required:
        for issue in verification.issues:
            if issue.message not in errors:
                errors.append(issue.message)

    return {
        "verification": verification,
        "valuation": None,
        "errors": errors,
        "human_review_required": human_review_required,
        "next_action": (
            "continue"
            if not human_review_required
            else "human_review"
        ),
        "audit_events": audit_events,
    }


def calculate_valuation_node(
    state: FundVoiceState,
) -> dict[str, Any]:
    """Calculate portfolio value only after successful verification."""

    portfolio = state.get("portfolio")
    nav_records = state.get("nav_records", [])
    verification = state.get("verification")

    if (
        portfolio is None
        or not nav_records
        or verification is None
        or verification.status != VerificationStatus.VERIFIED
    ):
        return {
            "valuation": None,
            "human_review_required": True,
            "next_action": "human_review",
            "audit_events": add_audit_event(
                state,
                "valuation_blocked",
                {"reason": "Verification has not passed."},
            ),
        }

    valuation = value_portfolio(portfolio, nav_records)

    return {
        "valuation": valuation,
        "human_review_required": False,
        "next_action": "generate_report",
        "audit_events": add_audit_event(
            state,
            "portfolio_valuation_completed",
            {
                "valuation_date": str(
                    valuation["valuation_date"]
                ),
                "total_value": str(valuation["total_value"]),
            },
        ),
    }


def generate_report_node(
    state: FundVoiceState,
) -> dict[str, Any]:
    """Generate a factual report from the verified valuation."""

    valuation = state.get("valuation")

    if valuation is None:
        return human_review_node(state)

    verification = state.get("verification")

    if (
        verification is None
        or verification.status != VerificationStatus.VERIFIED
    ):
        return human_review_node(state)

    total_value = valuation["total_value"]
    valuation_date = valuation["valuation_date"]

    report = (
        f"Portfolio valuation for {valuation_date}. "
        f"The calculated portfolio value is ₹{total_value:,.2f}. "
        "This report presents a valuation, not investment advice."
    )

    return {
        "report": report,
        "next_action": "completed",
        "human_review_required": False,
        "audit_events": add_audit_event(
            state,
            "report_generated",
            {
                "valuation_date": str(valuation_date),
                "total_value": str(total_value),
            },
        ),
    }


def human_review_node(
    state: FundVoiceState,
) -> dict[str, Any]:
    """Require human review and prevent an unverified valuation."""

    errors = list(state.get("errors", []))
    verification = state.get("verification")

    if verification is not None:
        for issue in verification.issues:
            if issue.message not in errors:
                errors.append(issue.message)

    if not errors:
        errors.append(
            "The portfolio could not be verified automatically."
        )

    report = (
        "Human review required. "
        + " ".join(errors)
        + " No verified valuation is being presented."
    )

    audit_events = add_audit_event(
        state,
        "human_review_required",
        {"reasons": errors},
    )

    return {
        "valuation": None,
        "report": report,
        "errors": errors,
        "human_review_required": True,
        "next_action": "human_review",
        "audit_events": audit_events,
    }
