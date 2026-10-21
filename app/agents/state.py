
from typing import Any, TypedDict

from app.models.nav import NAVRecord
from app.models.portfolio import PortfolioStatement
from app.models.verification import VerificationResult


class AuditEvent(TypedDict):
    event: str
    timestamp: str


class FundVoiceState(TypedDict, total=False):
    """
    Shared state passed between FundVoice AI workflow nodes.

    Fields are progressively populated as the workflow runs.
    """

    # Input
    portfolio: PortfolioStatement

    # NAV retrieval
    nav_records: list[NAVRecord]

    # Verification and valuation
    verification: VerificationResult
    valuation: dict[str, Any]

    # Report output
    report: str

    # Workflow control
    errors: list[str]
    human_review_required: bool
    retry_count: int
    next_action: str

    # Audit trail
    audit_events: list[AuditEvent]
