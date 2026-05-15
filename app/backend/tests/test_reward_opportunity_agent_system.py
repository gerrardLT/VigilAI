"""Agent-system integration tests for the reward-opportunity context."""

from __future__ import annotations

import os
import sys


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reward_opportunity.a2a import build_reward_agent_cards  # noqa: E402
from reward_opportunity.a2a import build_a2a_task_response, get_reward_agent_card  # noqa: E402
from reward_opportunity.agent_loop import run_investigation_cycle  # noqa: E402
from reward_opportunity.browser_collector import BrowserCollectConstraints, browser_collect  # noqa: E402
from reward_opportunity.graph import RewardInvestigationGraph  # noqa: E402
from reward_opportunity.mcp_tools import agent_reach_search, fetch_page_markdown, search_web  # noqa: E402
from reward_opportunity.mcp_server import build_mcp_server  # noqa: E402
from reward_opportunity.models import RewardEvaluationOutput  # noqa: E402
from reward_opportunity.pydantic_evaluator import (  # noqa: E402
    ModelUnavailableError,
    build_openai_compatible_client_config,
    evaluate_with_pydantic_ai,
)
from reward_opportunity.telemetry import EvaluationMetrics, TraceRecorder  # noqa: E402


def test_run_investigation_cycle_uses_graph_and_preserves_legacy_shape():
    result = run_investigation_cycle(
        candidate={"id": "candidate-1", "title": "Invite friends and get $25", "source_url": "https://example.com/promo"},
        evidence_bundle={
            "reward_snippets": ["receive a $25 cash reward"],
            "action_snippets": ["invite three friends"],
            "time_snippets": [],
            "rule_snippets": [],
            "eligibility_snippets": [],
            "external_links": ["https://example.com/rules"],
        },
        max_rounds=1,
        evaluator_client=lambda _bundle, evidence: {
            "is_target_opportunity": True,
            "opportunity_type": "invite_reward",
            "reward_type": "cash",
            "stage_label": "needs_more_evidence",
            "confidence": 0.8,
            "evidence_sufficiency": "partial",
            "missing_evidence": ["time_or_deadline"],
            "risk_flags": ["deadline_missing"],
            "required_next_actions": ["search_deadline"],
            "quoted_evidence_ids": [evidence[0]["id"]],
            "reasoning_brief": "Reward and action evidence are present.",
        },
    )

    assert result["status"] in {"classified", "needs_follow_up"}
    assert result["graph_version"] == "reward-investigation-v1"
    assert "evaluation" in result
    assert result["actions"]


def test_reward_investigation_graph_records_state_transitions():
    graph = RewardInvestigationGraph(evaluator_client=lambda _bundle, evidence: {
        "is_target_opportunity": True,
        "opportunity_type": "task_reward",
        "reward_type": "unknown",
        "stage_label": "needs_more_evidence",
        "confidence": 0.72,
        "evidence_sufficiency": "partial",
        "missing_evidence": ["time_or_deadline"],
        "risk_flags": ["deadline_missing"],
        "required_next_actions": ["search_deadline"],
        "quoted_evidence_ids": [evidence[0]["id"]],
        "reasoning_brief": "Reward and action evidence are present.",
    })

    result = graph.invoke(
        {
            "candidate": {"id": "candidate-graph-1", "title": "Complete quests to earn rewards"},
            "evidence_bundle": {
                "reward_snippets": ["earn rewards"],
                "action_snippets": ["complete quests"],
                "time_snippets": [],
                "rule_snippets": [],
                "eligibility_snippets": [],
            },
            "budgets": {"max_rounds": 0, "max_new_links": 2, "timeout_seconds": 10},
        }
    )

    assert result["status"] == "needs_follow_up"
    assert result["round_index"] == 0
    assert "evaluate_baseline" in result["step_names"]
    assert "finalize" in result["step_names"]


def test_reward_investigation_graph_marks_model_failure_when_real_model_required():
    graph = RewardInvestigationGraph(evaluator_client=lambda _bundle, _evidence: (_ for _ in ()).throw(ModelUnavailableError("missing key")))

    result = graph.invoke(
        {
            "candidate": {"id": "candidate-graph-2", "title": "Invite friends to earn cash"},
            "evidence_bundle": {
                "reward_snippets": ["earn cash"],
                "action_snippets": ["invite friends"],
                "time_snippets": [],
                "rule_snippets": [],
                "eligibility_snippets": [],
            },
            "budgets": {"max_rounds": 0, "max_new_links": 2, "timeout_seconds": 10},
        }
    )

    assert result["status"] == "failed"
    assert result["errors"][0]["failure_type"] == "model_unavailable"


