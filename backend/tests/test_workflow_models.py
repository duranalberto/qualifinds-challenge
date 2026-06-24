import pytest
from pydantic import ValidationError

from app.domain.workflow import (
    IntegrationName,
    RetryConfig,
    StepExecutionResult,
    WorkflowExecution,
    WorkflowPlan,
)


def test_workflow_plan_model_accepts_structured_steps() -> None:
    plan = WorkflowPlan.model_validate(
        {
            "workflow_id": "wf_demo",
            "tenant_id": "tenant_acme",
            "name": "Demo Workflow",
            "instruction": "Notify sales when a large HubSpot lead is enriched.",
            "steps": [
                {
                    "step_id": "step_get_company",
                    "name": "Load company from HubSpot",
                    "integration": "hubspot",
                    "action": "get_company",
                    "input": {"company_id": "{{trigger.company_id}}"},
                },
                {
                    "step_id": "step_enrich_company",
                    "name": "Enrich company in SAP",
                    "integration": "sap",
                    "action": "enrich_company",
                    "input": {"company_id": "{{steps.step_get_company.company_id}}"},
                    "depends_on": ["step_get_company"],
                    "condition": "{{steps.step_get_company.employee_count}} > 500",
                },
                {
                    "step_id": "step_notify_sales",
                    "name": "Notify sales in Slack",
                    "integration": "slack",
                    "action": "send_message",
                    "input": {
                        "channel": "#sales",
                        "text": "Large account lead is ready for follow-up.",
                    },
                    "depends_on": ["step_enrich_company"],
                },
            ],
        }
    )

    assert plan.steps[0].integration == IntegrationName.hubspot
    assert plan.steps[1].depends_on == ["step_get_company"]
    assert plan.steps[2].action == "send_message"
    assert plan.name == "Demo Workflow"


def test_workflow_plan_requires_name() -> None:
    with pytest.raises(ValidationError):
        WorkflowPlan.model_validate(
            {
                "workflow_id": "wf_demo",
                "tenant_id": "tenant_acme",
                "name": "",
                "instruction": "Notify sales when a large HubSpot lead is enriched.",
                "steps": [
                    {
                        "step_id": "step_get_company",
                        "name": "Load company from HubSpot",
                        "integration": "hubspot",
                        "action": "get_company",
                        "input": {},
                    }
                ],
            }
        )


def test_step_execution_result_timing_fields() -> None:
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    result = StepExecutionResult(
        step_id="step_test",
        status="succeeded",
        started_at=now,
        completed_at=now,
        duration_ms=42,
    )
    assert result.duration_ms == 42
    assert result.started_at is not None
    data = result.model_dump()
    assert data["duration_ms"] == 42


def test_step_execution_result_none_timing_fields() -> None:
    result = StepExecutionResult(step_id="step_test", status="pending")
    assert result.started_at is None
    assert result.completed_at is None
    assert result.duration_ms is None


def test_retry_config_validates_max_attempts() -> None:
    with pytest.raises(ValidationError):
        RetryConfig(max_attempts=0)


def test_retry_config_valid() -> None:
    rc = RetryConfig(max_attempts=2, delay_ms=500)
    assert rc.max_attempts == 2
    assert rc.delay_ms == 500


def test_step_without_retry_serializes_cleanly() -> None:
    from app.domain.workflow import WorkflowStep

    step = WorkflowStep(
        step_id="s1",
        name="Step One",
        integration=IntegrationName.hubspot,
        action="get_company",
    )
    data = step.model_dump(exclude_none=True)
    assert "retry" not in data


def test_workflow_execution_timing_fields() -> None:
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    execution = WorkflowExecution(
        execution_id="exec_001",
        workflow_id="wf_001",
        tenant_id="tenant_acme",
        status="succeeded",
        started_at=now,
        duration_ms=150,
    )
    assert execution.duration_ms == 150
    assert execution.started_at is not None


def test_workflow_execution_defaults_no_timing() -> None:
    execution = WorkflowExecution(
        execution_id="exec_002",
        workflow_id="wf_001",
        tenant_id="tenant_acme",
        status="queued",
    )
    assert execution.duration_ms is None
    assert execution.started_at is None


def test_all_integration_names_valid() -> None:
    valid = {"hubspot", "sap", "slack", "salesforce", "zendesk", "jira", "stripe", "gmail"}
    assert {m.value for m in IntegrationName} == valid
