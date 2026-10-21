
from datetime import date, datetime, timezone
from decimal import Decimal

from app.agents.graph import fundvoice_graph
from app.models.nav import NAVRecord, NAVEvidence
from app.models.portfolio import Holding, PortfolioStatement
from app.models.verification import VerificationStatus
from unittest.mock import patch
from app.agents.nodes import generate_report_node
from app.agents.state import FundVoiceState
from types import SimpleNamespace

def make_portfolio():
    return PortfolioStatement(
        portfolio_id="portfolio-001",
        valuation_date=date(2026, 10, 20),
        holdings=[
            Holding(
                holding_id="holding-001",
                scheme_name="Example Equity Fund",
                units=Decimal("10"),
            )
        ],
    )


def make_nav(nav_date=date(2026, 10, 20)):
    return NAVRecord(
        scheme_name="Example Equity Fund",
        nav_date=nav_date,
        nav=Decimal("25.50"),
        evidence=NAVEvidence(
            evidence_id="evidence-001",
            source_url="https://example.com/nav",
            retrieved_at=datetime.now(timezone.utc),
            evidence_text="Example NAV evidence for testing only.",
        ),
    )


def test_missing_portfolio_goes_to_human_review():
    result = fundvoice_graph.invoke({})

    assert result["human_review_required"] is True
    assert result["next_action"] == "human_review"
    assert result.get("report") is None
    assert any(
        event["event"] == "Workflow paused for human review"
        for event in result.get("audit_events", [])
    )

def test_portfolio_without_nav_goes_to_human_review():
    result = fundvoice_graph.invoke({
        "portfolio": make_portfolio(),
        "nav_records": [],
    })

    assert result["human_review_required"] is True
    assert result["next_action"] == "human_review"
    assert result.get("report") is None


def test_nav_date_mismatch_goes_to_human_review():
    result = fundvoice_graph.invoke({
        "portfolio": make_portfolio(),
        "nav_records": [make_nav(date(2026, 10, 19))],
    })

    assert result["verification"].status == VerificationStatus.REVIEW_REQUIRED
    assert result["human_review_required"] is True
    assert result["next_action"] == "human_review"
    assert result.get("report") is None


def test_matching_nav_passes_verification():
    result = fundvoice_graph.invoke({
        "portfolio": make_portfolio(),
        "nav_records": [make_nav()],
    })

    assert result["verification"].status == VerificationStatus.VERIFIED
    assert result["human_review_required"] is False
    assert result["next_action"] == "complete"
    assert result.get("report")
    assert "FundVoice AI" in result["report"]
    assert "Example Equity Fund" in result["report"]
    assert "255.00" in result["report"]
    assert "evidence-001" in result["report"]
    assert "https://example.com/nav" in result["report"]
    assert any(
        event["event"] == "Report generated"
        for event in result.get("audit_events", [])
    )
    audit_events = [
        event["event"]
        for event in result.get("audit_events", [])
    ]

    assert "Portfolio input accepted for NAV retrieval" in audit_events
    assert "NAV records supplied for verification" in audit_events
    assert "NAV verification status: VERIFIED" in audit_events
    assert "Portfolio valuation calculated" in audit_events
    assert "Report generated" in audit_events
    assert "₹25.50" in result["report"]
    assert "₹255.00" in result["report"]


def test_valuation_failure_goes_to_human_review():
    with patch(
        "app.services.portfolio_valuation.value_portfolio",
        side_effect=ValueError("Simulated valuation failure"),
    ):
        result = fundvoice_graph.invoke({
            "portfolio": make_portfolio(),
            "nav_records": [make_nav()],
        })

    assert result["human_review_required"] is True
    assert result["next_action"] == "human_review"
    assert result.get("report") is None
    assert any(
        "Valuation failed" in error
        for error in result.get("errors", [])
    )


def test_verification_exception_goes_to_human_review():
    with patch(
        "app.verification.engine.verify_portfolio",
        side_effect=RuntimeError("Simulated verification failure"),
    ):
        result = fundvoice_graph.invoke({
            "portfolio": make_portfolio(),
            "nav_records": [make_nav()],
        })

    assert result["human_review_required"] is True
    assert result["next_action"] == "human_review"
    assert result.get("report") is None
    assert any(
        "Verification could not complete" in error
        for error in result.get("errors", [])
    )


def test_retrieval_node_uses_amfi_fetcher_when_nav_missing():
    from app.services.nav_retriever import AMFI_NAV_URL

    csv_text = (
        "100001;INF000000001;INF000000001;"
        "Example Equity Fund;25.50;20-Oct-2026\n"
    )

    with patch(
        "app.services.nav_retriever.fetch_nav_history_sync",
        return_value=csv_text,
    ) as mock_fetch:
        result = fundvoice_graph.invoke({
            "portfolio": make_portfolio(),
            "nav_records": [],
        })

    mock_fetch.assert_called_once_with(
        date(2026, 10, 20),
        date(2026, 10, 20),
    )
    assert result["verification"].status == VerificationStatus.VERIFIED
    assert result["human_review_required"] is False
    assert result.get("report")
    assert "255.00" in result["report"]
    assert any(
        record.evidence.source_url == AMFI_NAV_URL
        for record in result["nav_records"]
    )


