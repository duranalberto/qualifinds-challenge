from app.domain.workflow import IntegrationName, WorkflowPlan


def test_workflow_plan_model_accepts_structured_steps() -> None:
    plan = WorkflowPlan.model_validate(
        {
            "workflow_id": "wf_demo",
            "tenant_id": "tenant_acme",
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
