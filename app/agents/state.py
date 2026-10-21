
from typing import Any, TypedDict


class FundVoiceState(TypedDict, total=False):
    """
    Shared state passed between FundVoice AI workflow nodes.

    Each node reads the information it needs and returns updates.
    total=False allows fields to be added as the workflow progresses.
    """

    # User's portfolio input
    portfolio: Any

    # NAV records retrieved from a data source
    nav_records: list[Any]

    # Verification result and calculated portfolio valuation
    verification: Any
    valuation: Any

    # Human-readable report
    report: str

    # Workflow control
    errors: list[str]
    human_review_required: bool
    retry_count: int
    next_action: str

    # Audit trail of workflow decisions
    audit_events: list[dict[str, Any]]
