from enum import Enum

from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    FAILED = "FAILED"


class VerificationIssue(BaseModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    holding_id: str | None = None


class VerificationResult(BaseModel):
    portfolio_id: str
    status: VerificationStatus
    checks_passed: list[str] = Field(default_factory=list)
    issues: list[VerificationIssue] = Field(default_factory=list)