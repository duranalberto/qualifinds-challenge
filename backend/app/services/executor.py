import asyncio
import logging
from datetime import UTC, datetime
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
from app.services.condition_evaluator import evaluate as eval_condition

logger = logging.getLogger(__name__)


class WorkflowExecutor:
    def __init__(self, connector_registry: dict[IntegrationName, IntegrationClient]) -> None:
        self._connector_registry = connector_registry

    async def execute(self, workflow: WorkflowPlan, request: ExecutionRequest) -> WorkflowExecution:
        execution_id = f"exec_{uuid4().hex[:12]}"
        exec_started = datetime.now(UTC)
        step_outputs: dict[str, dict[str, object]] = {}
        results: list[StepExecutionResult] = []

        for step in workflow.steps:
            if step.condition and not eval_condition(step.condition, step_outputs):
                now = datetime.now(UTC)
                results.append(
                    StepExecutionResult(
                        step_id=step.step_id,
                        status=StepStatus.skipped,
                        error="Condition evaluated to false.",
                        started_at=now,
                        completed_at=now,
                        duration_ms=0,
                    )
                )
                continue

            client = self._connector_registry.get(step.integration)
            if client is None:
                now = datetime.now(UTC)
                results.append(
                    StepExecutionResult(
                        step_id=step.step_id,
                        status=StepStatus.failed,
                        error=f"Missing connector: {step.integration}",
                        started_at=now,
                        completed_at=now,
                        duration_ms=0,
                    )
                )
                exec_duration = int((datetime.now(UTC) - exec_started).total_seconds() * 1000)
                return WorkflowExecution(
                    execution_id=execution_id,
                    workflow_id=workflow.workflow_id,
                    tenant_id=workflow.tenant_id,
                    status=ExecutionStatus.failed,
                    step_results=results,
                    started_at=exec_started,
                    duration_ms=exec_duration,
                )

            payload = resolve_payload(step.input, request.trigger_payload, step_outputs)
            max_attempts = step.retry.max_attempts if step.retry else 1
            delay_ms = step.retry.delay_ms if step.retry else 0

            step_started = datetime.now(UTC)
            integration_result = None
            for attempt in range(max_attempts):
                if attempt > 0 and delay_ms > 0:
                    await asyncio.sleep(delay_ms / 1000)
                integration_result = await client.call(
                    IntegrationCall(
                        tenant_id=request.tenant_id,
                        action=step.action,
                        payload=payload,
                        idempotency_key=None,
                    )
                )
                if integration_result.ok:
                    break

            step_completed = datetime.now(UTC)
            step_duration = int((step_completed - step_started).total_seconds() * 1000)

            if integration_result is None:
                raise RuntimeError("integration_result is None after retry loop")
            if integration_result.ok:
                step_outputs[step.step_id] = integration_result.data
                results.append(
                    StepExecutionResult(
                        step_id=step.step_id,
                        status=StepStatus.succeeded,
                        output=integration_result.data,
                        started_at=step_started,
                        completed_at=step_completed,
                        duration_ms=step_duration,
                    )
                )
            else:
                results.append(
                    StepExecutionResult(
                        step_id=step.step_id,
                        status=StepStatus.failed,
                        error=integration_result.error,
                        started_at=step_started,
                        completed_at=step_completed,
                        duration_ms=step_duration,
                    )
                )
                exec_duration = int((datetime.now(UTC) - exec_started).total_seconds() * 1000)
                return WorkflowExecution(
                    execution_id=execution_id,
                    workflow_id=workflow.workflow_id,
                    tenant_id=workflow.tenant_id,
                    status=ExecutionStatus.failed,
                    step_results=results,
                    started_at=exec_started,
                    duration_ms=exec_duration,
                )

        exec_duration = int((datetime.now(UTC) - exec_started).total_seconds() * 1000)
        return WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow.workflow_id,
            tenant_id=workflow.tenant_id,
            status=ExecutionStatus.succeeded,
            step_results=results,
            started_at=exec_started,
            duration_ms=exec_duration,
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
    if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
        inner = value[2:-2].strip()
        if inner.startswith("trigger."):
            field = inner.removeprefix("trigger.")
            return trigger_payload.get(field, value)
        if inner.startswith("steps."):
            path = inner.removeprefix("steps.")
            step_id, _, field = path.partition(".")
            return step_outputs.get(step_id, {}).get(field, value)
    return value