def test_pydantic_evaluator_schema_and_explicit_fallback_to_baseline():
    baseline = {
        "is_target_opportunity": True,
        "opportunity_type": "invite_reward",
        "reward_type": "cash",
        "ai_stage_2_label": "baseline",
        "ai_confidence": 0.7,
        "ai_missing_evidence": ["time_or_deadline"],
        "ai_risk_flags": ["deadline_missing"],
        "recommended_next_actions": ["search_deadline"],
        "needs_investigation": True,
    }

    def failing_client(_bundle, _evidence):
        raise RuntimeError("model unavailable")

    result = evaluate_with_pydantic_ai(
        {"reward_snippets": ["$25"], "action_snippets": ["invite friends"]},
        baseline_result=baseline,
        evaluator_client=failing_client,
        allow_baseline_fallback=True,
    )

    assert result["source"] == "baseline_fallback"
    assert result["ai_stage_2_label"] == "baseline"
    output = RewardEvaluationOutput.from_baseline(result)
    assert output.required_next_actions == ["search_deadline"]


def test_pydantic_evaluator_raises_when_real_model_is_required_and_unavailable():
    def missing_client(_bundle, _evidence):
        raise ModelUnavailableError("OPENAI_API_KEY is required")

    try:
        evaluate_with_pydantic_ai(
            {"reward_snippets": ["$25"], "action_snippets": ["invite friends"]},
            evaluator_client=missing_client,
            allow_baseline_fallback=False,
        )
    except ModelUnavailableError as exc:
        assert "OPENAI_API_KEY" in str(exc)
    else:
        raise AssertionError("expected ModelUnavailableError")


