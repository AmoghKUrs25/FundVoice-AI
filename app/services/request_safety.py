
import re
from typing import Any
from uuid import uuid4

from app.storage.audit_repository import AuditRepository


TRADE_PATTERNS = [
    r"\bsell\b",
    r"\bbuy\b",
    r"\bredeem\b",
    r"\bpurchase\b",
    r"\btrade\b",
    r"\bplace\s+(?:an?\s+)?order\b",
    r"\bexecute\s+(?:an?\s+)?order\b",
    r"\bsubmit\s+(?:an?\s+)?order\b",
]


def classify_request(user_request: str) -> dict[str, Any]:
    """Classify a request without performing a financial action."""
    request = (
        user_request.strip()
        if isinstance(user_request, str)
        else ""
    )

    if not request:
        return {
            "status": "REJECTED",
            "reason": "The request is empty.",
            "trade_executed": False,
            "action": "NONE",
        }

    for pattern in TRADE_PATTERNS:
        if re.search(pattern, request, flags=re.IGNORECASE):
            return {
                "status": "OUT_OF_SCOPE",
                "reason": (
                    "Trading requests are outside FundVoice AI's scope. "
                    "The system provides portfolio reporting only."
                ),
                "trade_executed": False,
                "action": "NONE",
            }

    return {
        "status": "ALLOWED",
        "reason": "The request passed the basic trade-intent safety check.",
        "trade_executed": False,
        "action": "PORTFOLIO_REPORTING",
    }


def audit_request_safety(
    user_request: str,
    audit_repository: AuditRepository | None = None,
) -> dict[str, Any]:
    """Classify a request and persist its safety decision to SQLite."""
    result = classify_request(user_request)
    run_id = str(uuid4())
    repository = audit_repository or AuditRepository()

    event = {
        "event_type": "request_safety_decision",
        "details": {
            "request": user_request,
            "status": result["status"],
            "reason": result["reason"],
            "action": result["action"],
            "trade_executed": False,
        },
    }

    repository.record_event(run_id, event)

    return {
        **result,
        "run_id": run_id,
        "audit_saved": True,
    }
