from fastapi.testclient import TestClient

from app.main import create_app


AUTH_HEADERS = {
    "Authorization": "Bearer demo-token",
    "X-Tenant-Id": "tenant_acme",
    "X-User-Id": "user_123",
}


def test_prototype_can_plan_and_execute_workflow() -> None:
    client = TestClient(create_app())

    plan_response = client.post(
        "/workflows/plan",
        headers=AUTH_HEADERS,
        json={
            "tenant_id": "tenant_acme",
            "instruction": (
                "When a new HubSpot lead has more than 500 employees, "
                "enrich the company profile, create a follow-up task, and notify Slack."
            ),
        },
    )

    assert plan_response.status_code == 200
    workflow = plan_response.json()
    assert workflow["workflow_id"].startswith("wf_")
    assert len(workflow["steps"]) >= 3

    execute_response = client.post(
        f"/workflows/{workflow['workflow_id']}/execute",
        headers=AUTH_HEADERS,
        json={
            "tenant_id": "tenant_acme",
            "workflow_id": workflow["workflow_id"],
            "trigger_payload": {"company_id": "company_demo"},
        },
    )

    assert execute_response.status_code == 200
    execution = execute_response.json()
    assert execution["status"] == "succeeded"
    assert execution["workflow_id"] == workflow["workflow_id"]
