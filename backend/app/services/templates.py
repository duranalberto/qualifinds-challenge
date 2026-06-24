from app.domain.workflow import IntegrationName, RetryConfig, WorkflowStep
from app.services.planner_state import DetectedThreshold, ExtractedIntent

_RETRY = RetryConfig(max_attempts=2, delay_ms=500)


def _condition(
    threshold: DetectedThreshold | None,
    step_id: str,
    default_field: str,
    default_op: str,
    default_val: str,
) -> str:
    if threshold is not None:
        val = f'"{threshold.value}"' if isinstance(threshold.value, str) else threshold.value
        return f"{{{{steps.{step_id}.{threshold.field}}}}} {threshold.operator} {val}"
    return f"{{{{steps.{step_id}.{default_field}}}}} {default_op} {default_val}"


def _pick_integration(
    intent: ExtractedIntent | None,
    candidates: list[str],
    default: IntegrationName,
) -> IntegrationName:
    if intent is None:
        return default
    for name in candidates:
        if name in intent.integrations:
            return IntegrationName(name)
    return default


def _build_notify_step(
    intent: ExtractedIntent | None,
    *,
    step_id: str,
    name: str,
    depends_on: list[str],
    slack_channel: str,
    slack_text: str,
    gmail_to: str,
    gmail_subject: str,
    condition: str | None = None,
) -> WorkflowStep:
    """Build the final notification step, choosing Gmail or Slack based on intent."""
    if intent is not None and "gmail" in intent.integrations:
        return WorkflowStep(
            step_id=step_id,
            name=f"{name} via Gmail",
            integration=IntegrationName.gmail,
            action="send_email",
            input={"to": gmail_to, "subject": gmail_subject},
            depends_on=depends_on,
            condition=condition,
            retry=_RETRY,
        )
    slack_int = _pick_integration(intent, ["slack"], IntegrationName.slack)
    return WorkflowStep(
        step_id=step_id,
        name=name,
        integration=slack_int,
        action="send_message",
        input={"channel": slack_channel, "text": slack_text},
        depends_on=depends_on,
        condition=condition,
        retry=_RETRY,
    )


def large_lead_enrichment(intent: ExtractedIntent | None) -> list[WorkflowStep]:
    threshold = intent.threshold if intent else None
    cond = _condition(threshold, "step_get_company", "employee_count", ">", "500")
    hub = _pick_integration(intent, ["hubspot"], IntegrationName.hubspot)
    sap = _pick_integration(intent, ["sap"], IntegrationName.sap)

    return [
        WorkflowStep(
            step_id="step_get_company",
            name="Load company from HubSpot",
            integration=hub,
            action="get_company",
            input={"company_id": "{{trigger.company_id}}"},
        ),
        WorkflowStep(
            step_id="step_enrich_company",
            name="Enrich company profile",
            integration=sap,
            action="enrich_company",
            input={"company_id": "{{steps.step_get_company.company_id}}"},
            depends_on=["step_get_company"],
            condition=cond,
            retry=_RETRY,
        ),
        WorkflowStep(
            step_id="step_create_task",
            name="Create sales follow-up task",
            integration=hub,
            action="create_task",
            input={
                "company_id": "{{steps.step_get_company.company_id}}",
                "title": "Follow up with large account lead",
            },
            depends_on=["step_enrich_company"],
            condition=cond,
        ),
        _build_notify_step(
            intent,
            step_id="step_notify_sales",
            name="Notify sales team",
            depends_on=["step_create_task"],
            slack_channel="#sales",
            slack_text="Large account lead is ready for follow-up.",
            gmail_to="sales@company.com",
            gmail_subject="Large account lead ready for follow-up",
            condition=cond,
        ),
    ]


def deal_closed_processing(intent: ExtractedIntent | None) -> list[WorkflowStep]:
    sf = _pick_integration(intent, ["salesforce"], IntegrationName.salesforce)
    sap = _pick_integration(intent, ["sap"], IntegrationName.sap)
    jira = _pick_integration(intent, ["jira"], IntegrationName.jira)

    return [
        WorkflowStep(
            step_id="step_get_account",
            name="Load account from Salesforce",
            integration=sf,
            action="get_account",
            input={"account_id": "{{trigger.account_id}}"},
        ),
        WorkflowStep(
            step_id="step_check_compliance",
            name="Check SAP compliance",
            integration=sap,
            action="check_compliance",
            input={"company_id": "{{steps.step_get_account.account_id}}"},
            depends_on=["step_get_account"],
            retry=_RETRY,
        ),
        WorkflowStep(
            step_id="step_create_issue",
            name="Create Jira onboarding issue",
            integration=jira,
            action="create_issue",
            input={"project": "OPS", "type": "Task"},
            depends_on=["step_check_compliance"],
            retry=_RETRY,
        ),
        _build_notify_step(
            intent,
            step_id="step_notify_sales",
            name="Notify sales team",
            depends_on=["step_create_issue"],
            slack_channel="#sales",
            slack_text="Deal closed and compliance checked.",
            gmail_to="sales@company.com",
            gmail_subject="Deal closed — compliance verified",
        ),
    ]


