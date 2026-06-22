from uuid import uuid4

from app.domain.workflow import (
    ExecutionRequest,
    ExecutionStatus,
    IntegrationName,
    StepExecutionResult,
    StepStatus,
    WorkflowExecution,
    WorkflowPlan,
)
from app.integrations.base import IntegrationCall, IntegrationClient


class WorkflowExecutor:
    def __init__(self, connector_registry: dict[IntegrationName, IntegrationClient]) -> None:
        self._connector_registry = connector_registry

    async def execute(self, workflow: WorkflowPlan, request: ExecutionRequest) -> WorkflowExecution:
        execution_id = f"exec_{uuid4().hex[:12]}"
        step_outputs: dict[str, dict[str, object]] = {}
        results: list[StepExecutionResult] = []

        for step in workflow.steps:
            if not should_run_step(step.condition, step_outputs):
                results.append(
                    StepExecutionResult(
                        step_id=step.step_id,
                        status=StepStatus.skipped,
                        error="Condition evaluated to false.",
                    )
                )
                continue

            client = self._connector_registry.get(step.integration)
            if client is None:
                results.append(
                    StepExecutionResult(
                        step_id=step.step_id,
                        status=StepStatus.failed,
                        error=f"Missing connector: {step.integration}",
                    )
                )
                return WorkflowExecution(
                    execution_id=execution_id,
                    workflow_id=workflow.workflow_id,
                    tenant_id=workflow.tenant_id,
                    status=ExecutionStatus.failed,
                    step_results=results,
                )

            payload = resolve_payload(step.input, request.trigger_payload, step_outputs)
            integration_result = await client.call(
                IntegrationCall(
                    tenant_id=request.tenant_id,
                    action=step.action,
                    payload=payload,
                    idempotency_key=None,
                )
            )

            if integration_result.ok:
                step_outputs[step.step_id] = integration_result.data
                results.append(
                    StepExecutionResult(
                        step_id=step.step_id,
                        status=StepStatus.succeeded,
                        output=integration_result.data,
                    )
                )
            else:
                results.append(
                    StepExecutionResult(
                        step_id=step.step_id,
                        status=StepStatus.failed,
                        error=integration_result.error,
                    )
                )
                return WorkflowExecution(
                    execution_id=execution_id,
                    workflow_id=workflow.workflow_id,
                    tenant_id=workflow.tenant_id,
                    status=ExecutionStatus.failed,
                    step_results=results,
                )

        return WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow.workflow_id,
            tenant_id=workflow.tenant_id,
            status=ExecutionStatus.succeeded,
            step_results=results,
        )


def resolve_payload(
    raw_payload: dict[str, object],
    trigger_payload: dict[str, object],
    step_outputs: dict[str, dict[str, object]],
) -> dict[str, object]:
    resolved: dict[str, object] = {}
    for key, value in raw_payload.items():
        if isinstance(value, str):
            resolved[key] = resolve_template(value, trigger_payload, step_outputs)
        else:
            resolved[key] = value
    return resolved


def resolve_template(
    value: str,
    trigger_payload: dict[str, object],
    step_outputs: dict[str, dict[str, object]],
) -> object:
    if value == "{{trigger.company_id}}":
        return trigger_payload.get("company_id", "company_demo")
    if value.startswith("{{steps.") and value.endswith("}}"):
        path = value.removeprefix("{{steps.").removesuffix("}}")
        step_id, _, field = path.partition(".")
        return step_outputs.get(step_id, {}).get(field, value)
    return value


def should_run_step(condition: str | None, step_outputs: dict[str, dict[str, object]]) -> bool:
    if condition is None:
        return True
    if condition == "{{steps.step_get_company.employee_count}} > 500":
        employee_count = step_outputs.get("step_get_company", {}).get("employee_count", 0)
        return isinstance(employee_count, int) and employee_count > 500
    return True
