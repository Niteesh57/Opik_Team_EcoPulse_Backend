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
from opik import track
import opik

client = Client()
prompt = client.pull_prompt("hwchase17/react")

from app.core.config import settings
from app.mcp.tools import APItools
from app.mcp.memory import MemoryTools
from app.ai.event_agent import build_event_subgraph, EventAgentState
from app.ai.opik import opik_tracer

# System prompt for AI Green Sentinel
SYSTEM_PROMPT = (
    "You are the AI Green Sentinel, the conversational assistant for EcoPulse - "
    "a community-driven sustainability platform for apartment and residential communities. "
    "Your role is to help residents with sustainability topics (recycling, composting, energy saving, "
    "green initiatives) and apartment community services (facilities, staff schedules, community spaces). "
    "\n\n"
    "CRITICAL RULES FOR TOOL USAGE:\n"
    "1. For greetings like 'hi', 'hello', 'hey', asking 'what is your name', 'who are you', or general chitchat: "
    "DO NOT call ANY tools. Respond directly and immediately.\n"
    "2. ONLY use tools when you MUST fetch information that is NOT already provided in your context.\n"
    "3. If user/community context is already in your system prompt, DO NOT call get_user_context or get_community_context.\n"
    "4. Do NOT make up or hallucinate any details about rooms, facilities, staff, or services.\n"
    "5. If asked about something you cannot find, politely say you don't have that information.\n"
    "6. Be concise, friendly, and encourage sustainable living practices.\n"
    "7. When discussing facilities, reference the actual community spaces and their availability.\n"
    "8. IF the user wants to CREATE an event, use the 'start_event_creation' tool. "
    "This will start a specialized workflow that collects all event details step-by-step.\n"
    "9. IF the user wants to UPDATE an existing event (add tag, change description, etc.), "
    "use the 'update_event_via_llm' tool with the event_id and the fields to update.\n"
    "10. CRITICAL: IF the user expresses a need for REAL-WORLD assistance (e.g., picking up food/kids, moving furniture, walking dog, emergency), "
    "DO NOT give generic advice. IMMEDIATELY use the 'broadcast_neighbor_help' tool to notify neighbors. "
    "Example: User says 'I need someone to pick up my food', You call 'broadcast_neighbor_help' with 'I need someone to pick up my food order from the gate'.\n"
    "11. Use the 'web_search' tool to find current information about sustainability, recycling guidelines, "
    "environmental news, or any topic you don't have direct knowledge of."
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
        model="openai/gpt-oss-20b",
        temperature=0.1,
        max_tokens=1024,
        max_retries=2,
        callbacks=[opik_tracer],
    )


def get_chat_llm() -> ChatGroq:
    """Return cached Groq LLM instance."""
    return _build_llm()


# --- All Tools ---
# Include all API tools + Memory tools
ALL_TOOLS = APItools + MemoryTools


class AgentState(EventAgentState):
    # Inherit from EventAgentState so we have all fields
    # messages is already in EventAgentState
    thread_id: Optional[str]


