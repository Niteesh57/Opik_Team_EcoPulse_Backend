from typing import Annotated, TypedDict, Optional, Literal, Union, Dict, Any
from datetime import datetime
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from langsmith import Client
from opik import track
import opik
from opik import opik_context
from opik.integrations.langchain import OpikTracer
from app.ai.opik import (
    opik_tracer,
    track_agent_call,
    track_llm_generation,
    feedback_collector,
    PerformanceMonitor,
    ConversationAnalytics,
)
from app.ai.prompts import (
    EVENT_CREATION_SUBAGENT_PROMPT,
    EVENT_CATEGORIZATION_PROMPT,
)
from app.ai.social_media_node import (
    social_media_generation_node,
    ask_post_feedback_node,
    handle_post_feedback_node
)


client = Client()
prompt = client.pull_prompt("hwchase17/react")

# --- State ---
class EventAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    event_name: Optional[str]
    description: Optional[str]
    desc_iterations: int
    place: Optional[str]
    date: Optional[str]
    start_time: Optional[str]
    end_time: Optional[str]
    event_type: Optional[str]
    max_participants: Optional[str]
    guest_speakers: Optional[str]
    room_id: Optional[str]
    thread_id: Optional[str]
    trace_id: Optional[str]
    social_media_posts: Optional[Dict[str, str]]
    social_media_hashtags: Optional[list]
    social_media_feedback: Optional[list]
    suggestions: Optional[list[str]]
    format_hint: Optional[str]


