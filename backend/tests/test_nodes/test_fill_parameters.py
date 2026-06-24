from app.services.nodes.fill_parameters import fill_parameters_node
from app.services.planner_state import ExtractedIntent, PlannerState


def _state(template_id: str, intent: ExtractedIntent | None = None) -> PlannerState:
    return {
        "instruction": "test instruction",
        "tenant_id": "tenant_a",
        "intent": intent,
        "template_id": template_id,
        "steps": [],
        "validation_errors": [],
        "validation_warnings": [],
        "workflow_name": "",
    }


def _intent(trigger: str, name: str) -> ExtractedIntent:
    return ExtractedIntent(
        trigger_type=trigger,
        integrations=[],
        action_intents=[],
        threshold=None,
        workflow_name=name,
    )


def test_fill_parameters_populates_steps_for_large_lead_enrichment() -> None:
    result = fill_parameters_node(_state("large_lead_enrichment"))
    assert len(result["steps"]) > 0


def test_fill_parameters_sets_workflow_name_from_intent() -> None:
    intent = _intent("new_lead", "My Custom Workflow")
    result = fill_parameters_node(_state("large_lead_enrichment", intent))
    assert result["workflow_name"] == "My Custom Workflow"


def test_fill_parameters_generates_name_when_intent_missing() -> None:
    result = fill_parameters_node(_state("large_lead_enrichment", None))
    assert len(result["workflow_name"]) > 0


def test_fill_parameters_works_with_none_intent() -> None:
    result = fill_parameters_node(_state("large_lead_enrichment", None))
    assert len(result["steps"]) > 0


def test_fill_parameters_each_template_produces_steps() -> None:
    templates = [
        "large_lead_enrichment",
        "deal_closed_processing",
        "high_risk_account_alert",
        "churn_risk_response",
        "enterprise_onboarding",
    ]
    for tid in templates:
        result = fill_parameters_node(_state(tid))
        assert len(result["steps"]) > 0, f"Template {tid} produced no steps"
