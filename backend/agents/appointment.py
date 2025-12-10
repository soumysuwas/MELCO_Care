"""
MELCO-Care Appointment Scheduling Agent
Handles appointment booking workflow
"""

from typing import Optional, Dict, Any
from database.models import DepartmentType, Priority
from backend.services.database_service import get_database_service
from backend.services.vlm_service import get_vlm_service
from backend.agents.rag_builder import get_rag_builder


class AppointmentAgent:
    """Agent for handling appointment scheduling"""
    
    def __init__(self):
        self.db_service = get_database_service()
        self.vlm_service = get_vlm_service()
        self.rag_builder = get_rag_builder()
    
    def close(self):
        self.db_service.close()
    
    def analyze_and_suggest(
        self,
        user_id: int,
        symptoms: str,
        image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze symptoms and suggest doctors for appointment
        """
        # Get user info
        user = self.db_service.get_user_by_id(user_id)
        if not user:
            return {"error": "User not found", "success": False}
        
        # Use VLM to analyze symptoms
        analysis = self.vlm_service.analyze_symptoms(
            symptoms=symptoms,
            image_path=image_path,
            user_age=user.age,
            user_gender=user.gender.value
        )
        
        suggested_dept_str = analysis.get("suggested_department", "General Medicine")
        
        # Convert to DepartmentType
        try:
            suggested_dept = DepartmentType(suggested_dept_str)
        except ValueError:
            suggested_dept = DepartmentType.GENERAL_MEDICINE
        
        # Get available doctors
        doctors = self.db_service.get_available_doctors_by_specialty(
            city=user.city,
            dept_type=suggested_dept
        )
        
        # If no doctors in suggested department, try General Medicine
        if not doctors and suggested_dept != DepartmentType.GENERAL_MEDICINE:
            doctors = self.db_service.get_available_doctors_by_specialty(
                city=user.city,
                dept_type=DepartmentType.GENERAL_MEDICINE
            )
            suggested_dept = DepartmentType.GENERAL_MEDICINE
        
        # Format doctor options
        doctor_options = []
        for doc_info in doctors[:5]:
            fee_text = "Free (Government Hospital)" if doc_info["hospital"].is_government else f"₹{doc_info['doctor'].consultation_fee}"
            doctor_options.append({
                "doctor_id": doc_info["doctor"].doctor_id,
                "doctor_name": doc_info["doctor_name"],
                "specialization": doc_info["doctor"].specialization,
                "hospital_name": doc_info["hospital"].name,
                "hospital_locality": doc_info["hospital"].locality,
                "queue_length": doc_info["queue_length"],
                "estimated_wait_mins": doc_info["estimated_wait"],
                "consultation_fee": fee_text,
                "is_government": doc_info["hospital"].is_government
            })
        
        return {
            "success": True,
            "suggested_department": suggested_dept.value,
            "symptoms_summary": analysis.get("symptoms_summary", symptoms[:200]),
            "priority": analysis.get("priority", "medium"),
            "recommendations": analysis.get("recommendations", []),
            "doctor_options": doctor_options,
            "total_doctors_found": len(doctors)
        }
    
    def book_appointment(
        self,
        user_id: int,
        doctor_id: int,
        symptoms_raw: str,
        symptoms_summary: str,
        priority: str = "medium",
        image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Book an appointment with a doctor
        """
        # Validate user
        user = self.db_service.get_user_by_id(user_id)
        if not user:
            return {"success": False, "error": "User not found"}
        
        # Convert priority string to enum
        try:
            priority_enum = Priority(priority.lower())
        except ValueError:
            priority_enum = Priority.MEDIUM
        
        try:
            # Create appointment
            appointment = self.db_service.create_appointment(
                patient_id=user_id,
                doctor_id=doctor_id,
                symptoms_raw=symptoms_raw,
                symptoms_summary=symptoms_summary,
                priority=priority_enum,
                image_path=image_path
            )
            
            # Get doctor info for response
            doctor = self.db_service.session.get_one(
                __import__('database.models', fromlist=['Doctor']).Doctor,
                doctor_id
            )
            doctor_user = self.db_service.get_user_by_id(doctor.user_id)
            
            return {
                "success": True,
                "appointment_id": appointment.appointment_id,
                "token_number": appointment.token_number,
                "doctor_name": doctor_user.name if doctor_user else "Doctor",
                "scheduled_date": appointment.scheduled_date.strftime("%Y-%m-%d %H:%M"),
                "message": f"Appointment booked successfully! Your token number is {appointment.token_number}."
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_patient_appointments(self, user_id: int) -> Dict[str, Any]:
        """Get all appointments for a patient"""
        appointments = self.db_service.get_patient_appointments(user_id)
        
        formatted = []
        for appt in appointments:
            formatted.append({
                "appointment_id": appt.appointment_id,
                "status": appt.status.value,
                "symptoms": appt.symptoms_summary,
                "priority": appt.priority.value,
                "token_number": appt.token_number,
                "scheduled_date": appt.scheduled_date.strftime("%Y-%m-%d %H:%M")
            })
        
        return {
            "success": True,
            "appointments": formatted,
            "total": len(formatted)
        }


# Factory function
def get_appointment_agent() -> AppointmentAgent:
    """Get appointment agent instance"""
    return AppointmentAgent()
