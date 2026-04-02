from fastapi.testclient import TestClient

from app.main import create_app


DOCUMENTED_HTTP_ROUTES = {
    "/api/v1/health",
    "/api/v1/alerts",
    "/api/v1/alerts/{alert_id}/ack",
    "/api/v1/jobs",
    "/api/v1/jobs/{job_id}",
    "/api/v1/jobs/{job_id}/events",
    "/api/v1/portfolio/snapshot",
    "/api/v1/graph/topology",
    "/api/v1/models/deployments",
    "/api/v1/models/deployments/{deployment_id}/activate",
    "/api/v1/models/deployments/{deployment_id}/deactivate",
    "/api/v1/strategies/instances",
    "/api/v1/strategies/instances/{instance_id}/start",
    "/api/v1/strategies/instances/{instance_id}/stop",
    "/api/v1/risk/overrides",
    "/api/v1/risk/decisions/recent",
}


def test_documented_http_routes_exist_in_openapi() -> None:
    app = create_app()
    with TestClient(app):
        openapi = app.openapi()
    actual_paths = set(openapi.get("paths", {}).keys())

    assert DOCUMENTED_HTTP_ROUTES <= actual_paths
