
from app.main import create_demo_state, run_workflow
from app.storage.audit_repository import AuditRepository
from decimal import Decimal

def test_run_workflow_persists_audit_events(tmp_path):
    repository = AuditRepository(tmp_path / "test_audit.db")

    execution = run_workflow(
        state=create_demo_state(),
        run_id="TEST-RUN-001",
        audit_repository=repository,
    )

    assert execution["run_id"] == "TEST-RUN-001"
    assert execution["audit_events_saved"] > 0

    saved_events = repository.get_events("TEST-RUN-001")

    assert len(saved_events) == execution["audit_events_saved"]
    assert any(
        event["event_type"] == "report_generated"
        for event in saved_events
    )


def test_run_workflow_returns_verified_result(tmp_path):
    repository = AuditRepository(tmp_path / "verified_audit.db")

    execution = run_workflow(
        state=create_demo_state(),
        run_id="TEST-RUN-002",
        audit_repository=repository,
    )

    result = execution["result"]

    assert result["verification"].status.value == "VERIFIED"
    assert result["valuation"] is not None
    assert result["report"]
    assert result["human_review_required"] is False

    
def test_run_workflow_audit_events_have_required_fields(tmp_path):
    repository = AuditRepository(tmp_path / "audit_fields.db")

    execution = run_workflow(
        state=create_demo_state(),
        run_id="TEST-RUN-003",
        audit_repository=repository,
    )

    saved_events = repository.get_events("TEST-RUN-003")

    assert saved_events

    for event in saved_events:
        assert event.get("event_type")
        assert event.get("timestamp")
        assert isinstance(event.get("details"), dict)


def test_verified_portfolio_total_matches_holding_values(tmp_path):
    repository = AuditRepository(tmp_path / "valuation_audit.db")

    execution = run_workflow(
        state=create_demo_state(),
        run_id="TEST-RUN-004",
        audit_repository=repository,
    )

    result = execution["result"]
    valuation = result["valuation"]

    assert valuation is not None
    assert result["verification"].status.value == "VERIFIED"

    holding_values = [
        Decimal(str(holding["value"]))
        for holding in valuation["holdings"]
    ]

    calculated_total = sum(holding_values, Decimal("0"))

    assert calculated_total == Decimal(str(valuation["total_value"]))
