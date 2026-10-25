
from app.models.verification import VerificationStatus
from app.services.valuation_display import (
    can_display_verified_valuation,
)


def test_verified_valuation_can_be_displayed():
    assert can_display_verified_valuation(
        valuation={"total_value": "1000.00"},
        verification_status=VerificationStatus.VERIFIED,
        human_review_required=False,
    ) is True


def test_missing_valuation_cannot_be_displayed():
    assert can_display_verified_valuation(
        valuation=None,
        verification_status=VerificationStatus.VERIFIED,
        human_review_required=False,
    ) is False


def test_review_required_blocks_verified_valuation():
    assert can_display_verified_valuation(
        valuation={"total_value": "1000.00"},
        verification_status=VerificationStatus.VERIFIED,
        human_review_required=True,
    ) is False


def test_unverified_status_blocks_valuation():
    assert can_display_verified_valuation(
        valuation={"total_value": "1000.00"},
        verification_status=VerificationStatus.REVIEW_REQUIRED,
        human_review_required=False,
    ) is False


def test_missing_verification_status_blocks_valuation():
    assert can_display_verified_valuation(
        valuation={"total_value": "1000.00"},
        verification_status=None,
        human_review_required=False,
    ) is False
