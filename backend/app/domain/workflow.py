from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class IntegrationName(StrEnum):
    hubspot = "hubspot"
    sap = "sap"
    slack = "slack"
    salesforce = "salesforce"
    zendesk = "zendesk"
    jira = "jira"
    stripe = "stripe"
    gmail = "gmail"


class ExecutionStatus(StrEnum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class StepStatus(StrEnum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    skipped = "skipped"


class RetryConfig(BaseModel):
    max_attempts: int = Field(default=2, ge=1)
    delay_ms: int = Field(default=500, ge=0)


class WorkflowCreateRequest(BaseModel):
    tenant_id: str = Field(min_length=1)
    instruction: str = Field(min_length=10, max_length=5_000)


class WorkflowStep(BaseModel):
    step_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    integration: IntegrationName
    action: str = Field(min_length=1)
    input: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    condition: str | None = None
    retry: RetryConfig | None = None


class WorkflowPlan(BaseModel):
    workflow_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    instruction: str = Field(min_length=10)
    name: str = Field(min_length=1)
    steps: list[WorkflowStep] = Field(min_length=1)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class ExecutionRequest(BaseModel):
    tenant_id: str = Field(min_length=1)
    workflow_id: str = Field(min_length=1)
    trigger_payload: dict[str, Any] = Field(default_factory=dict)


class StepExecutionResult(BaseModel):
    step_id: str = Field(min_length=1)
    status: StepStatus
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None


class WorkflowExecution(BaseModel):
    execution_id: str = Field(min_length=1)
    workflow_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    status: ExecutionStatus
    step_results: list[StepExecutionResult] = Field(default_factory=list)
    started_at: datetime | None = None
    duration_ms: int | None = None
