"""Webhook endpoints for external service callbacks."""
import json
from typing import Optional
import base64
import requests
from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.event import Event
from app.utils.image import upload_image_to_imgbb

router = APIRouter()


class DeAPIWebhookPayload(BaseModel):
    """Payload structure for DeAPI image generation webhook."""
    request_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None



@router.post("/deapi/image", status_code=status.HTTP_200_OK)
async def deapi_image_webhook(request: Request):
    try:
        payload = await request.json()
        print(f"DeAPI Webhook received: {json.dumps(payload)}")

        data = payload.get("data", {})

        request_id = (
            data.get("job_request_id")
            or data.get("request_id")
            or payload.get("job_request_id")
            or payload.get("request_id")
        )

        status_value = data.get("status") or payload.get("status")

        image_url = (
            data.get("result_url")
            or payload.get("result_url")
            or data.get("image_url")
            or payload.get("image_url")
        )

        if not request_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing job_request_id"
            )

        with SessionLocal() as db:
            event = db.query(Event).filter(
                Event.image_request_id == request_id
            ).first()

            if not event:
                return {
                    "status": "acknowledged",
                    "message": f"No event found for request_id {request_id}"
                }

            if status_value == "done" and image_url:
                # 🔥 Upload to ImgBB and get public URL
                public_url = upload_image_to_imgbb(image_url)

                # ✅ Save ONLY the URL
                event.event_image_url = public_url
                db.commit()

                return {
                    "status": "success",
                    "event_id": event.event_id,
                    "image_url": public_url
                }

            if status_value == "failed":
                return {
                    "status": "failed",
                    "event_id": event.event_id,
                    "error": payload.get("error")
                }

            return {
                "status": "acknowledged",
                "message": f"Webhook received, status: {status_value}"
            }

    except Exception as exc:
        print(f"Webhook error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing error"
        )



@router.get("/deapi/image/status/{request_id}")
async def check_image_status(request_id: str):
    """
    Check the status of an image generation request.
    
    This endpoint allows polling for image status if webhooks fail.
    """
    with SessionLocal() as db:
        event = db.query(Event).filter(Event.image_request_id == request_id).first()
        
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No event found with request_id: {request_id}"
            )
        
        return {
            "event_id": event.event_id,
            "request_id": request_id,
            "has_image": bool(event.event_image_url),
            "image_url": event.event_image_url
        }

@router.get("/alert")
async def opik():
    try:
        print("Received alert webhook")
        return {
            "output": {"message": "Alert received successfully!"},  # You can customize this response as needed 
        }
    except Exception as e:
        return {
            "output": {"error": str(e)},
        }