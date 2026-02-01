"""Model Context Protocol tools for AI assistants."""
from typing import Any, Dict, List, Optional
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime

from app.database import SessionLocal
from app.crud import room as room_crud
from app.crud import user as user_crud
from app.utils.image import image_request

# --- Helper Functions ---

def _format_user_rooms(rooms) -> List[str]:
    formatted = []
    for membership in rooms:
        unit_id = membership.room_number or 'n/a'
        apt_number = membership.room_id
        formatted.append(
            f"Unit/Room ID: {unit_id}, Apartment Number: {apt_number}"
        )
    return formatted


def _format_staff_assignments(
    assignments: Optional[Dict[str, Dict[str, Any]]]
) -> str:
    """Format staff assignments without exposing user IDs."""
    if not assignments:
        return "No staff assigned."

    lines: List[str] = []
    for role, details in assignments.items():
        timing = details.get("available_timing", "N/A")
        days = details.get("days", "N/A")
        lines.append(f"  - {role.capitalize()}: available {timing}, {days}")
    return "\n".join(lines)


def _format_room_flags(room) -> str:
    """Return a comma-separated list of enabled facility flags."""
    flags = []
    if room.doctor: flags.append("Doctor")
    if room.shop: flags.append("Shop")
    if room.security: flags.append("Security")
    if room.partyhall: flags.append("Party Hall")
    if room.cleaning: flags.append("Cleaning")
    if room.playground: flags.append("Playground")
    return ", ".join(flags) if flags else "None"

# --- Context Builders ---

def build_user_context(user_id: int) -> str:
    """Return a short description of the user and joined rooms."""
    with SessionLocal() as db:
        user = user_crud.get_user_by_id(db, user_id)
        if not user:
            return "User not found."

        # Use the relationship to get user's rooms
        room_lines = _format_user_rooms(user.user_rooms)
        rooms_text = "\n".join(room_lines) if room_lines else "No joined communities."

        return (
            f"User Profile\n"
            f"- Name: {user.full_name or user.username}\n"
            f"- Email: {user.email}\n"
            f"- Active: {user.is_active}\n"
            f"- Joined Communities:\n{rooms_text}"
        )


def build_community_context(room_id: str) -> str:
    """Return detailed Community info including facilities and staff schedules."""
    with SessionLocal() as db:
        room = room_crud.get_room_by_room_id(db, room_id)
        if not room:
            return "Community not found."

        facilities = _format_room_flags(room)
        staff = _format_staff_assignments(room.staff_assignments)

        return (
            f"Community Details\n"
            f"- Name: {room.name}\n"
            f"- Description: {room.description or 'N/A'}\n"
            f"- Location: {room.location or 'N/A'}\n"
            f"- Facilities: {facilities}\n"
            f"- Staff:\n{staff}"
        )


def build_all_communities_context() -> str:
    """Return a summary of all available communities."""
    with SessionLocal() as db:
        rooms = room_crud.get_rooms(db, skip=0, limit=50)
        if not rooms:
            return "No communities available."

        sections: List[str] = []
        for room in rooms:
            facilities = _format_room_flags(room)
            staff = _format_staff_assignments(room.staff_assignments)
            sections.append(
                f"Community: {room.name} ({room.room_id})\n"
                f"  Location: {room.location or 'N/A'}\n"
                f"  Description: {room.description or 'N/A'}\n"
                f"  Facilities: {facilities}\n"
                f"  Staff:\n{staff}"
            )
        return "\n\n".join(sections)

# --- Tool Registrations ---

@tool
def get_user_context(runtime: ToolRuntime) -> str:
    """Retrieve the current user's profile, email status, and list of joined community rooms."""
    user_id = int(runtime.config["configurable"]["user_id"])
    return build_user_context(user_id)


@tool
def get_community_context(room_id: str, runtime: ToolRuntime) -> str:
    """Retrieve detailed information for a specific community, including its facilities and staff schedules."""
    return build_community_context(room_id)


@tool
def get_all_communities_context(runtime: ToolRuntime) -> str:
    """Retrieve a list of all available communities with their descriptions, locations, and staff details."""
    return build_all_communities_context()


