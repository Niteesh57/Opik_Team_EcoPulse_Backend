"""LangGraph agent with Groq LLM, tools, and PostgreSQL persistence."""
from functools import lru_cache
from typing import Annotated, Optional, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from psycopg_pool import ConnectionPool
from pydantic import BaseModel
from langsmith import Client

client = Client()
prompt = client.pull_prompt("hwchase17/react")

from app.core.config import settings
from app.mcp.tools import APItools
from app.mcp.memory import MemoryTools

# System prompt for AI Green Sentinel
SYSTEM_PROMPT = (
    "You are the AI Green Sentinel, the conversational assistant for EcoPulse - "
    "a community-driven sustainability platform for apartment and residential communities. "
    "Your role is to help residents with sustainability topics (recycling, composting, energy saving, "
    "green initiatives) and apartment community services (facilities, staff schedules, community spaces). "
    "\n\n"
    "IMPORTANT RULES:\n"
    "1. Use the available tools to fetch user context, community info, and memories.\n"
    "2. The get_user_context tool automatically retrieves the authenticated user's information - you DO NOT need to ask for user ID.\n"
    "3. Do NOT make up or hallucinate any details about rooms, facilities, staff, or services.\n"
    "4. If asked about something you cannot find via tools, politely say you don't have that information.\n"
    "5. Be concise, friendly, and encourage sustainable living practices.\n"
    "6. When discussing facilities, reference the actual community spaces and their availability."
)


class GroqConfigurationError(RuntimeError):
    """Raised when Groq configuration is invalid."""


# --- Connection Pool ---
_pool: Optional[ConnectionPool] = None


def get_connection_pool() -> ConnectionPool:
    """Return a lazily-initialized connection pool."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=settings.DATABASE_URL,
            max_size=10,
            kwargs={"autocommit": True},
        )
    return _pool


# --- LLM Client ---
@lru_cache(maxsize=1)
def _build_llm() -> ChatGroq:
    if not settings.GROQ_API_KEY:
        raise GroqConfigurationError("GROQ_API_KEY is not configured")
    return ChatGroq(
        groq_api_key=settings.GROQ_API_KEY,
        model="openai/gpt-oss-120b",
        temperature=0.1,
        max_tokens=1024,
        max_retries=2,
    )


def get_chat_llm() -> ChatGroq:
    """Return cached Groq LLM instance."""
    return _build_llm()


# --- All Tools ---
ALL_TOOLS = APItools + MemoryTools


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def compile_react_agent_with_persistence(conn):
    """Compile a LangGraph agent with PostgreSQL checkpointer and store."""
    checkpointer = PostgresSaver(conn)
    store = PostgresStore(conn)
    checkpointer.setup()
    store.setup()

    model = get_chat_llm().bind_tools(ALL_TOOLS)

    def call_model(state: AgentState):
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            full_messages = [SystemMessage(content=SYSTEM_PROMPT), *messages]
        else:
            full_messages = messages
        response = model.invoke(full_messages)
        return {"messages": [response]}

    def should_continue(state: AgentState):
        if not state["messages"]:
            return "end"
        last = state["messages"][-1]
        tool_calls = getattr(last, "tool_calls", None)
        if tool_calls:
            return "tools"
        return "end"

    graph = StateGraph(AgentState)
    graph.add_node("llm", call_model)
    graph.add_node("tools", ToolNode(ALL_TOOLS))
    graph.add_edge(START, "llm")
    graph.add_conditional_edges(
        "llm",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        },
    )
    graph.add_edge("tools", "llm")

    agent = graph.compile(checkpointer=checkpointer, store=store)

    return agent, store




# --- Request Model ---
class ChatRequest(BaseModel):
    user_id: str
    thread_id: Optional[str] = None
    message: str


# --- Helpers ---
def create_initial_messages(user_message: str) -> list:
    """Create the initial message list with user prompt."""
    return [HumanMessage(content=user_message)]


__all__ = [
    "GroqConfigurationError",
    "SYSTEM_PROMPT",
    "get_chat_llm",
    "get_connection_pool",
    "compile_react_agent_with_persistence",
    "ChatRequest",
    "create_initial_messages",
    "ALL_TOOLS",
]



