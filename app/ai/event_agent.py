from typing import Annotated, TypedDict, Optional, Literal, Union, Dict, Any
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from langsmith import Client
from opik import track
import opik
from opik.integrations.langchain import OpikTracer
from app.ai.opik import opik_tracer


client = Client()
prompt = client.pull_prompt("hwchase17/react")

SUBAGENT_PROMPT = (
    "\n\n"
    "EVENT CREATION WORKFLOW (MANDATORY):\n"
    "When a user wants to create an event, you MUST collect details step by step:\n"
    "1. Ask for EVENT NAME (if not given)\n"
    "2. Generate a description and ask for feedback (refine up to 4 times)\n"
    "3. Ask for PLACE/LOCATION\n"
    "4. Ask for DATE (e.g., February 2, 2026)\n"
    "5. Ask for TIME (start and end, e.g., 4 pm - 6 pm)\n"
    "6. Ask for EVENT TYPE (public, private, community, social)\n"
    "7. Ask for MAX PARTICIPANTS (number or 'no limit')\n"
    "8. Ask for GUEST SPEAKERS (names or 'none')\n"
    "\n"
    "CRITICAL: After collecting ALL details, you MUST call the 'create_event_via_llm' tool to save the event to the database. "
    "DO NOT just summarize the event - you MUST call the tool. The event is NOT created until you call the tool.\n"
    "Pass all collected values to create_event_via_llm: event_name, event_description, event_type, event_place, event_date, start_time, end_time, max_participants, guest_speakers."
)

# --- State ---
class EventAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    event_name: Optional[str]
    description: Optional[str]
    desc_iterations: Optional[int]
    place: Optional[str]
    date: Optional[str]
    start_time: Optional[str]
    end_time: Optional[str]
    event_type: Optional[str]
    max_participants: Optional[str]
    guest_speakers: Optional[str]
    room_id: Optional[str]
    thread_id: Optional[str]


def _opik_config(state: EventAgentState, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    config: Dict[str, Any] = {"callbacks": [opik_tracer]}
    metadata = (extra.get("metadata", {}).copy() if extra and "metadata" in extra else {})
    thread_id = state.get("thread_id")
    if thread_id:
        metadata["thread_id"] = thread_id
    if metadata:
        config["metadata"] = metadata
    if extra:
        for key, value in extra.items():
            if key == "metadata":
                continue
            config[key] = value
    return config

# --- Nodes ---

def entry_node(state: EventAgentState):
    """Analyze the initial input to extract event name."""
    msg = state["messages"][-1]
    # Attempt to extract name if not present.
    if isinstance(msg, HumanMessage) and not state.get("event_name"):
        # For simplicity, we assume the user intent *is* the name or contains it.
        # Ideally, we would use an extraction chain here.
        return {"event_name": msg.content}
    return {}

def generate_description_node(state: EventAgentState):
    """Generate or refine event description (max 100 chars)."""
    from app.ai.groq_client import get_chat_llm
    
    @opik.track(name="Generate Event Description")
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

        response = llm.invoke([
            SystemMessage(content="You are an event planner assistant. Generate descriptions that are under 100 characters."), 
            HumanMessage(content=prompt),
        ], config=_opik_config(state))
        return response.content.strip()
    
    description = _generate_description()
    
    # Truncate to 100 chars if needed
    if len(description) > 100:
        description = description[:97] + "..."
    
    # Prepare the response message with description preview
    response_msg = f"Here's the description:\n\n\"{description}\"\n\nDoes this look good? (Reply 'yes' to proceed, or tell me how to refine it)"
    
    return {
        "description": description,
        "desc_iterations": state.get("desc_iterations", 0) + 1,
        "messages": [AIMessage(content=response_msg)]
    }

def ask_feedback_node(state: EventAgentState):
    """Skip this - we now combine with generate_description_node."""
    # This node is now essentially a pass-through since we ask in generate_desc
    return {}

def handle_feedback_node(state: EventAgentState):
    # Just a pass-through node to serve as interrupt point anchor or state update if needed
    return {}

def route_feedback(state: EventAgentState):
    last_msg = state["messages"][-1].content.lower()
    is_satisfied = any(x in last_msg for x in ["yes", "good", "ok", "fine", "great", "perfect", "looks good", "proceed"])
    is_maxed_out = state.get("desc_iterations", 0) >= 4
    
    if is_satisfied or is_maxed_out:
        return "ask_place"
    return "generate_desc"  # Loop back to refine

def ask_place_node(state: EventAgentState):
    return {"messages": [AIMessage(content="Where will the event take place?")]}

def handle_place_node(state: EventAgentState):
    place = state["messages"][-1].content
    return {"place": place}

def ask_date_node(state: EventAgentState):
    return {"messages": [AIMessage(content="When is the event scheduled for? (e.g., February 2, 2026)")]}

def handle_date_node(state: EventAgentState):
    date_str = state["messages"][-1].content
    return {"date": date_str}

def ask_time_node(state: EventAgentState):
    return {"messages": [AIMessage(content="What time does the event start and end? (e.g., 4 pm - 6 pm)")]}

def handle_time_node(state: EventAgentState):
    time_str = state["messages"][-1].content
    # Try to parse start and end times
    # Simple parsing - can be enhanced
    parts = time_str.lower().replace("to", "-").replace("until", "-").split("-")
    start_time = parts[0].strip() if len(parts) > 0 else time_str
    end_time = parts[1].strip() if len(parts) > 1 else ""
    return {"start_time": start_time, "end_time": end_time}

def ask_type_node(state: EventAgentState):
    return {"messages": [AIMessage(content="What type of event is this? (public, private, community, or social)")]}

def handle_type_node(state: EventAgentState):
    evt_type = state["messages"][-1].content
    return {"event_type": evt_type}

def ask_participants_node(state: EventAgentState):
    return {"messages": [AIMessage(content="Is there a maximum number of participants? (Enter a number or 'no limit')")]}

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
    return {"messages": [AIMessage(content="Will there be any guest speakers? (Enter names or 'none')")]}

def handle_guest_speakers_node(state: EventAgentState):
    response = state["messages"][-1].content
    guest_speakers = None if response.lower() in ["no", "none", "n/a"] else response
    return {"guest_speakers": guest_speakers}

def finalize_node(state: EventAgentState, config: RunnableConfig):
    from app.mcp.tools import create_event_via_llm
    from app.ai.groq_client import get_chat_llm
    
    @opik.track(name="Finalize Event Creation")
    def _categorize_event():
        llm = get_chat_llm()
        name = state.get("event_name", "")
        desc = state.get("description", "")
        evt_type = state.get("event_type", "public")
        
        tag_prompt = (
            f"For an event named '{name}' with description '{desc}' and type '{evt_type}', "
            f"provide exactly:\n"
            f"1. TAG: A single word tag (e.g., eco, wellness, social, networking, learning, charity, sports)\n"
            f"2. CLASS: A single word classification (e.g., party, workshop, meetup, seminar, cleanup, celebration)\n\n"
            f"Respond ONLY in this format:\nTAG: [word]\nCLASS: [word]"
        )
        
        resp = llm.invoke([
            SystemMessage(content="You are a helpful assistant that categorizes events. Respond only with TAG and CLASS in the exact format requested."),
            HumanMessage(content=tag_prompt)
        ], config=_opik_config(state)).content
        
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
    
    print("Calling create_event_via_llm...")
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
        "room_id": None  # Tool will resolve
    }, config=_opik_config(state))
    
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
    
    workflow.add_edge("finalize", END)
    
    return workflow

