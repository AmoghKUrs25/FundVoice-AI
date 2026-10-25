from typing import Any, TypedDict

from app.models.nav import NAVRecord
from app.models.portfolio import PortfolioStatement
from app.models.verification import VerificationResult


class FundVoiceState(TypedDict, total=False):
    """State shared by all FundVoiceAI workflow nodes."""

    portfolio: PortfolioStatement
    nav_records: list[NAVRecord]

    verification: VerificationResult | None
    valuation: dict[str, Any] | None
    report: str | None

    errors: list[str]
    audit_events: list[dict[str, Any]]

    human_review_required: bool
    retry_count: int
    next_action: str