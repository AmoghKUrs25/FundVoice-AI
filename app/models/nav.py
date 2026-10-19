from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class NAVEvidence(BaseModel):
    """
    Records where a NAV observation came from
    and when the evidence was collected.
    """

    evidence_id: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    retrieved_at: datetime
    evidence_text: str = Field(min_length=1)

    @field_validator("retrieved_at")
    @classmethod
    def validate_retrieved_at(cls, value: datetime) -> datetime:
        """
        Require timezone-aware evidence retrieval timestamps.
        """

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "Evidence retrieval time must include a valid timezone."
            )

        return value


class NAVRecord(BaseModel):
    """
    Represents a mutual fund NAV associated with
    a specific scheme and NAV date.
    """

    scheme_name: str = Field(min_length=1)
    nav_date: date
    nav: Decimal = Field(gt=Decimal("0"))
    evidence: NAVEvidence

    @field_validator("nav")
    @classmethod
    def validate_nav(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("NAV must be a finite number.")

        return value