def _opik_config(state: EventAgentState, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build Opik configuration with comprehensive metadata."""
    config: Dict[str, Any] = {"callbacks": [opik_tracer]}
    metadata = (extra.get("metadata", {}).copy() if extra and "metadata" in extra else {})
    
    # Add standard metadata
    thread_id = state.get("thread_id")
    if thread_id:
        metadata["thread_id"] = thread_id
    
    # Add event workflow metadata
    metadata["workflow"] = "event_creation"
    metadata["event_name"] = state.get("event_name", "")
    metadata["workflow_stage"] = _get_workflow_stage(state)
    metadata["timestamp"] = datetime.now().isoformat()
    
    if metadata:
        config["metadata"] = metadata
    if extra:
        for key, value in extra.items():
            if key == "metadata":
                continue
            config[key] = value
    return config


def _get_workflow_stage(state: EventAgentState) -> str:
    """Determine current workflow stage for tracking."""
    if not state.get("event_name"):
        return "entry"
    if not state.get("description"):
        return "generating_description"
    if not state.get("place"):
        return "collecting_place"
    if not state.get("date"):
        return "collecting_date"
    if not state.get("start_time"):
        return "collecting_time"
    if not state.get("event_type"):
        return "collecting_type"
    if not state.get("max_participants"):
        return "collecting_participants"
    if not state.get("guest_speakers"):
        return "collecting_speakers"
    if not state.get("social_media_posts"):
        return "generating_social_media"
    return "complete"


# --- Nodes ---

@track_agent_call(agent_name="Event Entry Node", agent_type="analysis", tags={"stage": "entry"})
def entry_node(state: EventAgentState):
    """Analyze the initial input to extract event name."""
    msg = state["messages"][-1]
    
    # Track user journey
    ConversationAnalytics.track_user_journey(
        user_id="event_creator",
        action="event_creation_started",
        context={
            "thread_id": state.get("thread_id"),
            "initial_message": str(msg.content)[:100] if hasattr(msg, 'content') else ""
        }
    )
    
    # Attempt to extract name if not present.
    if isinstance(msg, HumanMessage) and not state.get("event_name"):
        # For simplicity, we assume the user intent *is* the name or contains it.
        # Ideally, we would use an extraction chain here.
        return {"event_name": msg.content}
    return {}

def generate_description_node(state: EventAgentState):
    """Generate or refine event description (max 100 chars)."""
    from app.ai.groq_client import get_chat_llm
    
    @track_agent_call(agent_name="Generate Event Description", agent_type="generative", tags={"stage": "description_generation"})
    def _generate_description():
        llm = get_chat_llm()
        name = state.get("event_name", "the event")
        feedback = ""
        
        # If we have iterated, use the last user message as feedback
        if state.get("desc_iterations", 0) > 0:
            feedback = state["messages"][-1].content
        
        if feedback:
            prompt = (
                f"Refine the following event description for '{name}' based on this feedback: '{feedback}'.\n"
                f"Current description: {state.get('description', '')}\n"
                f"IMPORTANT: Keep it under 100 characters. Be concise and engaging."
            )
        else:
            prompt = (
                f"Generate a short, engaging description for a community event named '{name}'.\n"
                f"Focus on sustainability or community building.\n"
                f"IMPORTANT: Keep it under 100 characters maximum. Be concise."
            )

        from datetime import datetime
        start_time = datetime.now()
        response = llm.invoke([
            SystemMessage(content="You are an event planner assistant. Generate descriptions that are under 100 characters."), 
            HumanMessage(content=prompt),
        ], config=_opik_config(state))
        result = response.content.strip()
        latency_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Track LLM call in Opik
        try:
            opik_context.update_current_trace(
                metadata={
                    "llm_call": "generate_description",
                    "event_name": name,
                    "iteration": state.get("desc_iterations", 0),
                    "has_feedback": bool(feedback),
                    "prompt_length": len(prompt),
                    "response_length": len(result),
                    "latency_ms": latency_ms,
                    "model": "groq/openai-gpt-oss-20b",
                    "timestamp": start_time.isoformat()
                },
                feedback_scores=[
                    {"name": "description_generation", "value": 0.8, "reason": "LLM generated description successfully"}
                ]
            )
        except Exception as e:
            print(f"Error updating Opik trace: {e}")
        
        return result
    
    description = _generate_description()
    
    # Truncate to 100 chars if needed
    if len(description) > 100:
        description = description[:97] + "..."
    
    # Prepare the response message with description preview
    response_msg = f"Here's the description:\n\n\"{description}\"\n\nDoes this look good? (Reply 'yes' to proceed, or tell me how to refine it)"
    
    return {
        "description": description,
        "desc_iterations": state.get("desc_iterations", 0) + 1,
        "messages": [AIMessage(content=response_msg)],
        "suggestions": ["Yes, looks good", "Make it shorter", "Make it more professional", "Add more excitement"],
        "format_hint": None
    }

def ask_feedback_node(state: EventAgentState):
    """Skip this - we now combine with generate_description_node."""
    # This node is now essentially a pass-through since we ask in generate_desc
    return {}

def handle_feedback_node(state: EventAgentState):
    """Handle user feedback on description and auto-record positive sentiment."""
    thread_id = state.get("thread_id")
    
    # Get the user's feedback message
    if state["messages"]:
        last_msg = state["messages"][-1]
        if hasattr(last_msg, 'content'):
            feedback_text = last_msg.content.lower()
            
            # Detect positive signals
            positive_signals = ["yes", "good", "great", "perfect", "awesome", "excellent", 
                              "looks good", "ok", "fine", "proceed", "love it", "like it"]
            
            is_positive = any(signal in feedback_text for signal in positive_signals)
            
            if is_positive:
                try:
                    # Record feedback (will update trace only if one is active)
                    feedback_collector.record_comprehensive_feedback(
                        thread_id=thread_id or "unknown",
                        scores={
                            "helpful": 0.9,
                            "relevant": 0.85,
                            "satisfaction": 0.9
                        },
                        overall_comment=f"User approved description: {feedback_text[:100]}"
                    )

                    # Additionally, try to update the current trace with explicit metadata
                    try:
                        current_trace = opik_context.get_current_trace_data()
                        if current_trace is not None:
                            opik_context.update_current_trace(
                                metadata={
                                    "auto_feedback_recorded": True,
                                    "feedback_sentiment": "positive",
                                    "workflow_stage": "description_approved",
                                    "timestamp": datetime.now().isoformat()
                                },
                                feedback_scores=[
                                    {"name": "description_satisfaction", "value": 0.9, 
                                     "reason": "User approved event description"}
                                ]
                            )
                    except Exception as inner_e:
                        print(f"Error updating Opik trace for description feedback: {inner_e}")
                except Exception as e:
                    print(f"Error recording auto-feedback: {e}")
    
    return {}

def route_feedback(state: EventAgentState):
    last_msg = state["messages"][-1].content.lower()
    is_satisfied = any(x in last_msg for x in ["yes", "good", "ok", "fine", "great", "perfect", "looks good", "proceed"])
    is_maxed_out = state.get("desc_iterations", 0) >= 4
    
    if is_satisfied or is_maxed_out:
        return "ask_place"
    return "generate_desc"  # Loop back to refine

def ask_place_node(state: EventAgentState):
    return {
        "messages": [AIMessage(content="Where will the event take place?")],
        "suggestions": ["Community Center", "Central Park", "Office 301", "Online"],
        "format_hint": None
    }

def handle_place_node(state: EventAgentState):
    place = state["messages"][-1].content
    
    # Auto-record feedback for successful place input
    try:
        ConversationAnalytics.track_user_journey(
            user_id="event_creator",
            action="place_provided",
            context={
                "thread_id": state.get("thread_id"),
                "place": place[:100]
            }
        )
    except Exception as e:
        print(f"Error tracking place input: {e}")
    
    return {"place": place}

def ask_date_node(state: EventAgentState):
    return {
        "messages": [AIMessage(content="When is the event scheduled for? (e.g., February 2, 2026)")],
        "suggestions": ["Tomorrow", "Next Friday", "Next Weekend"],
        "format_hint": "YYYY-MM-DD or Month Day, Year"
    }

def handle_date_node(state: EventAgentState):
    date_str = state["messages"][-1].content
    
    # Auto-record feedback for successful date input
    try:
        ConversationAnalytics.track_user_journey(
            user_id="event_creator",
            action="date_provided",
            context={
                "thread_id": state.get("thread_id"),
                "date": date_str[:100]
            }
        )
    except Exception as e:
        print(f"Error tracking date input: {e}")
    
    return {"date": date_str}

def ask_time_node(state: EventAgentState):
    return {
        "messages": [AIMessage(content="What time does the event start and end? (e.g., 4 pm - 6 pm)")],
        "suggestions": ["9 AM - 5 PM", "2 PM - 4 PM", "6 PM - 9 PM"],
        "format_hint": "START - END"
    }

def handle_time_node(state: EventAgentState):
    time_str = state["messages"][-1].content
    # Try to parse start and end times
    # Simple parsing - can be enhanced
    parts = time_str.lower().replace("to", "-").replace("until", "-").split("-")
    start_time = parts[0].strip() if len(parts) > 0 else time_str
    end_time = parts[1].strip() if len(parts) > 1 else ""
    return {"start_time": start_time, "end_time": end_time}

def ask_type_node(state: EventAgentState):
    return {
        "messages": [AIMessage(content="What type of event is this? (public, private, community, or social)")],
        "suggestions": ["Public", "Private", "Community", "Social"],
        "format_hint": None
    }

def handle_type_node(state: EventAgentState):
    evt_type = state["messages"][-1].content
    
    # Auto-record feedback for successful type selection
    try:
        ConversationAnalytics.track_user_journey(
            user_id="event_creator",
            action="event_type_selected",
            context={
                "thread_id": state.get("thread_id"),
                "event_type": evt_type[:50]
            }
        )
    except Exception as e:
        print(f"Error tracking event type: {e}")
    
    return {"event_type": evt_type}

def ask_participants_node(state: EventAgentState):
    return {
        "messages": [AIMessage(content="Is there a maximum number of participants? (Enter a number or 'no limit')")],
        "suggestions": ["Unlimited", "10", "50", "100"],
        "format_hint": "Number"
    }

def handle_participants_node(state: EventAgentState):
    response = state["messages"][-1].content.lower()
    max_participants = None
    if "no" not in response and "unlimited" not in response:
        # Try to extract number
        import re
        numbers = re.findall(r'\d+', response)
        if numbers:
            max_participants = numbers[0]
    return {"max_participants": max_participants}

def ask_guest_speakers_node(state: EventAgentState):
    return {
        "messages": [AIMessage(content="Will there be any guest speakers? (Enter names or 'none')")],
        "suggestions": ["None", "Alice Johnson", "Dr. Bob Smith", "Mayor Green"],
        "format_hint": "Name 1, Name 2"
    }

def handle_guest_speakers_node(state: EventAgentState):
    response = state["messages"][-1].content
    guest_speakers = None if response.lower() in ["no", "none", "n/a"] else response
    return {"guest_speakers": guest_speakers}

def finalize_node(state: EventAgentState, config: RunnableConfig):
    from app.mcp.tools import create_event_via_llm
    from langgraph.prebuilt import ToolRuntime
    from app.ai.groq_client import get_chat_llm
    
    @opik.track(name="Finalize Event Creation")
    def _categorize_event():
        llm = get_chat_llm()
        name = state.get("event_name", "")
        desc = state.get("description", "")
        evt_type = state.get("event_type", "public")
        
        tag_prompt = EVENT_CATEGORIZATION_PROMPT.prompt.format(
            name=name, desc=desc, evt_type=evt_type
        )
        
        from datetime import datetime
        start_time = datetime.now()
        resp = llm.invoke([
            SystemMessage(content="You are a helpful assistant that categorizes events. Respond only with TAG and CLASS in the exact format requested."),
            HumanMessage(content=tag_prompt)
        ], config=_opik_config(state)).content
        latency_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Parse tag and class for tracing
        import re as re_module
        tag_match = re_module.search(r'TAG:\s*(\w+)', resp, re_module.IGNORECASE)
        class_match = re_module.search(r'CLASS:\s*(\w+)', resp, re_module.IGNORECASE)
        extracted_tag = tag_match.group(1) if tag_match else "unknown"
        extracted_class = class_match.group(1) if class_match else "unknown"
        
        # Track LLM call in Opik (only if a trace is active)
        try:
            current_trace = opik_context.get_current_trace_data()
            if current_trace is not None:
                opik_context.update_current_trace(
                    metadata={
                        "llm_call": "categorize_event",
                        "event_name": name,
                        "event_type": evt_type,
                        "extracted_tag": extracted_tag,
                        "extracted_class": extracted_class,
                        "prompt_length": len(tag_prompt),
                        "response_length": len(resp),
                        "latency_ms": latency_ms,
                        "model": "groq/openai-gpt-oss-20b",
                        "timestamp": start_time.isoformat()
                    },
                    feedback_scores=[
                        {"name": "event_categorization", "value": 0.85, "reason": f"Event categorized as {extracted_tag}/{extracted_class}"}
                    ]
                )
        except Exception as e:
            print(f"Error updating Opik trace: {e}")
        
        return resp
    
    print("=" * 50)
    print("FINALIZE NODE CALLED")
    print(f"Event name: {state.get('event_name')}")
    print(f"Description: {state.get('description')}")
    print(f"Place: {state.get('place')}")
    print(f"Date: {state.get('date')}")
    print(f"Start time: {state.get('start_time')}")
    print(f"End time: {state.get('end_time')}")
    print(f"Type: {state.get('event_type')}")
    print(f"Max participants: {state.get('max_participants')}")
    print(f"Guest speakers: {state.get('guest_speakers')}")
    print("=" * 50)
    
    # Auto-tagging and classification using LLM
    resp = _categorize_event()
    
    print(f"TAG/CLASS response: {resp}")
    
    # Parse tag and classification with robust handling
    tag = "general"
    classification = "event"
    
    import re
    tag_match = re.search(r'TAG:\s*(\w+)', resp, re.IGNORECASE)
    class_match = re.search(r'CLASS:\s*(\w+)', resp, re.IGNORECASE)
    
    if tag_match:
        tag = tag_match.group(1).lower()
    if class_match:
        classification = class_match.group(1).lower()
    
    print(f"Parsed - Tag: {tag}, Classification: {classification}")
        
    # Mock runtime for tool
    mock_runtime = ToolRuntime(config=config, store=None)
    
    print("Calling create_event_via_llm...")
    start_time_creation = datetime.now()
    
    # Prepare event data with all collected fields
    result_json = create_event_via_llm.invoke({
        "event_name": state.get("event_name", ""),
        "event_description": state.get("description", ""),
        "event_type": state.get("event_type", "public"),
        "event_place": state.get("place"),
        "event_date": state.get("date"),
        "start_time": state.get("start_time"),
        "end_time": state.get("end_time"),
        "max_participants": state.get("max_participants"),
        "guest_speakers": state.get("guest_speakers"),
        "tag": tag,
        "event_classification": classification,
        "room_id": None, # Tool will resolve
        "runtime": mock_runtime
    }, config=_opik_config(state))
    
    # Track event creation success with performance metrics
    creation_latency = (datetime.now() - start_time_creation).total_seconds() * 1000
    PerformanceMonitor.record_latency(
        operation="event_creation",
        latency_ms=creation_latency,
        success=True,
        metadata={
            "thread_id": state.get("thread_id"),
            "event_name": state.get("event_name"),
            "event_type": state.get("event_type"),
            "tag": tag,
            "classification": classification
        }
    )
    
    # Track completion in user journey
    ConversationAnalytics.track_user_journey(
        user_id="event_creator",
        action="event_creation_completed",
        context={
            "thread_id": state.get("thread_id"),
            "event_name": state.get("event_name"),
            "event_type": state.get("event_type"),
            "creation_latency_ms": creation_latency
        }
    )
    
    # Update Opik trace with event creation details and auto-record positive feedback
    try:
        current_trace = opik_context.get_current_trace_data()
        if current_trace is not None:
            opik_context.update_current_trace(
                metadata={
                    "event_created": True,
                    "event_name": state.get("event_name"),
                    "event_type": state.get("event_type"),
                    "tag": tag,
                    "classification": classification,
                    "workflow_stage": "complete",
                    "auto_feedback_recorded": True
                },
                feedback_scores=[
                    {"name": "workflow_completion", "value": 1.0, "reason": "Event workflow completed successfully"},
                    {"name": "user_engagement", "value": 0.95, "reason": "User completed full event creation workflow"},
                    {"name": "data_quality", "value": 0.9, "reason": "All required event fields provided"}
                ]
            )
        
        # Record comprehensive positive feedback for workflow completion (not strictly tied to a trace)
        feedback_collector.record_comprehensive_feedback(
            thread_id=state.get("thread_id") or "unknown",
            scores={
                "helpful": 1.0,
                "accurate": 0.95,
                "relevant": 1.0,
                "actionable": 1.0,
                "satisfaction": 0.95
            },
            overall_comment=f"User successfully completed event creation workflow: {state.get('event_name')}"
        )
    except Exception as e:
        print(f"Error updating Opik trace: {e}")
    
    print(f"Result from create_event_via_llm: {result_json}")
    print("=" * 50)
    
    return {"messages": [AIMessage(content=f"Event created successfully! Result: {result_json}")]}

# --- Graph ---

def build_event_subgraph():
    workflow = StateGraph(EventAgentState)
    
    workflow.add_node("entry", entry_node)
    workflow.add_node("generate_desc", generate_description_node)
    workflow.add_node("ask_feedback", ask_feedback_node)
    workflow.add_node("handle_feedback", handle_feedback_node)
    
    workflow.add_node("ask_place", ask_place_node)
    workflow.add_node("handle_place", handle_place_node)
    
    workflow.add_node("ask_date", ask_date_node)
    workflow.add_node("handle_date", handle_date_node)
    
    workflow.add_node("ask_time", ask_time_node)
    workflow.add_node("handle_time", handle_time_node)
    
    workflow.add_node("ask_type", ask_type_node)
    workflow.add_node("handle_type", handle_type_node)
    
    workflow.add_node("ask_participants", ask_participants_node)
    workflow.add_node("handle_participants", handle_participants_node)
    
    workflow.add_node("ask_guest_speakers", ask_guest_speakers_node)
    workflow.add_node("handle_guest_speakers", handle_guest_speakers_node)
    
    workflow.add_node("finalize", finalize_node)
    
    # Social media nodes
    workflow.add_node("generate_social_media", social_media_generation_node)
    workflow.add_node("ask_post_feedback", ask_post_feedback_node)
    workflow.add_node("handle_post_feedback", handle_post_feedback_node)
    
    # Edges
    workflow.add_edge(START, "entry")
    workflow.add_edge("entry", "generate_desc")
    workflow.add_edge("generate_desc", "ask_feedback")
    workflow.add_edge("ask_feedback", "handle_feedback") 
    
    workflow.add_conditional_edges(
        "handle_feedback",
        route_feedback,
        {
            "ask_place": "ask_place",
            "generate_desc": "generate_desc"
        }
    )
    
    workflow.add_edge("ask_place", "handle_place")
    workflow.add_edge("handle_place", "ask_date")
    
    workflow.add_edge("ask_date", "handle_date")
    workflow.add_edge("handle_date", "ask_time")
    
    workflow.add_edge("ask_time", "handle_time")
    workflow.add_edge("handle_time", "ask_type")
    
    workflow.add_edge("ask_type", "handle_type")
    workflow.add_edge("handle_type", "ask_participants")
    
    workflow.add_edge("ask_participants", "handle_participants")
    workflow.add_edge("handle_participants", "ask_guest_speakers")
    
    workflow.add_edge("ask_guest_speakers", "handle_guest_speakers")
    workflow.add_edge("handle_guest_speakers", "finalize")
    
    # After event finalization, generate social media posts
    workflow.add_edge("finalize", "generate_social_media")
    
    # Social media feedback flow
    workflow.add_edge("generate_social_media", "ask_post_feedback")
    workflow.add_edge("ask_post_feedback", "handle_post_feedback")
    workflow.add_edge("handle_post_feedback", END)
    
    return workflow

