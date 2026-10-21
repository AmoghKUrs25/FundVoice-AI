
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.agents.state import FundVoiceState


def add_audit_event(state: FundVoiceState, message: str) -> list[dict[str, Any]]:
    """Return a new audit trail containing this workflow event."""
    events = list(state.get("audit_events", []))
    events.append(
        {
            "event": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    return events


def validate_portfolio_node(state: FundVoiceState) -> dict:
    """Check that a portfolio was provided before proceeding."""
    portfolio = state.get("portfolio")
    errors = list(state.get("errors", []))

    if portfolio is None:
        errors.append("Portfolio input is missing.")
        return {
            "errors": errors,
            "human_review_required": True,
            "next_action": "human_review",
            "audit_events": add_audit_event(
                state, "Portfolio validation failed: missing input"
            ),
        }

    holdings = getattr(portfolio, "holdings", None)
    if holdings is None and isinstance(portfolio, dict):
        holdings = portfolio.get("holdings")

    if not holdings:
        errors.append("Portfolio has no holdings.")
        return {
            "errors": errors,
            "human_review_required": True,
            "next_action": "human_review",
            "audit_events": add_audit_event(
                state, "Portfolio validation failed: no holdings"
            ),
        }

    return {
        "errors": errors,
        "human_review_required": False,
        "next_action": "retrieve_nav",
        "audit_events": add_audit_event(
            state, "Portfolio input accepted for NAV retrieval"
        ),
    }


def retrieve_nav_node(state: FundVoiceState) -> dict:
    """Use supplied NAV records or retrieve them from AMFI."""

    from app.services.nav_retriever import (
        NAVRetrievalError,
        fetch_nav_history_sync,
        parse_nav_csv,
    )

    portfolio = state.get("portfolio")
    nav_records = state.get("nav_records", [])

    # Preserve preloaded records used by tests or other integrations.
    if nav_records:
        return {
            "human_review_required": False,
            "next_action": "verify_nav",
            "audit_events": add_audit_event(
                state, "NAV records supplied for verification"
            ),
        }

    if portfolio is None:
        return {
            "human_review_required": True,
            "next_action": "human_review",
            "errors": list(state.get("errors", []))
            + ["Cannot retrieve NAV without a portfolio."],
            "audit_events": add_audit_event(
                state, "NAV retrieval stopped: portfolio missing"
            ),
        }

    valuation_date = portfolio.valuation_date
    retrieved_records = []

    try:
        csv_text = fetch_nav_history_sync(
            valuation_date,
            valuation_date,
        )

        for holding in portfolio.holdings:
            record = parse_nav_csv(
                csv_text,
                holding.scheme_name,
                valuation_date,
            )
            retrieved_records.append(record)

    except (NAVRetrievalError, ValueError) as exc:
        return {
            "human_review_required": True,
            "next_action": "human_review",
            "errors": list(state.get("errors", []))
            + [f"NAV retrieval failed: {exc}"],
            "audit_events": add_audit_event(
                state, "NAV retrieval failed; human review required"
            ),
        }

    return {
        "nav_records": retrieved_records,
        "human_review_required": False,
        "next_action": "verify_nav",
        "audit_events": add_audit_event(
            state, "NAV records retrieved from AMFI"
        ),
    }


def verify_nav_node(state: FundVoiceState) -> dict:
    """Run the project's existing verification engine."""
    from app.verification.engine import verify_portfolio

    portfolio = state.get("portfolio")
    nav_records = state.get("nav_records", [])

    if portfolio is None or not nav_records:
        return {
            "human_review_required": True,
            "next_action": "human_review",
            "errors": list(state.get("errors", []))
            + ["Portfolio or NAV data is missing for verification."],
            "audit_events": add_audit_event(
                state, "Verification stopped because required data is missing"
            ),
        }

    try:
        result = verify_portfolio(portfolio, nav_records)
    except Exception as exc:
        return {
            "human_review_required": True,
            "next_action": "human_review",
            "errors": list(state.get("errors", []))
            + [f"Verification could not complete: {exc}"],
            "audit_events": add_audit_event(
                state, "Verification raised an exception"
            ),
        }

    status = getattr(result, "status", None)
    status_value = getattr(status, "value", status)
    verified = str(status_value).upper() == "VERIFIED"

    return {
        "verification": result,
        "human_review_required": not verified,
        "next_action": "calculate_valuation" if verified else "human_review",
        "audit_events": add_audit_event(
            state, f"NAV verification status: {status_value}"
        ),
    }


def calculate_valuation_node(state: FundVoiceState) -> dict:
    """Calculate portfolio valuation only after successful verification."""
    verification = state.get("verification")
    status = getattr(verification, "status", None)
    status_value = getattr(status, "value", status)

    if str(status_value).upper() != "VERIFIED":
        return {
            "human_review_required": True,
            "next_action": "human_review",
            "errors": list(state.get("errors", []))
            + ["Valuation blocked because verification did not pass."],
            "audit_events": add_audit_event(
                state, "Valuation blocked by verification gate"
            ),
        }

    from app.services.portfolio_valuation import value_portfolio

    try:
        valuation = value_portfolio(
            state["portfolio"],
            state.get("nav_records", []),
        )
    except Exception as exc:
        return {
            "human_review_required": True,
            "next_action": "human_review",
            "errors": list(state.get("errors", []))
            + [f"Valuation failed: {exc}"],
            "audit_events": add_audit_event(
                state, "Valuation calculation failed"
            ),
        }

    return {
        "valuation": valuation,
        "human_review_required": False,
        "next_action": "generate_report",
        "audit_events": add_audit_event(
            state, "Portfolio valuation calculated"
        ),
    }


def generate_report_node(state: FundVoiceState) -> dict:
    """Generate a portfolio report from verified valuation results."""

    verification = state.get("verification")
    status = getattr(verification, "status", None)
    status_value = getattr(status, "value", status)

    if str(status_value).upper() != "VERIFIED":
        errors = list(state.get("errors", []))
        errors.append(
            "Report generation blocked because NAV verification did not pass."
        )
        return human_review_node({**state, "errors": errors})

    valuation = state.get("valuation")
    if not valuation:
        errors = list(state.get("errors", []))
        errors.append(
            "Valuation is missing; report generation was blocked."
        )
        return human_review_node({**state, "errors": errors})

    holdings = valuation.get("holdings", [])

    report_lines = [
        "FundVoice AI — Mutual Fund Portfolio Report",
        f"Portfolio ID: {valuation['portfolio_id']}",
        f"Valuation date: {valuation['valuation_date']}",
        "",
        "Holdings:",
    ]

    for holding in holdings:
        report_lines.extend(
            [
                f"Fund: {holding['scheme_name']}",
                f"Units: {holding['units']}",
                f"NAV: ₹{holding['nav']}",
                f"Holding value: ₹{holding['value']}",
                f"NAV date: {holding['nav_date']}",
                f"Evidence ID: {holding['evidence_id']}",
                f"Source: {holding['source_url']}",
                "",
            ]
        )

    report_lines.extend(
        [
            f"Total portfolio value: ₹{valuation['total_value']}",
            "",
            "Verification: Passed by the configured verification checks.",
            (
                "Note: NAV evidence presence was checked; "
                "independent source authentication is not implied."
            ),
        ]
    )

    audit_events = add_audit_event(state, "Report generated")

    return {
        "report": "\n".join(report_lines),
        "human_review_required": False,
        "next_action": "complete",
        "errors": state.get("errors", []),
        "audit_events": audit_events,
    }


def human_review_node(state: FundVoiceState) -> dict:
    """Pause the workflow and flag it for human review."""
    return {
        "human_review_required": True,
        "next_action": "human_review",
        "errors": list(state.get("errors", [])),
        "audit_events": add_audit_event(
            state, "Workflow paused for human review"
        ),
    }
