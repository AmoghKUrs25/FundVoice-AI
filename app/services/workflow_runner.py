
"""Public entry point for running the FundVoice AI workflow."""

from app.agents.graph import fundvoice_graph
from app.models.portfolio import PortfolioStatement


def run_portfolio_report(portfolio: PortfolioStatement) -> dict:
    """Run the existing workflow for a validated portfolio."""
    result = fundvoice_graph.invoke({"portfolio": portfolio})

    verification = result.get("verification")
    verification_status = None

    if verification is not None:
        status = getattr(verification, "status", None)
        verification_status = getattr(status, "value", status)

    return {
        "portfolio_id": portfolio.portfolio_id,
        "status": (
            "human_review_required"
            if result.get("human_review_required", False)
            else "completed"
        ),
        "report": result.get("report"),
        "valuation": result.get("valuation"),
        "verification_status": verification_status,
        "human_review_required": result.get("human_review_required", False),
        "errors": result.get("errors", []),
        "audit_events": result.get("audit_events", []),
    }
