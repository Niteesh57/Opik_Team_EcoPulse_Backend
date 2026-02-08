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
from opik.integrations.langchain import track_langgraph, OpikTracer

from app.core.config import settings
from app.mcp.tools_manager import event_tools
from app.ai.groq_client import get_connection_pool, _build_llm
from app.ai.prompts import EVENT_MANAGER_SYSTEM_PROMPT


class EventAgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    event_id: Optional[str]
    thread_id: Optional[str]



def get_event_manager_agent(conn):
    """Compile the Event Manager Agent with persistence."""
    from app.core.config import settings
    # We need to import the savers specifically for SQLite vs Postgres
    from langgraph.checkpoint.postgres import PostgresSaver
    from langgraph.checkpoint.sqlite import SqliteSaver

    if settings.DATABASE_URL.startswith("sqlite"):
        checkpointer = SqliteSaver(conn)
    else:
        checkpointer = PostgresSaver(conn)
        
    checkpointer.setup()

    llm = _build_llm()
    model = llm.bind_tools(event_tools)

    def _build_invoke_config(state: EventAgentState) -> dict:
        # We'll use a default tracer here since opik_tracer is created later
        from app.ai.opik import opik_tracer as default_tracer
        config = {"callbacks": [default_tracer]}
        thread_id = state.get("thread_id")
        if thread_id:
            config["metadata"] = {"thread_id": thread_id}
        return config

    @opik.track(name="Event Manager Agent Call")
    def call_model(state: EventAgentState):
        messages = state["messages"]
        # Prepend system prompt if not present
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=EVENT_MANAGER_SYSTEM_PROMPT.prompt)] + messages
        elif isinstance(messages[0], SystemMessage):
             # Force update system prompt
            messages[0] = SystemMessage(content=EVENT_MANAGER_SYSTEM_PROMPT.prompt)
            
        response = model.invoke(messages, config=_build_invoke_config(state))
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
    opik_tracer = OpikTracer(graph=app.get_graph(xray=True))
    app = track_langgraph(app, opik_tracer)
    return app
