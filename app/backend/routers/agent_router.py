"""
Agent platform router - handles all /api/agent/* endpoints.
"""

from __future__ import annotations

import logging
from typing import Optional

from agent_platform.artifact_service import ArtifactService
from agent_platform.conversation_engine import ConversationEngine
from agent_platform.memory_service import MemoryService
from agent_platform.reflection_service import ReflectionService
from agent_platform.repository import AgentPlatformRepository
from agent_platform.tool_router import ToolRouter, build_default_registry
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])


# --- Pydantic Models ---


class AgentSessionCreateRequest(BaseModel):
    domain_type: str
    entry_mode: str = "chat"
    policy_mode: str = "standard"
    memory_scope: str = "domain"
    title: Optional[str] = None


class AgentTurnCreateRequest(BaseModel):
    content: str


class WorkbenchSaveRequest(BaseModel):
    domain: str  # "opportunity" or "product_selection"
    session_id: str
    turn_id: str
    title: str
    url: str = ""
    description: str = ""
    category: str = ""
    source_name: str = "Agent"


# --- Helper Functions ---


def _serialize_model(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _get_agent_repository(request: Request) -> AgentPlatformRepository:
    repository = getattr(request.app.state, "agent_platform_repository", None)
    data_manager = getattr(request.app.state, "data_manager", None)
    if data_manager is None:
        raise RuntimeError("Data manager is not initialized")

    if repository is None or getattr(repository, "db_path", None) != data_manager.db_path:
        repository = AgentPlatformRepository(data_manager.db_path)
        request.app.state.agent_platform_repository = repository

    return repository


def _get_tool_router(request: Request) -> ToolRouter:
    tool_router = getattr(request.app.state, "agent_tool_router", None)
    data_manager = getattr(request.app.state, "data_manager", None)
    if data_manager is None:
        raise RuntimeError("Data manager is not initialized")

    registry_key = getattr(data_manager, "db_path", None)
    if tool_router is None or getattr(tool_router, "registry_key", None) != registry_key:
        tool_router = ToolRouter(
            tool_registry=build_default_registry(data_manager=data_manager),
            registry_key=registry_key,
        )
        request.app.state.agent_tool_router = tool_router
    return tool_router


def _get_conversation_engine(request: Request) -> ConversationEngine:
    tool_router = _get_tool_router(request)
    engine = getattr(request.app.state, "agent_conversation_engine", None)
    if engine is None or getattr(engine, "tool_router", None) is not tool_router:
        engine = ConversationEngine(tool_router=tool_router)
        request.app.state.agent_conversation_engine = engine
    return engine


def _get_artifact_service(request: Request) -> ArtifactService:
    artifact_service = getattr(request.app.state, "agent_artifact_service", None)
    repository = _get_agent_repository(request)
    if artifact_service is None or getattr(artifact_service, "repository", None) is not repository:
        artifact_service = ArtifactService(repository=repository)
        request.app.state.agent_artifact_service = artifact_service
    return artifact_service


def _get_memory_service(request: Request) -> MemoryService:
    memory_service = getattr(request.app.state, "agent_memory_service", None)
    repository = _get_agent_repository(request)
    if memory_service is None or getattr(memory_service, "repository", None) is not repository:
        memory_service = MemoryService(repository=repository)
        request.app.state.agent_memory_service = memory_service
    return memory_service


def _get_reflection_service(request: Request) -> ReflectionService:
    reflection_service = getattr(request.app.state, "agent_reflection_service", None)
    repository = _get_agent_repository(request)
    if reflection_service is None or getattr(reflection_service, "repository", None) is not repository:
        reflection_service = ReflectionService(repository=repository)
        request.app.state.agent_reflection_service = reflection_service
    return reflection_service


# --- Endpoints ---


@router.post("/sessions")
async def create_agent_session(request: Request, payload: AgentSessionCreateRequest):
    repository = _get_agent_repository(request)
    session = repository.create_session(
        domain_type=payload.domain_type,
        entry_mode=payload.entry_mode,
        policy_mode=payload.policy_mode,
        memory_scope=payload.memory_scope,
        title=payload.title,
    )
    return _serialize_model(session)


@router.get("/sessions")
async def list_agent_sessions(
    request: Request,
    domain_type: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
):
    repository = _get_agent_repository(request)
    return repository.list_sessions(domain_type=domain_type, limit=limit)


@router.get("/sessions/{session_id}")
async def get_agent_session(request: Request, session_id: str):
    repository = _get_agent_repository(request)
    session = repository.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Agent 会话不存在")
    return _serialize_model(session)


@router.post("/sessions/{session_id}/turns")
async def post_agent_turn(request: Request, session_id: str, payload: AgentTurnCreateRequest):
    repository = _get_agent_repository(request)
    session = repository.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Agent 会话不存在")

    recalled_memories = _get_memory_service(request).recall_for_session(session)
    recalled_reflections = _get_reflection_service(request).recall_for_session(session)
    user_turn = repository.append_turn(session_id, role="user", content=payload.content)
    reply = _get_conversation_engine(request).reply(
        session=session,
        user_turn=user_turn,
        recalled_memories=recalled_memories,
        recalled_reflections=recalled_reflections,
    )
    assistant_turn = repository.append_turn(session_id, role="assistant", content=reply.assistant_turn)
    artifacts = _get_artifact_service(request).persist(session_id, reply.artifacts)
    execution_plan = repository.create_execution_plan(
        session_id,
        source_turn_id=user_turn.id,
        mode=reply.execution_plan.mode,
        summary=reply.execution_plan.summary,
        requested_steps=[item.model_dump(mode="json") for item in reply.execution_plan.requested_steps],
        runnable_tools=reply.execution_plan.runnable_tools,
        blocked_tools=reply.execution_plan.blocked_tools,
        risk_flags=reply.execution_plan.risk_flags,
        reasoning=reply.execution_plan.reasoning,
        payload=reply.execution_plan.payload,
    )
    session_state = repository.upsert_session_state(
        session_id,
        **reply.session_state.model_dump(),
    )
    insights = [
        repository.create_insight(
            session_id,
            insight_type=draft.insight_type,
            content=draft.content,
            importance=draft.importance,
            payload=draft.payload,
            source_turn_id=user_turn.id,
        )
        for draft in reply.insights
    ]
    thinking_steps = [
        repository.create_thinking_step(
            session_id,
            phase=draft.phase,
            summary=draft.summary,
            tool_name=draft.tool_name,
            payload=draft.payload,
            source_turn_id=user_turn.id,
        )
        for draft in reply.thinking_steps
    ]
    memories = _get_memory_service(request).promote_from_turn(
        session=session,
        user_turn=user_turn,
        session_state=session_state,
        insights=insights,
    )
    reflections = [
        _get_reflection_service(request).create_turn_reflection(
            session=session,
            user_turn=user_turn,
            session_state=session_state,
            tool_calls=reply.tool_calls,
            insights=insights,
        )
    ]

    if reply.next_state != session.status:
        session = repository.update_session_status(session_id, status=reply.next_state)
    else:
        session = repository.get_session(session_id) or session

    turns = repository.list_turns(session_id)
    return {
        "session": _serialize_model(session),
        "user_turn": _serialize_model(user_turn),
        "assistant_turn": _serialize_model(assistant_turn),
        "artifacts": [_serialize_model(artifact) for artifact in artifacts],
        "tool_calls": reply.tool_calls,
        "execution_plan": _serialize_model(execution_plan),
        "recalled_memories": [_serialize_model(item) for item in recalled_memories],
        "recalled_reflections": [_serialize_model(item) for item in recalled_reflections],
        "session_state": _serialize_model(session_state),
        "insights": [_serialize_model(item) for item in insights],
        "thinking_steps": [_serialize_model(item) for item in thinking_steps],
        "memories": [_serialize_model(item) for item in memories],
        "reflections": [_serialize_model(item) for item in reflections],
        "turns": [_serialize_model(turn) for turn in turns],
    }


@router.post("/sessions/{session_id}/turns/stream")
async def post_agent_turn_stream(request: Request, session_id: str, payload: AgentTurnCreateRequest):
    """Stream an Agent reply via Server-Sent Events."""
    repository = _get_agent_repository(request)
    session = repository.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Agent 会话不存在")

    user_turn = repository.append_turn(session_id, role="user", content=payload.content)

    conversation_engine = _get_conversation_engine(request)
    from streaming import SSEEngine

    sse_engine = SSEEngine(conversation_engine)

    return await sse_engine.stream_reply(
        session=session,
        user_turn=user_turn,
        request=request,
    )


@router.get("/sessions/{session_id}/turns")
async def list_agent_turns(request: Request, session_id: str):
    repository = _get_agent_repository(request)
    session = repository.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Agent 会话不存在")
    return [_serialize_model(turn) for turn in repository.list_turns(session_id)]


@router.get("/sessions/{session_id}/artifacts")
async def list_agent_artifacts(request: Request, session_id: str):
    repository = _get_agent_repository(request)
    session = repository.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Agent 会话不存在")
    return [
        _serialize_model(artifact)
        for artifact in _get_artifact_service(request).list_for_session(session_id)
    ]


@router.get("/sessions/{session_id}/state")
async def get_agent_session_state(request: Request, session_id: str):
    repository = _get_agent_repository(request)
    session = repository.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Agent session not found")
    state = repository.get_session_state(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Agent session state not found")
    return _serialize_model(state)


@router.get("/sessions/{session_id}/insights")
async def list_agent_session_insights(
    request: Request,
    session_id: str,
    limit: int = Query(20, ge=1, le=100),
):
    repository = _get_agent_repository(request)
    session = repository.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Agent session not found")
    return [_serialize_model(item) for item in repository.list_insights(session_id, limit=limit)]


@router.get("/sessions/{session_id}/thinking")
async def list_agent_session_thinking(
    request: Request,
    session_id: str,
    limit: int = Query(50, ge=1, le=200),
):
    repository = _get_agent_repository(request)
    session = repository.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Agent session not found")
    return [_serialize_model(item) for item in repository.list_thinking_steps(session_id, limit=limit)]


@router.get("/sessions/{session_id}/plans")
async def list_agent_session_plans(
    request: Request,
    session_id: str,
    limit: int = Query(20, ge=1, le=100),
):
    repository = _get_agent_repository(request)
    session = repository.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Agent session not found")
    return [_serialize_model(item) for item in repository.list_execution_plans(session_id, limit=limit)]


@router.get("/sessions/{session_id}/memories")
async def list_agent_session_memories(
    request: Request,
    session_id: str,
    limit: int = Query(20, ge=1, le=100),
):
    repository = _get_agent_repository(request)
    session = repository.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Agent session not found")
    return [_serialize_model(item) for item in repository.list_memories(session_id, limit=limit)]


@router.get("/sessions/{session_id}/reflections")
async def list_agent_session_reflections(
    request: Request,
    session_id: str,
    limit: int = Query(20, ge=1, le=100),
):
    repository = _get_agent_repository(request)
    session = repository.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Agent session not found")
    return [_serialize_model(item) for item in repository.list_reflections(session_id, limit=limit)]


@router.get("/sessions/{session_id}/context")
async def get_agent_session_context(
    request: Request,
    session_id: str,
    turn_limit: int = Query(10, ge=1, le=50),
    plan_limit: int = Query(10, ge=1, le=50),
    insight_limit: int = Query(20, ge=1, le=100),
    thinking_limit: int = Query(50, ge=1, le=200),
    memory_limit: int = Query(20, ge=1, le=100),
    reflection_limit: int = Query(20, ge=1, le=100),
):
    repository = _get_agent_repository(request)
    session = repository.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Agent session not found")

    state = repository.get_session_state(session_id)
    turns = repository.list_turns(session_id)
    memories = repository.list_memories(session_id, limit=memory_limit)
    reflections = repository.list_reflections(session_id, limit=reflection_limit)
    recalled_memories = _get_memory_service(request).recall_for_session(session, limit=memory_limit)
    recalled_reflections = _get_reflection_service(request).recall_for_session(session, limit=reflection_limit)

    return {
        "session": _serialize_model(session),
        "state": _serialize_model(state) if state is not None else None,
        "turns": [_serialize_model(turn) for turn in turns[-turn_limit:]],
        "execution_plans": [
            _serialize_model(item) for item in repository.list_execution_plans(session_id, limit=plan_limit)
        ],
        "insights": [_serialize_model(item) for item in repository.list_insights(session_id, limit=insight_limit)],
        "thinking_steps": [
            _serialize_model(item) for item in repository.list_thinking_steps(session_id, limit=thinking_limit)
        ],
        "memories": [_serialize_model(item) for item in memories],
        "reflections": [_serialize_model(item) for item in reflections],
        "recalled_memories": [_serialize_model(item) for item in recalled_memories],
        "recalled_reflections": [_serialize_model(item) for item in recalled_reflections],
    }


@router.post("/workbench/save")
async def save_to_workbench(request: Request, payload: WorkbenchSaveRequest):
    """Save an Agent conversation insight to the structured workbench."""
    from services.workbench_bridge import WorkbenchBridge

    pool = request.app.state.data_manager._pool
    bridge = WorkbenchBridge(pool)
    result = await bridge.save_to_workbench(
        session_id=payload.session_id,
        turn_id=payload.turn_id,
        payload=payload.model_dump(),
    )
    return result
