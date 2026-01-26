"""Model Context Protocol tools for AI assistants."""
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from app.database import SessionLocal
from app.crud import room as room_crud
from app.crud import user as user_crud
from app.crud import user_room as user_room_crud


def _format_user_rooms(rooms) -> List[str]:
    formatted = []
    for membership in rooms:
        formatted.append(
            f"Room {membership.room_id} (number: {membership.room_number or 'n/a'})"
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
    if room.doctor:
        flags.append("Doctor")
    if room.shop:
        flags.append("Shop")
    if room.security:
        flags.append("Security")
    if room.partyhall:
        flags.append("Party Hall")
    if room.cleaning:
        flags.append("Cleaning")
    if room.playground:
        flags.append("Playground")
    return ", ".join(flags) if flags else "None"


def build_user_context(user_id: int) -> str:
    """Return a short description of the user and joined rooms."""
    with SessionLocal() as db:
        user = user_crud.get_user_by_id(db, user_id)
        if not user:
            return "User not found."

        rooms = user_room_crud.get_user_rooms(db, user_id=user_id)

        room_lines = _format_user_rooms(rooms)
        rooms_text = "\n".join(room_lines) if room_lines else "No joined rooms."

        return (
            f"User Profile\n"
            f"- Name: {user.full_name or user.username}\n"
            f"- Email: {user.email}\n"
            f"- Active: {user.is_active}\n"
            f"- Rooms:\n{rooms_text}"
        )


def build_room_context(room_id: str) -> str:
    """Return detailed room info including facilities and staff schedules."""
    with SessionLocal() as db:
        room = room_crud.get_room_by_room_id(db, room_id)
        if not room:
            return "Room not found."

        facilities = _format_room_flags(room)
        staff = _format_staff_assignments(room.staff_assignments)

        return (
            f"Room Details\n"
            f"- Name: {room.name}\n"
            f"- Description: {room.description or 'N/A'}\n"
            f"- Location: {room.location or 'N/A'}\n"
            f"- Facilities: {facilities}\n"
            f"- Staff:\n{staff}"
        )


def build_all_rooms_context() -> str:
    """Return a summary of all available rooms."""
    with SessionLocal() as db:
        rooms = room_crud.get_rooms(db, skip=0, limit=50)
        if not rooms:
            return "No rooms available."

        sections: List[str] = []
        for room in rooms:
            facilities = _format_room_flags(room)
            staff = _format_staff_assignments(room.staff_assignments)
            sections.append(
                f"Room: {room.name} ({room.room_id})\n"
                f"  Location: {room.location or 'N/A'}\n"
                f"  Description: {room.description or 'N/A'}\n"
                f"  Facilities: {facilities}\n"
                f"  Staff:\n{staff}"
            )
        return "\n\n".join(sections)


@tool("get_user_context")
def get_user_context(user_id: int) -> str:
    """MCP tool wrapper that returns user profile context."""
    return build_user_context(user_id)


@tool("get_room_context")
def get_room_context(room_id: str) -> str:
    """MCP tool returning room details, facilities, and staff schedules."""
    return build_room_context(room_id)


@tool("get_all_rooms_context")
def get_all_rooms_context() -> str:
    """MCP tool returning summary of all rooms with facilities and staff."""
    return build_all_rooms_context()


__all__ = [
    "get_user_context",
    "get_room_context",
    "get_all_rooms_context",
    "build_user_context",
    "build_room_context",
    "build_all_rooms_context",
]
