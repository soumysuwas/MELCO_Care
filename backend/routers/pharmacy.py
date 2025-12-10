"""
MELCO-Care Pharmacy API Router
Endpoints for prescription validation and medicine search
"""

import os
import shutil
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from pydantic import BaseModel

from backend.agents.pharmacy import get_pharmacy_agent


router = APIRouter(prefix="/pharmacy", tags=["Pharmacy"])


# ============== MODELS ==============

class MedicineSearchRequest(BaseModel):
    """Request model for medicine search"""
    user_id: int
    medicines: List[str]
    max_distance_km: float = 10.0
    city: str = "Hyderabad"


class MedicineItem(BaseModel):
    """Single medicine in search results"""
    name: str
    salt: Optional[str]
    price: Optional[float]
    stock: int
    in_stock: bool
    requires_prescription: bool


class PharmacyResult(BaseModel):
    """Pharmacy with medicine availability"""
    pharmacy_id: int
    name: str
    address: str
    locality: str
    distance_km: float
    operating_hours: str
    is_24hr: bool
    phone: Optional[str]
    medicines: List[MedicineItem]
    all_available: bool
    available_count: int


class MedicineSearchResponse(BaseModel):
    """Response model for medicine search"""
    success: bool
    pharmacies: List[PharmacyResult]
    all_found: bool
    missing_medicines: List[str]
    total_pharmacies_searched: int


class PrescriptionValidationResponse(BaseModel):
    """Response model for prescription validation"""
    success: bool
    valid: bool
    extracted_data: Optional[dict]
    doctor_verified: bool
    date_valid: Optional[bool]
    error: Optional[str]
    medicines: Optional[List[str]]


# ============== ENDPOINTS ==============

@router.post("/validate-prescription", response_model=PrescriptionValidationResponse)
async def validate_prescription(
    user_id: int = Form(...),
    image: UploadFile = File(...)
):
    """
    Validate a prescription image
    
    - Extracts patient, doctor, medicines via OCR
    - Verifies doctor registration number
    - Checks prescription date validity
    """
    # Save uploaded image
    upload_dir = Path("uploads/prescriptions")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"prescription_{user_id}_{timestamp}_{image.filename}"
    file_path = upload_dir / filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save image: {str(e)}")
    
    # Validate prescription
    pharmacy_agent = get_pharmacy_agent()
    result = pharmacy_agent.validate_prescription(
        image_path=str(file_path),
        user_id=user_id
    )
    
    # Extract medicine names for easy access
    medicines = []
    if result.get("extracted_data") and result["extracted_data"].get("medicines"):
        medicines = [m.get("name") for m in result["extracted_data"]["medicines"] if m.get("name")]
    
    return PrescriptionValidationResponse(
        success=result.get("valid", False),
        valid=result.get("valid", False),
        extracted_data=result.get("extracted_data"),
        doctor_verified=result.get("doctor_verified", False),
        date_valid=result.get("date_valid"),
        error=result.get("error"),
        medicines=medicines
    )


@router.post("/search", response_model=MedicineSearchResponse)
async def search_medicines(request: MedicineSearchRequest):
    """
    Search for medicines at nearby pharmacies
    
    - Searches by medicine name or salt composition
    - Sorts by availability and distance
    - Returns top 10 pharmacies
    """
    if not request.medicines:
        raise HTTPException(status_code=400, detail="At least one medicine name is required")
    
    pharmacy_agent = get_pharmacy_agent()
    
    # Default coordinates for Hyderabad (center)
    user_lat = 17.385
    user_lon = 78.486
    
    result = pharmacy_agent.search_medicines(
        medicine_names=request.medicines,
        user_lat=user_lat,
        user_lon=user_lon,
        max_distance_km=request.max_distance_km,
        city=request.city
    )
    
    return MedicineSearchResponse(
        success=True,
        pharmacies=result.get("pharmacies", []),
        all_found=result.get("all_found", False),
        missing_medicines=result.get("missing_medicines", []),
        total_pharmacies_searched=result.get("total_pharmacies_searched", 0)
    )


@router.get("/recommendations/{user_id}")
async def get_pharmacy_recommendations(
    user_id: int,
    medicines: str,  # Comma-separated list
    city: str = "Hyderabad"
):
    """
    Get formatted pharmacy recommendations
    
    - Returns human-readable recommendations
    - Suitable for LLM response integration
    """
    medicine_list = [m.strip() for m in medicines.split(",") if m.strip()]
    
    if not medicine_list:
        raise HTTPException(status_code=400, detail="At least one medicine name is required")
    
    pharmacy_agent = get_pharmacy_agent()
    recommendations = pharmacy_agent.get_pharmacy_recommendations(
        medicines=medicine_list,
        user_id=user_id,
        city=city
    )
    
    return {
        "success": True,
        "user_id": user_id,
        "medicines_searched": medicine_list,
        "recommendations": recommendations
    }


@router.get("/inventory/{pharmacy_id}")
async def get_pharmacy_inventory(pharmacy_id: int):
    """Get full inventory for a specific pharmacy"""
    from sqlmodel import Session, select
    from database.connection import get_engine
    from database.models import Pharmacy, Inventory
    
    engine = get_engine()
    with Session(engine) as session:
        pharmacy = session.get(Pharmacy, pharmacy_id)
        if not pharmacy:
            raise HTTPException(status_code=404, detail="Pharmacy not found")
        
        inventory = session.exec(
            select(Inventory).where(Inventory.pharmacy_id == pharmacy_id)
        ).all()
        
        return {
            "pharmacy": {
                "id": pharmacy.pharmacy_id,
                "name": pharmacy.name,
                "address": pharmacy.address,
                "operating_hours": pharmacy.operating_hours
            },
            "inventory": [
                {
                    "medicine_name": item.medicine_name,
                    "salt_composition": item.salt_composition,
                    "category": item.category.value,
                    "stock": item.stock_count,
                    "price": item.price_inr,
                    "requires_prescription": item.requires_prescription
                }
                for item in inventory
            ],
            "total_items": len(inventory)
        }


@router.get("/list")
async def list_pharmacies(city: str = "Hyderabad"):
    """List all pharmacies in a city"""
    from sqlmodel import Session, select
    from database.connection import get_engine
    from database.models import Pharmacy
    
    engine = get_engine()
    with Session(engine) as session:
        pharmacies = session.exec(
            select(Pharmacy).where(
                Pharmacy.city == city,
                Pharmacy.is_active == True
            )
        ).all()
        
        return {
            "city": city,
            "pharmacies": [
                {
                    "pharmacy_id": p.pharmacy_id,
                    "name": p.name,
                    "address": p.address,
                    "locality": p.locality,
                    "operating_hours": p.operating_hours,
                    "is_24hr": p.is_24hr,
                    "phone": p.phone,
                    "hospital_attached": p.hospital_id is not None
                }
                for p in pharmacies
            ],
            "total": len(pharmacies)
        }
