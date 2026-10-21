
from typing import Any, TypedDict

from app.models.nav import NAVRecord
from app.models.portfolio import PortfolioStatement
from app.models.verification import VerificationResult


class AuditEvent(TypedDict):
    event: str
    timestamp: str


class FundVoiceState(TypedDict, total=False):
    """
    Shared state and output contract for the FundVoice AI workflow.

    Successful workflow:
        report: generated portfolio report
        human_review_required: False
        next_action: "complete"

    Human-review workflow:
        human_review_required: True
        next_action: "human_review"

    Callers should handle fields that may be absent.
    """

    portfolio: PortfolioStatement
    nav_records: list[NAVRecord]
    verification: VerificationResult
    valuation: dict[str, Any]
    report: str

    errors: list[str]
    human_review_required: bool
    retry_count: int
    next_action: str

    audit_events: list[AuditEvent]
