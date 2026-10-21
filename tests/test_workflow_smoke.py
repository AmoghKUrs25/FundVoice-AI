
from datetime import date, datetime, timezone
from decimal import Decimal

from app.agents.graph import fundvoice_graph
from app.models.nav import NAVRecord, NAVEvidence
from app.models.portfolio import Holding, PortfolioStatement
from app.models.verification import VerificationStatus


def test_valid_portfolio_completes_full_workflow():
    portfolio = PortfolioStatement(
        portfolio_id="smoke-test-001",
        valuation_date=date(2026, 10, 20),
        holdings=[
            Holding(
                holding_id="holding-001",
                scheme_name="Example Equity Fund",
                units=Decimal("10"),
            )
        ],
    )

    nav_record = NAVRecord(
        scheme_name="Example Equity Fund",
        nav_date=date(2026, 10, 20),
        nav=Decimal("25.50"),
        evidence=NAVEvidence(
            evidence_id="smoke-evidence-001",
            source_url="https://example.com/nav",
            retrieved_at=datetime.now(timezone.utc),
            evidence_text="Synthetic NAV evidence for testing only.",
        ),
    )

    result = fundvoice_graph.invoke(
        {
            "portfolio": portfolio,
            "nav_records": [nav_record],
            "errors": [],
            "audit_events": [],
        }
    )

    # Workflow must complete without requiring human review.
    assert result["human_review_required"] is False
    assert result["next_action"] == "complete"

    # NAV verification and valuation must be present and correct.
    assert result["verification"].status == VerificationStatus.VERIFIED
    assert result["valuation"]["total_value"] == Decimal("255.00")

    # A report must be generated with its supporting evidence.
    report = result["report"]
    assert "FundVoice AI" in report
    assert "Example Equity Fund" in report
    assert "smoke-evidence-001" in report
    assert "https://example.com/nav" in report

    # Audit trail must record the main workflow milestones.
    audit_events = [
        event["event"] for event in result["audit_events"]
    ]
    assert "Portfolio input accepted for NAV retrieval" in audit_events
    assert "NAV verification status: VERIFIED" in audit_events
    assert "Portfolio valuation calculated" in audit_events
    assert "Report generated" in audit_events

