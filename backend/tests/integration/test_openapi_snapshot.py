"""Keep the committed machine-readable API contract synchronized with FastAPI."""

import json
from pathlib import Path

from price_analyst.main import create_app


def test_committed_openapi_snapshot_matches_application() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    snapshot_path = repository_root / "docs" / "openapi.json"

    committed = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert committed == create_app().openapi()