# --- Event creation tool for LLM ---
@tool
def create_event_via_llm(
    event_name: str,
    event_description: str,
    event_type: str,
    event_place: Optional[str] = None,
    event_date: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    max_participants: Optional[str] = None,
    guest_speakers: Optional[str] = None,
    tag: Optional[str] = None,
    event_classification: Optional[str] = None,
    room_id: Optional[str] = None,
    runtime: ToolRuntime = None,
) -> str:
    """Create a new event in the database with all collected details.
    Use this tool ONLY after collecting and confirming all necessary details from the user.
    """
    import json
    from datetime import datetime, time as dt_time
    from dateutil import parser as date_parser
    from app.crud import event as event_crud
    from app.schemas.event import EventCreate, EventStatus
    from app.database import SessionLocal
    from app.crud import user as user_crud

    # Resolve user id
    try:
        user_id = int(runtime.config["configurable"]["user_id"])
    except Exception:
        return json.dumps({"status": "error", "message": "Unable to determine authenticated user."})
    
    # Parse event date
    parsed_date = None
    if event_date:
        try:
            parsed_date = date_parser.parse(event_date)
        except Exception:
            pass
    
    # Parse times
    parsed_start_time = None
    parsed_end_time = None
    if start_time:
        try:
            # Try to parse time string like "4 pm", "16:00", etc.
            time_obj = date_parser.parse(start_time)
            parsed_start_time = time_obj.time()
        except Exception:
            pass
    
    if end_time:
        try:
            time_obj = date_parser.parse(end_time)
            parsed_end_time = time_obj.time()
        except Exception:
            pass
    
    # Parse max participants
    parsed_max_participants = None
    if max_participants:
        try:
            parsed_max_participants = int(max_participants)
        except Exception:
            pass
    
    # Determine room_id from user's joined communities
    with SessionLocal() as db:
        user = user_crud.get_user_by_id(db, user_id)
        if not user:
            return json.dumps({"status": "error", "message": "User not found."})
        
        # If no room_id specified, use the first joined room
        if not room_id and user.user_rooms:
            room_id = user.user_rooms[0].room_id
        
        if not room_id:
            return json.dumps({"status": "error", "message": "No community found for this user."})
        
        # Create event
        try:
            event_payload = EventCreate(
                event_name=event_name,
                event_description=event_description,
                event_place=event_place,
                event_date=parsed_date,
                event_type=event_type,
                event_image_url=None,
                tag=tag,
                event_classification=event_classification,
                room_id=room_id,
                start_time=parsed_start_time,
                end_time=parsed_end_time,
                max_participants=parsed_max_participants,
                guest_speakers=guest_speakers,
                event_status=EventStatus.confirmed,  # Set as confirmed when created via workflow
                rsvp_required=False,
                reminder_enabled=False,
            )

            data = image_request(event_name)
            event_payload.image_request_id = data
            
            db_event = event_crud.create_event(db, event_payload, user_id)

            
            # Auto-join the creator to the event
            from app.crud import event_user as event_user_crud
            event_user_crud.join_event(db, db_event, user_id)
            
            return json.dumps({
                "status": "success",
                "event_id": db_event.event_id,
                "event_name": db_event.event_name,
                "message": f"Event '{event_name}' created successfully!"
            })
        except Exception as exc:
            import traceback
            error_details = traceback.format_exc()
            print(f"ERROR creating event: {str(exc)}")
            print(f"Traceback: {error_details}")
            return json.dumps({"status": "error", "message": f"Failed to create event: {str(exc)}"})


