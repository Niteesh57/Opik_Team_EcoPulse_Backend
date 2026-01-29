"""Chat session and message endpoints."""
import json
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai.groq_client import (
    GroqConfigurationError,
    get_connection_pool,
    compile_react_agent_with_persistence,
    create_initial_messages,
    ChatRequest,
)
from app.crud import user_message as user_message_crud
from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.user import User as UserModel
from app.schemas.user_message import (
    MessageSession,
    MessageSessionCreate,
    UserMessage,
    UserMessageCreate,
)


router = APIRouter()


class SessionCreateRequest(BaseModel):
    first_user_message: str = Field(..., min_length=1, description="Initial user prompt")


class SessionCreateResponse(BaseModel):
    session_id: str


class MessageCreateRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    user_message: str = Field(..., min_length=1)
    ai_message: Optional[str] = None


class FeedbackRequest(BaseModel):
    liked: Optional[bool] = None
    disliked: Optional[bool] = None


class ChatStreamRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="User query to send to Groq")
    session_id: Optional[str] = Field(
        None,
        description="Existing session identifier; create new session when omitted",
    )


def format_sse_payload(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def _extract_chunk_text(chunk: object) -> str:
    """Best-effort extraction of text from LangChain streaming chunks."""
    candidate = getattr(chunk, "content", None)
    if isinstance(candidate, list):
        candidate = "".join(str(part) for part in candidate if part)
    if isinstance(candidate, str) and candidate:
        return candidate

    message = getattr(chunk, "message", None)
    if message is not None:
        message_content = getattr(message, "content", None)
        if isinstance(message_content, list):
            message_content = "".join(str(part) for part in message_content if part)
        if isinstance(message_content, str) and message_content:
            return message_content

    return ""


@router.post("/sessions", response_model=SessionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: SessionCreateRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new chat session and seed it with the first user message."""
    first_message = _clean_text(payload.first_user_message)
    if not first_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content is empty",
        )

    session_payload = MessageSessionCreate(
        user_id=current_user.id,
        first_user_message=first_message,
    )
    session = user_message_crud.create_session(db, session_payload)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to create session",
        )

    message_payload = UserMessageCreate(
        session_id=session.session_id,
        role="user",
        user_id=current_user.id,
        user_message=first_message,
    )
    user_message_crud.create_user_message(db, message_payload)

    return SessionCreateResponse(session_id=session.session_id)


@router.post("/messages", response_model=UserMessage, status_code=status.HTTP_201_CREATED)
async def create_message(
    payload: MessageCreateRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Persist a chat exchange for an existing session."""
    session = user_message_crud.get_session(db, payload.session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    user_text = _clean_text(payload.user_message)
    ai_text = _clean_text(payload.ai_message)

    message_payload = UserMessageCreate(
        session_id=payload.session_id,
        role="user",
        user_id=current_user.id,
        user_message=user_text,
        ai_message=ai_text,
    )
    message = user_message_crud.create_user_message(db, message_payload)
    if message is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content is empty",
        )
    return message


@router.get("/sessions", response_model=List[MessageSession])
async def list_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Return paginated chat sessions for the current user."""
    return user_message_crud.get_user_sessions(db, user_id=current_user.id, skip=skip, limit=limit)


@router.get("/sessions/{session_id}", response_model=MessageSession)
async def get_session(
    session_id: str,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve session metadata."""
    session = user_message_crud.get_session(db, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return session


@router.delete("/sessions/{session_id}", status_code=status.HTTP_200_OK)
async def delete_session(
    session_id: str,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Remove a chat session and its messages."""
    deleted = user_message_crud.delete_session(db, session_id=session_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return {"message": "Session deleted"}


@router.get("/sessions/{session_id}/messages", response_model=List[UserMessage])
async def list_session_messages(
    session_id: str,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Fetch ordered chat history for a session."""
    session = user_message_crud.get_session(db, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return user_message_crud.get_session_messages(db, session_id)


@router.patch("/messages/{message_id}/feedback", response_model=UserMessage)
async def update_feedback(
    message_id: int,
    payload: FeedbackRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Toggle message like/dislike flags."""
    if payload.liked and payload.disliked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be liked and disliked simultaneously",
        )

    message = user_message_crud.get_message(db, message_id)
    if not message or message.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    updated = user_message_crud.set_feedback(db, message_id, payload.liked, payload.disliked)
    return updated



@router.post("/stream", response_class=StreamingResponse)
async def stream_chat(
    payload: ChatRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Stream LangGraph agent responses as Server-Sent Events with tool calling."""
    prompt_text = _clean_text(payload.message)
    if not prompt_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content is empty",
        )

    # Determine or create thread_id
    thread_id = payload.thread_id or str(uuid.uuid4())
    user_id_str = str(current_user.id)

    # Persist user message in our DB
    session = None
    created_session = False

    if payload.thread_id:
        session = user_message_crud.get_session(db, payload.thread_id)
        if not session or session.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
    else:
        session_payload = MessageSessionCreate(
            user_id=current_user.id,
            first_user_message=prompt_text,
        )
        session = user_message_crud.create_session(db, session_payload)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to create session",
            )
        thread_id = session.session_id
        created_session = True

    # Store user message
    message = user_message_crud.create_user_message(
        db,
        UserMessageCreate(
            session_id=session.session_id,
            role="user",
            user_id=current_user.id,
            user_message=prompt_text,
        ),
    )
    if message is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content is empty",
        )

    session_id_value = session.session_id
    message_id_value = message.id
    current_user_id = current_user.id

    def event_stream():
        ai_chunks: list[str] = []
        assistant_message_id: Optional[int] = None
        current_step: Optional[str] = None

        # 1. Send Initial Session Info
        yield format_sse_payload({
            "event": "session",
            "session_id": session_id_value,
            "message_id": message_id_value,
            "thread_id": thread_id,
            "created_session": created_session,
        })

        try:
            pool = get_connection_pool()
            with pool.connection() as conn:
                agent, store = compile_react_agent_with_persistence(conn)

                config = {
                    "configurable": {
                        "thread_id": thread_id,
                        "user_id": user_id_str,
                    }
                }

                initial_messages = create_initial_messages(prompt_text)
                tool_descriptions = {
                    "get_user_context": "Fetching user profile",
                    "get_community_context": "Loading community details",
                    "get_all_communities_context": "Retrieving all communities",
                    "save_memory": "Saving to memory",
                    "remove_memory": "Removing from memory",
                    "list_memories": "Reading memories",
                }

                # Track what we've already sent to compute deltas
                sent_content_length = 0
                seen_tool_calls = set()
                seen_tool_results = set()

                # stream_mode="values" yields full state snapshots
                for state in agent.stream(
                    {"messages": initial_messages},
                    config,
                    stream_mode="values",
                ):
                    messages = state.get("messages", [])
                    if not messages:
                        continue

                    # Process each message in the state
                    for msg in messages:
                        msg_type = getattr(msg, "type", "")
                        msg_id = getattr(msg, "id", id(msg))

                        # Handle tool calls from AI messages
                        tool_calls = getattr(msg, "tool_calls", None)
                        if tool_calls:
                            for tc in tool_calls:
                                tc_id = tc.get("id") or tc.get("name", "")
                                if tc_id in seen_tool_calls:
                                    continue
                                seen_tool_calls.add(tc_id)

                                if current_step != "reasoning":
                                    yield format_sse_payload({
                                        "event": "status",
                                        "status": "reasoning",
                                        "message": "Analyzing your request...",
                                    })
                                    current_step = "reasoning"

                                yield format_sse_payload({
                                    "event": "tool_start",
                                    "tool": tc.get("name"),
                                    "description": tool_descriptions.get(tc.get("name"), "Executing tool"),
                                    "args": tc.get("args"),
                                })
                                current_step = "tool"

                        # Handle tool result messages
                        if msg_type == "tool":
                            tool_call_id = getattr(msg, "tool_call_id", msg_id)
                            if tool_call_id in seen_tool_results:
                                continue
                            seen_tool_results.add(tool_call_id)

                            preview = str(getattr(msg, "content", ""))[:200]
                            yield format_sse_payload({
                                "event": "tool_end",
                                "tool": getattr(msg, "name", "tool"),
                                "result_preview": preview,
                            })
                            continue

                    # Get final AI message content for streaming
                    last_msg = messages[-1]
                    if getattr(last_msg, "type", "") == "ai" and not getattr(last_msg, "tool_calls", None):
                        content = getattr(last_msg, "content", "")
                        if isinstance(content, list):
                            content = "".join(
                                c.get("text", "") if isinstance(c, dict) else str(c)
                                for c in content
                            )

                        if content and len(content) > sent_content_length:
                            if current_step != "writing":
                                yield format_sse_payload({
                                    "event": "status",
                                    "status": "writing",
                                    "message": "Writing answer...",
                                })
                                current_step = "writing"

                            # Send only the new portion
                            delta = content[sent_content_length:]
                            sent_content_length = len(content)
                            ai_chunks.append(delta)
                            yield format_sse_payload({"delta": delta})

        except Exception as exc:
            yield format_sse_payload({"error": str(exc)})
            return

        # 3. Finalize and Store
        ai_message = "".join(ai_chunks).strip()
        if ai_message:
            assistant_msg = user_message_crud.create_user_message(
                db,
                UserMessageCreate(
                    session_id=session_id_value,
                    role="assistant",
                    user_id=current_user_id,
                    ai_message=ai_message,
                ),
            )
            assistant_message_id = assistant_msg.id if assistant_msg else None

        yield format_sse_payload({
            "event": "end",
            "session_id": session_id_value,
            "message_id": message_id_value,
            "assistant_message_id": assistant_message_id,
        })

    return StreamingResponse(event_stream(), media_type="text/event-stream")