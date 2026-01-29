"""Long-term memory tools for the AI agent."""
import uuid
from typing import Any

from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime


@tool
def save_memory(note: str, runtime: ToolRuntime) -> str:
    """Save important information or a note about the user to long-term memory."""
    user_id = runtime.config["configurable"]["user_id"]
    namespace = ("memories", user_id)
    memory_id = str(uuid.uuid4())[:8]
    
    runtime.store.put(namespace, memory_id, {"data": note})
    return f"✅ Successfully saved to long-term memory: '{note}'"

@tool
def remove_memory(query: str, runtime: ToolRuntime) -> str:
    """Remove a specific note or piece of information from the user's long-term memory."""
    user_id = runtime.config["configurable"]["user_id"]
    namespace = ("memories", user_id)
    
    # Simple search and delete logic
    items = runtime.store.search(namespace, query=query)
    if items:
        runtime.store.delete(namespace, items[0].key)
        return f"🗑️ Removed the most relevant note: '{items[0].value['data']}'"
    return "I couldn't find a matching note to remove."

@tool
def list_memories(runtime: ToolRuntime) -> str:
    """List all current notes and saved facts about the user."""
    user_id = runtime.config["configurable"]["user_id"]
    namespace = ("memories", user_id)
    
    items = runtime.store.search(namespace)
    if not items:
        return "You have no saved notes."
    
    mem_list = "\n".join([f"- {m.value['data']} (ID: {m.key})" for m in items])
    return f"Here are your saved memories:\n{mem_list}"


# Tool list for binding to LLM
MemoryTools = [save_memory, remove_memory, list_memories]

__all__ = [
    "MemoryTools",
    "save_memory",
    "remove_memory",
    "list_memories",
]