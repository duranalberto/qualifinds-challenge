from fastapi.testclient import TestClient

from app.main import create_app


def test_workflow_plan_requires_auth() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/workflows/plan",
        json={
            "tenant_id": "tenant_acme",
            "instruction": "Notify Slack when a large HubSpot lead is enriched.",
        },
    )

    assert response.status_code == 401


def test_workflow_plan_rejects_cross_tenant_request() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/workflows/plan",
        headers={
            "Authorization": "Bearer demo-token",
            "X-Tenant-Id": "tenant_acme",
            "X-User-Id": "user_123",
        },
        json={
            "tenant_id": "tenant_other",
            "instruction": "Notify Slack when a large HubSpot lead is enriched.",
        },
    )

    assert response.status_code == 403
