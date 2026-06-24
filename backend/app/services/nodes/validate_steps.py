from app.domain.workflow import IntegrationName
from app.services.condition_evaluator import is_parseable
from app.services.planner_state import PlannerState


def validate_steps_node(state: PlannerState) -> PlannerState:
    steps = state["steps"]
    errors = list(state["validation_errors"])
    step_ids = {s.step_id for s in steps}

    for step in steps:
        if step.integration not in IntegrationName.__members__.values():
            errors.append(f"Invalid integration '{step.integration}' on step '{step.step_id}'.")

        for dep in step.depends_on:
            if dep not in step_ids:
                errors.append(
                    f"Step '{step.step_id}' depends_on unknown step '{dep}'."
                )

        if step.condition and not is_parseable(step.condition):
            errors.append(
                f"Condition '{step.condition}' on step '{step.step_id}' is not parseable."
            )

    if not _is_dag(steps):
        errors.append("Circular dependency detected in workflow steps.")

    return {**state, "validation_errors": errors}


def _is_dag(steps: list) -> bool:  # type: ignore[type-arg]
    graph: dict[str, list[str]] = {s.step_id: list(s.depends_on) for s in steps}
    visited: set[str] = set()
    in_stack: set[str] = set()

    def has_cycle(node: str) -> bool:
        visited.add(node)
        in_stack.add(node)
        for dep in graph.get(node, []):
            if dep not in visited:
                if has_cycle(dep):
                    return True
            elif dep in in_stack:
                return True
        in_stack.discard(node)
        return False

    for step_id in graph:
        if step_id not in visited:
            if has_cycle(step_id):
                return False
    return True
