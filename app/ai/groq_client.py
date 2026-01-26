"""Utilities for interacting with Groq chat models."""

from functools import lru_cache
from typing import Iterable

from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

from app.core.config import settings

SYSTEM_PROMPT = (
    "You are the AI Green Sentinel, the conversational assistant for EcoPulse - "
    "a community-driven sustainability platform for apartment and residential communities. "
    "Your role is to help residents with sustainability topics (recycling, composting, energy saving, "
    "green initiatives) and apartment community services (facilities, staff schedules, community spaces). "
    "\n\n"
    "IMPORTANT RULES:\n"
    "1. ONLY use information from the 'User Context' and 'Room Context' sections provided below.\n"
    "2. Do NOT make up or hallucinate any details about rooms, facilities, staff, or services.\n"
    "3. If asked about something not in the provided context, politely say you don't have that information.\n"
    "4. Be concise, friendly, and encourage sustainable living practices.\n"
    "5. When discussing facilities, reference the actual community spaces and their availability."
)


class GroqConfigurationError(RuntimeError):
    """Raised when Groq configuration is invalid."""


@lru_cache(maxsize=1)
def _build_client() -> ChatGroq:
    if not settings.GROQ_API_KEY:
        raise GroqConfigurationError("GROQ_API_KEY is not configured")

    return ChatGroq(
        groq_api_key=settings.GROQ_API_KEY,
        model="openai/gpt-oss-120b",
        temperature=0.1,
        max_tokens=1000,
        reasoning_format="parsed",
        max_retries=2,
    )


def get_chat_client() -> ChatGroq:
    """Return a cached Groq ChatGroq instance."""
    return _build_client()


def build_prompt(user_context: str, room_context: str, user_prompt: str) -> str:
    """Build a grounded prompt with user and room context."""
    sections: list[str] = [SYSTEM_PROMPT]
    if user_context.strip():
        sections.append(f"User Context:\n{user_context.strip()}")
    if room_context.strip():
        sections.append(f"Room Context:\n{room_context.strip()}")
    sections.append(f"User Question:\n{user_prompt.strip()}")
    return "\n\n".join(sections)


def stream_chat_completion(prompt: str) -> Iterable:
    """Return a streaming iterator for the given prompt."""
    client = get_chat_client()
    return client.stream([HumanMessage(content=prompt)])


__all__ = [
    "GroqConfigurationError",
    "SYSTEM_PROMPT",
    "build_prompt",
    "stream_chat_completion",
    "get_chat_client",
]
