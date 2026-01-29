"""Model Context Protocol tools for AI assistants."""
from typing import Any, Dict, List, Optional
from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime

from app.database import SessionLocal
from app.crud import room as room_crud
from app.crud import user as user_crud

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

# --- Exports ---

# This list should contain the actual @tool functions to be bound to your LLM
APItools = [get_user_context, get_community_context, get_all_communities_context]

__all__ = [
    "APItools",
    "get_user_context",
    "get_community_context",
    "get_all_communities_context",
    "build_user_context",
    "build_community_context",
    "build_all_communities_context",
]