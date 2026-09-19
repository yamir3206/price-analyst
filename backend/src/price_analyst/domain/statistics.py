"""Local deterministic statistics contracts."""

from pydantic import BaseModel, ConfigDict, Field

from price_analyst.domain.enums import Currency


class PriceStatistics(BaseModel):
    """Statistics calculated from comparable prices in one currency."""

    model_config = ConfigDict(extra="forbid")

    count: int = Field(ge=0)
    currency: Currency | None = None
    minimum: float | None = Field(default=None, ge=0)
    p10: float | None = Field(default=None, ge=0)
    p25: float | None = Field(default=None, ge=0)
    median: float | None = Field(default=None, ge=0)
    p50: float | None = Field(default=None, ge=0)
    p75: float | None = Field(default=None, ge=0)
    p90: float | None = Field(default=None, ge=0)
    mean: float | None = Field(default=None, ge=0)
    maximum: float | None = Field(default=None, ge=0)
    standard_deviation: float | None = Field(default=None, ge=0)
    price_range: float | None = Field(default=None, ge=0)
    coefficient_of_variation: float | None = Field(default=None, ge=0)
