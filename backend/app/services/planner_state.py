from typing import Literal, TypedDict

from pydantic import BaseModel

from app.domain.workflow import WorkflowStep


class DetectedThreshold(BaseModel):
    field: str
    operator: Literal[">", "<", ">=", "<=", "==", "!="]
    value: float | str


class ExtractedIntent(BaseModel):
    trigger_type: str
    integrations: list[str]
    action_intents: list[str]
    threshold: DetectedThreshold | None
    workflow_name: str


class PlannerState(TypedDict):
    instruction: str
    tenant_id: str
    intent: ExtractedIntent | None
    template_id: str | None
    steps: list[WorkflowStep]
    validation_errors: list[str]
    validation_warnings: list[str]
    workflow_name: str
