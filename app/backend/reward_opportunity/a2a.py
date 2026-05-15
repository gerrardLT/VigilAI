"""A2A agent-card scaffolding for private reward agents."""

from __future__ import annotations

from typing import Any


def _agent_card(base_url: str, name: str, description: str, skill: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "url": f"{base_url.rstrip('/')}/a2a/{name}",
        "version": "0.1.0",
        "capabilities": {"streaming": False, "pushNotifications": False},
        "authentication": {"schemes": ["Bearer"]},
        "skills": [skill],
        "metadata": {
            "discovery": "private",
            "uses_mcp_policy": True,
            "requires_tool_approval": True,
        },
    }


def build_reward_agent_cards(base_url: str) -> list[dict[str, Any]]:
    return [
        _agent_card(
            base_url,
            "RewardScoutAgent",
            "Discovers candidate reward activity sources through governed tools.",
            {
                "id": "reward_source_discovery",
                "name": "Reward Source Discovery",
                "description": "Find likely reward, referral, bounty, and campaign sources.",
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
                "examples": ["Find reward campaign sources for developer tools."],
            },
        ),
        _agent_card(
            base_url,
            "RewardBrowserInvestigatorAgent",
            "Performs read-only browser investigation for reward activity evidence.",
            {
                "id": "read_only_browser_investigation",
                "name": "Read-only Browser Investigation",
                "description": "Open pages, follow rules/FAQ links, and collect evidence without write actions.",
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
                "examples": ["Collect rules and eligibility evidence from a campaign page."],
            },
        ),
        _agent_card(
            base_url,
            "RewardVerdictAgent",
            "Evaluates collected evidence and returns a governed reward-opportunity verdict.",
            {
                "id": "reward_verdict",
                "name": "Reward Verdict",
                "description": "Classify reward opportunities using evidence-linked structured output.",
                "inputModes": ["application/json"],
                "outputModes": ["application/json"],
                "examples": ["Classify this evidence bundle as high value or needs more evidence."],
            },
        ),
    ]


def get_reward_agent_card(base_url: str, agent_name: str) -> dict[str, Any]:
    for card in build_reward_agent_cards(base_url):
        if card["name"] == agent_name:
            return card
    raise KeyError(f"Unknown reward agent: {agent_name}")


def build_a2a_task_response(task_id: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": task_id,
        "status": {"state": "completed"},
        "artifacts": [
            {
                "artifactId": f"{task_id}:result",
                "parts": [{"kind": "data", "data": result}],
            }
        ],
    }
