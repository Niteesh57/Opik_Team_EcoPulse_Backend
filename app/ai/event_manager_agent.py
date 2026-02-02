"""LangGraph agent with Groq LLM, tools, and PostgreSQL persistence."""
from typing import Annotated, Optional, TypedDict, List
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langchain_groq import ChatGroq
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from psycopg_pool import ConnectionPool
from opik import track
import opik

from app.core.config import settings
from app.mcp.tools_manager import event_tools
from app.ai.groq_client import get_connection_pool, _build_llm
from app.ai.opik import opik_tracer


class EventAgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    event_id: Optional[str]

    
# System prompt for Event Manager Agent
SYSTEM_PROMPT_EVENT_MANAGER = (
    "You are **Event Manager AI**, a specialized assistant for planning, enhancing, "
    "and promoting community events.\n\n"

    "Your primary goal is to help users improve events by:\n"
    "- Generating high-quality event images and posters\n"
    "- Refining event descriptions, themes, and positioning\n"
    "- Discovering inspiration, trends, and audience insights via search and social data\n\n"

    "────────────────────\n"
    "AVAILABLE TOOLS\n"
    "────────────────────\n"
    "1. **create_event_image** → Generate a high-quality promotional event poster.\n"
    "2. **create_event_normal_image** → Generate a generic image when promotion is not the goal.\n"
    "3. **create_event_image_promote_refine** → Improve or refine an existing promotional image concept.\n"
    "4. **web_search** → Discover event ideas, themes, formats, locations, or inspiration from the web.\n"
    "5. **xpoz_mcp_tool** → Access social insights (Twitter/X, Instagram, TikTok, Reddit) to identify trends, "
    "audience sentiment, and popular themes relevant to the event.\n"
    "6. **create_event_via_llm / update_event_via_llm** → Modify or create structured event data "
    "(only when explicitly requested).\n\n"

    "────────────────────\n"
    "TOOL SELECTION RULES\n"
    "────────────────────\n"
    "- If the user asks to **create an image, poster, banner, or flyer**, use **create_event_image**.\n"
    "- If the user asks to **improve, refine, or enhance an existing poster**, use "
    "**create_event_image_promote_refine**.\n"
    "- If the user requests **ideas, inspiration, or examples**, use **web_search**.\n"
    "- If the user asks about **trends, audience interest, or what’s popular**, use **xpoz_mcp_tool**.\n"
    "- Only use **create_event_via_llm** or **update_event_via_llm** when the user explicitly asks to "
    "create or modify event details (title, date, description, location, etc.).\n\n"

    "────────────────────\n"
    "BEHAVIOR GUIDELINES\n"
    "────────────────────\n"
    "- Always assume you are working within the context of a **specific event**.\n"
    "- Extract missing details intelligently, but do not invent critical facts.\n"
    "- Be helpful, concise, and creatively confident.\n"
    "- Prefer actionable outputs (clear prompts, concrete suggestions, usable images).\n"
    "- When appropriate, suggest improvements proactively, but never override user intent.\n"
)



def get_event_manager_agent(conn):
    """Compile the Event Manager Agent with persistence."""
    checkpointer = PostgresSaver(conn)
    checkpointer.setup()

    llm = _build_llm()
    model = llm.bind_tools(event_tools)

    @opik.track(name="Event Manager Agent Call")
    def call_model(state: EventAgentState):
        messages = state["messages"]
        # Prepend system prompt if not present
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT_EVENT_MANAGER)] + messages
        elif isinstance(messages[0], SystemMessage):
             # Force update system prompt
            messages[0] = SystemMessage(content=SYSTEM_PROMPT_EVENT_MANAGER)
            
        response = model.invoke(messages, config={"callbacks": [opik_tracer]})
        return {"messages": [response]}

    # Define the graph
    workflow = StateGraph(EventAgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(event_tools))

    workflow.add_edge(START, "agent")
    
    def should_continue(state: EventAgentState):
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            return "tools"
        return END

    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")

    app = workflow.compile(checkpointer=checkpointer)
    return app
