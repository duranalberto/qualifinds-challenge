from unittest.mock import AsyncMock, patch

import pytest

from app.domain.workflow import WorkflowCreateRequest
from app.services.planner_state import DetectedThreshold, ExtractedIntent, PlannerState

_DEFAULT_INSTRUCTION = "When a new HubSpot lead has more than 500 employees, notify Slack."


def _request(instruction: str = _DEFAULT_INSTRUCTION) -> WorkflowCreateRequest:
    return WorkflowCreateRequest(tenant_id="tenant_acme", instruction=instruction)


def _intent() -> ExtractedIntent:
    return ExtractedIntent(
        trigger_type="new_lead",
        integrations=["hubspot", "slack"],
        action_intents=["notify"],
        threshold=DetectedThreshold(field="employee_count", operator=">", value=500),
        workflow_name="Large Lead Enrichment",
    )


@pytest.mark.asyncio
async def test_planner_graph_with_valid_intent() -> None:
    async def mock_extract(state: PlannerState) -> PlannerState:
        return {**state, "intent": _intent()}

    with patch("app.services.planner_graph._graph") as mock_graph:
        mock_graph.ainvoke = AsyncMock(return_value={
            "instruction": "test",
            "tenant_id": "tenant_acme",
            "intent": _intent(),
            "template_id": "large_lead_enrichment",
            "steps": [],
            "validation_errors": [],
            "validation_warnings": [],
            "workflow_name": "Large Lead Enrichment",
        })
        from app.services.planner_graph import LangGraphPlanner
        from app.services.templates import large_lead_enrichment

        steps = large_lead_enrichment(_intent())
        mock_graph.ainvoke = AsyncMock(return_value={
            "instruction": "test",
            "tenant_id": "tenant_acme",
            "intent": _intent(),
            "template_id": "large_lead_enrichment",
            "steps": steps,
            "validation_errors": [],
            "validation_warnings": [],
            "workflow_name": "Large Lead Enrichment",
        })

        planner = LangGraphPlanner()
        plan = await planner.plan(_request())

    assert plan.workflow_id.startswith("wf_")
    assert plan.name == "Large Lead Enrichment"
    assert len(plan.steps) == 4


@pytest.mark.asyncio
async def test_planner_graph_with_none_intent_uses_fallback() -> None:
    from app.services.templates import large_lead_enrichment

    fallback_steps = large_lead_enrichment(None)

    with patch("app.services.planner_graph._graph") as mock_graph:
        mock_graph.ainvoke = AsyncMock(return_value={
            "instruction": "test",
            "tenant_id": "tenant_acme",
            "intent": None,
            "template_id": "large_lead_enrichment",
            "steps": fallback_steps,
            "validation_errors": [],
            "validation_warnings": [],
            "workflow_name": "Workflow",
        })

        from app.services.planner_graph import LangGraphPlanner

        planner = LangGraphPlanner()
        plan = await planner.plan(_request())

    assert len(plan.steps) > 0
    assert plan.workflow_id.startswith("wf_")


@pytest.mark.asyncio
async def test_planner_end_to_end_with_mocked_llm() -> None:
    async def mock_extract(state: PlannerState) -> PlannerState:
        return {**state, "intent": _intent()}

    with patch("app.services.nodes.extract_intent.get_llm") as mock_get_llm:
        from unittest.mock import MagicMock
        mock_structured = AsyncMock(return_value=_intent())
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = MagicMock(ainvoke=mock_structured)
        mock_get_llm.return_value = mock_llm

        from app.services.planner_graph import LangGraphPlanner

        planner = LangGraphPlanner()
        plan = await planner.plan(_request())

    assert plan.workflow_id.startswith("wf_")
    assert len(plan.steps) == 4
