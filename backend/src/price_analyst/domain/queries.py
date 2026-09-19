"""Normalized search query contracts."""

from pydantic import BaseModel, ConfigDict, Field


class NormalizedQuery(BaseModel):
    """A deterministic representation of the user's search intent."""

    model_config = ConfigDict(extra="forbid")

    original: str = Field(min_length=1)
    normalized_text: str = Field(min_length=1)
    brand: str | None = None
    model: str | None = None
    capacity: str | None = None
    color: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)
    variants: list[str] = Field(default_factory=list, max_length=5)
