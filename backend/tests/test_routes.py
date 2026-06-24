from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.planner_state import DetectedThreshold, ExtractedIntent

AUTH_HEADERS = {
    "Authorization": "Bearer demo-token",
    "X-Tenant-Id": "tenant_acme",
    "X-User-Id": "user_123",
}

AUTH_HEADERS_B = {
    "Authorization": "Bearer demo-token",
    "X-Tenant-Id": "tenant_b",
    "X-User-Id": "user_456",
}


def _make_client() -> TestClient:
    return TestClient(create_app())


def _intent() -> ExtractedIntent:
    return ExtractedIntent(
        trigger_type="new_lead",
        integrations=["hubspot", "slack"],
        action_intents=["notify"],
        threshold=DetectedThreshold(field="employee_count", operator=">", value=500),
        workflow_name="Large Lead Enrichment",
    )


_DEFAULT_INSTR = "When a new HubSpot lead has more than 500 employees, notify Slack."


def _plan_with_mocked_llm(  # type: ignore[return]
    http_client: TestClient,
    instruction: str = _DEFAULT_INSTR,
) -> dict:  # type: ignore[type-arg]
    with patch("app.services.nodes.extract_intent.get_llm") as mock_get_llm:
        mock_structured = AsyncMock(return_value=_intent())
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = MagicMock(ainvoke=mock_structured)
        mock_get_llm.return_value = mock_llm

        response = http_client.post(
            "/workflows/plan",
            headers=AUTH_HEADERS,
            json={"tenant_id": "tenant_acme", "instruction": instruction},
        )
    assert response.status_code == 200
    return response.json()  # type: ignore[no-any-return]


def test_list_workflows_returns_saved_workflows() -> None:
    http_client = _make_client()
    for i in range(3):
        instruction = f"When a new lead has more than 500 employees, notify Slack. Case {i}."
        _plan_with_mocked_llm(http_client, instruction)

    response = http_client.get("/workflows", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


def test_list_workflows_cross_tenant_sees_only_own_workflows() -> None:
    http_client = _make_client()
    _plan_with_mocked_llm(http_client)  # saved for tenant_acme

    # tenant_b can list their own workflows (0 items), cannot see tenant_acme's
    response = http_client.get("/workflows", headers=AUTH_HEADERS_B)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_workflows_requires_auth() -> None:
    http_client = _make_client()
    response = http_client.get("/workflows")
    assert response.status_code == 401


def test_list_executions_returns_saved_executions() -> None:
    http_client = _make_client()
    workflow = _plan_with_mocked_llm(http_client)

    for _ in range(2):
        exec_response = http_client.post(
            f"/workflows/{workflow['workflow_id']}/execute",
            headers=AUTH_HEADERS,
            json={
                "tenant_id": "tenant_acme",
                "workflow_id": workflow["workflow_id"],
                "trigger_payload": {"company_id": "company_demo"},
            },
        )
        assert exec_response.status_code == 200

    response = http_client.get("/executions", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


def test_list_executions_requires_auth() -> None:
    http_client = _make_client()
    response = http_client.get("/executions")
    assert response.status_code == 401
