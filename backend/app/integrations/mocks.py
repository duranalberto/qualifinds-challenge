from datetime import UTC, datetime

from app.domain.workflow import IntegrationName
from app.integrations.base import IntegrationCall, IntegrationClient, IntegrationResult

_COMPANY_PROFILES: dict[str, dict[str, object]] = {
    "company_demo": {
        "name": "Acme Corp", "employee_count": 750,
        "industry": "Manufacturing", "annual_revenue": 1_200_000,
    },
    "company_small": {
        "name": "Initech Ltd", "employee_count": 120,
        "industry": "Consulting", "annual_revenue": 300_000,
    },
    "company_large": {
        "name": "Globex Industries", "employee_count": 2400,
        "industry": "Technology", "annual_revenue": 4_200_000,
    },
}
_COMPANY_DEFAULT: dict[str, object] = {
    "name": "Unknown Co", "employee_count": 50, "industry": "Unknown", "annual_revenue": 0,
}


class MockHubSpotClient:
    integration = IntegrationName.hubspot

    async def call(self, call: IntegrationCall) -> IntegrationResult:
        if call.action == "get_company":
            cid = call.payload.get("company_id", "company_demo")
            profile = _COMPANY_PROFILES.get(str(cid), _COMPANY_DEFAULT)
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={"company_id": cid, **profile},
            )
        if call.action == "create_task":
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={"task_id": "task_demo"},
            )
        if call.action == "update_company_stage":
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={
                    "company_id": call.payload.get("company_id"),
                    "stage": call.payload.get("stage", "qualified"),
                    "updated": True,
                },
            )
        if call.action == "get_contacts":
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={
                    "contacts": [
                        {"id": "ct_001", "name": "Jane Smith", "email": "jane@acme.com"},
                        {"id": "ct_002", "name": "Bob Lee", "email": "bob@acme.com"},
                    ]
                },
            )
        if call.action == "create_deal":
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={
                    "deal_id": "deal_7291",
                    "company_id": call.payload.get("company_id"),
                    "value": call.payload.get("value", 50000),
                    "stage": "proposal",
                },
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
        if call.action == "get_credit_rating":
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={
                    "company_id": call.payload.get("company_id"),
                    "rating": "A",
                    "score": 87,
                    "agency": "SAP Credit",
                },
            )
        if call.action == "check_compliance":
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={
                    "company_id": call.payload.get("company_id"),
                    "status": "approved",
                    "flags": [],
                    "checked_at": datetime.now(UTC).isoformat(),
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
        if call.action == "send_dm":
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={
                    "user_id": call.payload.get("user_id"),
                    "message_id": "1718392847.000100",
                    "ok": True,
                },
            )
        if call.action == "create_channel":
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={
                    "channel_id": "C08DEMO999",
                    "name": call.payload.get("name", "workflow-alerts"),
                    "created": True,
                },
            )
        return unsupported(self.integration, call.action)


class MockSalesforceClient:
    integration = IntegrationName.salesforce

    async def call(self, call: IntegrationCall) -> IntegrationResult:
        if call.action == "get_account":
            cid = call.payload.get("account_id", "company_demo")
            profile = _COMPANY_PROFILES.get(str(cid), _COMPANY_DEFAULT)
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={
                    "account_id": cid,
                    "name": profile["name"],
                    "annual_revenue": profile["annual_revenue"],
                    "industry": profile["industry"],
                    "employee_count": profile["employee_count"],
                },
            )
        if call.action == "create_opportunity":
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={
                    "opportunity_id": "OPP-8821",
                    "account_id": call.payload.get("account_id"),
                    "stage": "Proposal",
                    "amount": call.payload.get("amount", 80000),
                },
            )
        if call.action == "update_stage":
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={
                    "opportunity_id": call.payload.get("opportunity_id"),
                    "stage": call.payload.get("stage", "Closed Won"),
                    "updated": True,
                },
            )
        return unsupported(self.integration, call.action)


