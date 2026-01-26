"""Model Context Protocol tools for AI assistants."""
from typing import List
import logging

from langchain_core.tools import tool

from app.database import SessionLocal
from app.crud import user as user_crud
from app.crud import user_room as user_room_crud

logger = logging.getLogger("app.mcp.tools")


def _format_user_rooms(rooms) -> List[str]:
	formatted = []
	for membership in rooms:
		formatted.append(
			f"Room {membership.room_id} (number: {membership.room_number or 'n/a'})"
		)
	return formatted


def build_user_context(user_id: int) -> str:
	"""Return a short description of the user and joined rooms."""
	with SessionLocal() as db:
		user = user_crud.get_user_by_id(db, user_id)
		if not user:
			logger.warning("User %s not found when building context", user_id)
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


@tool("get_user_context")
def get_user_context(user_id: int) -> str:
	"""MCP tool wrapper that returns user profile context."""
	return build_user_context(user_id)


__all__ = ["get_user_context", "build_user_context"]
