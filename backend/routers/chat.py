"""
MELCO-Care Chat Router
Main /chat endpoint for user interactions
"""

import os
import uuid
import shutil
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from backend.agents.orchestrator import get_orchestrator_agent
from backend.agents.appointment import get_appointment_agent
from backend.services.database_service import get_database_service


router = APIRouter()

# Directory for uploaded images
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ============== PYDANTIC MODELS ==============

class ChatRequest(BaseModel):
    user_id: int
    message: str
    session_id: Optional[int] = None


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: str


class ChatResponse(BaseModel):
    success: bool
    response: str
    intent: Optional[str] = None
    suggested_department: Optional[str] = None
    priority: Optional[str] = None
    doctor_options: Optional[List[dict]] = None
    action_data: Optional[dict] = None


class BookAppointmentRequest(BaseModel):
    user_id: int
    doctor_id: int
    symptoms: str
    symptoms_summary: str
    priority: str = "medium"


class BookAppointmentResponse(BaseModel):
    success: bool
    appointment_id: Optional[int] = None
    token_number: Optional[int] = None
    doctor_name: Optional[str] = None
    message: str


# ============== ENDPOINTS ==============

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint - handles text-only messages
    """
    orchestrator = get_orchestrator_agent()
    db_service = get_database_service()
    
    try:
        # Get or create chat session
        chat_session = db_service.get_or_create_chat_session(request.user_id)
        
        # Get chat history for context
        history = db_service.get_chat_history(chat_session.session_id, limit=5)
        chat_history = [
            {"role": msg.role, "content": msg.content}
            for msg in history
        ]
        
        # Save user message
        db_service.add_chat_message(
            session_id=chat_session.session_id,
            role="user",
            content=request.message
        )
        
        # Process request through orchestrator
        result = orchestrator.process_request(
            user_id=request.user_id,
            message=request.message,
            image_path=None,
            chat_history=chat_history
        )
        
        # Save assistant response
        db_service.add_chat_message(
            session_id=chat_session.session_id,
            role="assistant",
            content=result.get("response", "")
        )
        
        # Extract doctor options if available
        doctor_options = None
        action_data = result.get("action_taken")
        if action_data and action_data.get("action") == "appointment_suggestion":
            doctor_options = action_data.get("doctor_options", [])
        
        return ChatResponse(
            success=result.get("success", False),
            response=result.get("response", "Sorry, I couldn't process your request."),
            intent=result.get("intent"),
            suggested_department=result.get("suggested_department"),
            priority=result.get("priority"),
            doctor_options=doctor_options,
            action_data=action_data
        )
    
    finally:
        orchestrator.close()
        db_service.close()


@router.post("/chat/with-image", response_model=ChatResponse)
async def chat_with_image(
    user_id: int = Form(...),
    message: str = Form(...),
    image: UploadFile = File(...)
):
    """
    Chat endpoint with image upload support
    """
    orchestrator = get_orchestrator_agent()
    db_service = get_database_service()
    
    try:
        # Save uploaded image
        image_filename = f"{uuid.uuid4()}_{image.filename}"
        image_path = os.path.join(UPLOAD_DIR, image_filename)
        
        with open(image_path, "wb") as f:
            shutil.copyfileobj(image.file, f)
        
        # Get or create chat session
        chat_session = db_service.get_or_create_chat_session(user_id)
        
        # Get chat history
        history = db_service.get_chat_history(chat_session.session_id, limit=5)
        chat_history = [
            {"role": msg.role, "content": msg.content}
            for msg in history
        ]
        
        # Save user message with image
        db_service.add_chat_message(
            session_id=chat_session.session_id,
            role="user",
            content=message,
            image_path=image_path
        )
        
        # Process request with image
        result = orchestrator.process_request(
            user_id=user_id,
            message=message,
            image_path=image_path,
            chat_history=chat_history
        )
        
        # Save assistant response
        db_service.add_chat_message(
            session_id=chat_session.session_id,
            role="assistant",
            content=result.get("response", "")
        )
        
        # Extract doctor options
        doctor_options = None
        action_data = result.get("action_taken")
        if action_data and action_data.get("action") == "appointment_suggestion":
            doctor_options = action_data.get("doctor_options", [])
        
        return ChatResponse(
            success=result.get("success", False),
            response=result.get("response", "Sorry, I couldn't process your request."),
            intent=result.get("intent"),
            suggested_department=result.get("suggested_department"),
            priority=result.get("priority"),
            doctor_options=doctor_options,
            action_data=action_data
        )
    
    finally:
        orchestrator.close()
        db_service.close()


@router.post("/book-appointment", response_model=BookAppointmentResponse)
async def book_appointment(request: BookAppointmentRequest):
    """
    Confirm and book an appointment
    """
    appointment_agent = get_appointment_agent()
    
    try:
        result = appointment_agent.book_appointment(
            user_id=request.user_id,
            doctor_id=request.doctor_id,
            symptoms_raw=request.symptoms,
            symptoms_summary=request.symptoms_summary,
            priority=request.priority
        )
        
        return BookAppointmentResponse(
            success=result.get("success", False),
            appointment_id=result.get("appointment_id"),
            token_number=result.get("token_number"),
            doctor_name=result.get("doctor_name"),
            message=result.get("message", result.get("error", "Failed to book appointment"))
        )
    
    finally:
        appointment_agent.close()


@router.get("/appointments/{user_id}")
async def get_appointments(user_id: int):
    """
    Get all appointments for a user
    """
    appointment_agent = get_appointment_agent()
    
    try:
        result = appointment_agent.get_patient_appointments(user_id)
        return result
    
    finally:
        appointment_agent.close()


@router.get("/chat/history/{user_id}")
async def get_chat_history(user_id: int, limit: int = 20):
    """
    Get chat history for a user
    """
    db_service = get_database_service()
    
    try:
        chat_session = db_service.get_or_create_chat_session(user_id)
        messages = db_service.get_chat_history(chat_session.session_id, limit=limit)
        
        return {
            "session_id": chat_session.session_id,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "has_image": msg.image_path is not None
                }
                for msg in messages
            ]
        }
    
    finally:
        db_service.close()