def high_risk_account_alert(intent: ExtractedIntent | None) -> list[WorkflowStep]:
    hub_or_sf = _pick_integration(intent, ["hubspot", "salesforce"], IntegrationName.hubspot)
    sap = _pick_integration(intent, ["sap"], IntegrationName.sap)
    zen = _pick_integration(intent, ["zendesk"], IntegrationName.zendesk)

    threshold = intent.threshold if intent else None
    cond = _condition(threshold, "step_get_company", "employee_count", ">", "500")

    return [
        WorkflowStep(
            step_id="step_get_company",
            name="Load company profile",
            integration=hub_or_sf,
            action="get_company",
            input={"company_id": "{{trigger.company_id}}"},
        ),
        WorkflowStep(
            step_id="step_check_compliance",
            name="Check SAP compliance",
            integration=sap,
            action="check_compliance",
            input={"company_id": "{{steps.step_get_company.company_id}}"},
            depends_on=["step_get_company"],
            condition=cond,
            retry=_RETRY,
        ),
        WorkflowStep(
            step_id="step_escalate_ticket",
            name="Escalate Zendesk ticket",
            integration=zen,
            action="escalate_ticket",
            input={"ticket_id": "{{trigger.ticket_id}}"},
            depends_on=["step_check_compliance"],
            condition=cond,
            retry=_RETRY,
        ),
        _build_notify_step(
            intent,
            step_id="step_notify_sales",
            name="Notify sales manager",
            depends_on=["step_escalate_ticket"],
            slack_channel="#sales",
            slack_text="High-risk account alert triggered.",
            gmail_to="manager@company.com",
            gmail_subject="High-risk account alert",
            condition=cond,
        ),
    ]


def churn_risk_response(intent: ExtractedIntent | None) -> list[WorkflowStep]:
    zen = _pick_integration(intent, ["zendesk"], IntegrationName.zendesk)
    hub = _pick_integration(intent, ["hubspot"], IntegrationName.hubspot)
    slk = _pick_integration(intent, ["slack"], IntegrationName.slack)

    # DM step preserves send_dm action; Gmail path sends an email instead
    use_gmail = intent is not None and "gmail" in intent.integrations
    dm_step: WorkflowStep
    if use_gmail:
        dm_step = WorkflowStep(
            step_id="step_send_dm",
            name="Alert sales rep via Gmail",
            integration=IntegrationName.gmail,
            action="send_email",
            input={"to": "salesrep@company.com", "subject": "Churn risk detected — follow up required"},
            depends_on=["step_assign_ticket"],
            retry=_RETRY,
        )
    else:
        dm_step = WorkflowStep(
            step_id="step_send_dm",
            name="Send Slack DM",
            integration=slk,
            action="send_dm",
            input={"user_id": "U_SALES_REP", "message": "Churn risk detected for account."},
            depends_on=["step_assign_ticket"],
            retry=_RETRY,
        )

    return [
        WorkflowStep(
            step_id="step_get_ticket",
            name="Load Zendesk ticket",
            integration=zen,
            action="create_ticket",
            input={"ticket_id": "{{trigger.ticket_id}}"},
        ),
        WorkflowStep(
            step_id="step_get_contacts",
            name="Get HubSpot contacts",
            integration=hub,
            action="get_contacts",
            input={"company_id": "{{trigger.company_id}}"},
            depends_on=["step_get_ticket"],
        ),
        WorkflowStep(
            step_id="step_assign_ticket",
            name="Assign Zendesk ticket",
            integration=zen,
            action="assign_ticket",
            input={"ticket_id": "{{trigger.ticket_id}}", "assignee_id": "agent_01"},
            depends_on=["step_get_contacts"],
            retry=_RETRY,
        ),
        dm_step,
    ]


