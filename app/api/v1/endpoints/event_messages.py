"""
API endpoints for Event Messages
"""
from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
import json
from datetime import datetime

from app.database import get_db, SessionLocal
from app.api.v1.endpoints import events
from app.crud import event_message as event_message_crud
from app.crud import event as event_crud
from app.crud import event_user as event_user_crud
from app.schemas.event_message import EventMessageCreate, EventMessageOut
from app.dependencies import get_current_active_user
from app.models.user import User
from googletrans import Translator

translator = Translator()

router = APIRouter(prefix="/messages", tags=["event-messages"])


class ConnectionManager:
    def __init__(self):
        # Map event_id to a list of (WebSocket, User) tuples
        self.active_connections: Dict[str, List[tuple]] = {}

    async def connect(self, websocket: WebSocket, event_id: str, user: User):
        await websocket.accept()
        if event_id not in self.active_connections:
            self.active_connections[event_id] = []
        self.active_connections[event_id].append((websocket, user))

    def disconnect(self, websocket: WebSocket, event_id: str):
        if event_id in self.active_connections:
            self.active_connections[event_id] = [
                (ws, u) for ws, u in self.active_connections[event_id] if ws != websocket
            ]
            if not self.active_connections[event_id]:
                del self.active_connections[event_id]

    async def broadcast(self, message: dict, event_id: str):
        """Broadcast message to all connections, translating to each user's language."""
        if event_id in self.active_connections:
            # Convert datetime objects to string for JSON serialization
            if "created_at" in message and isinstance(message["created_at"], datetime):
                message["created_at"] = message["created_at"].isoformat()
            
            original_text = message.get("message", "")
            
            for websocket, user in self.active_connections[event_id]:
                try:
                    print(user.lang)
                    # Translate message if user has a preferred language
                    user_lang = getattr(user, 'lang', None) or 'en'
                    translated_text = original_text
                    if user_lang and user_lang != 'en':
                        try:
                            translation = await translator.translate(original_text, dest=user_lang)
                            translated_text = translation.text
                        except Exception as translate_err:
                            print(f"Translation error: {translate_err}")
                            # Fall back to original text
                    
                    # Create a copy of the message with translated text
                    user_message = message.copy()
                    user_message["message"] = translated_text
                    
                    json_msg = json.dumps(user_message)
                    await websocket.send_text(json_msg)
                except Exception:
                    # Handle broken connections gracefully
                    pass

manager = ConnectionManager()


async def handle_ai_request(event_id: str, prompt: str, db_session_factory, user_id: int):
    """Process AI request asynchronously and broadcast response."""
    from app.ai.event_manager_agent import get_event_manager_agent
    from app.ai.groq_client import get_connection_pool
    from langchain_core.messages import HumanMessage
    
    try:
        pool = get_connection_pool()
        with pool.connection() as conn:
             agent = get_event_manager_agent(conn)
             
             # Config - use a unique thread per event-user interaction context or just event context
             config = {"configurable": {"thread_id": f"event_{event_id}_ai_interaction"}}
             
             # Invoke Agent
             # Since invoke is synchronous (LangGraph default execution), we run it in a thread to verify
             # But ChatGroq/LangGraph usually handle IO well. 
             # For safety in this async loop, we use direct invocation as LangGraph steps are generally sync unless using async version
             
             # IMPORTANT: To make it truly async non-blocking, we should use aconvoke if available or run_in_executor
             # For now, simplistic invocation:
             response = agent.invoke(
                 {
                    "messages": [HumanMessage(content=prompt)],
                    "event_id": event_id,
                    "thread_id": config["configurable"]["thread_id"],
                 },
                 config=config
             )
             
             ai_message = response["messages"][-1].content
             
             # Save AI response to DB
             with db_session_factory() as db:
                 # Need to get the actual Event PK ID from the string public ID
                 # Since event_messages uses ForeignKey("events.id") which is Integer
                 from app.crud import event as event_crud_module
                 event_obj = event_crud_module.get_event_by_event_id(db, event_id)
                 
                 if event_obj:
                     saved_msg = event_message_crud.create_message(
                        db, 
                        message_in=EventMessageCreate(message=f"{ai_message}"), 
                        user_id=user_id, 
                        event_id=event_obj.id  # Pass the Integer PK
                    )
                     
                     # Broadcast
                     # We still use the string event_id for the WS channel
                     response_msg = {
                        "id": saved_msg.id,
                        "event_id": event_id,
                        "user_id": user_id, 
                        "username": "AI Agent", # Override display name
                        "full_name": "Event Manager AI",
                        "message": saved_msg.message,
                        "created_at": saved_msg.created_at
                     }
                     await manager.broadcast(response_msg, event_id)
                 else:
                     print(f"AI Agent Error: Event {event_id} not found for saving message.")

    except Exception as e:
        print(f"AI Agent Error: {e}")
        error_msg = {
            "id": 0,
            "event_id": event_id,
            "user_id": 4,
            "username": "AI Agent",
            "full_name": "Event Manager AI",
            "message": f"Error processing request!! sorry",
            "created_at": datetime.now().isoformat()
        }
        await manager.broadcast(error_msg, event_id)


