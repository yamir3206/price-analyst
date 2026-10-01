"""Deterministic opportunity calculation contracts."""

from pydantic import BaseModel, ConfigDict, Field

from price_analyst.domain.enums import Currency, PriceClassification
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

    offer_id: str | None = Field(default=None, min_length=1)
    currency: Currency
    total_cost: float = Field(ge=0)
    profit: float
    profit_margin: float | None = None
    roi: float | None = None
    spread: float | None = None
    classification: PriceClassification = PriceClassification.BELOW_MARKET
    assumptions: OpportunityInputs