class MockZendeskClient:
    integration = IntegrationName.zendesk

    async def call(self, call: IntegrationCall) -> IntegrationResult:
        if call.action == "create_ticket":
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={
                    "ticket_id": "ZD-9821",
                    "status": "open",
                    "priority": call.payload.get("priority", "normal"),
                    "subject": call.payload.get("subject", "Workflow-generated ticket"),
                },
            )
        if call.action == "escalate_ticket":
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={
                    "ticket_id": call.payload.get("ticket_id"),
                    "priority": "urgent",
                    "escalated": True,
                },
            )
        if call.action == "assign_ticket":
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={
                    "ticket_id": call.payload.get("ticket_id"),
                    "assignee_id": call.payload.get("assignee_id", "agent_01"),
                    "assigned": True,
                },
            )
        return unsupported(self.integration, call.action)


class MockJiraClient:
    integration = IntegrationName.jira

    async def call(self, call: IntegrationCall) -> IntegrationResult:
        if call.action == "create_issue":
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={
                    "issue_id": "JIRA-4421",
                    "project": call.payload.get("project", "OPS"),
                    "type": call.payload.get("type", "Task"),
                    "status": "To Do",
                },
            )
        if call.action == "update_issue":
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={
                    "issue_id": call.payload.get("issue_id"),
                    "status": call.payload.get("status", "In Progress"),
                    "updated": True,
                },
            )
        return unsupported(self.integration, call.action)


class MockStripeClient:
    integration = IntegrationName.stripe

    async def call(self, call: IntegrationCall) -> IntegrationResult:
        if call.action == "create_invoice":
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={
                    "invoice_id": "inv_demo123",
                    "customer_id": call.payload.get("customer_id"),
                    "amount": call.payload.get("amount", 5000),
                    "currency": "usd",
                    "status": "draft",
                },
            )
        if call.action == "finalize_invoice":
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={
                    "invoice_id": call.payload.get("invoice_id", "inv_demo123"),
                    "status": "open",
                    "due_date": "2026-07-24",
                },
            )
        if call.action == "charge_customer":
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={
                    "charge_id": "ch_demo456",
                    "customer_id": call.payload.get("customer_id"),
                    "amount": call.payload.get("amount", 5000),
                    "currency": "usd",
                    "status": "succeeded",
                },
            )
        return unsupported(self.integration, call.action)


class MockGmailClient:
    integration = IntegrationName.gmail

    async def call(self, call: IntegrationCall) -> IntegrationResult:
        if call.action == "send_email":
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={
                    "message_id": "msg_demo789",
                    "to": call.payload.get("to", "customer@example.com"),
                    "subject": call.payload.get("subject", "Notification from Workflow"),
                    "sent": True,
                },
            )
        if call.action == "create_draft":
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={
                    "draft_id": "draft_demo321",
                    "to": call.payload.get("to"),
                    "subject": call.payload.get("subject"),
                },
            )
        if call.action == "get_thread":
            return IntegrationResult(
                integration=self.integration,
                action=call.action,
                ok=True,
                data={
                    "thread_id": call.payload.get("thread_id"),
                    "messages": 3,
                    "last_message": datetime.now(UTC).isoformat(),
                },
            )
        return unsupported(self.integration, call.action)


def build_mock_registry() -> dict[IntegrationName, IntegrationClient]:
    clients: list[IntegrationClient] = [
        MockHubSpotClient(),
        MockSAPClient(),
        MockSlackClient(),
        MockSalesforceClient(),
        MockZendeskClient(),
        MockJiraClient(),
        MockStripeClient(),
        MockGmailClient(),
    ]
    return {client.integration: client for client in clients}


def unsupported(integration: IntegrationName, action: str) -> IntegrationResult:
    return IntegrationResult(
        integration=integration,
        action=action,
        ok=False,
        error=f"Unsupported action: {action}",
    )
