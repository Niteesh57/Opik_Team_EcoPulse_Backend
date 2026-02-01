from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from app.mcp.tools import web_search, create_event_via_llm, update_event_via_llm
from app.utils.image import image_request_promote_refine, image_request

@tool
def create_event_image(description: str, runtime: ToolRuntime = None) -> str:
    """Generate a specialized event poster image for an event.
    
    Args:
        description: Detailed description of the event to put on the poster.
    """
    url = image_request_promote_refine(description)
    if url:
        return f"Image generated successfully: {url}"
    return "Failed to generate image."

@tool
def create_event_normal_image(description: str, runtime: ToolRuntime = None) -> str:
    """Generate a standard image based on a prompt.
    
    Args:
        description: Prompt for the image.
    """
    # Using the same refine logic for better quality, or could use standard image_request logic
    # but image_request_promote_refine handles waiting for completion which is better for synchronous agent response.
    url = image_request_promote_refine(description)
    if url:
        return f"Image generated successfully: {url}"
    return "Failed to generate image."
    
@tool
def create_event_image_promote_refine(description: str, runtime: ToolRuntime = None) -> str:
    """Generate and refine an event image promotion.
    
    Args:
        description: Description of the promotion.
    """
    url = image_request_promote_refine(description)
    if url:
        return f"Refined promotion image generated: {url}"
    return "Failed to generate refined image."

event_tools = [
    web_search,
    create_event_image,
    create_event_normal_image,
    create_event_image_promote_refine,
    update_event_via_llm
]