from app.services.nodes.select_template import select_template_node
from app.services.planner_state import DetectedThreshold, ExtractedIntent, PlannerState


def _state(intent: ExtractedIntent | None) -> PlannerState:
    return {
        "instruction": "test",
        "tenant_id": "tenant_a",
        "intent": intent,
        "template_id": None,
        "steps": [],
        "validation_errors": [],
        "validation_warnings": [],
        "workflow_name": "",
    }


def _intent(trigger: str, threshold: DetectedThreshold | None = None) -> ExtractedIntent:
    return ExtractedIntent(
        trigger_type=trigger,
        integrations=[],
        action_intents=[],
        threshold=threshold,
        workflow_name="Test",
    )


def test_none_intent_defaults_to_large_lead_enrichment() -> None:
    result = select_template_node(_state(None))
    assert result["template_id"] == "large_lead_enrichment"


def test_new_lead_with_threshold_gives_large_lead_enrichment() -> None:
    threshold = DetectedThreshold(field="employee_count", operator=">", value=500)
    result = select_template_node(_state(_intent("new_lead", threshold)))
    assert result["template_id"] == "large_lead_enrichment"


def test_new_lead_without_threshold_gives_enterprise_onboarding() -> None:
    result = select_template_node(_state(_intent("new_lead")))
    assert result["template_id"] == "enterprise_onboarding"


def test_deal_closed_gives_deal_closed_processing() -> None:
    result = select_template_node(_state(_intent("deal_closed")))
    assert result["template_id"] == "deal_closed_processing"


def test_account_updated_gives_high_risk_account_alert() -> None:
    result = select_template_node(_state(_intent("account_updated")))
    assert result["template_id"] == "high_risk_account_alert"


def test_support_ticket_gives_churn_risk_response() -> None:
    result = select_template_node(_state(_intent("support_ticket")))
    assert result["template_id"] == "churn_risk_response"


def test_invoice_created_maps_to_invoice_payment_processing() -> None:
    result = select_template_node(_state(_intent("invoice_created")))
    assert result["template_id"] == "invoice_payment_processing"
    assert result["validation_warnings"] == []
    assert result["validation_errors"] == []


def test_contract_expiring_maps_to_contract_renewal_automation() -> None:
    result = select_template_node(_state(_intent("contract_expiring")))
    assert result["template_id"] == "contract_renewal_automation"
    assert result["validation_errors"] == []


def test_unknown_trigger_falls_back_to_default() -> None:
    result = select_template_node(_state(_intent("unknown")))
    assert result["template_id"] == "large_lead_enrichment"