def enterprise_onboarding(intent: ExtractedIntent | None) -> list[WorkflowStep]:
    hub = _pick_integration(intent, ["hubspot"], IntegrationName.hubspot)
    jira = _pick_integration(intent, ["jira"], IntegrationName.jira)

    return [
        WorkflowStep(
            step_id="step_get_company",
            name="Load company from HubSpot",
            integration=hub,
            action="get_company",
            input={"company_id": "{{trigger.company_id}}"},
        ),
        WorkflowStep(
            step_id="step_create_deal",
            name="Create HubSpot deal",
            integration=hub,
            action="create_deal",
            input={"company_id": "{{steps.step_get_company.company_id}}", "value": 50000},
            depends_on=["step_get_company"],
        ),
        WorkflowStep(
            step_id="step_create_issue",
            name="Create Jira onboarding issue",
            integration=jira,
            action="create_issue",
            input={"project": "OPS", "type": "Task"},
            depends_on=["step_create_deal"],
            retry=_RETRY,
        ),
        _build_notify_step(
            intent,
            step_id="step_notify_sales",
            name="Notify sales team",
            depends_on=["step_create_issue"],
            slack_channel="#sales",
            slack_text="Enterprise onboarding initiated.",
            gmail_to="sales@company.com",
            gmail_subject="Enterprise onboarding initiated",
        ),
    ]


def invoice_payment_processing(intent: ExtractedIntent | None) -> list[WorkflowStep]:
    hub = _pick_integration(intent, ["hubspot"], IntegrationName.hubspot)
    stripe = _pick_integration(intent, ["stripe"], IntegrationName.stripe)
    slk = _pick_integration(intent, ["slack"], IntegrationName.slack)

    return [
        WorkflowStep(
            step_id="step_get_company",
            name="Load company from HubSpot",
            integration=hub,
            action="get_company",
            input={"company_id": "{{trigger.company_id}}"},
        ),
        WorkflowStep(
            step_id="step_create_invoice",
            name="Create Stripe invoice",
            integration=stripe,
            action="create_invoice",
            input={
                "customer_id": "{{steps.step_get_company.company_id}}",
                "amount": 5000,
            },
            depends_on=["step_get_company"],
            retry=_RETRY,
        ),
        WorkflowStep(
            step_id="step_charge_customer",
            name="Charge customer via Stripe",
            integration=stripe,
            action="charge_customer",
            input={
                "customer_id": "{{steps.step_get_company.company_id}}",
                "invoice_id": "{{steps.step_create_invoice.invoice_id}}",
            },
            depends_on=["step_create_invoice"],
            retry=_RETRY,
        ),
        WorkflowStep(
            step_id="step_notify_finance",
            name="Notify finance team",
            integration=slk,
            action="send_message",
            input={"channel": "#finance", "text": "Invoice created and customer charged successfully."},
            depends_on=["step_charge_customer"],
            retry=_RETRY,
        ),
    ]


def contract_renewal_automation(intent: ExtractedIntent | None) -> list[WorkflowStep]:
    sf = _pick_integration(intent, ["salesforce"], IntegrationName.salesforce)
    hub = _pick_integration(intent, ["hubspot"], IntegrationName.hubspot)
    gmail = _pick_integration(intent, ["gmail"], IntegrationName.gmail)
    slk = _pick_integration(intent, ["slack"], IntegrationName.slack)

    return [
        WorkflowStep(
            step_id="step_get_account",
            name="Load account from Salesforce",
            integration=sf,
            action="get_account",
            input={"account_id": "{{trigger.account_id}}"},
        ),
        WorkflowStep(
            step_id="step_get_contacts",
            name="Get HubSpot contacts",
            integration=hub,
            action="get_contacts",
            input={"company_id": "{{steps.step_get_account.account_id}}"},
            depends_on=["step_get_account"],
        ),
        WorkflowStep(
            step_id="step_send_renewal_email",
            name="Send renewal email via Gmail",
            integration=gmail,
            action="send_email",
            input={
                "to": "customer@example.com",
                "subject": "Your contract is expiring — let's renew",
            },
            depends_on=["step_get_contacts"],
            retry=_RETRY,
        ),
        WorkflowStep(
            step_id="step_notify_sales",
            name="Alert sales team in Slack",
            integration=slk,
            action="send_message",
            input={"channel": "#sales", "text": "Contract renewal email sent — follow up required."},
            depends_on=["step_send_renewal_email"],
            retry=_RETRY,
        ),
    ]


TEMPLATE_REGISTRY: dict[str, object] = {
    "large_lead_enrichment": large_lead_enrichment,
    "deal_closed_processing": deal_closed_processing,
    "high_risk_account_alert": high_risk_account_alert,
    "churn_risk_response": churn_risk_response,
    "enterprise_onboarding": enterprise_onboarding,
    "invoice_payment_processing": invoice_payment_processing,
    "contract_renewal_automation": contract_renewal_automation,
}
