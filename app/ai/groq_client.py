"""LangGraph agent with Groq LLM, tools, and PostgreSQL persistence."""
from functools import lru_cache
from typing import Annotated, Optional, TypedDict
from datetime import datetime

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
from opik import opik_context
from opik.integrations.langchain import track_langgraph, OpikTracer

client = Client()
prompt = client.pull_prompt("hwchase17/react")

from app.core.config import settings
from app.mcp.tools import APItools
from app.mcp.memory import MemoryTools
from app.mcp.social_media_tools import SocialMediaTools
from app.ai.event_agent import build_event_subgraph, EventAgentState
from app.ai.opik import (
    opik_tracer,
    track_agent_call,
    track_llm_generation,
    feedback_collector,
    PerformanceMonitor,
    ConversationAnalytics,
    SustainabilityRelevance,
    CommunityEngagement,
    ResponseQuality,
)
from app.ai.prompts import GREEN_SENTINEL_SYSTEM_PROMPT

# Custom evaluation metrics instances
sustainability_metric = SustainabilityRelevance()
engagement_metric = CommunityEngagement()
quality_metric = ResponseQuality()

# System prompt for AI Green Sentinel
SYSTEM_PROMPT = GREEN_SENTINEL_SYSTEM_PROMPT.prompt


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
# Include all API tools + Memory tools + Social Media tools
ALL_TOOLS = APItools + MemoryTools + SocialMediaTools


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

    @track_agent_call(agent_name="Green Sentinel", agent_type="conversational")
    def call_model(state: AgentState):
        """Main agent call with comprehensive Opik tracking."""
        start_time = datetime.now()
        messages = state["messages"]
        
        if not messages or not isinstance(messages[0], SystemMessage):
            full_messages = [SystemMessage(content=dynamic_system_prompt), *messages]
        else:
            if isinstance(messages[0], SystemMessage):
                full_messages = [SystemMessage(content=dynamic_system_prompt)] + messages[1:]
            else:
                full_messages = [SystemMessage(content=dynamic_system_prompt)] + messages

        metadata = {
            "agent": "Green Sentinel",
            "model": "groq/openai-gpt-oss-20b",
            "timestamp": datetime.now().isoformat(),
            "message_count": len(messages),
            "task_type": "conversational_response"
        }
        thread_id = state.get("thread_id")
        if thread_id:
            metadata["thread_id"] = thread_id

        invoke_config = {"callbacks": [opik_tracer], "metadata": metadata}

        response = model.invoke(full_messages, config=invoke_config)
        
        # Calculate latency and track performance
        latency_ms = (datetime.now() - start_time).total_seconds() * 1000
        PerformanceMonitor.record_latency(
            operation="agent_call",
            latency_ms=latency_ms,
            success=True,
            metadata={"thread_id": thread_id, "message_count": len(messages)}
        )
        
        # Evaluate response quality with custom metrics
        if hasattr(response, 'content') and response.content:
            response_text = response.content
            
            # Run custom evaluation metrics
            sustainability_score = sustainability_metric.score(response_text)
            engagement_score = engagement_metric.score(response_text)
            quality_scores = quality_metric.score(response_text)
            
            # Determine if task was completed based on response
            has_tool_calls = hasattr(response, 'tool_calls') and response.tool_calls
            task_completed = not has_tool_calls or any(tc.get("name") in ["create_event_via_llm", "update_event_via_llm"] for tc in (response.tool_calls or []))
            
            # Track evaluation results in Opik (metadata only, no auto-feedback)
            try:
                opik_context.update_current_trace(
                    metadata={
                        "task_completed": task_completed,
                        "has_tool_calls": has_tool_calls,
                        "evaluation_metrics": {
                            "sustainability_relevance": sustainability_score,
                            "community_engagement": engagement_score,
                            "response_quality": quality_scores,
                            "latency_ms": latency_ms
                        },
                        "response_length": len(response_text)
                    }
                )
            except Exception as e:
                print(f"Error updating evaluation metrics: {e}")
        
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
        
        # Check if this is a task completion (no tool calls = final response)
        # Only ask for feedback when task is completed
        if len(state["messages"]) > 5:  # At least system + user + response
            # This is a final response to user's request - ask for feedback
            return "ask_feedback"
        
        return "end"
    
    def ask_feedback_node(state: AgentState):
        """Ask user for feedback on the AI response."""
        return {
            "messages": [
                HumanMessage(
                    content="[Feedback UI: Did you find this response helpful? Please rate or provide feedback]"
                )
            ]
        }
    
    def handle_feedback_node(state: AgentState):
        """Handle and record user feedback on AI response with comprehensive Opik tracking."""
        thread_id = state.get("thread_id")
        
        # Record feedback using the enhanced FeedbackCollector
        try:
            # Get the last user message (their feedback)
            feedback_text = ""
            if state["messages"]:
                last_msg = state["messages"][-1]
                if hasattr(last_msg, 'content'):
                    feedback_text = last_msg.content.lower()
            
            # Analyze sentiment from feedback text
            positive_signals = ["good", "great", "helpful", "thanks", "perfect", "awesome", "excellent", "exactly", "yes"]
            negative_signals = ["bad", "wrong", "unhelpful", "incorrect", "no", "not helpful", "terrible", "poor"]
            
            is_positive = any(signal in feedback_text for signal in positive_signals)
            is_negative = any(signal in feedback_text for signal in negative_signals)
            
            # Record comprehensive feedback after task completion
            if is_positive:
                feedback_collector.record_comprehensive_feedback(
                    thread_id=thread_id or "unknown",
                    scores={
                        "helpful": 0.9,
                        "accurate": 0.85,
                        "relevant": 0.9,
                        "actionable": 0.8,
                        "satisfaction": 0.9
                    },
                    overall_comment=f"User positive feedback on task completion: {feedback_text[:150]}"
                )
                
                # Update Opik trace with positive completion feedback
                try:
                    opik_context.update_current_trace(
                        metadata={
                            "feedback_sentiment": "positive",
                            "feedback_text": feedback_text[:200],
                            "task_completion_feedback": True,
                            "timestamp": datetime.now().isoformat()
                        },
                        feedback_scores=[
                            {"name": "user_satisfaction", "value": 0.9, "reason": "User provided positive feedback"},
                            {"name": "task_success", "value": 1.0, "reason": "Task completed successfully per user"},
                            {"name": "response_accuracy", "value": 0.85, "reason": "User confirmed accuracy"},
                            {"name": "completion_confidence", "value": 0.95, "reason": "High confidence task completion"}
                        ]
                    )
                except Exception as e:
                    print(f"Error updating positive completion feedback in Opik: {e}")
                    
            elif is_negative:
                feedback_collector.record_comprehensive_feedback(
                    thread_id=thread_id or "unknown",
                    scores={
                        "helpful": 0.2,
                        "accurate": 0.3,
                        "relevant": 0.25,
                        "actionable": 0.2,
                        "satisfaction": 0.1
                    },
                    overall_comment=f"User negative feedback on task: {feedback_text[:150]}"
                )
                
                # Update Opik trace with negative completion feedback
                try:
                    opik_context.update_current_trace(
                        metadata={
                            "feedback_sentiment": "negative",
                            "feedback_text": feedback_text[:200],
                            "task_completion_feedback": True,
                            "needs_improvement": True,
                            "timestamp": datetime.now().isoformat()
                        },
                        feedback_scores=[
                            {"name": "user_satisfaction", "value": 0.1, "reason": "User provided negative feedback"},
                            {"name": "task_success", "value": 0.2, "reason": "Task failed per user assessment"},
                            {"name": "response_accuracy", "value": 0.25, "reason": "User reported inaccuracy"},
                            {"name": "completion_confidence", "value": 0.15, "reason": "Low confidence in task completion"}
                        ]
                    )
                except Exception as e:
                    print(f"Error updating negative completion feedback in Opik: {e}")
            else:
                # Neutral feedback
                feedback_collector.record_feedback(
                    trace_id=None,
                    thread_id=thread_id,
                    feedback_type="helpful",
                    score=0.5,
                    reason=f"Neutral user feedback on task: {feedback_text[:150]}"
                )
                
                # Update Opik trace with neutral completion feedback
                try:
                    opik_context.update_current_trace(
                        metadata={
                            "feedback_sentiment": "neutral",
                            "feedback_text": feedback_text[:200],
                            "task_completion_feedback": True,
                            "timestamp": datetime.now().isoformat()
                        },
                        feedback_scores=[
                            {"name": "user_satisfaction", "value": 0.5, "reason": "User provided neutral feedback"},
                            {"name": "task_success", "value": 0.6, "reason": "Task partially completed per user"},
                            {"name": "response_accuracy", "value": 0.55, "reason": "Mixed accuracy feedback"},
                            {"name": "completion_confidence", "value": 0.5, "reason": "Moderate confidence in task completion"}
                        ]
                    )
                except Exception as e:
                    print(f"Error updating neutral completion feedback in Opik: {e}")
            
            # Track user journey with feedback
            ConversationAnalytics.track_user_journey(
                user_id="agent_user",
                action="task_completion_feedback",
                context={
                    "thread_id": thread_id,
                    "sentiment": "positive" if is_positive else ("negative" if is_negative else "neutral"),
                    "feedback_length": len(feedback_text),
                    "timestamp": datetime.now().isoformat(),
                    "feedback_recorded": True
                }
            )
            
        except Exception as e:
            print(f"Error recording feedback: {e}")
        
        return {}

    # Compile the event subgraph
    event_workflow = build_event_subgraph()
    
    # We define the interrupt points where we wait for human input.
    # We interrupt BEFORE the nodes that process the human's response.
    event_agent = event_workflow.compile(
        interrupt_before=[
            "handle_feedback", 
            "handle_place", 
            "handle_date", 
            "handle_type",
            "handle_post_feedback"  # Also interrupt for social media feedback
        ]
    ) 
    event_agent = track_langgraph(event_agent, opik_tracer)

    graph = StateGraph(AgentState)
    graph.add_node("llm", call_model)
    graph.add_node("tools", ToolNode(ALL_TOOLS))
    graph.add_node("ask_feedback", ask_feedback_node)
    graph.add_node("handle_feedback", handle_feedback_node)
    
    # Add the event subgraph as a node
    graph.add_node("event_manager", event_agent)

    graph.add_edge(START, "llm")
    
    graph.add_conditional_edges(
        "llm",
        route_step,
        {
            "tools": "tools",
            "event_manager": "event_manager",
            "ask_feedback": "ask_feedback",
            "end": END,
        },
    )
    graph.add_edge("tools", "llm")
    graph.add_edge("event_manager", END)
    graph.add_edge("ask_feedback", "handle_feedback")
    graph.add_edge("handle_feedback", END)

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

    # Initialize OpikTracer with the compiled graph structure
    local_opik_tracer = OpikTracer(graph=agent.get_graph(xray=True))
    agent = track_langgraph(agent, local_opik_tracer)
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

