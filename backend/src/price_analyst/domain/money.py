"""Money values with explicit currency and integer source units."""

from pydantic import BaseModel, ConfigDict, Field

from price_analyst.domain.enums import Currency


class Money(BaseModel):
    """An exact monetary value.

    ``amount`` is stored as an integer in the source currency's smallest
    meaningful unit. Conversion between IRR and IRT is deliberately outside
    this model and must be explicit when it is ever introduced.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    amount: int = Field(ge=0)
    currency: Currency
