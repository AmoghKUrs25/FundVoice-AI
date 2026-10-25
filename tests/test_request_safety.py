from app.services.request_safety import audit_request_safety
from app.storage.audit_repository import AuditRepository
from app.services.request_safety import classify_request


def test_portfolio_report_request_is_allowed():
    result = classify_request(
        "Generate my mutual fund portfolio report"
    )

    assert result["status"] == "ALLOWED"
    assert result["action"] == "PORTFOLIO_REPORTING"
    assert result["trade_executed"] is False


def test_sell_fund_request_is_rejected():
    result = classify_request("Sell this fund")

    assert result["status"] == "OUT_OF_SCOPE"
    assert "outside FundVoice AI's scope" in result["reason"]
    assert result["action"] == "NONE"
    assert result["trade_executed"] is False


def test_place_order_request_is_rejected():
    result = classify_request("Place an order to sell my fund")

    assert result["status"] == "OUT_OF_SCOPE"
    assert result["trade_executed"] is False
    assert result["action"] == "NONE"


def test_empty_request_is_rejected():
    result = classify_request("")

    assert result["status"] == "REJECTED"
    assert result["trade_executed"] is False
    assert result["action"] == "NONE"
    
def test_sell_request_is_saved_to_audit(tmp_path):
    repository = AuditRepository(tmp_path / "test_audit.db")

    result = audit_request_safety(
        "Sell this fund",
        audit_repository=repository,
    )

    events = repository.get_events(result["run_id"])

    assert result["status"] == "OUT_OF_SCOPE"
    assert result["audit_saved"] is True
    assert len(events) == 1
    assert events[0]["event_type"] == "request_safety_decision"

    details = events[0]["details"]
    assert details["status"] == "OUT_OF_SCOPE"
    assert details["action"] == "NONE"
    assert details["trade_executed"] is False
    assert "outside FundVoice AI's scope" in details["reason"]


def test_allowed_report_request_is_saved_to_audit(tmp_path):
    repository = AuditRepository(tmp_path / "test_audit.db")

    result = audit_request_safety(
        "Generate my mutual fund portfolio report",
        audit_repository=repository,
    )

    events = repository.get_events(result["run_id"])

    assert result["status"] == "ALLOWED"
    assert len(events) == 1
    assert events[0]["details"]["trade_executed"] is False

