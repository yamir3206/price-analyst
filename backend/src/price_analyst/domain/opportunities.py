"""Opportunity calculation contracts.

The calculation service is intentionally a later phase; these typed contracts
make its inputs and assumptions explicit from the beginning.
"""

from pydantic import BaseModel, ConfigDict, Field

from price_analyst.domain.money import Money


class OpportunityInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    purchase_price: Money
    expected_resale_price: Money
    shipping: Money | None = None
    platform_fee: Money | None = None
    payment_fee: Money | None = None
    other_costs: Money | None = None


class OpportunityResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency: str
    total_cost: float = Field(ge=0)
    profit: float
    profit_margin: float | None = None
    roi: float | None = None
    spread: float | None = None
    assumptions: OpportunityInputs
