import pytest
from pydantic import ValidationError

from app.services.planner_state import DetectedThreshold, ExtractedIntent, PlannerState


def test_extracted_intent_validates_all_fields() -> None:
    intent = ExtractedIntent(
        trigger_type="new_lead",
        integrations=["hubspot", "slack"],
        action_intents=["enrich", "notify"],
        threshold=DetectedThreshold(field="employee_count", operator=">", value=500),
        workflow_name="Large Lead Enrichment",
    )
    assert intent.trigger_type == "new_lead"
    assert intent.threshold is not None
    assert intent.threshold.operator == ">"


def test_detected_threshold_rejects_invalid_operator() -> None:
    with pytest.raises(ValidationError):
        DetectedThreshold(field="employee_count", operator="?", value=500)


def test_extracted_intent_no_threshold() -> None:
    intent = ExtractedIntent(
        trigger_type="deal_closed",
        integrations=[],
        action_intents=[],
        threshold=None,
        workflow_name="Deal Closed Processing",
    )
    assert intent.threshold is None


def test_planner_state_can_be_constructed_as_dict() -> None:
    state: PlannerState = {
        "instruction": "test",
        "tenant_id": "tenant_a",
        "intent": None,
        "template_id": None,
        "steps": [],
        "validation_errors": [],
        "validation_warnings": [],
        "workflow_name": "",
    }
    assert state["instruction"] == "test"
