"""Utilities for interacting with Groq chat models."""
import logging
from functools import lru_cache
from typing import Iterable

from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

from app.core.config import settings

logger = logging.getLogger("app.ai.groq")

SYSTEM_PROMPT = (
    "You are the virtual concierge for OPIK. Provide concise, helpful and friendly "
    "answers about apartment living, community rooms, maintenance, and resident services."
)


class GroqConfigurationError(RuntimeError):
    """Raised when Groq configuration is invalid."""


@lru_cache(maxsize=1)
def _build_client() -> ChatGroq:
    if not settings.GROQ_API_KEY:
        raise GroqConfigurationError("GROQ_API_KEY is not configured")

    logger.info("Initializing Groq chat client using model openai/gpt-oss-120b")
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


def build_prompt(user_context: str, user_prompt: str) -> str:
    sections: list[str] = [SYSTEM_PROMPT]
    if user_context.strip():
        sections.append(f"User Context:\n{user_context.strip()}")
    sections.append(f"User:\n{user_prompt.strip()}")
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
