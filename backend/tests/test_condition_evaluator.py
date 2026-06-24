from app.services.condition_evaluator import evaluate


def _outputs(step_id: str, **fields: object) -> dict[str, dict[str, object]]:
    return {step_id: dict(fields)}


def test_employee_count_greater_than_passes() -> None:
    assert evaluate(
        "{{steps.step_get_company.employee_count}} > 500",
        _outputs("step_get_company", employee_count=750),
    )


def test_employee_count_greater_than_fails() -> None:
    assert not evaluate(
        "{{steps.step_get_company.employee_count}} > 500",
        _outputs("step_get_company", employee_count=200),
    )


def test_string_equality_passes() -> None:
    assert evaluate(
        '{{steps.step_enrich_company.risk_score}} == "high"',
        _outputs("step_enrich_company", risk_score="high"),
    )


def test_string_equality_fails() -> None:
    assert not evaluate(
        '{{steps.step_enrich_company.risk_score}} == "high"',
        _outputs("step_enrich_company", risk_score="low"),
    )


def test_missing_step_fails_open() -> None:
    assert evaluate(
        "{{steps.step_missing.employee_count}} > 500",
        {},
    )


def test_unparseable_condition_fails_open() -> None:
    assert evaluate("this is not a valid condition", {})


def test_less_than_operator() -> None:
    assert evaluate(
        "{{steps.step_a.score}} < 100",
        _outputs("step_a", score=50),
    )
    assert not evaluate(
        "{{steps.step_a.score}} < 100",
        _outputs("step_a", score=200),
    )


def test_not_equal_operator() -> None:
    assert evaluate(
        "{{steps.step_a.status}} != approved",
        _outputs("step_a", status="rejected"),
    )
    assert not evaluate(
        "{{steps.step_a.status}} != approved",
        _outputs("step_a", status="approved"),
    )