@tool
def update_event_via_llm(
    event_id: str,
    event_name: Optional[str] = None,
    event_description: Optional[str] = None,
    tag: Optional[str] = None,
    event_classification: Optional[str] = None,
    event_place: Optional[str] = None,
    event_date: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    event_type: Optional[str] = None,
    max_participants: Optional[str] = None,
    guest_speakers: Optional[str] = None,
    runtime: ToolRuntime = None,
) -> str:
    """Update an existing event. Use this when the user wants to modify an event's details.
    
    Args:
        event_id: The event ID (e.g., EVT12345678) - REQUIRED
        event_name: New name for the event
        event_description: New description
        tag: New tag (e.g., eco, wellness, social)
        event_classification: New classification (e.g., party, workshop, meetup)
        event_place: New location
        event_date: New date
        start_time: New start time
        end_time: New end time
        event_type: New type (public, private, community, social)
        max_participants: New max participants
        guest_speakers: New guest speakers
        
    Returns:
        JSON with status and updated event details
    """
    import json
    from app.crud import event as event_crud
    from app.schemas.event import EventUpdate
    
    # Resolve user from runtime
    try:
        user_id = int(runtime.config["configurable"]["user_id"])
    except Exception:
        return json.dumps({"status": "error", "message": "Unable to determine authenticated user."})
    
    with SessionLocal() as db:
        # Find the event
        event = event_crud.get_event_by_event_id(db, event_id)
        if not event:
            return json.dumps({"status": "error", "message": f"Event '{event_id}' not found."})
        
        # Verify user has permission (creator or admin)
        if event.user_id != user_id:
            return json.dumps({"status": "error", "message": "You don't have permission to update this event."})
        
        # Build update data
        update_data = {}
        if event_name:
            update_data["event_name"] = event_name
        if event_description:
            update_data["event_description"] = event_description
        if tag:
            update_data["tag"] = tag
        if event_classification:
            update_data["event_classification"] = event_classification
        if event_place:
            update_data["event_place"] = event_place
        if event_type:
            update_data["event_type"] = event_type
        if guest_speakers:
            update_data["guest_speakers"] = guest_speakers
        
        # Parse date if provided
        if event_date:
            from dateutil import parser as date_parser
            try:
                update_data["event_date"] = date_parser.parse(event_date)
            except Exception:
                pass
        
        # Parse times
        if start_time:
            from dateutil import parser as date_parser
            try:
                update_data["start_time"] = date_parser.parse(start_time).time()
            except Exception:
                pass
        
        if end_time:
            from dateutil import parser as date_parser
            try:
                update_data["end_time"] = date_parser.parse(end_time).time()
            except Exception:
                pass
        
        # Parse max participants
        if max_participants:
            try:
                update_data["max_participants"] = int(max_participants)
            except Exception:
                pass
        
        if not update_data:
            return json.dumps({"status": "error", "message": "No fields to update provided."})
        
        try:
            event_update = EventUpdate(**update_data)
            updated_event = event_crud.update_event(db, event, event_update)
            
            return json.dumps({
                "status": "success",
                "event_id": updated_event.event_id,
                "message": f"Event '{updated_event.event_name}' updated successfully!",
                "updated_fields": list(update_data.keys())
            })
        except Exception as exc:
            return json.dumps({"status": "error", "message": f"Failed to update event: {str(exc)}"})


@tool
def start_event_creation(event_name: str) -> str:
    """Iitiate the event creation process. Use this tool when the user wants to create a new event.
    The system will then switch to a specialized workflow to collect details.
    """
    return "Event creation flow started."


@tool
def submit_user_response(thread_id: str, user_message: str, runtime: ToolRuntime = None) -> str:
    """Store a user's reply into the persistent chat session so the sub-agent can resume.

    This is useful for programmatic submission of user responses (e.g., from frontend UIs).
    The runtime is used to determine the authenticated user and validate permissions.
    """
    import json
    from app.crud import user_message as user_message_crud
    from app.schemas.user_message import UserMessageCreate

    # Resolve user id
    try:
        user_id = int(runtime.config["configurable"]["user_id"])
    except Exception:
        return json.dumps({"status": "error", "message": "Unable to determine authenticated user."})

    # Persist the user response
    with SessionLocal() as db:
        try:
            msg = user_message_crud.create_user_message(
                db,
                UserMessageCreate(
                    session_id=thread_id,
                    role="user",
                    user_id=user_id,
                    user_message=user_message,
                ),
            )
        except Exception as exc:
            return json.dumps({"status": "error", "message": f"Failed to store message: {str(exc)}"})

    return json.dumps({"status": "ok", "message_id": getattr(msg, "id", None)})


