"""Structured evaluation helpers for reward-opportunity evidence bundles."""

from __future__ import annotations

from typing import Any


def _join_text(parts: list[str]) -> str:
    return " ".join(part.strip() for part in parts if part and part.strip())


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _infer_reward_type(text: str) -> str:
    if _contains_any(text, ("$", "cash", "usd", "奖金", "现金", "返现", "礼金")):
        return "cash"
    if _contains_any(text, ("coupon", "voucher", "券", "优惠券")):
        return "coupon"
    if _contains_any(text, ("points", "积分", "credits")):
        return "points"
    if _contains_any(text, ("airdrop", "token", "代币")):
        return "token"
    return "unknown"


def _infer_opportunity_type(text: str) -> str:
    if _contains_any(text, ("invite", "refer", "referral", "邀请", "拉新")):
        return "invite_reward"
    if _contains_any(text, ("register", "signup", "sign up", "注册", "开户", "新用户")):
        return "registration_reward"
    if _contains_any(text, ("task", "quest", "complete", "submit", "mission", "任务", "投稿", "测试", "试玩", "打卡")):
        return "task_reward"
    return "general_reward"


def evaluate_evidence_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    reward_snippets = list(bundle.get("reward_snippets") or [])
    action_snippets = list(bundle.get("action_snippets") or [])
    time_snippets = list(bundle.get("time_snippets") or [])
    rule_snippets = list(bundle.get("rule_snippets") or [])
    eligibility_snippets = list(bundle.get("eligibility_snippets") or [])
    external_links = list(bundle.get("external_links") or [])

    combined_text = _join_text(
        reward_snippets
        + action_snippets
        + time_snippets
        + rule_snippets
        + eligibility_snippets
        + [str(bundle.get("title") or ""), str(bundle.get("raw_text_excerpt") or "")]
    ).lower()

    has_reward = bool(reward_snippets)
    has_action = bool(action_snippets)
    has_time = bool(time_snippets)
    has_rules = bool(rule_snippets)
    has_eligibility = bool(eligibility_snippets)

    missing_evidence: list[str] = []
    if not has_reward:
        missing_evidence.append("reward_detail")
    if not has_action:
        missing_evidence.append("action_detail")
    if not has_time:
        missing_evidence.append("time_or_deadline")
    if not has_rules:
        missing_evidence.append("rule_or_faq")
    if not has_eligibility:
        missing_evidence.append("eligibility")

    reward_type = _infer_reward_type(combined_text)
    opportunity_type = _infer_opportunity_type(combined_text)
    target_score = sum((has_reward, has_action, has_time, has_rules, has_eligibility))
    is_target_opportunity = has_reward and (has_action or has_time or has_rules)

    recommended_next_actions: list[str] = []
    if not has_time:
        recommended_next_actions.append("search_deadline")
    if not has_rules:
        recommended_next_actions.append("open_rule_page")
    if not has_eligibility:
        recommended_next_actions.append("find_eligibility")
    if external_links:
        recommended_next_actions.append("follow_external_link")

    if not is_target_opportunity:
        label = "拒绝"
        confidence = 0.32
        evidence_sufficiency = "insufficient"
        summary = "缺少足够奖励活动证据，当前更像非目标内容或噪音线索。"
    elif target_score >= 5:
        label = "高价值"
        confidence = 0.93
        evidence_sufficiency = "strong"
        summary = "奖励、动作、时间、规则和资格证据完整，可直接进入重点机会库。"
    elif target_score >= 4:
        label = "可跟"
        confidence = 0.82
        evidence_sufficiency = "good"
        summary = "已具备主要奖励活动证据，仍可继续补充细则，但已足够作为有效机会。"
    elif has_reward and has_action and (not has_time or not has_rules or not has_eligibility):
        label = "待补证据"
        confidence = 0.71
        evidence_sufficiency = "partial"
        summary = "已识别奖励和参与动作，但关键细则仍不完整，建议继续补证据。"
    elif target_score >= 3:
        label = "待补证据"
        confidence = 0.68
        evidence_sufficiency = "partial"
        summary = "像有效奖励活动，但仍缺少关键证据，建议继续追规则、资格或时间信息。"
    elif has_reward:
        label = "低价值"
        confidence = 0.51
        evidence_sufficiency = "weak"
        summary = "存在奖励线索，但参与动作或规则支撑偏弱，优先级较低。"
    else:
        label = "拒绝"
        confidence = 0.3
        evidence_sufficiency = "insufficient"
        summary = "没有形成明确奖励活动证据。"

    risk_flags: list[str] = []
    if has_reward and not has_time:
        risk_flags.append("deadline_missing")
    if has_reward and not has_rules:
        risk_flags.append("rule_missing")
    if has_reward and not has_eligibility:
        risk_flags.append("eligibility_missing")
    if _contains_any(combined_text, ("expired", "ended", "已结束", "截止", "过期")) and not has_time:
        risk_flags.append("possible_expired")

    reasoning_parts = []
    if has_reward:
        reasoning_parts.append("reward")
    if has_action:
        reasoning_parts.append("action")
    if has_time:
        reasoning_parts.append("time")
    if has_rules:
        reasoning_parts.append("rules")
    if has_eligibility:
        reasoning_parts.append("eligibility")

    return {
        "is_target_opportunity": is_target_opportunity,
        "opportunity_type": opportunity_type,
        "reward_type": reward_type,
        "evidence_sufficiency": evidence_sufficiency,
        "recommended_next_actions": recommended_next_actions,
        "ai_stage_2_label": label,
        "ai_confidence": confidence,
        "ai_summary": summary,
        "ai_reasoning_brief": " / ".join(reasoning_parts) if reasoning_parts else "insufficient_evidence",
        "ai_missing_evidence": missing_evidence,
        "ai_risk_flags": risk_flags,
        "ai_structured_evidence": {
            "reward_snippets": reward_snippets,
            "action_snippets": action_snippets,
            "time_snippets": time_snippets,
            "rule_snippets": rule_snippets,
            "eligibility_snippets": eligibility_snippets,
            "recommended_next_actions": recommended_next_actions,
            "evidence_sufficiency": evidence_sufficiency,
            "is_target_opportunity": is_target_opportunity,
        },
        "needs_investigation": label == "待补证据",
    }