def test_reward_evaluator_config_supports_dashscope_qwen(monkeypatch):
    monkeypatch.setenv("REWARD_AGENT_PROVIDER", "qwen")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-dashscope-key")
    monkeypatch.setenv("REWARD_AGENT_MODEL", "qwen-plus")

    config = build_openai_compatible_client_config()

    assert config["api_key"] == "test-dashscope-key"
    assert config["base_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert config["model"] == "qwen-plus"


def test_reward_evaluator_qwen_requires_dashscope_key(monkeypatch):
    monkeypatch.setenv("REWARD_AGENT_PROVIDER", "qwen")
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    try:
        build_openai_compatible_client_config()
    except ModelUnavailableError as exc:
        assert "DASHSCOPE_API_KEY" in str(exc)
    else:
        raise AssertionError("expected ModelUnavailableError")


def test_pydantic_evaluator_accepts_real_model_client_output():
    def real_client(_bundle, evidence):
        return {
            "is_target_opportunity": True,
            "opportunity_type": "invite_reward",
            "reward_type": "cash",
            "stage_label": "needs_more_evidence",
            "confidence": 0.86,
            "evidence_sufficiency": "partial",
            "missing_evidence": ["time_or_deadline"],
            "risk_flags": ["deadline_missing"],
            "required_next_actions": ["search_deadline"],
            "quoted_evidence_ids": [evidence[0]["id"]],
            "reasoning_brief": "Reward and action evidence are present.",
        }

    result = evaluate_with_pydantic_ai(
        {"reward_snippets": ["$25"], "action_snippets": ["invite friends"]},
        evaluator_client=real_client,
        allow_baseline_fallback=False,
    )

    assert result["source"] == "pydantic_ai"
    assert result["ai_confidence"] == 0.86
    assert result["ai_structured_evidence"]["quoted_evidence_ids"] == ["reward_snippets:1"]


def test_mcp_tools_return_uniform_envelopes():
    search_result = search_web(
        "invite reward",
        domains=["example.com"],
        search_fn=lambda query, max_results: ["https://example.com/rewards", "https://other.test/nope"],
    )
    page_result = fetch_page_markdown("https://example.com/rewards", fetch_fn=lambda url: "# Rewards")
    unavailable_result = agent_reach_search(
        "reddit",
        "invite reward",
        runner=lambda _platform, _query, _limit: (_ for _ in ()).throw(FileNotFoundError("agent-reach")),
    )

    assert search_result["ok"] is True
    assert search_result["data"]["results"] == ["https://example.com/rewards"]
    assert page_result["ok"] is True
    assert page_result["data"]["markdown"] == "# Rewards"
    assert unavailable_result["ok"] is False
    assert unavailable_result["failure_type"] == "unavailable"
    assert {"ok", "data", "source", "failure_type", "error_message", "fetched_at"} <= set(unavailable_result)


def test_mcp_server_builds_real_tool_server():
    server = build_mcp_server()

    assert server.name == "reward-opportunity-tools"


def test_browser_collect_enforces_read_only_policy():
    constraints = BrowserCollectConstraints(allowed_domains=["example.com"])

    result = browser_collect(
        "https://example.com/rewards",
        "find rules",
        constraints=constraints,
        runner=lambda _url, _objective, _constraints: {
            "final_url": "https://example.com/rewards",
            "text": "Rules and rewards",
            "actions": [{"action_type": "open_url"}, {"action_type": "submit_form"}],
        },
    )

    assert result["ok"] is False
    assert result["failure_type"] == "approval_required"
    assert "submit_form" in result["error_message"]


def test_browser_collect_default_runner_uses_real_browser_for_page_text():
    result = browser_collect(
        "data:text/html,<html><title>Reward Rules</title><body><h1>Reward Rules</h1><a href='https://example.com/terms'>Terms</a></body></html>",
        "collect visible reward rules",
        constraints=BrowserCollectConstraints(),
    )

    assert result["ok"] is True
    assert result["data"]["engine"] in {"browser_use", "playwright"}
    assert "Reward Rules" in result["data"]["text"]


def test_trace_recorder_and_metrics_capture_agent_run_shape():
    recorder = TraceRecorder(run_id="run-1")
    recorder.record_step("evaluate_baseline", {"status": "running"}, {"status": "needs_follow_up"}, latency_ms=12)
    recorder.record_tool_call("search_web", {"query": "reward"}, {"ok": True}, latency_ms=5)

    payload = recorder.to_payload()
    metrics = EvaluationMetrics.from_cases(
        [
            {"expected": True, "actual": True, "evidence_complete": True},
            {"expected": False, "actual": True, "evidence_complete": False},
        ]
    )

    assert payload["run_id"] == "run-1"
    assert payload["steps"][0]["name"] == "evaluate_baseline"
    assert payload["tool_calls"][0]["tool_name"] == "search_web"
    assert metrics.precision == 0.5
    assert metrics.recall == 1.0
    assert metrics.evidence_completeness == 0.5


def test_trace_recorder_flushes_to_langsmith_client():
    class FakeLangSmithClient:
        def __init__(self):
            self.created = []
            self.updated = []

        def create_run(self, **kwargs):
            self.created.append(kwargs)

        def update_run(self, *args, **kwargs):
            self.updated.append((args, kwargs))

    recorder = TraceRecorder(run_id="run-langsmith")
    recorder.record_step("evaluate_llm", {}, {"source": "pydantic_ai"})
    client = FakeLangSmithClient()

    result = recorder.flush_to_langsmith(project_name="test-project", client=client)

    assert result["ok"] is True
    assert client.created[0]["project_name"] == "test-project"
    assert client.updated[0][1]["outputs"]["run_id"] == "run-langsmith"


def test_a2a_agent_cards_are_private_and_permissioned():
    cards = build_reward_agent_cards(base_url="https://agents.internal.example")

    assert {card["name"] for card in cards} == {
        "RewardScoutAgent",
        "RewardBrowserInvestigatorAgent",
        "RewardVerdictAgent",
    }
    for card in cards:
        assert card["url"].startswith("https://agents.internal.example")
        assert card["metadata"]["discovery"] == "private"
        assert card["metadata"]["uses_mcp_policy"] is True
        assert card["skills"]


def test_a2a_helpers_return_cards_and_task_artifacts():
    card = get_reward_agent_card("https://agents.internal.example", "RewardVerdictAgent")
    response = build_a2a_task_response("task-1", {"status": "classified"})

    assert card["name"] == "RewardVerdictAgent"
    assert response["status"]["state"] == "completed"
    assert response["artifacts"][0]["parts"][0]["data"]["status"] == "classified"
