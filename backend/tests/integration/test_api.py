from fastapi.testclient import TestClient

from price_analyst.infrastructure.config import Settings
from price_analyst.main import create_app


def test_health_endpoint_reports_configuration() -> None:
    app = create_app(
        Settings(environment="test", cors_origins=["*"], torob_enabled=False)
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] == "test"
    assert body["gemini_configured"] is False


def test_search_endpoint_returns_truthful_phase_one_snapshot() -> None:
    app = create_app(
        Settings(environment="test", cors_origins=["*"], torob_enabled=False)
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/searches",
            json={"query": "Samsung S24 Ultra 256 GB"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["query"]["brand"] == "samsung"
    assert body["query"]["capacity"] == "256GB"
    assert body["offers"] == []
    assert body["statistics"] is None
    assert body["local_analysis"]["matches"] == []
    assert body["collection_status"] == "no_sources_configured"
    assert {status["source"] for status in body["source_statuses"]} == {
        "torob",
        "basalam",
        "digikala",
        "divar",
    }


def test_search_request_rejects_unknown_fields() -> None:
    app = create_app(
        Settings(environment="test", cors_origins=["*"], torob_enabled=False)
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/searches",
            json={"query": "laptop", "raw_html": "must not be accepted"},
        )

    assert response.status_code == 422


def test_analysis_is_explicit_and_disabled_without_a_server_key() -> None:
    app = create_app(
        Settings(environment="test", cors_origins=["*"], torob_enabled=False)
    )

    with TestClient(app) as client:
        normal = client.post("/api/v1/searches", json={"query": "laptop"})
        analyzed = client.post("/api/v1/searches/analysis", json={"query": "laptop"})

    assert normal.status_code == 200
    assert normal.json()["ai_analysis"]["status"] == "not_requested"
    assert analyzed.status_code == 200
    assert analyzed.json()["ai_analysis"]["status"] == "disabled"
    assert analyzed.json()["offers"] == []
