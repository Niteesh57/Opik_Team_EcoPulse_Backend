import requests
from app.core.config import settings
from typing import Optional
import requests
import base64
import time
from app.core.config import settings

def image_request(description: str) -> str:
    """Request image generation from DeAPI.
    
    Returns:
        The request_id for tracking, or None if the request fails.
    """
    url = "https://api.deapi.ai/api/v1/client/txt2img"

    headers = {
        "Authorization": "Bearer " + (settings.DEAPI_TOKEN or ""),
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "prompt": f"Event poster for: {description}. Professional, vibrant, community event style.",
        "model": "Flux1schnell",
        "width": 512,
        "height": 512,
        "steps": 4,
        "guidance": 0,
        "seed": 12345,
        "loras": [],
        "webhook_url": settings.WEBHOOK_URL  # Optional: Set if you want DeAPI to call back when done
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        data = response.json()
        
        # Handle different response structures
        if "data" in data and "request_id" in data["data"]:
            return data["data"]["request_id"]
        elif "request_id" in data:
            return data["request_id"]
        else:
            print(f"Image API unexpected response: {data}")
            return None
    except Exception as e:
        print(f"Image request failed: {e}")
        return None



def image_request_promote_refine(description: str) -> Optional[str]:
    """Generate an image via DeAPI and return the final image URL."""

    create_url = "https://api.deapi.ai/api/v1/client/txt2img"
    status_url = "https://api.deapi.ai/api/v1/client/request-status/{}"

    headers = {
        "Authorization": "Bearer " + (settings.DEAPI_TOKEN or ""),
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "prompt": (
            f"Event poster for: {description}. "
            "Professional, vibrant, community event style. "
            "Mention event name, date, time, location, description, and tags if available."
        ),
        "model": "Flux1schnell",
        "width": 512,
        "height": 512,
        "steps": 4,
        "guidance": 0,
        "seed": 12345,
        "loras": []
    }

    try:
        response = requests.post(create_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        request_id = data.get("data", {}).get("request_id")
        if not request_id:
            print("No request_id returned:", data)
            return None

        for _ in range(10):  # ~60 seconds max
            time.sleep(2)

            status_response = requests.get(
                status_url.format(request_id),
                headers=headers,
                timeout=15
            )
            status_data = status_response.json().get("data", {})

            if status_data.get("status") == "done":
                url = upload_image_to_imgbb(status_data.get("result_url"))
                return url

            if status_data.get("status") == "failed":
                print("Image generation failed:", status_data)
                return None

        print("Image generation timed out")
        return None

    except Exception as e:
        print(f"Image generation error: {e}")
        return None

def upload_image_to_imgbb(image_url: str) -> str:
    response = requests.get(image_url, timeout=30)
    response.raise_for_status()

    image_base64 = base64.b64encode(response.content)

    upload = requests.post(
        "https://api.imgbb.com/1/upload",
        data={
            "key": settings.IMGBB_API_KEY,
            "image": image_base64
        },
        timeout=30
    )
    upload.raise_for_status()

    return upload.json()["data"]["url"]
