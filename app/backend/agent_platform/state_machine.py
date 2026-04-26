"""
Minimal shared state helpers for agent sessions.
"""

from __future__ import annotations

AGENT_SESSION_STATUS_ACTIVE = "active"
AGENT_SESSION_STATUS_PAUSED = "paused"
AGENT_SESSION_STATUS_COMPLETED = "completed"
AGENT_SESSION_STATUS_ERROR = "error"

VALID_AGENT_SESSION_STATUSES = {
    AGENT_SESSION_STATUS_ACTIVE,
    AGENT_SESSION_STATUS_PAUSED,
    AGENT_SESSION_STATUS_COMPLETED,
    AGENT_SESSION_STATUS_ERROR,
}

TERMINAL_AGENT_SESSION_STATUSES = {
    AGENT_SESSION_STATUS_COMPLETED,
    AGENT_SESSION_STATUS_ERROR,
}

VALID_AGENT_TURN_ROLES = {"system", "user", "assistant", "tool"}


class InvalidAgentSessionState(ValueError):
    """Raised when an unknown session state is used."""


class InvalidAgentTurnRole(ValueError):
    """Raised when an unknown turn role is used."""


class InvalidAgentSessionTransition(ValueError):
    """Raised when a session transition is not allowed."""


def default_session_status() -> str:
    return AGENT_SESSION_STATUS_ACTIVE


def validate_session_status(status: str) -> str:
    if status not in VALID_AGENT_SESSION_STATUSES:
        raise InvalidAgentSessionState(f"Unsupported agent session status: {status}")
    return status


def validate_turn_role(role: str) -> str:
    if role not in VALID_AGENT_TURN_ROLES:
        raise InvalidAgentTurnRole(f"Unsupported agent turn role: {role}")
    return role


def ensure_session_allows_turns(status: str) -> None:
    validate_session_status(status)
    if status in TERMINAL_AGENT_SESSION_STATUSES:
        raise InvalidAgentSessionTransition(f"Cannot append turns to session in status '{status}'")


def transition_session_status(current_status: str, next_status: str) -> str:
    current_status = validate_session_status(current_status)
    next_status = validate_session_status(next_status)

    if current_status == next_status:
        return next_status

    allowed_transitions = {
        AGENT_SESSION_STATUS_ACTIVE: {
            AGENT_SESSION_STATUS_PAUSED,
            AGENT_SESSION_STATUS_COMPLETED,
            AGENT_SESSION_STATUS_ERROR,
        },
        AGENT_SESSION_STATUS_PAUSED: {
            AGENT_SESSION_STATUS_ACTIVE,
            AGENT_SESSION_STATUS_COMPLETED,
            AGENT_SESSION_STATUS_ERROR,
        },
        AGENT_SESSION_STATUS_COMPLETED: set(),
        AGENT_SESSION_STATUS_ERROR: set(),
    }

    if next_status not in allowed_transitions[current_status]:
        raise InvalidAgentSessionTransition(
            f"Cannot transition session from '{current_status}' to '{next_status}'"
        )

    return next_status
