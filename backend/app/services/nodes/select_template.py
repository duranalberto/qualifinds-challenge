from app.services.planner_state import PlannerState


def select_template_node(state: PlannerState) -> PlannerState:
    intent = state["intent"]
    errors = list(state["validation_errors"])

    if intent is None:
        return {**state, "template_id": "large_lead_enrichment", "validation_errors": errors}

    trigger = intent.trigger_type

    warnings = list(state["validation_warnings"])

    if trigger == "new_lead":
        template_id = (
            "large_lead_enrichment" if intent.threshold is not None else "enterprise_onboarding"
        )
    elif trigger == "deal_closed":
        template_id = "deal_closed_processing"
    elif trigger == "account_updated":
        template_id = "high_risk_account_alert"
    elif trigger == "support_ticket":
        template_id = "churn_risk_response"
    elif trigger == "invoice_created":
        template_id = "invoice_payment_processing"
    elif trigger == "contract_expiring":
        template_id = "contract_renewal_automation"
    else:
        if trigger not in ("unknown",):
            warnings.append(
                f"No template for trigger_type '{trigger}'; using large_lead_enrichment fallback."
            )
        template_id = "large_lead_enrichment"

    return {**state, "template_id": template_id, "validation_errors": errors, "validation_warnings": warnings}
