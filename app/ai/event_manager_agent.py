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

from app.core.config import settings
from app.mcp.tools_manager import event_tools
from app.ai.groq_client import get_connection_pool, _build_llm

class EventAgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    event_id: Optional[str]

    
# System prompt for Event Manager Agent
SYSTEM_PROMPT_EVENT_MANAGER = (
    "You are the 'Event Manager AI', a specialized assistant for managing community events. "
    "Your role is to help users enhance their events by generating images, refining details, "
    "and finding inspiration via web search.\n\n"
    "TOOLS AVAILABLE:\n"
    "1. 'create_event_image': Generate a specialized event poster/promotional image.\n"
    "2. 'create_event_normal_image': Generate a standard image for other purposes.\n"
    "3. 'create_event_image_promote_refine': Similar to create_event_image but implies a refinement process.\n"
    "4. 'web_search': Search the web for event ideas, themes, or info.\n"
    "5. 'create_event_via_llm' / 'update_event_via_llm': Tools to modify the event structure itself if asked.\n\n"
    "BEHAVIOR:\n"
    "- If asked to 'create an image' or 'make a poster', use 'create_event_image'. Extract a good prompt from the user's request.\n"
    "- If asked to 'search for ideas', use 'web_search'.\n"
    "- Be helpful, concise, and creative.\n"
    "- Always assume you are working within the context of a specific event."
)


def get_event_manager_agent(conn):
    """Compile the Event Manager Agent with persistence."""
    checkpointer = PostgresSaver(conn)
    checkpointer.setup()

    llm = _build_llm()
    model = llm.bind_tools(event_tools)

    def call_model(state: EventAgentState):
        messages = state["messages"]
        # Prepend system prompt if not present
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT_EVENT_MANAGER)] + messages
        elif isinstance(messages[0], SystemMessage):
             # Force update system prompt
            messages[0] = SystemMessage(content=SYSTEM_PROMPT_EVENT_MANAGER)
            
        response = model.invoke(messages)
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
