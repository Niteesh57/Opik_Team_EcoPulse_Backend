from langchain_core.tools import tool
import requests
from app.core.config import settings

@tool
def xpoz_mcp_tool(query: str) -> str:
    """
    Interact with the Xpoz MCP service.
    
    Args:
        query: The query to send to the Xpoz MCP service.
    """

    headers = {
        "Authorization": f"Bearer {settings.XPOZ_API_KEY}"
    }
    
    try:
        response = requests.post("https://mcp.xpoz.ai/mcp", headers=headers, json={"query": query})
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        return f"An error occurred: {e}"
