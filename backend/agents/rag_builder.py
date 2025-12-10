"""
MELCO-Care RAG Context Builder
Retrieves and formats database context for LLM prompts
"""

from typing import Optional, Dict, Any, List
from database.models import DepartmentType
from backend.services.database_service import DatabaseService


# Map symptom keywords to departments
SYMPTOM_DEPARTMENT_MAP = {
    # General Medicine
    "fever": DepartmentType.GENERAL_MEDICINE,
    "bukhar": DepartmentType.GENERAL_MEDICINE,
    "cold": DepartmentType.GENERAL_MEDICINE,
    "cough": DepartmentType.GENERAL_MEDICINE,
    "weakness": DepartmentType.GENERAL_MEDICINE,
    "fatigue": DepartmentType.GENERAL_MEDICINE,
    
    # Dermatology
    "skin": DepartmentType.DERMATOLOGY,
    "rash": DepartmentType.DERMATOLOGY,
    "itching": DepartmentType.DERMATOLOGY,
    "khujli": DepartmentType.DERMATOLOGY,
    "allergy": DepartmentType.DERMATOLOGY,
    
    # ENT
    "ear": DepartmentType.ENT,
    "kaan": DepartmentType.ENT,
    "throat": DepartmentType.ENT,
    "gala": DepartmentType.ENT,
    "nose": DepartmentType.ENT,
    "naak": DepartmentType.ENT,
    
    # Ophthalmology
    "eye": DepartmentType.OPHTHALMOLOGY,
    "aankh": DepartmentType.OPHTHALMOLOGY,
    "vision": DepartmentType.OPHTHALMOLOGY,
    
    # Orthopedics
    "joint": DepartmentType.ORTHOPEDICS,
    "bone": DepartmentType.ORTHOPEDICS,
    "knee": DepartmentType.ORTHOPEDICS,
    "back pain": DepartmentType.ORTHOPEDICS,
    "kamar": DepartmentType.ORTHOPEDICS,
    
    # Pediatrics
    "baby": DepartmentType.PEDIATRICS,
    "child": DepartmentType.PEDIATRICS,
    "baccha": DepartmentType.PEDIATRICS,
    
    # Gynecology
    "periods": DepartmentType.GYNECOLOGY,
    "pregnancy": DepartmentType.GYNECOLOGY,
    "menstrual": DepartmentType.GYNECOLOGY,
    
    # Psychiatry
    "anxiety": DepartmentType.PSYCHIATRY,
    "depression": DepartmentType.PSYCHIATRY,
    "stress": DepartmentType.PSYCHIATRY,
    "sleep": DepartmentType.PSYCHIATRY,
    "neend": DepartmentType.PSYCHIATRY,
    
    # Cardiology
    "heart": DepartmentType.CARDIOLOGY,
    "chest pain": DepartmentType.CARDIOLOGY,
    "dil": DepartmentType.CARDIOLOGY,
    "breathless": DepartmentType.CARDIOLOGY,
    
    # Dental
    "tooth": DepartmentType.DENTAL,
    "teeth": DepartmentType.DENTAL,
    "daant": DepartmentType.DENTAL,
    "gums": DepartmentType.DENTAL,
    
    # Gastro (mapped to General for now)
    "stomach": DepartmentType.GENERAL_MEDICINE,
    "pet": DepartmentType.GENERAL_MEDICINE,
    "vomit": DepartmentType.GENERAL_MEDICINE,
    "diarrhea": DepartmentType.GENERAL_MEDICINE,
    
    # Emergency
    "accident": DepartmentType.EMERGENCY,
    "bleeding": DepartmentType.EMERGENCY,
    "unconscious": DepartmentType.EMERGENCY,
    "severe": DepartmentType.EMERGENCY,
}


