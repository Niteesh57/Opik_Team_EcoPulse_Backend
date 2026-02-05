"""Social media tools for event promotion and post generation."""
from langchain_core.tools import tool
import json
from typing import Optional


@tool
def create_social_media_posts(
    event_name: str,
    event_description: str,
    event_place: str,
    event_date: str,
    event_type: str,
    hashtags: Optional[str] = None
) -> str:
    """
    Create optimized social media posts for an event across multiple platforms.
    
    This tool generates platform-specific posts for:
    - Twitter (280 characters)
    - Instagram (150 characters with emojis)
    - LinkedIn (300 characters, professional)
    
    Args:
        event_name: Name of the event
        event_description: Brief description of the event
        event_place: Location/venue of the event
        event_date: Date of the event (e.g., "February 15, 2026")
        event_type: Type of event (e.g., "eco", "wellness", "social", "networking")
        hashtags: Optional comma-separated hashtags to include (e.g., "#sustainability,#community")
    
    Returns:
        JSON string containing posts for each platform
    
    Example:
        create_social_media_posts(
            event_name="Community Recycling Drive",
            event_description="Join us for a community-wide recycling initiative",
            event_place="Central Park, Building A",
            event_date="February 15, 2026",
            event_type="eco",
            hashtags="#sustainability,#ecofriendly"
        )
    """
    from app.ai.social_media_node import (
        generate_social_media_post,
        fetch_trending_hashtags
    )
    
    try:
        # Parse hashtags if provided
        hashtag_list = None
        if hashtags:
            hashtag_list = [h.strip() for h in hashtags.split(",") if h.strip()]
        
        # If no hashtags provided, fetch trending ones
        if not hashtag_list:
            hashtag_list = fetch_trending_hashtags(event_type, event_name)
        
        # Generate posts
        posts = generate_social_media_post(
            event_name=event_name,
            event_description=event_description,
            event_place=event_place,
            event_date=event_date,
            event_type=event_type,
            hashtags=hashtag_list
        )
        
        return json.dumps({
            "status": "success",
            "event_name": event_name,
            "posts": posts,
            "hashtags": hashtag_list[:5],
            "message": "Social media posts generated successfully!"
        }, indent=2)
    
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to generate social media posts: {str(e)}"
        }, indent=2)


@tool
def get_trending_hashtags(event_type: str, event_name: str) -> str:
    """
    Fetch trending hashtags relevant to an event type.
    
    Args:
        event_type: Type of event (eco, wellness, social, networking, learning, charity, sports)
        event_name: Name of the event
    
    Returns:
        JSON string containing list of trending hashtags
    
    Example:
        get_trending_hashtags(
            event_type="eco",
            event_name="Community Sustainability Workshop"
        )
    """
    from app.ai.social_media_node import fetch_trending_hashtags
    
    try:
        hashtags = fetch_trending_hashtags(event_type, event_name)
        return json.dumps({
            "status": "success",
            "event_type": event_type,
            "hashtags": hashtags,
            "message": f"Found {len(hashtags)} trending hashtags"
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to fetch hashtags: {str(e)}"
        }, indent=2)


@tool
def refine_social_media_post(
    post_content: str,
    platform: str,
    refinement_request: str
) -> str:
    """
    Refine an existing social media post based on user feedback.
    
    Args:
        post_content: The original post content to refine
        platform: Target platform (twitter, instagram, or linkedin)
        refinement_request: Description of changes needed (e.g., "make it more energetic", "add more emojis")
    
    Returns:
        JSON string containing the refined post
    
    Example:
        refine_social_media_post(
            post_content="Join our event on Feb 15!",
            platform="instagram",
            refinement_request="Add more emojis and make it fun"
        )
    """
    from app.ai.groq_client import get_chat_llm
    from langchain_core.messages import SystemMessage, HumanMessage
    
    try:
        llm = get_chat_llm()
        
        # Character limits per platform
        char_limits = {
            "twitter": 280,
            "instagram": 150,
            "linkedin": 300
        }
        
        char_limit = char_limits.get(platform.lower(), 280)
        
        prompt = f"""Refine this social media post for {platform.upper()} based on the feedback provided.

Original Post:
{post_content}

Refinement Request:
{refinement_request}

Requirements:
- Maximum {char_limit} characters
- Platform: {platform}
- Maintain the core message
- Be engaging and professional

Provide ONLY the refined post, nothing else."""
        
        response = llm.invoke([
            SystemMessage(content=f"You are an expert social media manager for {platform}. Refine posts to be more engaging while respecting character limits."),
            HumanMessage(content=prompt)
        ])
        
        refined_post = response.content.strip()
        
        return json.dumps({
            "status": "success",
            "platform": platform,
            "original": post_content,
            "refined": refined_post,
            "character_count": len(refined_post),
            "character_limit": char_limit,
            "within_limit": len(refined_post) <= char_limit,
            "message": "Post refined successfully!"
        }, indent=2)
    
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to refine post: {str(e)}"
        }, indent=2)


# Export all social media tools
SocialMediaTools = [
    create_social_media_posts,
    get_trending_hashtags,
    refine_social_media_post
]
