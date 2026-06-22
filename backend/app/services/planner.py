from typing import Protocol
from uuid import uuid4

from app.domain.workflow import IntegrationName, WorkflowCreateRequest, WorkflowPlan, WorkflowStep


class WorkflowPlanner(Protocol):
    async def plan(self, request: WorkflowCreateRequest) -> WorkflowPlan:
        """Turn a natural-language instruction into a validated workflow plan."""


class RuleBasedPlanner:
    async def plan(self, request: WorkflowCreateRequest) -> WorkflowPlan:
        text = request.instruction.lower()
        steps: list[WorkflowStep] = [
            WorkflowStep(
                step_id="step_get_company",
                name="Load company from HubSpot",
                integration=IntegrationName.hubspot,
                action="get_company",
                input={"company_id": "{{trigger.company_id}}"},
            )
        ]

        if "sap" in text or "enrich" in text:
            steps.append(
                WorkflowStep(
                    step_id="step_enrich_company",
                    name="Enrich company profile",
                    integration=IntegrationName.sap,
                    action="enrich_company",
                    input={"company_id": "{{steps.step_get_company.company_id}}"},
                    depends_on=["step_get_company"],
                    condition="{{steps.step_get_company.employee_count}} > 500",
                )
            )

        if "task" in text or "follow-up" in text or "follow up" in text:
            steps.append(
                WorkflowStep(
                    step_id="step_create_task",
                    name="Create sales follow-up task",
                    integration=IntegrationName.hubspot,
                    action="create_task",
                    input={
                        "company_id": "{{steps.step_get_company.company_id}}",
                        "title": "Follow up with large account lead",
                    },
                    depends_on=["step_get_company"],
                    condition="{{steps.step_get_company.employee_count}} > 500",
                )
            )

        if "slack" in text or "notify" in text:
            steps.append(
                WorkflowStep(
                    step_id="step_notify_sales",
                    name="Notify sales team",
                    integration=IntegrationName.slack,
                    action="send_message",
                    input={
                        "channel": "#sales",
                        "text": "Large account lead is ready for follow-up.",
                    },
                    depends_on=[steps[-1].step_id],
                    condition="{{steps.step_get_company.employee_count}} > 500",
                )
            )

        return WorkflowPlan(
            workflow_id=f"wf_{uuid4().hex[:12]}",
            tenant_id=request.tenant_id,
            instruction=request.instruction,
            steps=steps,
            assumptions=[
                "Prototype planner uses keyword matching instead of an LLM.",
                "Company size threshold is hard-coded when large-account intent is detected.",
            ],
            risks=[
                "No robust workflow validation is performed before execution.",
                "Generated steps are not authorized against tenant-specific connector policy.",
            ],
        )
