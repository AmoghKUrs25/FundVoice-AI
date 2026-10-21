
from unittest.mock import patch

from app.services.workflow_runner import run_portfolio_report


def test_runner_returns_completed_workflow_result():
    fake_result = {
        "verification": {"status": "VERIFIED"},
        "valuation": {"total_value": "1000.00"},
        "report": "Portfolio report generated.",
        "human_review_required": False,
        "errors": [],
        "audit_events": [],
    }

    with patch(
        "app.services.workflow_runner.fundvoice_graph.invoke",
        return_value=fake_result,
    ):
        result = run_portfolio_report(
            portfolio=type(
                "FakePortfolio",
                (),
                {"portfolio_id": "TEST-001"},
            )()
        )

    assert result["portfolio_id"] == "TEST-001"
    assert result["status"] == "completed"
    assert result["report"] == "Portfolio report generated."
    assert result["human_review_required"] is False


def test_runner_reports_human_review_required():
    fake_result = {
        "verification": None,
        "valuation": None,
        "report": None,
        "human_review_required": True,
        "errors": ["NAV verification failed."],
        "audit_events": [],
    }

    with patch(
        "app.services.workflow_runner.fundvoice_graph.invoke",
        return_value=fake_result,
    ):
        result = run_portfolio_report(
            portfolio=type(
                "FakePortfolio",
                (),
                {"portfolio_id": "TEST-002"},
            )()
        )

    assert result["status"] == "human_review_required"
    assert result["human_review_required"] is True
    assert "NAV verification failed." in result["errors"]
    assert result["report"] is None
