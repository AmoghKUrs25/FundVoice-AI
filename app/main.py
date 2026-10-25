
import json
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from app.agents.graph import fundvoice_graph
from app.models.nav import NAVEvidence, NAVRecord
from app.models.portfolio import Holding, PortfolioStatement
from app.storage.audit_repository import AuditRepository


def run_workflow(
    state: dict[str, Any],
    run_id: str | None = None,
    audit_repository: AuditRepository | None = None,
) -> dict[str, Any]:
    """
    Execute FundVoice AI and persist its audit events in SQLite.
    """

    execution_id = run_id or str(uuid.uuid4())
    repository = audit_repository or AuditRepository()

    result = fundvoice_graph.invoke(state)

    events = result.get("audit_events", [])

    if events:
        repository.record_events(execution_id, events)

    return {
        "run_id": execution_id,
        "result": result,
        "audit_events_saved": len(events),
    }


def create_demo_state() -> dict[str, Any]:
    """Create sample data for testing the workflow locally."""

    valuation_date = date.today()

    portfolio = PortfolioStatement(
        portfolio_id="DEMO001",
        valuation_date=valuation_date,
        holdings=[
            Holding(
                holding_id="H001",
                scheme_name="Example Equity Fund",
                units=Decimal("125.500"),
            )
        ],
    )

    nav_record = NAVRecord(
        scheme_name="Example Equity Fund",
        nav_date=valuation_date,
        nav=Decimal("80.25"),
        evidence=NAVEvidence(
            evidence_id="DEMO-E001",
            source_url="https://example.com/demo-nav",
            retrieved_at=datetime.now(timezone.utc),
            evidence_text=(
                "DEMO DATA ONLY: Example Equity Fund "
                f"NAV is 80.25 for {valuation_date.isoformat()}."
            ),
        ),
    )

    return {
        "portfolio": portfolio,
        "nav_records": [nav_record],
        "errors": [],
        "audit_events": [],
        "retry_count": 0,
        "human_review_required": False,
    }


def main() -> None:
    print("Starting FundVoice AI...")

    repository = AuditRepository()
    run_id = str(uuid.uuid4())

    execution = run_workflow(
        state=create_demo_state(),
        run_id=run_id,
        audit_repository=repository,
    )

    result = execution["result"]

    print("\nWorkflow completed.")
    print(f"Run ID: {execution['run_id']}")
    print(f"Audit events saved: {execution['audit_events_saved']}")
    print(f"Portfolio ID: {result['portfolio'].portfolio_id}")

    verification = result.get("verification")
    if verification is not None:
        print(f"Verification status: {verification.status.value}")

    valuation = result.get("valuation")
    if valuation is not None:
        print(
            "Portfolio value: "
            f"{valuation['total_value']}"
        )

    print(f"Human review required: {result.get('human_review_required', False)}")

    saved_events = repository.get_events(run_id)
    print(f"Events retrieved from SQLite: {len(saved_events)}")

    print("\nAudit event types:")
    for event in saved_events:
        print(f"- {event['event_type']}")


if __name__ == "__main__":
    main()
