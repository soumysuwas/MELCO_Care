"""
MELCO-Care Central Orchestrator Agent
Routes user requests to appropriate sub-agents based on intent
"""

from typing import Optional, Dict, Any, List
from enum import Enum

from backend.services.vlm_service import get_vlm_service
from backend.services.database_service import get_database_service
from backend.agents.rag_builder import get_rag_builder
from backend.agents.appointment import get_appointment_agent
from backend.agents.pharmacy import get_pharmacy_agent


class Intent(str, Enum):
    """Possible user intents"""
    APPOINTMENT = "appointment"
    EMERGENCY = "emergency"
    SYMPTOM_CHECK = "symptom_check"
    HOSPITAL_INFO = "hospital_info"
    PHARMACY = "pharmacy"
    GENERAL = "general"


class OrchestratorAgent:
    """
    Central orchestrator that:
    1. Classifies user intent
    2. Gathers relevant context via RAG
    3. Routes to appropriate sub-agents
    4. Generates final response
    """
    
    def __init__(self):
        self.vlm_service = get_vlm_service()
        self.db_service = get_database_service()
        self.rag_builder = get_rag_builder()
    
    def close(self):
        self.db_service.close()
        self.rag_builder.close()
    
    def process_request(
        self,
        user_id: int,
        message: str,
        image_path: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Main entry point - process a user request
        """
        # Step 1: Get user context
        user = self.db_service.get_user_by_id(user_id)
        if not user:
            return {
                "success": False,
                "response": "User not found. Please register first.",
                "intent": None,
                "action_taken": None
            }
        
        # Step 2: Classify intent using VLM
        intent_result = self.vlm_service.classify_intent(message, image_path)
        intent_str = intent_result.get("intent", "general")
        
        try:
            intent = Intent(intent_str)
        except ValueError:
            intent = Intent.GENERAL
        
        # Step 3: Route based on intent
        action_result = None
        context = ""
        
        if intent == Intent.APPOINTMENT or intent == Intent.SYMPTOM_CHECK:
            action_result = self._handle_appointment_flow(
                user_id=user_id,
                message=message,
                image_path=image_path,
                intent_result=intent_result
            )
        
        elif intent == Intent.EMERGENCY:
            action_result = self._handle_emergency(user_id, message, intent_result)
        
        elif intent == Intent.HOSPITAL_INFO:
            action_result = self._handle_hospital_info(user.city)
        
        elif intent == Intent.PHARMACY:
            action_result = self._handle_pharmacy_flow(
                user_id=user_id,
                message=message,
                intent_result=intent_result
            )
        
        else:
            action_result = {"action": "general_query"}
        
        # Step 4: Build context for response generation
        if action_result:
            context = self._format_action_context(action_result)
        
        # Step 5: Generate natural language response
        response = self.vlm_service.generate_response(
            user_message=message,
            context=context,
            chat_history=chat_history
        )
        
        return {
            "success": True,
            "response": response,
            "intent": intent.value,
            "action_taken": action_result,
            "suggested_department": intent_result.get("suggested_department"),
            "priority": intent_result.get("priority", "medium")
        }
    
    def _handle_appointment_flow(
        self,
        user_id: int,
        message: str,
        image_path: Optional[str],
        intent_result: Dict
    ) -> Dict[str, Any]:
        """Handle appointment booking flow"""
        appointment_agent = get_appointment_agent()
        
        try:
            # Analyze symptoms and get doctor suggestions
            result = appointment_agent.analyze_and_suggest(
                user_id=user_id,
                symptoms=message,
                image_path=image_path
            )
            
            result["action"] = "appointment_suggestion"
            return result
        
        finally:
            appointment_agent.close()
    
    def _handle_emergency(
        self,
        user_id: int,
        message: str,
        intent_result: Dict
    ) -> Dict[str, Any]:
        """Handle emergency situations"""
        user = self.db_service.get_user_by_id(user_id)
        city = user.city if user else "Hyderabad"
        
        # Get emergency departments
        from database.models import DepartmentType
        emergency_docs = self.db_service.get_available_doctors_by_specialty(
            city=city,
            dept_type=DepartmentType.EMERGENCY
        )
        
        hospitals = []
        for doc_info in emergency_docs[:3]:
            hospitals.append({
                "hospital": doc_info["hospital"].name,
                "locality": doc_info["hospital"].locality,
                "phone": doc_info["hospital"].phone
            })
        
        return {
            "action": "emergency_alert",
            "priority": "emergency",
            "message": "🚨 EMERGENCY: Please proceed to the nearest hospital immediately!",
            "emergency_contact": "108 (Ambulance)",
            "nearest_hospitals": hospitals,
            "recommendations": [
                "Call 108 for ambulance if needed",
                "Go to the nearest Emergency department",
                "Do not delay seeking medical attention"
            ]
        }
    
    def _handle_hospital_info(self, city: str) -> Dict[str, Any]:
        """Handle hospital information queries"""
        hospital_context = self.rag_builder.get_hospital_info_context(city)
        
        return {
            "action": "hospital_info",
            "hospitals": hospital_context.get("hospitals", []),
            "total": hospital_context.get("total_hospitals", 0)
        }
    
    def _handle_pharmacy_flow(
        self,
        user_id: int,
        message: str,
        intent_result: Dict
    ) -> Dict[str, Any]:
        """Handle pharmacy-related queries"""
        pharmacy_agent = get_pharmacy_agent()
        
        # Extract medicine names from the message
        # The VLM should have extracted symptoms, we use those to suggest medicines
        # Or user might directly ask for specific medicines
        
        # For now, extract potential medicine-related keywords
        common_medicines = [
            "paracetamol", "dolo", "crocin", "combiflam", "azithromycin",
            "amoxicillin", "cetirizine", "pantoprazole", "omeprazole",
            "metformin", "aspirin", "vitamin", "becosules"
        ]
        
        # Check if user mentions specific medicines
        mentioned_medicines = []
        message_lower = message.lower()
        for med in common_medicines:
            if med in message_lower:
                mentioned_medicines.append(med)
        
        if not mentioned_medicines:
            # If no specific medicines, provide general pharmacy info
            return {
                "action": "pharmacy_info",
                "message": "Please upload your prescription or tell me which medicines you need. I can help you find nearby pharmacies with availability.",
                "needs_prescription": True
            }
        
        # Search for medicines
        recommendations = pharmacy_agent.get_pharmacy_recommendations(
            medicines=mentioned_medicines,
            user_id=user_id
        )
        
        return {
            "action": "pharmacy_search",
            "medicines_searched": mentioned_medicines,
            "recommendations": recommendations
        }
    
    def _format_action_context(self, action_result: Dict) -> str:
        """Format action result as context for LLM"""
        action = action_result.get("action", "")
        
        if action == "appointment_suggestion":
            doctors = action_result.get("doctor_options", [])
            if not doctors:
                return "No doctors currently available. Please try again later or visit the hospital directly."
            
            context = f"Suggested Department: {action_result.get('suggested_department', 'General Medicine')}\n"
            context += f"Priority: {action_result.get('priority', 'medium')}\n\n"
            context += "Available Doctors:\n"
            
            for i, doc in enumerate(doctors[:3], 1):
                context += f"{i}. {doc['doctor_name']} - {doc['specialization']}\n"
                context += f"   Hospital: {doc['hospital_name']}, {doc['hospital_locality']}\n"
                context += f"   Wait Time: ~{doc['estimated_wait_mins']} mins ({doc['queue_length']} patients)\n"
                context += f"   Fee: {doc['consultation_fee']}\n\n"
            
            return context
        
        elif action == "emergency_alert":
            return action_result.get("message", "Emergency! Seek immediate medical attention.")
        
        elif action == "hospital_info":
            hospitals = action_result.get("hospitals", [])
            context = f"Found {len(hospitals)} hospitals:\n"
            for h in hospitals[:5]:
                context += f"- {h['name']} ({h['locality']}): {h['available_beds']} beds available\n"
            return context
        
        elif action == "pharmacy_search":
            return action_result.get("recommendations", "No pharmacy information available.")
        
        elif action == "pharmacy_info":
            return action_result.get("message", "Please provide prescription or medicine details.")
        
        return ""


# Factory function
def get_orchestrator_agent() -> OrchestratorAgent:
    """Get orchestrator agent instance"""
    return OrchestratorAgent()