class RAGContextBuilder:
    """Builds context from database for LLM prompts"""
    
    def __init__(self):
        self.db_service = DatabaseService()
    
    def close(self):
        self.db_service.close()
    
    def infer_department_from_symptoms(self, symptoms: str) -> Optional[DepartmentType]:
        """Simple keyword-based department inference"""
        symptoms_lower = symptoms.lower()
        
        for keyword, dept in SYMPTOM_DEPARTMENT_MAP.items():
            if keyword in symptoms_lower:
                return dept
        
        return None
    
    def get_available_doctors_context(
        self,
        city: str,
        department: Optional[DepartmentType] = None,
        symptoms: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get formatted context about available doctors
        """
        # Infer department from symptoms if not provided
        if department is None and symptoms:
            department = self.infer_department_from_symptoms(symptoms)
        
        # Default to General Medicine
        if department is None:
            department = DepartmentType.GENERAL_MEDICINE
        
        doctors = self.db_service.get_available_doctors_by_specialty(city, department)
        
        if not doctors:
            # Try general medicine as fallback
            doctors = self.db_service.get_available_doctors_by_specialty(
                city, 
                DepartmentType.GENERAL_MEDICINE
            )
        
        # Format for LLM context
        formatted_doctors = []
        for doc_info in doctors[:5]:  # Limit to top 5
            formatted_doctors.append({
                "doctor_id": doc_info["doctor"].doctor_id,
                "name": doc_info["doctor_name"],
                "specialization": doc_info["doctor"].specialization,
                "hospital": doc_info["hospital"].name,
                "locality": doc_info["hospital"].locality,
                "queue_length": doc_info["queue_length"],
                "estimated_wait_mins": doc_info["estimated_wait"],
                "consultation_fee": doc_info["doctor"].consultation_fee,
                "is_government": doc_info["hospital"].is_government
            })
        
        return {
            "suggested_department": department.value,
            "available_doctors": formatted_doctors,
            "total_doctors_found": len(doctors)
        }
    
    def get_hospital_info_context(self, city: str) -> Dict[str, Any]:
        """Get formatted context about hospitals in a city"""
        hospitals = self.db_service.get_hospitals_by_city(city)
        
        formatted_hospitals = []
        for hospital in hospitals:
            # Get departments for this hospital
            depts = self.db_service.get_departments_by_hospital(hospital.hospital_id)
            dept_names = [d.name.value for d in depts]
            
            formatted_hospitals.append({
                "hospital_id": hospital.hospital_id,
                "name": hospital.name,
                "locality": hospital.locality,
                "total_beds": hospital.total_beds,
                "available_beds": hospital.total_beds - hospital.occupied_beds,
                "is_government": hospital.is_government,
                "departments": dept_names[:8]  # Limit for context
            })
        
        return {
            "city": city,
            "hospitals": formatted_hospitals,
            "total_hospitals": len(hospitals)
        }
    
    def get_user_context(self, user_id: int) -> Dict[str, Any]:
        """Get context about a user"""
        user = self.db_service.get_user_by_id(user_id)
        
        if not user:
            return {"error": "User not found"}
        
        # Get user's recent appointments if they're a patient
        appointments = []
        if user.role.value == "patient":
            recent_appts = self.db_service.get_patient_appointments(user_id)[:3]
            appointments = [
                {
                    "date": appt.scheduled_date.strftime("%Y-%m-%d"),
                    "status": appt.status.value,
                    "symptoms": appt.symptoms_summary
                }
                for appt in recent_appts
            ]
        
        return {
            "user_id": user.user_id,
            "name": user.name,
            "role": user.role.value,
            "city": user.city,
            "locality": user.locality,
            "age": user.age,
            "gender": user.gender.value,
            "recent_appointments": appointments
        }
    
    def build_appointment_context(
        self,
        user_id: int,
        symptoms: str,
        suggested_department: Optional[str] = None
    ) -> str:
        """Build full context for appointment booking"""
        user_context = self.get_user_context(user_id)
        
        # Convert string to DepartmentType if provided
        dept_type = None
        if suggested_department:
            try:
                dept_type = DepartmentType(suggested_department)
            except ValueError:
                pass
        
        doctors_context = self.get_available_doctors_context(
            city=user_context.get("city", "Hyderabad"),
            department=dept_type,
            symptoms=symptoms
        )
        
        # Format as natural language for LLM
        context_text = f"""
Patient Information:
- Name: {user_context.get('name', 'Unknown')}
- Age: {user_context.get('age', 'Unknown')} years
- Gender: {user_context.get('gender', 'Unknown')}
- Location: {user_context.get('locality', 'Unknown')}, {user_context.get('city', 'Hyderabad')}

Suggested Department: {doctors_context['suggested_department']}

Available Doctors (sorted by shortest wait time):
"""
        
        for i, doc in enumerate(doctors_context['available_doctors'], 1):
            fee_text = "Free (Govt)" if doc['is_government'] else f"₹{doc['consultation_fee']}"
            context_text += f"""
{i}. Dr. {doc['name']}
   - Specialization: {doc['specialization']}
   - Hospital: {doc['hospital']}, {doc['locality']}
   - Current Queue: {doc['queue_length']} patients
   - Estimated Wait: ~{doc['estimated_wait_mins']} minutes
   - Fee: {fee_text}
"""
        
        return context_text


# Singleton instance
_rag_builder = None

def get_rag_builder() -> RAGContextBuilder:
    """Get RAG context builder singleton"""
    global _rag_builder
    if _rag_builder is None:
        _rag_builder = RAGContextBuilder()
    return _rag_builder
