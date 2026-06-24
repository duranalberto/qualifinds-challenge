import logging
import re

logger = logging.getLogger(__name__)

_PATTERN = re.compile(
    r"^\{\{steps\.(?P<step_id>[^.]+)\.(?P<field>[^}]+)\}\}\s*(?P<operator>[><!]=?|==)\s*(?P<value>.+)$"
)

_OPS = {
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def evaluate(condition: str, step_outputs: dict[str, dict[str, object]]) -> bool:
    match = _PATTERN.match(condition.strip())
    if not match:
        logger.warning("Unparseable condition '%s'; failing open", condition)
        return True

    step_id = match.group("step_id")
    field = match.group("field")
    operator = match.group("operator")
    raw_value = match.group("value").strip().strip('"').strip("'")

    if step_id not in step_outputs:
        logger.warning("Step '%s' not in step_outputs; failing open", step_id)
        return True

    resolved = step_outputs[step_id].get(field)
    if resolved is None:
        logger.warning("Field '%s' not in step '%s' outputs; failing open", field, step_id)
        return True

    try:
        if isinstance(resolved, (int, float)):
            cast_value: object = type(resolved)(raw_value)
        else:
            cast_value = raw_value
    except (ValueError, TypeError):
        cast_value = raw_value

    op_fn = _OPS.get(operator)
    if op_fn is None:
        logger.warning("Unknown operator '%s'; failing open", operator)
        return True

    try:
        return bool(op_fn(resolved, cast_value))
    except TypeError:
        logger.warning(
            "Type error comparing '%s' %s '%s'; failing open", resolved, operator, cast_value
        )
        return True


def is_parseable(condition: str) -> bool:
    return bool(_PATTERN.match(condition.strip()))