def compile_react_agent_with_persistence(conn, user_id=None):
    """Compile a LangGraph agent with PostgreSQL checkpointer and store.
    If user_id is provided, pre-fetch context and inject into system prompt.
    """
    checkpointer = PostgresSaver(conn)
    store = PostgresStore(conn)
    checkpointer.setup()
    store.setup()

    # --- Pre-fetch Context if User ID is present ---
    dynamic_system_prompt = SYSTEM_PROMPT
    
    if user_id:
        try:
            from app.mcp.tools import build_user_context, build_community_context
            from app.database import SessionLocal
            from app.crud import user as user_crud
            
            # Fetch User Context
            user_context = build_user_context(int(user_id))
            
            # Fetch Community Context (if user has a room)
            community_context = ""
            with SessionLocal() as db:
                user_obj = user_crud.get_user_by_id(db, int(user_id))
                if user_obj and user_obj.user_rooms:
                    # Use the first room's community context
                    first_room_id = user_obj.user_rooms[0].room_id
                    community_context = build_community_context(first_room_id)
            
            combined_context = (
                f"\n\n"
                f"========== PRE-LOADED CONTEXT (USE THIS - DO NOT FETCH AGAIN) ==========\n"
                f"{user_context}\n\n"
                f"{community_context}\n"
                f"==========================================================================\n\n"
                f"IMPORTANT: The user and community context above is ALREADY LOADED. "
                f"You MUST NOT call 'get_user_context', 'get_community_context', or 'get_all_communities_context' "
                f"because you already have this information. Use it directly to answer questions."
            )
            dynamic_system_prompt += combined_context
        except Exception as e:
            print(f"Error injecting context: {e}")

    model = get_chat_llm().bind_tools(ALL_TOOLS)

    @opik.track(name="Groq React Agent Call")
    def call_model(state: AgentState):
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            full_messages = [SystemMessage(content=dynamic_system_prompt), *messages]
        else:
            # If the first message is system, make sure it is OUR dynamic prompt
            # But the state persistence might load the OLD prompt if we are resuming?
            # Actually, standard pattern is to prepend system prompt if not present, but 
            # if we resume a thread, the history has messages.
            # ReAct agent usually treats the system prompt as ephemeral or part of the run.
            # We will force the first message to be our dynamic prompt if it's a SystemMessage, or insert it.
            
            if isinstance(messages[0], SystemMessage):
                 # Replace the existing system prompt with the fresh one (in case context changed)
                full_messages = [SystemMessage(content=dynamic_system_prompt)] + messages[1:]
            else:
                full_messages = [SystemMessage(content=dynamic_system_prompt)] + messages

        metadata = {}
        thread_id = state.get("thread_id")
        if thread_id:
            metadata["thread_id"] = thread_id

        invoke_config = {"callbacks": [opik_tracer]}
        if metadata:
            invoke_config["metadata"] = metadata

        response = model.invoke(full_messages, config=invoke_config)
        return {"messages": [response]}

    def route_step(state: AgentState):
        if not state["messages"]:
            return "end"
        last = state["messages"][-1]
        
        # Check for tool calls
        if hasattr(last, "tool_calls") and last.tool_calls:
            # Check for specific event start tool
            if any(tc["name"] == "start_event_creation" for tc in last.tool_calls):
                return "event_manager"
            return "tools"
        return "end"

    # Compile the event subgraph
    event_workflow = build_event_subgraph()
    
    # We define the interrupt points where we wait for human input.
    # We interrupt BEFORE the nodes that process the human's response.
    event_agent = event_workflow.compile(
        interrupt_before=[
            "handle_feedback", 
            "handle_place", 
            "handle_date", 
            "handle_type"
        ]
    ) 

    graph = StateGraph(AgentState)
    graph.add_node("llm", call_model)
    graph.add_node("tools", ToolNode(ALL_TOOLS))
    
    # Add the event subgraph as a node
    graph.add_node("event_manager", event_agent)

    graph.add_edge(START, "llm")
    
    graph.add_conditional_edges(
        "llm",
        route_step,
        {
            "tools": "tools",
            "event_manager": "event_manager",
            "end": END,
        },
    )
    graph.add_edge("tools", "llm")
    graph.add_edge("event_manager", END) # After event flow finishes, we end (or loop back to llm?)

    # IMPORTANT: We need to define interrupts for the PARENT graph if the child has them?
    # No, if 'event_agent' is a compiled graph Node, LangGraph handles it.
    # However, 'interrupt_before' works on nodes.
    # The event_agent returns a Runnable.
    # We need to make sure the checkpoints are passed down.
    
    agent = graph.compile(
        checkpointer=checkpointer, 
        store=store,
        # We might need to expose the interrupt points of the subgraph?
        # If the subgraph interrupts, the parent 'event_manager' node is effectively paused.
        # But for 'human in the loop', the user needs to invoke again.
    )

    return agent, store




# --- Request Model ---
class ChatRequest(BaseModel):
    user_id: Optional[str] = None
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

