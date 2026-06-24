from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.workflow import (
    ExecutionRequest,
    IntegrationName,
    RetryConfig,
    StepStatus,
    WorkflowPlan,
    WorkflowStep,
)
from app.integrations.base import IntegrationResult
from app.services.executor import WorkflowExecutor, resolve_template


def _plan(steps: list[WorkflowStep]) -> WorkflowPlan:
    return WorkflowPlan(
        workflow_id="wf_test",
        tenant_id="tenant_acme",
        instruction="A test instruction here.",
        name="Test Workflow",
        steps=steps,
    )


def _request() -> ExecutionRequest:
    return ExecutionRequest(
        tenant_id="tenant_acme",
        workflow_id="wf_test",
        trigger_payload={"company_id": "company_demo"},
    )


def _ok_client(data: dict) -> MagicMock:  # type: ignore[type-arg]
    client = MagicMock()
    client.integration = IntegrationName.hubspot
    client.call = AsyncMock(
        return_value=IntegrationResult(
            integration=IntegrationName.hubspot,
            action="get_company",
            ok=True,
            data=data,
        )
    )
    return client


def _fail_client() -> MagicMock:  # type: ignore[type-arg]
    client = MagicMock()
    client.integration = IntegrationName.hubspot
    client.call = AsyncMock(
        return_value=IntegrationResult(
            integration=IntegrationName.hubspot,
            action="get_company",
            ok=False,
            error="Integration error",
        )
    )
    return client


@pytest.mark.asyncio
async def test_step_timing_fields_populated() -> None:
    hub = IntegrationName.hubspot
    steps = [
        WorkflowStep(step_id="step_a", name="A", integration=hub, action="get_company"),
        WorkflowStep(step_id="step_b", name="B", integration=hub, action="get_company"),
        WorkflowStep(step_id="step_c", name="C", integration=hub, action="get_company"),
    ]
    client = _ok_client({"company_id": "c1", "employee_count": 750})
    executor = WorkflowExecutor({IntegrationName.hubspot: client})
    execution = await executor.execute(_plan(steps), _request())

    for result in execution.step_results:
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.duration_ms is not None


@pytest.mark.asyncio
async def test_execution_duration_ms_present() -> None:
    steps = [
        WorkflowStep(step_id="step_a", name="A", integration=IntegrationName.hubspot,
                     action="get_company"),
    ]
    client = _ok_client({"company_id": "c1"})
    executor = WorkflowExecutor({IntegrationName.hubspot: client})
    execution = await executor.execute(_plan(steps), _request())

    assert execution.duration_ms is not None
    assert execution.duration_ms >= 0


@pytest.mark.asyncio
async def test_started_at_before_completed_at() -> None:
    steps = [
        WorkflowStep(step_id="step_a", name="A", integration=IntegrationName.hubspot,
                     action="get_company"),
    ]
    client = _ok_client({"company_id": "c1"})
    executor = WorkflowExecutor({IntegrationName.hubspot: client})
    execution = await executor.execute(_plan(steps), _request())

    result = execution.step_results[0]
    assert result.started_at is not None
    assert result.completed_at is not None
    assert result.started_at <= result.completed_at


@pytest.mark.asyncio
async def test_retry_succeeds_after_failures() -> None:
    client = MagicMock()
    client.integration = IntegrationName.hubspot

    hub = IntegrationName.hubspot
    fail_result = IntegrationResult(integration=hub, action="get_company", ok=False, error="fail")
    ok_result = IntegrationResult(
        integration=hub, action="get_company", ok=True, data={"company_id": "c1"}
    )

    client.call = AsyncMock(side_effect=[fail_result, fail_result, ok_result])

    steps = [
        WorkflowStep(
            step_id="step_a",
            name="A",
            integration=IntegrationName.hubspot,
            action="get_company",
            retry=RetryConfig(max_attempts=3, delay_ms=0),
        )
    ]
    executor = WorkflowExecutor({IntegrationName.hubspot: client})
    execution = await executor.execute(_plan(steps), _request())
    assert execution.step_results[0].status == StepStatus.succeeded
    assert client.call.call_count == 3


@pytest.mark.asyncio
async def test_retry_fails_after_max_attempts() -> None:
    client = _fail_client()
    steps = [
        WorkflowStep(
            step_id="step_a",
            name="A",
            integration=IntegrationName.hubspot,
            action="get_company",
            retry=RetryConfig(max_attempts=2, delay_ms=0),
        )
    ]
    executor = WorkflowExecutor({IntegrationName.hubspot: client})
    execution = await executor.execute(_plan(steps), _request())
    assert execution.step_results[0].status == StepStatus.failed
    assert client.call.call_count == 2


# resolve_template tests (TICK-039)

def test_resolve_trigger_company_id() -> None:
    result = resolve_template("{{trigger.company_id}}", {"company_id": "company_demo"}, {})
    assert result == "company_demo"


def test_resolve_trigger_ticket_id() -> None:
    result = resolve_template("{{trigger.ticket_id}}", {"ticket_id": "ZD-001"}, {})
    assert result == "ZD-001"


def test_resolve_trigger_account_id() -> None:
    result = resolve_template("{{trigger.account_id}}", {"account_id": "acc_123"}, {})
    assert result == "acc_123"


def test_resolve_unknown_trigger_field_returns_raw() -> None:
    raw = "{{trigger.nonexistent_field}}"
    result = resolve_template(raw, {}, {})
    assert result == raw


def test_resolve_steps_field() -> None:
    result = resolve_template(
        "{{steps.step_get_company.company_id}}",
        {},
        {"step_get_company": {"company_id": "c_resolved"}},
    )
    assert result == "c_resolved"


def test_non_template_string_returned_as_is() -> None:
    assert resolve_template("plain string", {}, {}) == "plain string"
