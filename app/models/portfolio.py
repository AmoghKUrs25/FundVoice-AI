
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator


class Holding(BaseModel):
    """
    Represents one mutual fund holding in a portfolio.
    """

    holding_id: str = Field(min_length=1)
    scheme_name: str = Field(min_length=1)
    units: Decimal = Field(ge=Decimal("0"))
    plan: str | None = None
    option: str | None = None

    @field_validator("units")
    @classmethod
    def validate_units(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("Units must be a finite number.")

        return value


class PortfolioStatement(BaseModel):
    """
    Represents the user's portfolio and requested valuation date.
    """

    portfolio_id: str = Field(min_length=1)
    valuation_date: date
    holdings: list[Holding] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_holding_ids(self):
        holding_ids = [
            holding.holding_id
            for holding in self.holdings
        ]

        if len(holding_ids) != len(set(holding_ids)):
            raise ValueError("Holding IDs must be unique.")

        return self
