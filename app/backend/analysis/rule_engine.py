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

LOCALIZED_LABELS = {
    "hard_gate": "硬门槛",
    "trust_gate": "可信门槛",
    "roi": "回报效率",
    "trust": "可信度",
    "priority": "优先级",
    "Hard gate": "硬门槛",
    "Trust gate": "可信门槛",
    "ROI": "回报效率",
    "Trust": "可信度",
    "Priority": "优先级",
    "reward_clarity": "奖励清晰度",
    "reward_clarity_score": "奖励清晰度",
    "Reward clarity": "奖励清晰度",
    "Reward must be explicit": "奖励必须明确",
    "solo_friendliness": "单人友好度",
    "Solo only": "仅限单人",
    "Must be solo-friendly": "必须适合单人",
    "effort_level": "投入成本",
    "Estimated effort": "投入成本",
    "payout_speed": "回款速度",
    "Payout speed": "回款速度",
    "source_trust": "来源可信度",
    "Source trust": "来源可信度",
    "roi_level": "回报效率",
    "roi_score": "回报效率",
    "ROI score": "回报效率",
    "ROI level": "回报效率",
    "trust_score": "可信度",
    "Trust score": "可信度",
}

PASSED_REASON_TEMPLATES = {
    "reward_clarity": "奖励信息相对明确，可以继续评估",
    "reward_clarity_score": "奖励信息相对明确，可以继续评估",
    "solo_friendliness": "更适合单人推进，执行阻力较小",
    "effort_level": "投入成本可控，适合继续推进",
    "payout_speed": "回款节奏较快，值得优先判断",
    "source_trust": "来源可信度达标，可以继续跟进",
    "roi_level": "回报效率有优势，可以优先判断",
    "roi_score": "回报效率达到预期，可以继续推进",
    "trust_score": "可信度处于可接受范围",
}

FAILED_REASON_TEMPLATES = {
    "reward_clarity": "奖励信息不够明确，建议先不要投入",
    "reward_clarity_score": "奖励信息不够明确，建议先不要投入",
    "solo_friendliness": "更像团队型机会，当前不适合单人推进",
    "effort_level": "投入成本偏高，建议暂时不要优先处理",
    "payout_speed": "回款周期偏长，建议降低优先级",
    "source_trust": "来源可信度不足，建议先核实再决定",
    "roi_level": "回报效率偏弱，建议暂缓投入",
    "roi_score": "回报效率偏低，暂时不建议优先投入",
    "trust_score": "可信度不足，建议人工复核后再决定",
}

BORDERLINE_REASON_TEMPLATES = {
    "reward_clarity": "奖励信息接近门槛，建议人工复核",
    "reward_clarity_score": "奖励信息接近门槛，建议人工复核",
    "effort_level": "投入成本接近门槛，建议人工复核",
    "payout_speed": "回款速度接近门槛，建议人工复核",
    "source_trust": "来源可信度接近门槛，建议人工复核",
    "roi_level": "回报效率接近门槛，建议人工复核",
    "roi_score": "回报效率接近门槛，建议人工复核",
    "trust_score": "可信度接近门槛，建议人工复核",
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


class SafetyGateDecision(BaseModel):
    force_status: str | None = None
    risk_flags: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    manual_review_required: bool = False


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
    if operator == "in":
        if not isinstance(expected, (list, tuple, set)):
            return False
        coerced_expected = {_coerce_value(item) for item in expected}
        return actual in coerced_expected
    if operator == "contains":
        if actual is None:
            return False
        if isinstance(actual, (list, tuple, set)):
            return expected in actual
        return str(expected) in str(actual)
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


def _localized_label(label: str) -> str:
    return LOCALIZED_LABELS.get(label, label)


def _human_reason(*, key: str, label: str, decision: str) -> str:
    if decision == "passed":
        return PASSED_REASON_TEMPLATES.get(key, f"已满足“{_localized_label(label)}”")
    if decision == "borderline":
        return BORDERLINE_REASON_TEMPLATES.get(key, f"“{_localized_label(label)}”接近门槛，建议人工复核")
    return FAILED_REASON_TEMPLATES.get(key, f"未满足“{_localized_label(label)}”，建议暂缓处理")


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
            reasons.append(_human_reason(key=key, label=label, decision="passed"))
            continue

        if condition.get("hard_fail"):
            failed = True
            reasons.append(_human_reason(key=key, label=label, decision="failed"))
            break

        if _is_borderline(actual, operator, expected, condition.get("strictness", "medium")):
            borderline = True
            reasons.append(_human_reason(key=key, label=label, decision="borderline"))
        else:
            failed = True
            reasons.append(_human_reason(key=key, label=label, decision="failed"))

    if failed:
        decision = "failed"
    elif borderline:
        decision = "borderline"
    else:
        decision = "passed"

    score = 1.0 if enabled_conditions == 0 else passed_conditions / enabled_conditions
    return LayerDecision(
        key=layer["key"],
        label=_localized_label(layer.get("label", layer["key"])),
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


def derive_safety_gate_decision(
    *,
    structured: Dict[str, Any],
    source_health: Dict[str, Any] | None = None,
) -> SafetyGateDecision:
    source_health = source_health or {}
    reward_clarity = str(structured.get("reward_clarity") or "low")
    solo_fit = str(structured.get("solo_fit") or structured.get("solo_friendliness") or "unclear")
    source_credibility = str(structured.get("source_credibility") or structured.get("source_trust") or "low")
    reward_estimate_present = bool(structured.get("reward_estimate_present"))
    freshness_level = str(source_health.get("freshness_level") or "never")

    risk_flags: List[str] = []
    reasons: List[str] = []
    force_status: str | None = None
    manual_review_required = False

    if solo_fit == "team_required":
        force_status = "reject"
        risk_flags.append("team_required")
        reasons.append("Team-only restrictions violate solo-fit requirements.")

    if source_credibility == "low" and freshness_level in {"critical", "never"}:
        force_status = "reject"
        risk_flags.append("obvious_trust_failure")
        reasons.append("Source credibility and freshness indicate obvious trust failure.")

    if reward_clarity == "low" and not reward_estimate_present and force_status is None:
        force_status = "watch"
        risk_flags.append("explicit_no_reward_signal")
        reasons.append("Reward evidence is too weak for autonomous approval.")

    if source_credibility != "high" or freshness_level in {"stale", "critical", "never"}:
        manual_review_required = True

    return SafetyGateDecision(
        force_status=force_status,
        risk_flags=risk_flags,
        reasons=reasons,
        manual_review_required=manual_review_required,
    )
