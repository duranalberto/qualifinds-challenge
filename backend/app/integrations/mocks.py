from app.domain.workflow import IntegrationName
from app.integrations.base import IntegrationCall, IntegrationClient, IntegrationResult


class MockHubSpotClient:
    integration = IntegrationName.hubspot

    async def call(self, call: IntegrationCall) -> IntegrationResult:
        if call.action == "get_company":
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={
                    "company_id": call.payload.get("company_id", "company_demo"),
                    "name": "Acme Corp",
                    "employee_count": 750,
                },
            )
        if call.action == "create_task":
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={"task_id": "task_demo"},
            )
        return unsupported(self.integration, call.action)


class MockSAPClient:
    integration = IntegrationName.sap

    async def call(self, call: IntegrationCall) -> IntegrationResult:
        if call.action == "enrich_company":
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={
                    "risk_score": "low",
                    "industry": "Manufacturing",
                    "region": "North America",
                },
            )
        return unsupported(self.integration, call.action)


class MockSlackClient:
    integration = IntegrationName.slack

    async def call(self, call: IntegrationCall) -> IntegrationResult:
        if call.action == "send_message":
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={
                    "channel": call.payload.get("channel", "#sales"),
                    "message_id": "msg_demo",
                },
            )
        return unsupported(self.integration, call.action)


def build_mock_registry() -> dict[IntegrationName, IntegrationClient]:
    clients: list[IntegrationClient] = [
        MockHubSpotClient(),
        MockSAPClient(),
        MockSlackClient(),
    ]
    return {client.integration: client for client in clients}


def unsupported(integration: IntegrationName, action: str) -> IntegrationResult:
    return IntegrationResult(
        integration=integration,
        action=action,
        ok=False,
        error=f"Unsupported action: {action}",
    )
