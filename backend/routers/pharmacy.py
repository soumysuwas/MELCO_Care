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


# ============== RESERVATION ENDPOINTS ==============

class ReserveMedicineRequest(BaseModel):
    """Request to reserve medicines"""
    user_id: int
    pharmacy_id: int
    medicines: List[dict]  # [{"name": "Dolo 650", "quantity": 2}]


class ReservationResponse(BaseModel):
    """Reservation confirmation"""
    success: bool
    reservation_id: Optional[int]
    pickup_code: Optional[str]
    expires_at: Optional[str]
    total_amount: Optional[float]
    pharmacy_name: Optional[str]
    message: str


@router.post("/reserve", response_model=ReservationResponse)
async def reserve_medicines(request: ReserveMedicineRequest):
    """
    Reserve medicines at a pharmacy for pickup
    
    - Reduces inventory by requested quantity
    - Generates pickup code
    - Sets 1-hour expiry time
    """
    import json
    import random
    from datetime import timedelta
    from sqlmodel import Session, select
    from database.connection import get_engine
    from database.models import Pharmacy, Inventory, MedicineReservation, ReservationStatus
    
    engine = get_engine()
    with Session(engine) as session:
        # First, expire old reservations
        _expire_old_reservations(session)
        
        # Get pharmacy
        pharmacy = session.get(Pharmacy, request.pharmacy_id)
        if not pharmacy:
            return ReservationResponse(
                success=False, message="Pharmacy not found",
                reservation_id=None, pickup_code=None, expires_at=None,
                total_amount=None, pharmacy_name=None
            )
        
        # Check stock and calculate total
        medicines_with_prices = []
        total_amount = 0.0
        
        for med in request.medicines:
            med_name = med.get("name", "")
            quantity = med.get("quantity", 1)
            
            # Find in inventory
            inventory_item = session.exec(
                select(Inventory).where(
                    Inventory.pharmacy_id == request.pharmacy_id,
                    Inventory.medicine_name == med_name
                )
            ).first()
            
            if not inventory_item:
                return ReservationResponse(
                    success=False, message=f"Medicine '{med_name}' not found at this pharmacy",
                    reservation_id=None, pickup_code=None, expires_at=None,
                    total_amount=None, pharmacy_name=pharmacy.name
                )
            
            if inventory_item.stock_count < quantity:
                return ReservationResponse(
                    success=False, 
                    message=f"Insufficient stock for '{med_name}'. Available: {inventory_item.stock_count}",
                    reservation_id=None, pickup_code=None, expires_at=None,
                    total_amount=None, pharmacy_name=pharmacy.name
                )
            
            # Reduce inventory
            inventory_item.stock_count -= quantity
            session.add(inventory_item)
            
            med_total = inventory_item.price_inr * quantity
            total_amount += med_total
            medicines_with_prices.append({
                "name": med_name,
                "quantity": quantity,
                "price": inventory_item.price_inr,
                "total": med_total
            })
        
        # Create reservation
        pickup_code = str(random.randint(100000, 999999))
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        reservation = MedicineReservation(
            user_id=request.user_id,
            pharmacy_id=request.pharmacy_id,
            medicines_json=json.dumps(medicines_with_prices),
            total_amount=total_amount,
            status=ReservationStatus.PENDING,
            expires_at=expires_at,
            pickup_code=pickup_code
        )
        session.add(reservation)
        session.commit()
        session.refresh(reservation)
        
        return ReservationResponse(
            success=True,
            reservation_id=reservation.reservation_id,
            pickup_code=pickup_code,
            expires_at=expires_at.isoformat(),
            total_amount=round(total_amount, 2),
            pharmacy_name=pharmacy.name,
            message=f"Reserved! Pickup within 1 hour. Show code: {pickup_code}"
        )


