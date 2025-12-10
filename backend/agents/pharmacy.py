"""
MELCO-Care Pharmacy Agent
Handles prescription validation and medicine search
"""

import json
import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

from sqlmodel import Session, select
from sqlalchemy import func

from database.connection import get_engine
from database.models import (
    Pharmacy, Inventory, DoctorSignature, PrescriptionRecord,
    MedicineCategory, User
)
from backend.services.vlm_service import get_vlm_service


class PharmacyAgent:
    """Agent for pharmacy-related operations"""
    
    def __init__(self):
        self.vlm_service = get_vlm_service()
        self.engine = get_engine()
    
    def validate_prescription(
        self, 
        image_path: str, 
        user_id: int
    ) -> Dict[str, Any]:
        """
        Validate a prescription image using OCR and verify doctor registration
        
        Returns:
            {
                "valid": bool,
                "extracted_data": {
                    "patient_name": str,
                    "doctor_name": str,
                    "reg_number": str,
                    "date": str,
                    "medicines": [{"name": str, "dosage": str, "quantity": str}]
                },
                "doctor_verified": bool,
                "error": str (if invalid)
            }
        """
        # Step 1: Use VLM to extract prescription data
        extracted = self._ocr_prescription(image_path)
        
        if not extracted or not extracted.get("medicines"):
            return {
                "valid": False,
                "extracted_data": None,
                "doctor_verified": False,
                "error": "Could not extract prescription data. Please upload a clearer image."
            }
        
        # Step 2: Verify doctor registration
        reg_number = extracted.get("reg_number")
        doctor_verified = False
        
        if reg_number:
            doctor_verified = self._verify_doctor_registration(reg_number)
        
        # Step 3: Check prescription date (reject if older than 30 days)
        is_date_valid = True
        prescription_date = extracted.get("date")
        if prescription_date:
            is_date_valid = self._check_prescription_age(prescription_date)
        
        # Step 4: Record the prescription
        is_valid = len(extracted.get("medicines", [])) > 0
        
        with Session(self.engine) as session:
            record = PrescriptionRecord(
                user_id=user_id,
                doctor_reg_number=reg_number or "UNKNOWN",
                image_path=image_path,
                extracted_medicines=json.dumps(extracted.get("medicines", [])),
                is_valid=is_valid and doctor_verified,
                validation_notes=f"Doctor verified: {doctor_verified}, Date valid: {is_date_valid}",
                prescription_date=datetime.utcnow()
            )
            session.add(record)
            session.commit()
        
        return {
            "valid": is_valid,
            "extracted_data": extracted,
            "doctor_verified": doctor_verified,
            "date_valid": is_date_valid,
            "error": None if is_valid else "Prescription validation failed"
        }
    
    def _ocr_prescription(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Use VLM to extract data from prescription image"""
        
        ocr_prompt = """Extract the following from this prescription image:
1. Patient Name
2. Doctor Name (look for "Dr." prefix)
3. Medical Registration Number (format like TS-12345 or similar)
4. Date of prescription
5. List of medicines with dosage and quantity

Respond ONLY with valid JSON in this exact format:
{
    "patient_name": "extracted name or null",
    "doctor_name": "extracted name or null",
    "reg_number": "extracted registration number or null",
    "date": "extracted date or null",
    "medicines": [
        {"name": "medicine name", "dosage": "dosage", "quantity": "quantity"}
    ]
}

If a field is unclear or missing, set it to null.
For medicines, extract all that you can identify."""

        try:
            response = self.vlm_service._call_ollama(
                prompt=ocr_prompt,
                model=self.vlm_service.vision_model,
                images=[image_path]
            )
            
            if response:
                # Parse JSON from response
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
        except Exception as e:
            print(f"OCR Error: {e}")
        
        return None
    
    def _verify_doctor_registration(self, reg_number: str) -> bool:
        """Check if doctor registration number exists in database"""
        with Session(self.engine) as session:
            signature = session.exec(
                select(DoctorSignature).where(
                    DoctorSignature.medical_reg_number == reg_number,
                    DoctorSignature.is_verified == True
                )
            ).first()
            return signature is not None
    
    def _check_prescription_age(self, date_str: str, max_days: int = 30) -> bool:
        """Check if prescription is within allowed age"""
        try:
            # Try common date formats
            for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d %b %Y"]:
                try:
                    rx_date = datetime.strptime(date_str, fmt)
                    age_days = (datetime.utcnow() - rx_date).days
                    return 0 <= age_days <= max_days
                except ValueError:
                    continue
        except Exception:
            pass
        return True  # If can't parse, allow it
    
    def search_medicines(
        self,
        medicine_names: List[str],
        user_lat: float,
        user_lon: float,
        max_distance_km: float = 10.0,
        city: str = "Hyderabad"
    ) -> Dict[str, Any]:
        """
        Search for medicines at nearby pharmacies
        
        Returns:
            {
                "pharmacies": [
                    {
                        "name": str,
                        "address": str,
                        "distance_km": float,
                        "operating_hours": str,
                        "phone": str,
                        "medicines": [
                            {"name": str, "price": float, "stock": int, "in_stock": bool}
                        ],
                        "all_available": bool
                    }
                ],
                "all_found": bool,
                "missing_medicines": [str]
            }
        """
        with Session(self.engine) as session:
            # Get all active pharmacies in the city
            pharmacies = session.exec(
                select(Pharmacy).where(
                    Pharmacy.city == city,
                    Pharmacy.is_active == True
                )
            ).all()
            
            results = []
            
            for pharmacy in pharmacies:
                # Calculate distance
                distance = self._haversine_distance(
                    user_lat, user_lon,
                    pharmacy.latitude, pharmacy.longitude
                )
                
                if distance > max_distance_km:
                    continue
                
                # Get inventory for requested medicines
                medicine_results = []
                for med_name in medicine_names:
                    # Search by name (partial match)
                    inventory_item = session.exec(
                        select(Inventory).where(
                            Inventory.pharmacy_id == pharmacy.pharmacy_id,
                            func.lower(Inventory.medicine_name).contains(med_name.lower())
                        )
                    ).first()
                    
                    if not inventory_item:
                        # Try salt composition
                        inventory_item = session.exec(
                            select(Inventory).where(
                                Inventory.pharmacy_id == pharmacy.pharmacy_id,
                                func.lower(Inventory.salt_composition).contains(med_name.lower())
                            )
                        ).first()
                    
                    if inventory_item:
                        medicine_results.append({
                            "name": inventory_item.medicine_name,
                            "salt": inventory_item.salt_composition,
                            "price": round(inventory_item.price_inr, 2),
                            "stock": inventory_item.stock_count,
                            "in_stock": inventory_item.stock_count > 0,
                            "requires_prescription": inventory_item.requires_prescription
                        })
                    else:
                        medicine_results.append({
                            "name": med_name,
                            "salt": None,
                            "price": None,
                            "stock": 0,
                            "in_stock": False,
                            "requires_prescription": True
                        })
                
                all_available = all(m["in_stock"] for m in medicine_results)
                
                results.append({
                    "pharmacy_id": pharmacy.pharmacy_id,
                    "name": pharmacy.name,
                    "address": pharmacy.address,
                    "locality": pharmacy.locality,
                    "distance_km": round(distance, 2),
                    "operating_hours": pharmacy.operating_hours,
                    "is_24hr": pharmacy.is_24hr,
                    "phone": pharmacy.phone,
                    "medicines": medicine_results,
                    "all_available": all_available,
                    "available_count": sum(1 for m in medicine_results if m["in_stock"])
                })
            
            # Sort by: all_available first, then by distance
            results.sort(key=lambda x: (-x["all_available"], -x["available_count"], x["distance_km"]))
            
            # Find missing medicines
            all_meds_found = True
            missing = []
            for med_name in medicine_names:
                found = any(
                    any(m["in_stock"] and med_name.lower() in m["name"].lower() 
                        for m in p["medicines"])
                    for p in results
                )
                if not found:
                    missing.append(med_name)
                    all_meds_found = False
            
            return {
                "pharmacies": results[:10],  # Top 10
                "all_found": all_meds_found,
                "missing_medicines": missing,
                "total_pharmacies_searched": len(pharmacies)
            }
    
    def _haversine_distance(
        self, 
        lat1: float, lon1: float, 
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two coordinates in km"""
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat/2)**2 + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def get_pharmacy_recommendations(
        self,
        medicines: List[str],
        user_id: int,
        city: str = "Hyderabad"
    ) -> str:
        """Get formatted pharmacy recommendations for LLM response"""
        
        # Get user location (default to city center if not available)
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            # Default Hyderabad coordinates
            user_lat = 17.385
            user_lon = 78.486
        
        # Search for medicines
        results = self.search_medicines(
            medicine_names=medicines,
            user_lat=user_lat,
            user_lon=user_lon,
            city=city
        )
        
        if not results["pharmacies"]:
            return "No pharmacies found in your area with the requested medicines."
        
        # Format response
        lines = []
        
        if results["all_found"]:
            lines.append("✅ All medicines are available!")
        else:
            lines.append(f"⚠️ Some medicines may not be available: {', '.join(results['missing_medicines'])}")
        
        lines.append("\n**Recommended Pharmacies:**\n")
        
        for i, pharmacy in enumerate(results["pharmacies"][:3], 1):
            lines.append(f"**{i}. {pharmacy['name']}** ({pharmacy['distance_km']} km)")
            lines.append(f"   📍 {pharmacy['address']}")
            lines.append(f"   ⏰ {pharmacy['operating_hours']}")
            if pharmacy['phone']:
                lines.append(f"   📞 {pharmacy['phone']}")
            
            lines.append("   💊 Medicines:")
            for med in pharmacy['medicines']:
                status = "✅ In Stock" if med['in_stock'] else "❌ Out of Stock"
                price = f"₹{med['price']}" if med['price'] else "N/A"
                lines.append(f"      - {med['name']}: {price} ({status})")
            
            lines.append("")
        
        return "\n".join(lines)


# Singleton
_pharmacy_agent = None

def get_pharmacy_agent() -> PharmacyAgent:
    """Get pharmacy agent singleton"""
    global _pharmacy_agent
    if _pharmacy_agent is None:
        _pharmacy_agent = PharmacyAgent()
    return _pharmacy_agent