@tool
def web_search(query: str) -> str:
    """Search the web for current information using Tavily.
    
    Use this tool when you need to find:
    - Current sustainability news and trends
    - Recycling guidelines for specific items
    - Environmental regulations or policies
    - General knowledge not available in the community context
    
    Args:
        query: The search query to look up
        
    Returns:
        Search results with relevant information
    """
    import json
    from app.core.config import settings
    
    if not settings.TAVILY_API_KEY:
        return json.dumps({"status": "error", "message": "Tavily API key not configured"})
    
    try:
        from tavily import TavilyClient
        
        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        
        # Perform search with sustainability focus
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=5,
            include_answer=True,
            include_raw_content=False,
        )
        
        # Format the response
        answer = response.get("answer", "")
        results = response.get("results", [])
        
        formatted_results = []
        for r in results[:3]:  # Limit to top 3 results
            formatted_results.append({
                "title": r.get("title", ""),
                "snippet": r.get("content", "")[:300],
                "url": r.get("url", ""),
            })
        
        return json.dumps({
            "status": "success",
            "answer": answer,
            "sources": formatted_results,
        })
        
    except ImportError:
        return json.dumps({"status": "error", "message": "Tavily library not installed. Run: pip install tavily-python"})
    except Exception as exc:
        return json.dumps({"status": "error", "message": f"Search failed: {str(exc)}"})


@tool
def broadcast_neighbor_help(help_request: str, runtime: ToolRuntime = None) -> str:
    """Broadcast a help request to all connected neighbors (Near People).
    
    Use this tool when the user needs real-world assistance (e.g., "I need help picking up my child").
    The system will:
    1. Fetch all users in the current user's "Near People" list.
    2. Create a notification for each neighbor with the help request message.
    
    Args:
        help_request: A clear, polite message explaining what help is needed. 
                      Generated by the AI based on the user's intent.
    """
    import json
    from app.crud import near_people as near_people_crud
    from app.crud import notification as notification_crud
    from app.crud import user as user_crud
    from app.schemas.notification import NotificationCreate
    from app.database import SessionLocal
    
    # Resolve user id
    try:
        user_id = int(runtime.config["configurable"]["user_id"])
    except Exception:
        return json.dumps({"status": "error", "message": "Unable to determine authenticated user."})
        
    with SessionLocal() as db:
        # Fetch sender info
        current_user = user_crud.get_user_by_id(db, user_id)
        sender_name = current_user.username if current_user else "Someone"
        
        # 1. Fetch neighbors
        neighbors = near_people_crud.get_near_people(db, user_id=user_id, limit=100)
        
        if not neighbors:
            return json.dumps({
                "status": "warning", 
                "message": "No neighbors found. Please add neighbors to your 'Near People' list first."
            })
            
        # 2. Broadcast notifications
        count = 0
        for neighbor in neighbors:
            try:
                # message content is already generated by AI (the caller)
                payload = NotificationCreate(
                    to_user_id=neighbor.near_user_id,
                    message=f"Neighbor Help Request from {sender_name}: {help_request}",
                    value=0  # 0 indicates normal priority
                )
                notification_crud.create_notification(db, notification_in=payload, from_user_id=user_id)
                count += 1
            except Exception as e:
                print(f"Failed to notify neighbor {neighbor.near_user_id}: {e}")
                
        return json.dumps({
            "status": "success",
            "message": f"Help request broadcasted to {count} neighbors.",
            "recipient_count": count
        })


# --- Exports ---

# This list should contain the actual @tool functions to be bound to your LLM
APItools = [
    get_user_context,
    get_community_context,
    get_all_communities_context,
    create_event_via_llm,
    update_event_via_llm,
    start_event_creation,
    submit_user_response,
    web_search,
    broadcast_neighbor_help,
]


__all__ = [
    "APItools",
    "get_user_context",
    "get_community_context",
    "get_all_communities_context",
    "build_user_context",
    "build_community_context",
    "build_all_communities_context",
]