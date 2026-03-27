"""
Analysis API tests.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import (  # noqa: E402
    AnalysisTemplateCreateRequest,
    AnalysisTemplatePreviewRequest,
    AnalysisTemplateUpdateRequest,
    app,
)
from data_manager import DataManager  # noqa: E402
from models import Activity, ActivityDates, Category, Prize  # noqa: E402


class DummyScheduler:
    async def refresh_source(self, source_id: str) -> bool:
        return True

    async def refresh_all(self) -> None:
        return None


@pytest.fixture
def temp_db():
    temp_root = os.path.join(os.path.dirname(__file__), ".tmp")
    os.makedirs(temp_root, exist_ok=True)
    db_path = os.path.join(temp_root, f"{uuid.uuid4().hex}.db")
    try:
        yield db_path
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.fixture
def data_manager(temp_db):
    return DataManager(db_path=temp_db)


@pytest.fixture
def client(data_manager):
    app.state.data_manager = data_manager
    app.state.scheduler = DummyScheduler()
    with TestClient(app) as test_client:
        yield test_client


def create_activity(data_manager: DataManager, url: str = "https://example.com/api-analysis") -> Activity:
    source = data_manager.get_sources_status()[0]
    now = datetime.now()
    return Activity(
        id=Activity.generate_id(source.id, url),
        title="Solo bug bounty with fast payout",
        description="Individual developers can submit a small fix and receive reward payout within 7 days.",
        source_id=source.id,
        source_name=source.name,
        url=url,
        category=Category.BOUNTY,
        prize=Prize(amount=1500, currency="USD", description="Guaranteed reward"),
        dates=ActivityDates(deadline=now + timedelta(days=5)),
        created_at=now,
        updated_at=now,
    )


def test_analysis_template_endpoints_list_duplicate_activate_update_and_delete(client):
    listed = client.get("/api/analysis/templates")
    default_template = client.get("/api/analysis/templates/default")

    template_id = default_template.json()["id"]
    duplicated = client.post(
        f"/api/analysis/templates/{template_id}/duplicate",
        json={"name": "Quick money copy"},
    )
    activated = client.post(f"/api/analysis/templates/{duplicated.json()['id']}/activate")
    updated = client.patch(
        f"/api/analysis/templates/{duplicated.json()['id']}",
        json={"name": "Quick money copy v2"},
    )
    deleted = client.delete(f"/api/analysis/templates/{duplicated.json()['id']}")

    assert listed.status_code == 200
    assert default_template.status_code == 200
    assert any(item["slug"] == "quick-money" for item in listed.json())
    assert duplicated.status_code == 200
    assert duplicated.json()["name"] == "Quick money copy"
    assert activated.status_code == 200
    assert activated.json()["id"] == duplicated.json()["id"]
    assert updated.status_code == 200
    assert updated.json()["name"] == "Quick money copy v2"
    assert deleted.status_code == 200
    assert deleted.json()["success"] is True


def test_analysis_template_request_models_keep_business_fields():
    create_request = AnalysisTemplateCreateRequest.model_validate(
        {
            "name": "Safe route",
            "preference_profile": "safety_first",
            "risk_tolerance": "conservative",
            "research_mode": "deep",
        }
    )
    update_request = AnalysisTemplateUpdateRequest.model_validate(
        {
            "preference_profile": "safety_first",
            "risk_tolerance": "conservative",
            "research_mode": "deep",
        }
    )
    preview_request = AnalysisTemplatePreviewRequest.model_validate(
        {
            "name": "Safe route",
            "preference_profile": "safety_first",
            "risk_tolerance": "conservative",
            "research_mode": "deep",
        }
    )

    assert create_request.model_dump()["preference_profile"] == "safety_first"
    assert create_request.model_dump()["risk_tolerance"] == "conservative"
    assert create_request.model_dump()["research_mode"] == "deep"
    assert update_request.model_dump(exclude_none=True)["preference_profile"] == "safety_first"
    assert update_request.model_dump(exclude_none=True)["risk_tolerance"] == "conservative"
    assert update_request.model_dump(exclude_none=True)["research_mode"] == "deep"
    assert preview_request.model_dump()["preference_profile"] == "safety_first"
    assert preview_request.model_dump()["risk_tolerance"] == "conservative"
    assert preview_request.model_dump()["research_mode"] == "deep"


def test_analysis_template_endpoints_preserve_business_fields_and_rebuild_legacy_shape(client):
    created = client.post(
        "/api/analysis/templates",
        json={
            "name": "Safe route",
            "preference_profile": "safety_first",
            "risk_tolerance": "conservative",
            "research_mode": "deep",
        },
    )

    created_body = created.json()
    trust_layer = next(layer for layer in created_body["layers"] if layer["key"] == "trust")

    assert created.status_code == 200
    assert created_body["preference_profile"] == "safety_first"
    assert created_body["risk_tolerance"] == "conservative"
    assert created_body["research_mode"] == "deep"
    assert created_body["sort_fields"] == ["trust", "clarity", "roi"]
    assert trust_layer["conditions"][0]["value"] == "high"

    updated = client.patch(
        f"/api/analysis/templates/{created_body['id']}",
        json={
            "preference_profile": "money_first",
            "risk_tolerance": "balanced",
            "research_mode": "layered",
        },
    )

    updated_body = updated.json()
    updated_trust_layer = next(layer for layer in updated_body["layers"] if layer["key"] == "trust")

    assert updated.status_code == 200
    assert updated_body["preference_profile"] == "money_first"
    assert updated_body["risk_tolerance"] == "balanced"
    assert updated_body["research_mode"] == "layered"
    assert updated_body["sort_fields"] == ["roi", "payout_speed", "trust"]
    assert updated_trust_layer["conditions"][0]["value"] == "medium"

    rebalanced = client.patch(
        f"/api/analysis/templates/{created_body['id']}",
        json={
            "preference_profile": "balanced",
            "risk_tolerance": "balanced",
            "research_mode": "layered",
        },
    )

    rebalanced_body = rebalanced.json()
    rebalanced_hard_gate = next(layer for layer in rebalanced_body["layers"] if layer["key"] == "hard_gate")

    assert rebalanced.status_code == 200
    assert rebalanced_body["preference_profile"] == "balanced"
    assert rebalanced_body["risk_tolerance"] == "balanced"
    assert rebalanced_body["research_mode"] == "layered"
    assert rebalanced_body["sort_fields"] == ["effort", "roi", "deadline"]
    assert rebalanced_hard_gate["conditions"][0]["key"] == "solo_friendliness"


def test_activity_detail_includes_analysis_payload(client, data_manager):
    activity = create_activity(data_manager, url="https://example.com/api-analysis-detail")
    data_manager.add_activity(activity)

    response = client.get(f"/api/activities/{activity.id}")

    payload = response.json()
    assert response.status_code == 200
    assert payload["analysis_fields"]["roi_level"] in {"medium", "high"}
    assert payload["analysis_status"] in {"passed", "watch", "rejected"}
    assert payload["analysis_summary_reasons"]
    assert payload["analysis_layer_results"]
    assert payload["analysis_layer_results"][0]["label"]
    assert payload["analysis_score_breakdown"]


def test_activity_list_filters_by_analysis_status(client, data_manager):
    passed_activity = create_activity(data_manager, url="https://example.com/api-analysis-passed")
    rejected_activity = create_activity(data_manager, url="https://example.com/api-analysis-rejected")
    data_manager.add_activity(passed_activity)
    data_manager.add_activity(rejected_activity)

    with data_manager._get_connection() as conn:
        conn.execute(
            "UPDATE activities SET analysis_status = ? WHERE id = ?",
            ("passed", passed_activity.id),
        )
        conn.execute(
            "UPDATE activities SET analysis_status = ? WHERE id = ?",
            ("rejected", rejected_activity.id),
        )
        conn.commit()

    response = client.get("/api/activities", params={"analysis_status": "passed"})

    payload = response.json()
    assert response.status_code == 200
    assert payload["total"] == 1
    assert [item["id"] for item in payload["items"]] == [passed_activity.id]


def test_analysis_run_endpoint_recomputes_existing_activities(client, data_manager):
    source = data_manager.get_sources_status()[0]
    activity = Activity(
        id=Activity.generate_id(source.id, "https://example.com/api-analysis-run"),
        title="Solo lightweight personal challenge",
        description="A solo-friendly lightweight project with no listed payout yet.",
        source_id=source.id,
        source_name=source.name,
        url="https://example.com/api-analysis-run",
        category=Category.BOUNTY,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    data_manager.add_activity(activity)

    roi_template = next(
        item for item in data_manager.get_analysis_templates() if item["slug"] == "low-effort-high-roi"
    )
    data_manager.set_default_analysis_template(roi_template["id"])

    with data_manager._get_connection() as conn:
        conn.execute(
            "UPDATE activities SET analysis_status = ? WHERE id = ?",
            ("rejected", activity.id),
        )
        conn.commit()

    response = client.post("/api/analysis/run")

    payload = response.json()
    repaired = data_manager.get_activity_by_id(activity.id)
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["processed"] >= 1
    assert repaired is not None
    assert repaired.analysis_status == "passed"


def test_analysis_template_preview_endpoint_returns_status_breakdown(client, data_manager):
    passed_activity = create_activity(data_manager, url="https://example.com/api-analysis-preview-passed")
    rejected_activity = Activity(
        id=Activity.generate_id(data_manager.get_sources_status()[0].id, "https://example.com/api-analysis-preview-rejected"),
        title="Large team enterprise proposal",
        description="Group submission with long-form proposal and no payout details yet.",
        source_id=data_manager.get_sources_status()[0].id,
        source_name=data_manager.get_sources_status()[0].name,
        url="https://example.com/api-analysis-preview-rejected",
        category=Category.BOUNTY,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    data_manager.add_activity(passed_activity)
    data_manager.add_activity(rejected_activity)

    template_id = next(
        item["id"] for item in data_manager.get_analysis_templates() if item["slug"] == "low-effort-high-roi"
    )

    response = client.get(f"/api/analysis/templates/{template_id}/preview")

    payload = response.json()
    assert response.status_code == 200
    assert payload["template_id"] == template_id
    assert payload["total"] == 2
    assert payload["passed"] + payload["watch"] + payload["rejected"] == 2
    assert payload["passed"] >= 1
    assert payload["rejected"] >= 1


def test_analysis_template_draft_preview_endpoint_accepts_unsaved_layers(client, data_manager):
    passed_activity = create_activity(data_manager, url="https://example.com/api-analysis-draft-preview-passed")
    rejected_activity = Activity(
        id=Activity.generate_id(data_manager.get_sources_status()[0].id, "https://example.com/api-analysis-draft-preview-rejected"),
        title="Large team enterprise proposal",
        description="Group submission with long-form proposal and no payout details yet.",
        source_id=data_manager.get_sources_status()[0].id,
        source_name=data_manager.get_sources_status()[0].name,
        url="https://example.com/api-analysis-draft-preview-rejected",
        category=Category.BOUNTY,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    data_manager.add_activity(passed_activity)
    data_manager.add_activity(rejected_activity)

    response = client.post(
        "/api/analysis/templates/preview",
        json={
            "id": "draft-template",
            "name": "Draft template",
            "layers": [
                {
                    "key": "hard_gate",
                    "label": "Hard gate",
                    "enabled": True,
                    "mode": "filter",
                    "conditions": [
                        {
                            "key": "solo_friendliness",
                            "label": "Solo only",
                            "enabled": True,
                            "operator": "eq",
                            "value": "solo_friendly",
                            "hard_fail": True,
                        }
                    ],
                }
            ],
            "sort_fields": ["roi_score"],
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["template_id"] == "draft-template"
    assert payload["total"] == 2
    assert payload["passed"] >= 1
    assert payload["rejected"] >= 1


def test_analysis_template_draft_preview_results_endpoint_returns_activity_breakdown(client, data_manager):
    passed_activity = create_activity(data_manager, url="https://example.com/api-analysis-draft-results-passed")
    rejected_activity = Activity(
        id=Activity.generate_id(data_manager.get_sources_status()[0].id, "https://example.com/api-analysis-draft-results-rejected"),
        title="Large team enterprise proposal",
        description="Group submission with long-form proposal and no payout details yet.",
        source_id=data_manager.get_sources_status()[0].id,
        source_name=data_manager.get_sources_status()[0].name,
        url="https://example.com/api-analysis-draft-results-rejected",
        category=Category.BOUNTY,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    data_manager.add_activity(passed_activity)
    data_manager.add_activity(rejected_activity)

    response = client.post(
        "/api/analysis/templates/preview/results",
        json={
            "id": "draft-template",
            "name": "Draft template",
            "activity_ids": [passed_activity.id, rejected_activity.id],
            "layers": [
                {
                    "key": "hard_gate",
                    "label": "Hard gate",
                    "enabled": True,
                    "mode": "filter",
                    "conditions": [
                        {
                            "key": "solo_friendliness",
                            "label": "Solo only",
                            "enabled": True,
                            "operator": "eq",
                            "value": "solo_friendly",
                            "hard_fail": True,
                        }
                    ],
                }
            ],
            "sort_fields": ["roi_score"],
        },
    )

    payload = response.json()
    items_by_id = {item["activity_id"]: item for item in payload["items"]}
    assert response.status_code == 200
    assert payload["template_id"] == "draft-template"
    assert payload["total"] == 2
    assert payload["passed"] >= 1
    assert payload["rejected"] >= 1
    assert items_by_id[passed_activity.id]["status"] == "passed"
    assert items_by_id[rejected_activity.id]["status"] == "rejected"
    assert items_by_id[rejected_activity.id]["failed_layer"] == "hard_gate"


def test_workspace_includes_analysis_overview_and_blocked_opportunities(client, data_manager):
    passed_activity = create_activity(data_manager, url="https://example.com/workspace-analysis-passed")
    rejected_activity = Activity(
        id=Activity.generate_id(data_manager.get_sources_status()[0].id, "https://example.com/workspace-analysis-rejected"),
        title="Large team enterprise proposal",
        description="Group submission with long-form proposal and no payout details yet.",
        source_id=data_manager.get_sources_status()[0].id,
        source_name=data_manager.get_sources_status()[0].name,
        url="https://example.com/workspace-analysis-rejected",
        category=Category.BOUNTY,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    data_manager.add_activity(passed_activity)
    data_manager.add_activity(rejected_activity)

    with data_manager._get_connection() as conn:
        conn.execute(
            "UPDATE activities SET analysis_status = ?, analysis_summary_reasons = ? WHERE id = ?",
            ("passed", '["Reward clarity passed"]', passed_activity.id),
        )
        conn.execute(
            "UPDATE activities SET analysis_status = ?, analysis_failed_layer = ?, analysis_summary_reasons = ? WHERE id = ?",
            ("rejected", "hard_gate", '["Solo only failed hard gate"]', rejected_activity.id),
        )
        conn.commit()

    response = client.get("/api/workspace")

    payload = response.json()
    assert response.status_code == 200
    assert payload["analysis_overview"]["passed"] >= 1
    assert payload["analysis_overview"]["rejected"] >= 1
    assert payload["blocked_opportunities"]
    assert payload["blocked_opportunities"][0]["analysis_status"] == "rejected"


def test_analysis_results_endpoint_lists_filtered_results(client, data_manager):
    passed_activity = create_activity(data_manager, url="https://example.com/analysis-results-passed")
    rejected_activity = create_activity(data_manager, url="https://example.com/analysis-results-rejected")
    data_manager.add_activity(passed_activity)
    data_manager.add_activity(rejected_activity)

    with data_manager._get_connection() as conn:
        conn.execute(
            "UPDATE activities SET analysis_status = ?, analysis_summary_reasons = ? WHERE id = ?",
            ("passed", '["Reward clarity passed"]', passed_activity.id),
        )
        conn.execute(
            "UPDATE activities SET analysis_status = ?, analysis_failed_layer = ?, analysis_summary_reasons = ? WHERE id = ?",
            ("rejected", "hard_gate", '["Solo only failed hard gate"]', rejected_activity.id),
        )
        conn.commit()

    response = client.get("/api/analysis/results", params={"analysis_status": "passed"})

    payload = response.json()
    assert response.status_code == 200
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == passed_activity.id
    assert payload["items"][0]["analysis_layer_results"]
    assert payload["items"][0]["analysis_score_breakdown"]


def test_analysis_result_detail_endpoint_returns_verdict_payload(client, data_manager):
    activity = create_activity(data_manager, url="https://example.com/analysis-result-detail")
    data_manager.add_activity(activity)

    response = client.get(f"/api/analysis/results/{activity.id}")

    payload = response.json()
    assert response.status_code == 200
    assert payload["id"] == activity.id
    assert payload["analysis_status"] in {"passed", "watch", "rejected"}
    assert payload["analysis_layer_results"]
    assert payload["analysis_score_breakdown"]
