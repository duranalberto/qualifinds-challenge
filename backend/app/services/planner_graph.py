from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from app.domain.workflow import WorkflowCreateRequest, WorkflowPlan
from app.services.nodes.extract_intent import extract_intent_node
from app.services.nodes.fill_parameters import fill_parameters_node
from app.services.nodes.select_template import select_template_node
from app.services.nodes.validate_steps import validate_steps_node
from app.services.planner_state import PlannerState

_graph = (
    StateGraph(PlannerState)
    .add_node("extract_intent", extract_intent_node)
    .add_node("select_template", select_template_node)
    .add_node("fill_parameters", fill_parameters_node)
    .add_node("validate_steps", validate_steps_node)
    .add_edge(START, "extract_intent")
    .add_edge("extract_intent", "select_template")
    .add_edge("select_template", "fill_parameters")
    .add_edge("fill_parameters", "validate_steps")
    .add_edge("validate_steps", END)
    .compile()
)


class LangGraphPlanner:
    async def plan(self, request: WorkflowCreateRequest) -> WorkflowPlan:
        initial_state: PlannerState = {
            "instruction": request.instruction,
            "tenant_id": request.tenant_id,
            "intent": None,
            "template_id": None,
            "steps": [],
            "validation_errors": [],
            "validation_warnings": [],
            "workflow_name": "",
        }

        final_state: PlannerState = await _graph.ainvoke(initial_state)  # type: ignore[assignment]

        errors = final_state["validation_errors"]
        if errors:
            raise ValueError("; ".join(errors))

        return WorkflowPlan(
            workflow_id=f"wf_{uuid4().hex[:12]}",
            tenant_id=request.tenant_id,
            instruction=request.instruction,
            name=final_state["workflow_name"] or "Workflow",
            steps=final_state["steps"],
            assumptions=[
                "LangGraph planner uses an LLM to extract intent from the instruction.",
                "If Ollama is unreachable, a fallback template is applied.",
            ],
            risks=[
                "LLM output may not always correctly classify the trigger type.",
                "Generated steps are not authorized against tenant-specific connector policy.",
            ],
        )
