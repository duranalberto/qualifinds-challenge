from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.planner_state import DetectedThreshold, ExtractedIntent, PlannerState


def _base_state() -> PlannerState:
    return {
        "instruction": "When a new HubSpot lead has more than 500 employees, notify Slack.",
        "tenant_id": "tenant_acme",
        "intent": None,
        "template_id": None,
        "steps": [],
        "validation_errors": [],
        "validation_warnings": [],
        "workflow_name": "",
    }


@pytest.mark.asyncio
async def test_extract_intent_success() -> None:
    mock_intent = ExtractedIntent(
        trigger_type="new_lead",
        integrations=["hubspot", "slack"],
        action_intents=["notify"],
        threshold=DetectedThreshold(field="employee_count", operator=">", value=500),
        workflow_name="Large Lead Enrichment",
    )

    mock_structured = AsyncMock(return_value=mock_intent)
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = MagicMock(ainvoke=mock_structured)

    with patch("app.services.nodes.extract_intent.get_llm", return_value=mock_llm):
        from app.services.nodes.extract_intent import extract_intent_node

        result = await extract_intent_node(_base_state())

    assert result["intent"] is not None
    assert result["intent"].trigger_type == "new_lead"
    assert result["validation_errors"] == []


@pytest.mark.asyncio
async def test_extract_intent_failure_returns_none_intent() -> None:
    mock_structured = AsyncMock(side_effect=Exception("Ollama unreachable"))
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = MagicMock(ainvoke=mock_structured)

    with patch("app.services.nodes.extract_intent.get_llm", return_value=mock_llm):
        from app.services.nodes.extract_intent import extract_intent_node

        result = await extract_intent_node(_base_state())

    assert result["intent"] is None
