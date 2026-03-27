"""
Layered analysis rule engine.
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


STRICTNESS_TOLERANCE = {
    "strict": 0.05,
    "medium": 0.10,
    "relaxed": 0.15,
}

ORDERED_VALUES = {
    "low": 1,
    "medium": 2,
    "high": 3,
}


class LayerDecision(BaseModel):
    key: str
    label: str
    decision: str
    reasons: List[str] = Field(default_factory=list)
    score: float = 0.0


class AnalysisRunResult(BaseModel):
    status: str
    failed_layer: str | None = None
    layer_results: List[LayerDecision] = Field(default_factory=list)
    score_breakdown: Dict[str, float] = Field(default_factory=dict)
    folded_summary_reasons: List[str] = Field(default_factory=list)


def _coerce_value(value: Any) -> Any:
    if isinstance(value, str):
        lowered = value.lower()
        if lowered in ORDERED_VALUES:
            return ORDERED_VALUES[lowered]
        if lowered.endswith("d") and lowered[:-1].isdigit():
            return int(lowered[:-1])
    return value


def _compare(actual: Any, operator: str, expected: Any) -> bool:
    actual = _coerce_value(actual)
    expected = _coerce_value(expected)
    if operator == "eq":
        return actual == expected
    if operator == "neq":
        return actual != expected
    if actual is None:
        return False
    if operator == "gte":
        return actual >= expected
    if operator == "lte":
        return actual <= expected
    if operator == "gt":
        return actual > expected
    if operator == "lt":
        return actual < expected
    raise ValueError(f"Unsupported operator: {operator}")


def _is_borderline(actual: Any, operator: str, expected: Any, strictness: str) -> bool:
    actual = _coerce_value(actual)
    expected = _coerce_value(expected)
    if actual is None or not isinstance(actual, (int, float)) or not isinstance(expected, (int, float)):
        return False
    tolerance = STRICTNESS_TOLERANCE.get(strictness, STRICTNESS_TOLERANCE["medium"])
    if operator == "gte":
        return actual >= expected * (1 - tolerance)
    if operator == "lte":
        return actual <= expected * (1 + tolerance)
    return False


def _evaluate_layer(layer: Dict[str, Any], analysis_fields: Dict[str, Any]) -> LayerDecision:
    reasons: List[str] = []
    borderline = False
    failed = False
    passed_conditions = 0
    enabled_conditions = 0

    for condition in layer.get("conditions", []):
        if not condition.get("enabled", True):
            continue
        enabled_conditions += 1
        key = condition["key"]
        operator = condition.get("operator", "eq")
        expected = condition.get("value")
        actual = analysis_fields.get(key)
        label = condition.get("label", key)
        passed = _compare(actual, operator, expected)
        if passed:
            passed_conditions += 1
            reasons.append(f"{label} passed")
            continue

        if condition.get("hard_fail"):
            failed = True
            reasons.append(f"{label} failed hard gate")
            break

        if _is_borderline(actual, operator, expected, condition.get("strictness", "medium")):
            borderline = True
            reasons.append(f"{label} is borderline")
        else:
            failed = True
            reasons.append(f"{label} failed")

    if failed:
        decision = "failed"
    elif borderline:
        decision = "borderline"
    else:
        decision = "passed"

    score = 1.0 if enabled_conditions == 0 else passed_conditions / enabled_conditions
    return LayerDecision(
        key=layer["key"],
        label=layer.get("label", layer["key"]),
        decision=decision,
        reasons=reasons,
        score=score,
    )


def run_analysis(
    *,
    activity: Dict[str, Any],
    template: Dict[str, Any],
    analysis_fields: Dict[str, Any] | None = None,
) -> AnalysisRunResult:
    analysis_fields = analysis_fields or {}
    layer_results: List[LayerDecision] = []
    summary_reasons: List[str] = []
    failed_layer: str | None = None
    watch = False

    for layer in template.get("layers", []):
        result = _evaluate_layer(layer, analysis_fields)
        layer_results.append(result)
        summary_reasons.extend(result.reasons[:1])

        if result.key == "priority":
            continue
        if result.decision == "failed":
            failed_layer = layer["key"]
            break
        if result.decision == "borderline":
            watch = True

    if failed_layer == "hard_gate":
        status = "rejected"
    elif failed_layer is not None:
        status = "watch"
    elif watch:
        status = "watch"
    else:
        status = "passed"

    return AnalysisRunResult(
        status=status,
        failed_layer=failed_layer,
        layer_results=layer_results,
        score_breakdown={layer.key: layer.score for layer in layer_results},
        folded_summary_reasons=summary_reasons[:3] or [activity.get("title", "Opportunity analyzed")],
    )
