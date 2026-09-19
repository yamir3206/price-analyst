"""Shared test configuration."""

import pytest

from price_analyst.infrastructure.config import Settings


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        environment="test",
        cors_origins=["*"],
        gemini_api_key=None,
    )