@router.websocket("/ws/{event_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    event_id: str,
    token: str = Query(...),  # Pass token as query param since headers are limited in WS
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time event chat.
    Requires 'token' query parameter for authentication.
    """
    # Authenticate user (simplified logic for WS)
    # in a real app, you'd decode the token here. 
    # For now, we'll try to get user from a temporary dependency or simple token check
    # But Depends(get_current_active_user) doesn't work easily with WS out of the box
    # due to header parsing.
    
    # We will assume client passes user_id for this demo or use a helper
    # For proper auth, we normally use a deps override or manual token verification
    from app.core import security
    from jose import jwt
    from app.core.config import settings
    
    user = None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_from_token = payload.get("sub")
        if user_id_from_token is not None:
             # Use a new DB session for async-like context if needed, or the injected one
            user = db.query(User).filter(User.id == int(user_id_from_token)).first()
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Verify event membership
    event = event_crud.get_event_by_event_id(db, event_id)
    if not event:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    is_member = event_user_crud.is_attending(db, event, user.id)
    if not is_member:
        # Just close connection if not member
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, event_id, user)
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            message_text = message_data.get("message")
            
            if message_text:
                # Save to DB
                # Note: creating new session for DB ops in loop is safer in some async setups
                # but 'db' from dependency usually works if careful. 
                # Ideally use async DB or run_in_executor for blocking calls.
                # For this simple setup, we use the existing sync crud.
                
                saved_msg = event_message_crud.create_message(
                    db, 
                    message_in=EventMessageCreate(message=message_text), 
                    user_id=user.id, 
                    event_id=event.id
                )
                
                # prepare broadcast message
                response_msg = {
                    "id": saved_msg.id,
                    "event_id": event.id,
                    "user_id": user.id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "message": saved_msg.message,
                    "created_at": saved_msg.created_at
                }
                
                await manager.broadcast(response_msg, event_id)
                
                # Check for AI Trigger
                trigger = "@AI"
                if message_text.strip().upper().startswith(trigger):
                    prompt = message_text.strip()[len(trigger):].strip()
                    if prompt:
                        # Call Agent asynchronously
                        import asyncio
                        # We pass SessionLocal so the async task can create its own DB session
                        # We use the current user_id for context
                        asyncio.create_task(
                            handle_ai_request(event_id, prompt, SessionLocal, 4)
                        )
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, event_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, event_id)

@router.post("/{event_id}", response_model=EventMessageOut)
def post_event_message(
    event_id: str,
    message_in: EventMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Post a message to an event's discussion board.
    User must have joined the event.
    """
    # Verify event exists
    event = event_crud.get_event_by_event_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    # Verify user has joined the event (optional but recommended)
    is_member = event_user_crud.is_attending(db, event, current_user.id)
    if not is_member:
        raise HTTPException(status_code=403, detail="You must join the event to post messages")

    # Create message
    message = event_message_crud.create_message(
        db, message_in=message_in, user_id=current_user.id, event_id=event.id
    )
    
    # Enrich with user details
    msg_out = EventMessageOut.from_orm(message)
    msg_out.username = current_user.username
    msg_out.full_name = current_user.full_name
    
    # Also broadcast via WebSocket!
    # Using async_to_sync or similar if needed, but since this is a sync endpoint, 
    # we can't easily await manager.broadcast(). 
    # For now, we rely on the WS clients sending messages via WS connection for real-time.
    # HTTP posts won't trigger WS broadcast in this simple implementation unless we use background tasks.
    
    return msg_out


@router.get("/{event_id}", response_model=List[EventMessageOut])
async def list_event_messages(
    event_id: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get messages for an event.
    """
    event = event_crud.get_event_by_event_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    messages = event_message_crud.get_event_messages(db, event_id=event.id, skip=skip, limit=limit)
    
    # Get user's preferred language
    user_lang = getattr(current_user, 'lang', None) or 'en'
    
    # Enrich with user details and translate messages
    results = []
    for msg in messages:
        try:
            msg_out = EventMessageOut.from_orm(msg)
            msg_out.username = msg.user.username
            msg_out.full_name = msg.user.full_name
            
            # Translate message if user has a preferred language other than English
            if user_lang and user_lang != 'en':
                try:
                    translation = await translator.translate(msg.message, dest=user_lang)
                    msg_out.message = translation.text
                except Exception as translate_err:
                    print(f"Translation error: {translate_err}")
                    # Fall back to original message
            
            results.append(msg_out)
        except Exception:
            continue
            
    return results
