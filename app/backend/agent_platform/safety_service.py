"""Safety checks for shared agent-session requests."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .models import AgentSession


class SafetyDecision(BaseModel):
    allowed: bool = True
    risk_flags: list[str] = Field(default_factory=list)
    safe_tool_names: list[str] = Field(default_factory=list)
    blocked_tool_names: list[str] = Field(default_factory=list)
    tool_policies: dict[str, dict[str, Any]] = Field(default_factory=dict)
    mode: str = "allow"
    blocked_reason: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentSafetyService:
    _READ_ONLY_TOOL_NAMES = {
        "opportunity_search",
        "opportunity_explain",
        "opportunity_next_action",
        "selection_query",
        "selection_compare",
    }
    _FULL_BLOCK_RISKS = {"credential_exfiltration", "destructive_request"}
    _GUARDED_EXECUTION_RISKS = {"bypass_or_scraping_abuse"}
    _TOOL_POLICY_MATRIX: dict[str, dict[str, str]] = {
        "opportunity_search": {
            "access_mode": "read_only",
            "data_scope": "opportunity_index",
            "risk_tier": "low",
        },
        "opportunity_explain": {
            "access_mode": "read_only",
            "data_scope": "opportunity_analysis",
            "risk_tier": "low",
        },
        "opportunity_next_action": {
            "access_mode": "read_only",
            "data_scope": "opportunity_tracking_view",
            "risk_tier": "medium",
        },
        "selection_query": {
            "access_mode": "read_only",
            "data_scope": "product_selection_pool",
            "risk_tier": "medium",
        },
        "selection_compare": {
            "access_mode": "read_only",
            "data_scope": "product_selection_cross_platform",
            "risk_tier": "medium",
        },
        "general_reasoning": {
            "access_mode": "reasoning_only",
            "data_scope": "none",
            "risk_tier": "review",
        },
    }
    _BLOCKED_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
        (
            "credential_exfiltration",
            ("cookie", "cookies", "token", "api key", "password", "session id", "credential", "密钥", "口令", "凭证"),
        ),
        (
            "bypass_or_scraping_abuse",
            ("绕过", "bypass", "anti-bot", "cloudflare", "风控", "验证码", "captcha", "proxy rotation", "fingerprint"),
        ),
        (
            "destructive_request",
            ("delete all", "drop table", "truncate", "wipe data", "删除所有", "清空数据库", "销毁"),
        ),
    )

    def evaluate(
        self,
        *,
        session: AgentSession,
        user_message: str,
        tool_names: list[str],
    ) -> SafetyDecision:
        normalized = (user_message or "").lower()
        risk_flags: list[str] = []

        for risk_flag, patterns in self._BLOCKED_PATTERNS:
            if any(pattern in normalized or pattern in user_message for pattern in patterns):
                risk_flags.append(risk_flag)

        if session.policy_mode == "strict" and risk_flags:
            tool_policies = self._build_tool_policies(
                tool_names=tool_names,
                safe_tool_names=[],
                blocked_tool_names=tool_names,
                mode="block",
                risk_flags=risk_flags,
            )
            return SafetyDecision(
                allowed=False,
                risk_flags=risk_flags,
                safe_tool_names=[],
                blocked_tool_names=tool_names,
                tool_policies=tool_policies,
                mode="block",
                blocked_reason=(
                    "This session is running in strict safety mode. Requests that trigger any risk policy are fully blocked."
                ),
                payload={"domain_type": session.domain_type, "policy_mode": session.policy_mode},
            )

        if any(flag in self._FULL_BLOCK_RISKS for flag in risk_flags):
            tool_policies = self._build_tool_policies(
                tool_names=tool_names,
                safe_tool_names=[],
                blocked_tool_names=tool_names,
                mode="block",
                risk_flags=risk_flags,
            )
            return SafetyDecision(
                allowed=False,
                risk_flags=risk_flags,
                safe_tool_names=[],
                blocked_tool_names=tool_names,
                tool_policies=tool_policies,
                mode="block",
                blocked_reason=(
                    "I can help with compliant research and workflow decisions, but I will not assist with "
                    "credential collection, bypassing platform protections, or destructive system actions."
                ),
                payload={"domain_type": session.domain_type, "policy_mode": session.policy_mode},
            )

        if any(flag in self._GUARDED_EXECUTION_RISKS for flag in risk_flags):
            safe_tool_names = [tool_name for tool_name in tool_names if tool_name in self._READ_ONLY_TOOL_NAMES]
            blocked_tool_names = [tool_name for tool_name in tool_names if tool_name not in safe_tool_names]
            if not safe_tool_names:
                tool_policies = self._build_tool_policies(
                    tool_names=tool_names,
                    safe_tool_names=[],
                    blocked_tool_names=tool_names,
                    mode="block",
                    risk_flags=risk_flags,
                )
                return SafetyDecision(
                    allowed=False,
                    risk_flags=risk_flags,
                    safe_tool_names=[],
                    blocked_tool_names=tool_names,
                    tool_policies=tool_policies,
                    mode="block",
                    blocked_reason=(
                        "I can continue only with compliant read-only research. This request currently centers on "
                        "bypassing platform protections, so I will not execute it."
                    ),
                    payload={"domain_type": session.domain_type, "policy_mode": session.policy_mode},
                )

            tool_policies = self._build_tool_policies(
                tool_names=tool_names,
                safe_tool_names=safe_tool_names,
                blocked_tool_names=blocked_tool_names,
                mode="guarded",
                risk_flags=risk_flags,
            )
            return SafetyDecision(
                allowed=True,
                risk_flags=risk_flags,
                safe_tool_names=safe_tool_names,
                blocked_tool_names=blocked_tool_names,
                tool_policies=tool_policies,
                mode="guarded",
                blocked_reason=(
                    "I will keep this within compliant research boundaries and will not help bypass platform "
                    "protections, anti-bot checks, or captcha flows."
                ),
                payload={"domain_type": session.domain_type, "policy_mode": session.policy_mode},
            )

        tool_policies = self._build_tool_policies(
            tool_names=tool_names,
            safe_tool_names=tool_names,
            blocked_tool_names=[],
            mode="allow",
            risk_flags=[],
        )
        return SafetyDecision(
            allowed=True,
            risk_flags=[],
            safe_tool_names=tool_names,
            blocked_tool_names=[],
            tool_policies=tool_policies,
            mode="allow",
            payload={"domain_type": session.domain_type, "policy_mode": session.policy_mode},
        )

    def _build_tool_policies(
        self,
        *,
        tool_names: list[str],
        safe_tool_names: list[str],
        blocked_tool_names: list[str],
        mode: str,
        risk_flags: list[str],
    ) -> dict[str, dict[str, Any]]:
        safe_set = set(safe_tool_names)
        blocked_set = set(blocked_tool_names)
        tool_policies: dict[str, dict[str, Any]] = {}

        for tool_name in tool_names:
            policy = dict(self._TOOL_POLICY_MATRIX.get(tool_name, {}))
            if not policy:
                policy = {
                    "access_mode": "unknown",
                    "data_scope": "unknown",
                    "risk_tier": "review",
                }

            if tool_name in blocked_set:
                decision = "blocked"
                reason = "The current request triggered safety controls for this tool."
            elif mode == "guarded" and tool_name in safe_set:
                decision = "guarded"
                reason = "The tool is allowed only in read-only guarded mode."
            else:
                decision = "allow"
                reason = "The tool is allowed under the current safety policy."

            tool_policies[tool_name] = {
                **policy,
                "decision": decision,
                "reason": reason,
                "risk_flags": list(risk_flags),
            }

        return tool_policies