@router.post("/pickup/{reservation_id}")
async def confirm_pickup(reservation_id: int, pickup_code: str):
    """Confirm medicine pickup with verification code"""
    from sqlmodel import Session
    from database.connection import get_engine
    from database.models import MedicineReservation, ReservationStatus
    
    engine = get_engine()
    with Session(engine) as session:
        reservation = session.get(MedicineReservation, reservation_id)
        
        if not reservation:
            raise HTTPException(status_code=404, detail="Reservation not found")
        
        if reservation.status != ReservationStatus.PENDING:
            raise HTTPException(status_code=400, detail=f"Reservation is {reservation.status.value}")
        
        if reservation.pickup_code != pickup_code:
            raise HTTPException(status_code=400, detail="Invalid pickup code")
        
        if datetime.utcnow() > reservation.expires_at:
            # Already expired, revert and mark
            _revert_reservation_inventory(session, reservation)
            reservation.status = ReservationStatus.EXPIRED
            session.add(reservation)
            session.commit()
            raise HTTPException(status_code=400, detail="Reservation expired")
        
        # Mark as picked up
        reservation.status = ReservationStatus.PICKED_UP
        reservation.updated_at = datetime.utcnow()
        session.add(reservation)
        session.commit()
        
        return {
            "success": True,
            "message": "Medicines picked up successfully!",
            "reservation_id": reservation_id,
            "total_paid": reservation.total_amount
        }


@router.post("/cancel/{reservation_id}")
async def cancel_reservation(reservation_id: int, user_id: int):
    """Cancel a reservation and restore inventory"""
    from sqlmodel import Session
    from database.connection import get_engine
    from database.models import MedicineReservation, ReservationStatus
    
    engine = get_engine()
    with Session(engine) as session:
        reservation = session.get(MedicineReservation, reservation_id)
        
        if not reservation:
            raise HTTPException(status_code=404, detail="Reservation not found")
        
        if reservation.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not your reservation")
        
        if reservation.status != ReservationStatus.PENDING:
            raise HTTPException(status_code=400, detail=f"Cannot cancel - status is {reservation.status.value}")
        
        # Revert inventory
        _revert_reservation_inventory(session, reservation)
        
        # Mark as cancelled
        reservation.status = ReservationStatus.CANCELLED
        reservation.updated_at = datetime.utcnow()
        session.add(reservation)
        session.commit()
        
        return {
            "success": True,
            "message": "Reservation cancelled. Inventory restored.",
            "reservation_id": reservation_id
        }


@router.get("/reservations/{user_id}")
async def get_user_reservations(user_id: int):
    """Get all reservations for a user"""
    import json
    from sqlmodel import Session, select
    from database.connection import get_engine
    from database.models import MedicineReservation, Pharmacy
    
    engine = get_engine()
    with Session(engine) as session:
        # Expire old ones first
        _expire_old_reservations(session)
        
        reservations = session.exec(
            select(MedicineReservation).where(
                MedicineReservation.user_id == user_id
            ).order_by(MedicineReservation.created_at.desc())
        ).all()
        
        result = []
        for r in reservations:
            pharmacy = session.get(Pharmacy, r.pharmacy_id)
            result.append({
                "reservation_id": r.reservation_id,
                "pharmacy_name": pharmacy.name if pharmacy else "Unknown",
                "medicines": json.loads(r.medicines_json),
                "total_amount": r.total_amount,
                "status": r.status.value,
                "pickup_code": r.pickup_code if r.status.value == "pending" else None,
                "expires_at": r.expires_at.isoformat(),
                "created_at": r.created_at.isoformat()
            })
        
        return {"user_id": user_id, "reservations": result}


def _expire_old_reservations(session):
    """Auto-expire old pending reservations and revert inventory"""
    import json
    from sqlmodel import select
    from database.models import MedicineReservation, ReservationStatus, Inventory
    
    expired = session.exec(
        select(MedicineReservation).where(
            MedicineReservation.status == ReservationStatus.PENDING,
            MedicineReservation.expires_at < datetime.utcnow()
        )
    ).all()
    
    for reservation in expired:
        _revert_reservation_inventory(session, reservation)
        reservation.status = ReservationStatus.EXPIRED
        reservation.updated_at = datetime.utcnow()
        session.add(reservation)
    
    if expired:
        session.commit()


def _revert_reservation_inventory(session, reservation):
    """Restore inventory for a cancelled/expired reservation"""
    import json
    from sqlmodel import select
    from database.models import Inventory
    
    medicines = json.loads(reservation.medicines_json)
    for med in medicines:
        inventory_item = session.exec(
            select(Inventory).where(
                Inventory.pharmacy_id == reservation.pharmacy_id,
                Inventory.medicine_name == med["name"]
            )
        ).first()
        
        if inventory_item:
            inventory_item.stock_count += med["quantity"]
            session.add(inventory_item)
