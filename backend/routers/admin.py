"""
MELCO-Care Admin Router
Endpoints for hospital and system administration
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session

from database.connection import get_session
from database.models import Hospital, Department, User, UserRole
from backend.services.database_service import get_database_service
from backend.services.vlm_service import get_vlm_service


router = APIRouter()


# ============== PYDANTIC MODELS ==============

class HospitalResponse(BaseModel):
    hospital_id: int
    name: str
    city: str
    locality: str
    total_beds: int
    occupied_beds: int
    available_beds: int
    is_government: bool


class UpdateBedsRequest(BaseModel):
    occupied_beds: int


class DepartmentResponse(BaseModel):
    dept_id: int
    name: str
    is_emergency: bool
    is_active: bool


class UserResponse(BaseModel):
    user_id: int
    name: str
    role: str
    city: str
    age: int
    gender: str


class SystemStatusResponse(BaseModel):
    database_status: str
    ollama_status: str
    models_available: List[str]
    total_users: int
    total_hospitals: int


# ============== ENDPOINTS ==============

@router.get("/hospitals", response_model=List[HospitalResponse])
async def list_hospitals(city: Optional[str] = None):
    """List all hospitals, optionally filtered by city"""
    db_service = get_database_service()
    try:
        if city:
            hospitals = db_service.get_hospitals_by_city(city)
        else:
            hospitals = db_service.get_all_hospitals()
        
        return [
            HospitalResponse(
                hospital_id=h.hospital_id,
                name=h.name,
                city=h.city,
                locality=h.locality,
                total_beds=h.total_beds,
                occupied_beds=h.occupied_beds,
                available_beds=h.total_beds - h.occupied_beds,
                is_government=h.is_government
            )
            for h in hospitals
        ]
    finally:
        db_service.close()


@router.get("/hospitals/{hospital_id}", response_model=HospitalResponse)
async def get_hospital(hospital_id: int):
    """Get hospital details by ID"""
    db_service = get_database_service()
    try:
        hospital = db_service.get_hospital_by_id(hospital_id)
        if not hospital:
            raise HTTPException(status_code=404, detail="Hospital not found")
        
        return HospitalResponse(
            hospital_id=hospital.hospital_id,
            name=hospital.name,
            city=hospital.city,
            locality=hospital.locality,
            total_beds=hospital.total_beds,
            occupied_beds=hospital.occupied_beds,
            available_beds=hospital.total_beds - hospital.occupied_beds,
            is_government=hospital.is_government
        )
    finally:
        db_service.close()


@router.patch("/hospitals/{hospital_id}/beds")
async def update_beds(hospital_id: int, request: UpdateBedsRequest):
    """Update occupied beds count for a hospital"""
    db_service = get_database_service()
    try:
        hospital = db_service.update_hospital_beds(hospital_id, request.occupied_beds)
        if not hospital:
            raise HTTPException(status_code=404, detail="Hospital not found")
        
        return {
            "message": "Beds updated successfully",
            "hospital_id": hospital.hospital_id,
            "occupied_beds": hospital.occupied_beds,
            "available_beds": hospital.total_beds - hospital.occupied_beds
        }
    finally:
        db_service.close()


@router.get("/hospitals/{hospital_id}/departments", response_model=List[DepartmentResponse])
async def list_departments(hospital_id: int):
    """List departments in a hospital"""
    db_service = get_database_service()
    try:
        departments = db_service.get_departments_by_hospital(hospital_id)
        return [
            DepartmentResponse(
                dept_id=d.dept_id,
                name=d.name.value,
                is_emergency=d.is_emergency,
                is_active=d.is_active
            )
            for d in departments
        ]
    finally:
        db_service.close()


@router.get("/users", response_model=List[UserResponse])
async def list_users(role: Optional[str] = None):
    """List users, optionally filtered by role"""
    db_service = get_database_service()
    try:
        if role:
            try:
                user_role = UserRole(role.lower())
                users = db_service.get_users_by_role(user_role)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid role")
        else:
            # Get all users (combine all roles)
            users = []
            for r in UserRole:
                users.extend(db_service.get_users_by_role(r))
        
        return [
            UserResponse(
                user_id=u.user_id,
                name=u.name,
                role=u.role.value,
                city=u.city,
                age=u.age,
                gender=u.gender.value
            )
            for u in users
        ]
    finally:
        db_service.close()


@router.get("/status", response_model=SystemStatusResponse)
async def system_status():
    """Get system status including Ollama availability"""
    db_service = get_database_service()
    vlm_service = get_vlm_service()
    
    try:
        # Check Ollama
        ollama_status = vlm_service.check_ollama_status()
        
        # Count users and hospitals
        users = []
        for r in UserRole:
            users.extend(db_service.get_users_by_role(r))
        hospitals = db_service.get_all_hospitals()
        
        return SystemStatusResponse(
            database_status="online",
            ollama_status=ollama_status.get("status", "unknown"),
            models_available=ollama_status.get("models_available", []),
            total_users=len(users),
            total_hospitals=len(hospitals)
        )
    finally:
        db_service.close()
