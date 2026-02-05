"""Social media post generation node for events."""
from typing import Optional, Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
import opik
from opik import opik_context
from app.ai.prompts import (
    SOCIAL_MEDIA_POST_GENERATION_PROMPT,
    SOCIAL_MEDIA_SYSTEM_PROMPT,
)


def _opik_config_social(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build Opik config for social media generation."""
    from app.ai.opik import opik_tracer
    
    config: Dict[str, Any] = {"callbacks": [opik_tracer]}
    if extra:
        for key, value in extra.items():
            config[key] = value
    return config


@opik.track(name="Social Media Post Generation")
def generate_social_media_post(
    event_name: str,
    event_description: str,
    event_place: str,
    event_date: str,
    event_type: str,
    hashtags: Optional[list] = None
) -> Dict[str, str]:
    """
    Generate social media posts optimized for different platforms.
    
    Args:
        event_name: Name of the event
        event_description: Event description
        event_place: Event location
        event_date: Event date
        event_type: Type of event
        hashtags: List of relevant hashtags
    
    Returns:
        Dictionary with posts for different platforms
    """
    from app.ai.groq_client import get_chat_llm
    
    llm = get_chat_llm()
    
    hashtags_str = " ".join(hashtags) if hashtags else ""
    
    prompt = SOCIAL_MEDIA_POST_GENERATION_PROMPT.prompt.format(
        event_name=event_name,
        event_description=event_description,
        event_place=event_place,
        event_date=event_date,
        event_type=event_type,
        hashtags_str=hashtags_str,
    )

    response = llm.invoke([
        SystemMessage(content=SOCIAL_MEDIA_SYSTEM_PROMPT.prompt),
        HumanMessage(content=prompt)
    ], config=_opik_config_social())
    
    # Parse the response
    content = response.content.strip()
    posts = {
        "twitter": "",
        "instagram": "",
        "linkedin": ""
    }
    
    try:
        parts = content.split("---")
        for i, part in enumerate(parts):
            if i == 0:
                continue
            lines = part.strip().split("\n")
            if len(lines) > 0:
                platform = lines[0].lower()
                post_content = "\n".join(lines[1:]).strip()
                if platform in posts:
                    posts[platform] = post_content
    except Exception as e:
        print(f"Error parsing social media posts: {e}")
        posts["twitter"] = content[:280]
        posts["instagram"] = content[:150]
        posts["linkedin"] = content[:300]
    
    return posts


@opik.track(name="Fetch Trending Hashtags")
def fetch_trending_hashtags(event_type: str, event_name: str) -> list:
    """
    Fetch trending hashtags relevant to the event from social media insights.
    
    Args:
        event_type: Type of event
        event_name: Name of event
    
    Returns:
        List of relevant hashtags
    """
    from app.mcp.xpoz_mcp import xpoz_mcp_tool
    
    try:
        # Query social trends for relevant hashtags
        query = f"trending hashtags for {event_type} events related to {event_name}"
        result = xpoz_mcp_tool.invoke({"query": query})
        
        # Extract hashtags from result
        if isinstance(result, dict):
            hashtags = result.get("hashtags", [])
            if isinstance(hashtags, str):
                # Parse comma-separated hashtags
                hashtags = [h.strip() for h in hashtags.split(",") if h.strip()]
            return hashtags[:10]  # Return top 10
        elif isinstance(result, list):
            return result[:10]
        else:
            return []
    except Exception as e:
        print(f"Error fetching trending hashtags: {e}")
        # Fallback hashtags based on event type
        fallback_tags = {
            "eco": ["#sustainability", "#ecofriendly", "#greeninitiative", "#climateaction"],
            "wellness": ["#wellness", "#health", "#community", "#wellbeing"],
            "social": ["#community", "#socialevents", "#neighbors", "#apartmentlife"],
            "networking": ["#networking", "#community", "#events", "#professional"],
            "learning": ["#learning", "#education", "#community", "#growth"],
            "charity": ["#charity", "#giveback", "#community", "#impact"],
            "sports": ["#sports", "#fitness", "#community", "#active"]
        }
        return fallback_tags.get(event_type.lower(), ["#community", "#event", "#local"])


@opik.track(name="Collect Post Feedback")
def collect_post_feedback(
    post_type: str,
    post_content: str,
    thread_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a feedback collection point for social media posts.
    
    Args:
        post_type: Type of post (twitter, instagram, linkedin)
        post_content: The generated post content
        thread_id: Thread ID for Opik tracking
    
    Returns:
        Feedback object with metadata
    """
    feedback_obj = {
        "post_type": post_type,
        "post_content": post_content,
        "feedback_score": None,
        "feedback_reason": None,
        "thread_id": thread_id
    }
    
    # Update Opik context with post generation
    try:
        opik_context.update_current_trace(
            metadata={
                "post_type": post_type,
                "thread_id": thread_id,
                "event": "social_media_post_generated"
            }
        )
    except Exception as e:
        print(f"Error updating Opik context: {e}")
    
    return feedback_obj


def social_media_generation_node(state):
    """
    Node for generating social media posts for the created event.
    
    This node:
    1. Fetches trending hashtags relevant to the event
    2. Generates platform-specific social media posts
    3. Prepares feedback collection
    """
    event_name = state.get("event_name", "Event")
    event_description = state.get("description", "")
    event_place = state.get("place", "")
    event_date = state.get("date", "")
    event_type = state.get("event_type", "community")
    thread_id = state.get("thread_id")
    
    # Step 1: Fetch trending hashtags
    hashtags = fetch_trending_hashtags(event_type, event_name)
    
    # Step 2: Generate social media posts
    posts = generate_social_media_post(
        event_name=event_name,
        event_description=event_description,
        event_place=event_place,
        event_date=event_date,
        event_type=event_type,
        hashtags=hashtags
    )
    
    # Step 3: Format response for user
    response_msg = f"""📱 **Social Media Posts Generated!**

Here are platform-optimized posts for your event:

**🐦 Twitter:**
{posts.get('twitter', 'N/A')}

**📷 Instagram:**
{posts.get('instagram', 'N/A')}

**💼 LinkedIn:**
{posts.get('linkedin', 'N/A')}

**Hashtags Used:** {" ".join(hashtags[:5])}

Would you like me to:
- Refine any of these posts?
- Generate more post variations?
- Create a posting schedule?
- Help with event promotion?"""
    
    # Store posts and hashtags in state for feedback
    return {
        "messages": [AIMessage(content=response_msg)],
        "social_media_posts": posts,
        "social_media_hashtags": hashtags,
        "social_media_feedback": []
    }


def ask_post_feedback_node(state):
    """Ask user for feedback on generated social media posts."""
    return {
        "messages": [AIMessage(
            content="How do you feel about these posts? Any changes you'd like me to make?"
        )]
    }


def handle_post_feedback_node(state):
    """Handle and store feedback on social media posts."""
    feedback_text = state["messages"][-1].content
    thread_id = state.get("thread_id")
    
    # Record feedback in Opik
    try:
        @opik.track(name="Social Media Post Feedback")
        def record_feedback():
            opik_context.update_current_trace(
                metadata={
                    "thread_id": thread_id,
                    "feedback_type": "social_media_post",
                    "feedback_content": feedback_text[:500]  # Limit to 500 chars
                },
                feedback_scores=[{
                    "name": "post_quality",
                    "value": 0.5,  # Neutral, user is providing input
                    "reason": "User feedback on generated posts"
                }]
            )
        record_feedback()
    except Exception as e:
        print(f"Error recording feedback: {e}")
    
    return {
        "messages": [AIMessage(content="Thanks for the feedback! I'll refine the posts based on your suggestions.")]
    }