def test_retrieval_failure_goes_to_human_review():
    from app.services.nav_retriever import NAVRetrievalError

    with patch(
        "app.services.nav_retriever.fetch_nav_history_sync",
        side_effect=NAVRetrievalError("Simulated AMFI outage"),
    ):
        result = fundvoice_graph.invoke({
            "portfolio": make_portfolio(),
            "nav_records": [],
        })

    assert result["human_review_required"] is True
    assert result["next_action"] == "human_review"
    assert result.get("report") is None
    assert any(
        "NAV retrieval failed" in error
        for error in result.get("errors", [])
    )
    assert any(
        event["event"]
        == "NAV retrieval failed; human review required"
        for event in result.get("audit_events", [])
    )
    


def test_multiple_holdings_retrieve_correct_navs():
    portfolio = PortfolioStatement(
        portfolio_id="portfolio-multiple",
        valuation_date=date(2026, 10, 20),
        holdings=[
            Holding(
                holding_id="holding-001",
                scheme_name="Example Equity Fund",
                units=Decimal("10"),
            ),
            Holding(
                holding_id="holding-002",
                scheme_name="Example Debt Fund",
                units=Decimal("20"),
            ),
        ],
    )

    csv_text = (
        "100001;INF000000001;INF000000001;"
        "Example Equity Fund;25.50;20-Oct-2026\n"
        "100002;INF000000002;INF000000002;"
        "Example Debt Fund;10.25;20-Oct-2026\n"
    )

    with patch(
        "app.services.nav_retriever.fetch_nav_history_sync",
        return_value=csv_text,
    ):
        result = fundvoice_graph.invoke({
            "portfolio": portfolio,
            "nav_records": [],
        })

    assert result["human_review_required"] is False
    assert len(result["nav_records"]) == 2
    assert result["valuation"]["total_value"] == Decimal("460.00")
    assert result.get("report")


def test_missing_nav_for_one_holding_requires_review():
    portfolio = PortfolioStatement(
        portfolio_id="portfolio-missing-nav",
        valuation_date=date(2026, 10, 20),
        holdings=[
            Holding(
                holding_id="holding-001",
                scheme_name="Example Equity Fund",
                units=Decimal("10"),
            ),
            Holding(
                holding_id="holding-002",
                scheme_name="Example Debt Fund",
                units=Decimal("20"),
            ),
        ],
    )

    csv_text = (
        "100001;INF000000001;INF000000001;"
        "Example Equity Fund;25.50;20-Oct-2026\n"
    )

    with patch(
        "app.services.nav_retriever.fetch_nav_history_sync",
        return_value=csv_text,
    ):
        result = fundvoice_graph.invoke({
            "portfolio": portfolio,
            "nav_records": [],
        })

    assert result["human_review_required"] is True
    assert result["next_action"] == "human_review"
    assert result.get("report") is None
    assert any(
        "NAV retrieval failed" in error
        or "NAV_DATE_MISMATCH" in error
        or "NAV_NOT_FOUND" in error
        for error in result.get("errors", [])
    )

def test_report_generation_blocked_without_verification():
    state: FundVoiceState = {
        "valuation": {
            "portfolio_id": "portfolio-001",
            "valuation_date": date(2026, 10, 20),
            "holdings": [],
            "total_value": Decimal("0.00"),
        },
        "errors": [],
    }

    result = generate_report_node(state)

    assert "report" not in result
    assert result["human_review_required"] is True
    assert result["next_action"] == "human_review"
    assert any(
        "verification did not pass" in error.lower()
        for error in result["errors"]
    )


def test_report_generation_blocked_when_verification_failed():
    state: FundVoiceState = {
        "verification": SimpleNamespace(status="REVIEW_REQUIRED"),
        "valuation": {
            "portfolio_id": "portfolio-001",
            "valuation_date": date(2026, 10, 20),
            "holdings": [],
            "total_value": Decimal("0.00"),
        },
        "errors": [],
    }

    result = generate_report_node(state)

    assert "report" not in result
    assert result["human_review_required"] is True
    assert result["next_action"] == "human_review"


def test_workflow_returns_structured_valuation_and_evidence():
    result = fundvoice_graph.invoke(
        {
            "portfolio": make_portfolio(),
            "nav_records": [make_nav()],
            "errors": [],
            "audit_events": [],
        }
    )

    assert result["human_review_required"] is False
    assert result["next_action"] == "complete"

    valuation = result["valuation"]

    assert valuation["portfolio_id"] == "portfolio-001"
    assert valuation["valuation_date"] == date(2026, 10, 20)
    assert valuation["total_value"] == Decimal("255.00")

    holding = valuation["holdings"][0]

    assert holding["holding_id"] == "holding-001"
    assert holding["nav"] == Decimal("25.50")
    assert holding["nav_date"] == date(2026, 10, 20)
    assert holding["evidence_id"] == "evidence-001"
    assert holding["source_url"] == "https://example.com/nav"
