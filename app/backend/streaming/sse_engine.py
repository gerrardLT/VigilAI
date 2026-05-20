"""Server-Sent Events streaming engine for Agent conversation responses.

Streams tool status updates and text chunks via FastAPI StreamingResponse,
providing real-time feedback to the frontend during Agent processing.

Validates: Requirements 13.1, 13.4, 13.5
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

from fastapi import Request
from fastapi.responses import StreamingResponse

if TYPE_CHECKING:
    from agent_platform.conversation_engine import ConversationEngine
    from agent_platform.models import AgentSession, AgentTurn


class SSEEngine:
    """Streams Agent replies as Server-Sent Events.

    Accepts a ConversationEngine instance and produces a FastAPI
    StreamingResponse with media_type="text/event-stream". Events are
    emitted in order: start → tool_start/tool_done → text chunks → done.
    On error, an error event is sent and the stream closes.
    """

    def __init__(self, conversation_engine: "ConversationEngine"):
        self.conversation_engine = conversation_engine

    async def stream_reply(
        self,
        *,
        session: "AgentSession",
        user_turn: "AgentTurn",
        request: Request,
    ) -> StreamingResponse:
        """Build and return a StreamingResponse that emits SSE events.

        Args:
            session: The active agent session.
            user_turn: The user's message turn.
            request: The FastAPI request (used for disconnect detection).

        Returns:
            A StreamingResponse with media_type="text/event-stream".
        """

        async def event_generator():
            try:
                # 1. Initial acknowledgment
                yield self._format_event({"type": "start"})

                # Execute the conversation engine reply
                reply = self.conversation_engine.reply(
                    session=session, user_turn=user_turn
                )

                # 2. Stream tool execution status
                for tool_call in reply.tool_calls:
                    if await request.is_disconnected():
                        return
                    tool_name = tool_call.get("tool_name", "")
                    yield self._format_event(
                        {"type": "tool_start", "tool": tool_name}
                    )
                    yield self._format_event(
                        {"type": "tool_done", "tool": tool_name}
                    )

                # 3. Stream text in ~50 character chunks with typewriter delay
                for chunk in self._split_text(reply.assistant_turn):
                    if await request.is_disconnected():
                        return
                    yield self._format_event({"type": "text", "content": chunk})
                    await asyncio.sleep(0.02)  # 20ms delay for typewriter effect

                # 4. Completion signal
                yield self._format_event(
                    {"type": "done", "session_id": session.id}
                )

            except Exception as e:
                # 5. Error event
                yield self._format_event(
                    {"type": "error", "message": str(e)}
                )

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @staticmethod
    def _format_event(data: dict) -> str:
        """Format a dict as an SSE data line: `data: {json}\\n\\n`."""
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    @staticmethod
    def _split_text(text: str, chunk_size: int = 50) -> list[str]:
        """Split text into chunks of approximately `chunk_size` characters."""
        if not text:
            return []
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
