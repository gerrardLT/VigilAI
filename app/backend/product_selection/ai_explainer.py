"""
Explainers for product-selection opportunity reasoning.
"""

from __future__ import annotations

from typing import Any


def build_reason_blocks(candidate: dict[str, Any]) -> list[str]:
    reasons: list[str] = []

    if float(candidate.get("demand_score") or 0) >= 70:
        reasons.append("需求侧公开信号较强，说明这个方向已经有稳定关注度。")
    if float(candidate.get("competition_score") or 0) <= 45:
        reasons.append("同类竞争密度还在可控区间，存在切入空间。")
    if float(candidate.get("price_fit_score") or 0) >= 65:
        reasons.append("价格带有可操作空间，适合做差异化组合或轻度升级。")
    if float(candidate.get("cross_platform_signal_score") or 0) >= 60:
        reasons.append("淘宝和闲鱼之间存在交叉验证信号，降低了单平台噪音。")
    if float(candidate.get("risk_score") or 0) >= 55:
        reasons.append("风险分偏高，建议先做小样验证，避免直接重投入。")

    risk_tags = candidate.get("risk_tags") or []
    if risk_tags:
        reasons.append("需要重点关注：" + "、".join(str(tag) for tag in risk_tags[:3]))

    return reasons or ["当前信号有限，建议先收集更多样本再判断。"]


def recommend_action(candidate: dict[str, Any]) -> str:
    opportunity_score = float(candidate.get("opportunity_score") or 0)
    risk_score = float(candidate.get("risk_score") or 0)

    if risk_score >= 60:
        return "先做小批量验证，重点核对售后、侵权和物流风险，再决定是否放大投入。"
    if opportunity_score >= 72:
        return "先收集 20 个同类 SKU，验证价格带、评论痛点和差异化卖点，再决定是否进入上新准备。"
    if opportunity_score >= 60:
        return "先补一轮竞品和价格带样本，确认是否仍有利润空间，再决定是否继续跟进。"
    return "先缩小关键词或类目范围，重新做一轮更聚焦的研究任务。"
