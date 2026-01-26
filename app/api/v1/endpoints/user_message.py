"""Chat session and message endpoints."""
import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai.groq_client import (
    GroqConfigurationError,
    build_prompt,
    stream_chat_completion,
)
from app.crud import user_message as user_message_crud
from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.user import User as UserModel
from app.mcp.tools import build_user_context
from app.schemas.user_message import (
    MessageSession,
    MessageSessionCreate,
    UserMessage,
    UserMessageCreate,
)

logger = logging.getLogger("app.user_messages")

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

    logger.info("Creating chat session for user %s", current_user.id)
    session_payload = MessageSessionCreate(
        user_id=current_user.id,
        first_user_message=first_message,
    )
    session = user_message_crud.create_session(db, session_payload)
    if session is None:
        logger.error("Failed to create chat session for user %s", current_user.id)
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
    logger.info("Stored message %s for session %s", message.id, payload.session_id)
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
    logger.info("Updated feedback for message %s", message_id)
    return updated


@router.post("/stream", response_class=StreamingResponse)
async def stream_chat(
    payload: ChatStreamRequest,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Stream Groq model responses as Server-Sent Events."""
    prompt_text = _clean_text(payload.prompt)
    if not prompt_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content is empty",
        )

    session = None
    created_session = False
    if payload.session_id:
        session = user_message_crud.get_session(db, payload.session_id)
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
        created_session = True

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
    user_id_value = current_user.id
    user_context_text = build_user_context(user_id_value)
    prompt_with_context = build_prompt(user_context_text, prompt_text)

    try:
        groq_stream = stream_chat_completion(prompt_with_context)
    except GroqConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    def event_stream():
        ai_chunks: list[str] = []
        assistant_message_id: Optional[int] = None

        yield format_sse_payload(
            {
                "event": "session",
                "session_id": session_id_value,
                "message_id": message_id_value,
                "created_session": created_session,
            }
        )

        try:
            for chunk in groq_stream:
                token = _extract_chunk_text(chunk)
                if not token:
                    continue

                ai_chunks.append(token)
                yield format_sse_payload({"delta": token})
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Groq streaming failed for session %s", session_id_value)
            yield format_sse_payload({"error": str(exc)})
            return
        else:
            ai_message = "".join(ai_chunks).strip()
            if ai_message:
                assistant_message = user_message_crud.create_user_message(
                    db,
                    UserMessageCreate(
                        session_id=session_id_value,
                        role="assistant",
                        user_id=user_id_value,
                        ai_message=ai_message,
                    ),
                )
                assistant_message_id = assistant_message.id if assistant_message else None
            yield format_sse_payload(
                {
                    "event": "end",
                    "session_id": session_id_value,
                    "message_id": message_id_value,
                    "assistant_message_id": assistant_message_id,
                }
            )

    return StreamingResponse(event_stream(), media_type="text/event-stream")
