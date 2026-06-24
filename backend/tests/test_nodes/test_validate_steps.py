from app.domain.workflow import IntegrationName, WorkflowStep
from app.services.nodes.validate_steps import validate_steps_node
from app.services.planner_state import PlannerState


def _state(steps: list[WorkflowStep]) -> PlannerState:
    return {
        "instruction": "test",
        "tenant_id": "tenant_a",
        "intent": None,
        "template_id": "large_lead_enrichment",
        "steps": steps,
        "validation_errors": [],
        "validation_warnings": [],
        "workflow_name": "Test",
    }


def _step(
    step_id: str,
    depends_on: list[str] | None = None,
    condition: str | None = None,
    integration: IntegrationName = IntegrationName.hubspot,
) -> WorkflowStep:
    return WorkflowStep(
        step_id=step_id,
        name=f"Step {step_id}",
        integration=integration,
        action="get_company",
        depends_on=depends_on or [],
        condition=condition,
    )


def test_valid_steps_produce_no_errors() -> None:
    steps = [
        _step("step_a"),
        _step("step_b", depends_on=["step_a"]),
    ]
    result = validate_steps_node(_state(steps))
    assert result["validation_errors"] == []


def test_invalid_depends_on_reference_produces_error() -> None:
    steps = [_step("step_a", depends_on=["step_nonexistent"])]
    result = validate_steps_node(_state(steps))
    assert any("step_nonexistent" in e for e in result["validation_errors"])


def test_self_referencing_depends_on_produces_error() -> None:
    steps = [_step("step_a", depends_on=["step_a"])]
    result = validate_steps_node(_state(steps))
    assert len(result["validation_errors"]) > 0


def test_circular_dependency_produces_error() -> None:
    s1 = WorkflowStep(
        step_id="step_a", name="A", integration=IntegrationName.hubspot,
        action="x", depends_on=["step_b"],
    )
    s2 = WorkflowStep(
        step_id="step_b", name="B", integration=IntegrationName.hubspot,
        action="x", depends_on=["step_a"],
    )
    result = validate_steps_node(_state([s1, s2]))
    assert any("ircular" in e for e in result["validation_errors"])
