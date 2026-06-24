from app.domain.workflow import IntegrationName
from app.services.planner_state import DetectedThreshold, ExtractedIntent
from app.services.templates import (
    churn_risk_response,
    deal_closed_processing,
    enterprise_onboarding,
    high_risk_account_alert,
    large_lead_enrichment,
)


def _intent(
    trigger: str = "new_lead",
    integrations: list[str] | None = None,
    threshold: DetectedThreshold | None = None,
) -> ExtractedIntent:
    return ExtractedIntent(
        trigger_type=trigger,
        integrations=integrations or [],
        action_intents=[],
        threshold=threshold,
        workflow_name="Test",
    )


def _all_deps_valid(steps: list) -> bool:  # type: ignore[type-arg]
    ids = {s.step_id for s in steps}
    for step in steps:
        for dep in step.depends_on:
            if dep not in ids:
                return False
    return True


def test_large_lead_enrichment_step_count() -> None:
    steps = large_lead_enrichment(_intent())
    assert len(steps) == 4
    assert _all_deps_valid(steps)


def test_large_lead_enrichment_step_ids() -> None:
    steps = large_lead_enrichment(_intent())
    ids = [s.step_id for s in steps]
    assert ids == [
        "step_get_company", "step_enrich_company", "step_create_task", "step_notify_sales"
    ]


def test_deal_closed_processing_step_count() -> None:
    steps = deal_closed_processing(_intent("deal_closed"))
    assert len(steps) == 4
    assert _all_deps_valid(steps)


def test_high_risk_account_alert_step_count() -> None:
    steps = high_risk_account_alert(_intent("account_updated"))
    assert len(steps) == 4
    assert _all_deps_valid(steps)


def test_churn_risk_response_step_count() -> None:
    steps = churn_risk_response(_intent("support_ticket"))
    assert len(steps) == 4
    assert _all_deps_valid(steps)


def test_enterprise_onboarding_step_count() -> None:
    steps = enterprise_onboarding(_intent("new_lead"))
    assert len(steps) == 4
    assert _all_deps_valid(steps)


def test_threshold_injected_into_condition_string() -> None:
    threshold = DetectedThreshold(field="annual_revenue", operator=">=", value=1000000)
    steps = large_lead_enrichment(_intent(threshold=threshold))
    cond_steps = [s for s in steps if s.condition]
    assert len(cond_steps) > 0
    assert "annual_revenue" in cond_steps[0].condition  # type: ignore[operator]
    assert ">=" in cond_steps[0].condition  # type: ignore[operator]


def test_default_condition_used_when_no_threshold() -> None:
    steps = large_lead_enrichment(_intent())
    cond_steps = [s for s in steps if s.condition]
    assert len(cond_steps) > 0
    assert "employee_count" in cond_steps[0].condition  # type: ignore[operator]
    assert "500" in cond_steps[0].condition  # type: ignore[operator]


def test_all_steps_have_valid_integrations() -> None:
    all_fns = [
        large_lead_enrichment, deal_closed_processing, high_risk_account_alert,
        churn_risk_response, enterprise_onboarding,
    ]
    for fn in all_fns:
        steps = fn(None)
        for step in steps:
            assert step.integration in IntegrationName.__members__.values()
