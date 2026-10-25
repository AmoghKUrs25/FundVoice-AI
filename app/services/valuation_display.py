
from app.models.verification import VerificationStatus


def can_display_verified_valuation(
    valuation,
    verification_status,
    human_review_required: bool,
) -> bool:
    """Return whether a portfolio valuation can be displayed as verified."""

    status_value = getattr(
        verification_status,
        "value",
        verification_status,
    )

    return (
        valuation is not None
        and status_value == VerificationStatus.VERIFIED.value
        and not human_review_required
    )
