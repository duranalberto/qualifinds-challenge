import pytest

from app.integrations.base import IntegrationCall
from app.integrations.mocks import (
    MockHubSpotClient,
    MockJiraClient,
    MockSalesforceClient,
    MockSAPClient,
    MockSlackClient,
    MockZendeskClient,
)

TENANT = "tenant_acme"


def _call(action: str, **payload: object) -> IntegrationCall:
    return IntegrationCall(tenant_id=TENANT, action=action, payload=dict(payload))


# HubSpot new actions

@pytest.mark.asyncio
async def test_hubspot_update_company_stage() -> None:
    client = MockHubSpotClient()
    result = await client.call(_call("update_company_stage", company_id="c1", stage="qualified"))
    assert result.ok
    assert result.data["stage"] == "qualified"
    assert result.data["updated"] is True


@pytest.mark.asyncio
async def test_hubspot_get_contacts() -> None:
    client = MockHubSpotClient()
    result = await client.call(_call("get_contacts", company_id="c1"))
    assert result.ok
    assert "contacts" in result.data
    assert len(result.data["contacts"]) == 2


@pytest.mark.asyncio
async def test_hubspot_create_deal() -> None:
    client = MockHubSpotClient()
    result = await client.call(_call("create_deal", company_id="c1", value=75000))
    assert result.ok
    assert result.data["deal_id"] == "deal_7291"
    assert result.data["value"] == 75000


# SAP new actions

@pytest.mark.asyncio
async def test_sap_get_credit_rating() -> None:
    client = MockSAPClient()
    result = await client.call(_call("get_credit_rating", company_id="c1"))
    assert result.ok
    assert result.data["rating"] == "A"
    assert "score" in result.data


@pytest.mark.asyncio
async def test_sap_check_compliance() -> None:
    client = MockSAPClient()
    result = await client.call(_call("check_compliance", company_id="c1"))
    assert result.ok
    assert result.data["status"] == "approved"
    assert "checked_at" in result.data


# Slack new actions

@pytest.mark.asyncio
async def test_slack_send_dm() -> None:
    client = MockSlackClient()
    result = await client.call(_call("send_dm", user_id="U123"))
    assert result.ok
    assert result.data["user_id"] == "U123"
    assert "message_id" in result.data


@pytest.mark.asyncio
async def test_slack_create_channel() -> None:
    client = MockSlackClient()
    result = await client.call(_call("create_channel", name="my-channel"))
    assert result.ok
    assert result.data["name"] == "my-channel"
    assert result.data["created"] is True


# Salesforce

@pytest.mark.asyncio
async def test_salesforce_get_account() -> None:
    client = MockSalesforceClient()
    result = await client.call(_call("get_account", account_id="company_demo"))
    assert result.ok
    assert result.data["employee_count"] == 750


@pytest.mark.asyncio
async def test_salesforce_create_opportunity() -> None:
    client = MockSalesforceClient()
    result = await client.call(_call("create_opportunity", account_id="acc1", amount=90000))
    assert result.ok
    assert result.data["opportunity_id"] == "OPP-8821"
    assert result.data["amount"] == 90000


@pytest.mark.asyncio
async def test_salesforce_update_stage() -> None:
    client = MockSalesforceClient()
    result = await client.call(_call("update_stage", opportunity_id="OPP-1", stage="Closed Won"))
    assert result.ok
    assert result.data["updated"] is True


# Zendesk

@pytest.mark.asyncio
async def test_zendesk_create_ticket() -> None:
    client = MockZendeskClient()
    result = await client.call(_call("create_ticket", priority="high"))
    assert result.ok
    assert result.data["ticket_id"] == "ZD-9821"
    assert result.data["priority"] == "high"


@pytest.mark.asyncio
async def test_zendesk_escalate_ticket() -> None:
    client = MockZendeskClient()
    result = await client.call(_call("escalate_ticket", ticket_id="ZD-001"))
    assert result.ok
    assert result.data["priority"] == "urgent"
    assert result.data["escalated"] is True


@pytest.mark.asyncio
async def test_zendesk_assign_ticket() -> None:
    client = MockZendeskClient()
    result = await client.call(_call("assign_ticket", ticket_id="ZD-001", assignee_id="agent_02"))
    assert result.ok
    assert result.data["assignee_id"] == "agent_02"
    assert result.data["assigned"] is True


# Jira

@pytest.mark.asyncio
async def test_jira_create_issue() -> None:
    client = MockJiraClient()
    result = await client.call(_call("create_issue", project="ENG", type="Bug"))
    assert result.ok
    assert result.data["issue_id"] == "JIRA-4421"
    assert result.data["project"] == "ENG"


@pytest.mark.asyncio
async def test_jira_update_issue() -> None:
    client = MockJiraClient()
    result = await client.call(_call("update_issue", issue_id="JIRA-4421", status="Done"))
    assert result.ok
    assert result.data["status"] == "Done"
    assert result.data["updated"] is True


# Company profile variations

@pytest.mark.asyncio
async def test_company_demo_returns_750_employees() -> None:
    client = MockHubSpotClient()
    result = await client.call(_call("get_company", company_id="company_demo"))
    assert result.ok
    assert result.data["employee_count"] == 750


@pytest.mark.asyncio
async def test_company_small_returns_120_employees() -> None:
    client = MockHubSpotClient()
    result = await client.call(_call("get_company", company_id="company_small"))
    assert result.ok
    assert result.data["employee_count"] == 120


@pytest.mark.asyncio
async def test_company_large_returns_2400_employees() -> None:
    client = MockHubSpotClient()
    result = await client.call(_call("get_company", company_id="company_large"))
    assert result.ok
    assert result.data["employee_count"] == 2400


@pytest.mark.asyncio
async def test_unknown_company_returns_50_employees() -> None:
    client = MockHubSpotClient()
    result = await client.call(_call("get_company", company_id="company_xyz_unknown"))
    assert result.ok
    assert result.data["employee_count"] == 50
