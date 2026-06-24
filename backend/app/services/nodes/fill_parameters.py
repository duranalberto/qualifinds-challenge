
from app.domain.workflow import WorkflowStep
from app.services.planner_state import PlannerState
from app.services.templates import TEMPLATE_REGISTRY


def fill_parameters_node(state: PlannerState) -> PlannerState:
    intent = state["intent"]
    template_id = state["template_id"] or "large_lead_enrichment"

    template_fn = TEMPLATE_REGISTRY.get(template_id)
    if template_fn is None:
        template_fn = TEMPLATE_REGISTRY["large_lead_enrichment"]

    steps: list[WorkflowStep] = (template_fn)(intent)  # type: ignore[operator]

    if intent and intent.workflow_name:
        workflow_name = intent.workflow_name
    elif intent:
        workflow_name = intent.trigger_type.replace("_", " ").title() + " Workflow"
    else:
        workflow_name = "Workflow"

    return {**state, "steps": steps, "workflow_name": workflow_name}
