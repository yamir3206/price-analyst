"""HTTP request/response schemas."""

from pydantic import BaseModel, ConfigDict, Field


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=200)
    refresh: bool = False


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=200)
    refresh: bool = False


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    gemini_configured: bool
