"""
MELCO-Care VLM Service
Handles communication with Ollama for Vision Language Model inference
"""

import base64
import json
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List

from backend.config import settings


class VLMService:
    """Service for Vision Language Model operations via Ollama"""
    
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.primary_model = settings.ollama_primary_model
        self.vision_model = settings.ollama_vision_model
        self.fallback_model = settings.ollama_fallback_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens
    
    def _encode_image(self, image_path: str) -> Optional[str]:
        """Encode image to base64 for Ollama"""
        try:
            path = Path(image_path)
            if path.exists():
                with open(path, "rb") as f:
                    return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            print(f"Error encoding image: {e}")
        return None
    
    def _call_ollama(
        self,
        prompt: str,
        model: Optional[str] = None,
        images: Optional[List[str]] = None,
        system_prompt: Optional[str] = None
    ) -> Optional[str]:
        """Make a request to Ollama API"""
        model = model or self.primary_model
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": 512  # Reduced for faster responses
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        if images:
            # Encode images to base64
            encoded_images = []
            for img_path in images:
                encoded = self._encode_image(img_path)
                if encoded:
                    encoded_images.append(encoded)
            if encoded_images:
                payload["images"] = encoded_images
        
        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except requests.exceptions.RequestException as e:
            print(f"Ollama request error: {e}")
            # Try fallback model
            if model != self.fallback_model:
                print(f"Trying fallback model: {self.fallback_model}")
                return self._call_ollama(
                    prompt=prompt,
                    model=self.fallback_model,
                    images=images,
                    system_prompt=system_prompt
                )
            return None
    
    def classify_intent(self, message: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Classify user intent from message and optional image
        Returns: {"intent": str, "confidence": float, "details": dict}
        """
        system_prompt = """You are MELCO-Care, an AI assistant for Indian healthcare.
Your job is to classify user intent from their message.

Possible intents:
1. "appointment" - User wants to book/schedule an appointment
2. "emergency" - User describes a medical emergency
3. "symptom_check" - User is describing symptoms for advice
4. "hospital_info" - User wants hospital/doctor information
5. "general" - General query or greeting

Respond ONLY with valid JSON in this exact format:
{
    "intent": "<one of the intents above>",
    "confidence": <0.0 to 1.0>,
    "suggested_department": "<department name or null>",
    "priority": "<low/medium/high/emergency>",
    "symptoms_summary": "<brief summary of symptoms if any>"
}"""

        prompt = f"User message: {message}"
        if image_path:
            prompt += "\n[User has also attached a medical image for analysis]"
        
        images = [image_path] if image_path else None
        
        response = self._call_ollama(
            prompt=prompt,
            model=self.vision_model if image_path else self.primary_model,
            images=images,
            system_prompt=system_prompt
        )
        
        # Parse JSON response
        if response:
            try:
                # Try to extract JSON from response
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # Default response if parsing fails
        return {
            "intent": "general",
            "confidence": 0.5,
            "suggested_department": None,
            "priority": "medium",
            "symptoms_summary": message[:100]
        }
    
    def analyze_symptoms(
        self, 
        symptoms: str, 
        image_path: Optional[str] = None,
        user_age: Optional[int] = None,
        user_gender: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze symptoms and suggest appropriate department
        """
        system_prompt = """You are MELCO-Care, a medical AI assistant for Indian healthcare.
Analyze the patient's symptoms and suggest the most appropriate medical department.

Available departments:
- General Medicine
- Pediatrics (for children)
- Dermatology (skin issues)
- Gynecology (women's health)
- Orthopedics (bones, joints)
- ENT (ear, nose, throat)
- Ophthalmology (eyes)
- Psychiatry (mental health)
- Cardiology (heart)
- Pulmonology (lungs)
- Dental (teeth, gums)
- Emergency (life-threatening)
- Neurology (brain, nerves)

Respond ONLY with valid JSON:
{
    "suggested_department": "<department name>",
    "priority": "<low/medium/high/emergency>",
    "symptoms_summary": "<professional summary of symptoms>",
    "recommendations": ["<list of immediate care tips>"],
    "confidence": <0.0 to 1.0>
}"""
        
        context = f"Patient symptoms: {symptoms}"
        if user_age:
            context += f"\nPatient age: {user_age} years"
        if user_gender:
            context += f"\nPatient gender: {user_gender}"
        if image_path:
            context += "\n[Medical image attached for analysis]"
        
        images = [image_path] if image_path else None
        
        response = self._call_ollama(
            prompt=context,
            model=self.vision_model if image_path else self.primary_model,
            images=images,
            system_prompt=system_prompt
        )
        
        if response:
            try:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        return {
            "suggested_department": "General Medicine",
            "priority": "medium",
            "symptoms_summary": symptoms[:200],
            "recommendations": ["Please visit a doctor for proper diagnosis"],
            "confidence": 0.3
        }
    
    def generate_response(
        self,
        user_message: str,
        context: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate a conversational response for the user
        """
        system_prompt = """You are MELCO-Care, a friendly and helpful AI healthcare assistant for Indian hospitals.
You help patients:
1. Book appointments with appropriate doctors
2. Provide information about hospitals and departments
3. Offer basic health guidance (while advising professional consultation)

Be warm, empathetic, and speak naturally. Support both English and Hinglish.
Keep responses concise but helpful. Always recommend seeing a doctor for medical concerns."""
        
        prompt = ""
        
        # Add chat history for context
        if chat_history:
            prompt += "Previous conversation:\n"
            for msg in chat_history[-5:]:  # Last 5 messages
                role = "Patient" if msg["role"] == "user" else "MELCO-Care"
                prompt += f"{role}: {msg['content']}\n"
            prompt += "\n"
        
        # Add current context
        if context:
            prompt += f"Available information:\n{context}\n\n"
        
        prompt += f"Patient: {user_message}\nMELCO-Care:"
        
        response = self._call_ollama(
            prompt=prompt,
            system_prompt=system_prompt
        )
        
        return response or "I apologize, I'm having trouble processing your request. Please try again or visit the hospital directly for assistance."
    
    def check_ollama_status(self) -> Dict[str, Any]:
        """Check if Ollama is running and models are available"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            
            return {
                "status": "online",
                "models_available": model_names,
                "primary_model_ready": any(self.primary_model in m for m in model_names),
                "vision_model_ready": any(self.vision_model in m for m in model_names)
            }
        except:
            return {
                "status": "offline",
                "models_available": [],
                "primary_model_ready": False,
                "vision_model_ready": False
            }


# Singleton instance
_vlm_service = None

def get_vlm_service() -> VLMService:
    """Get VLM service singleton"""
    global _vlm_service
    if _vlm_service is None:
        _vlm_service = VLMService()
    return _vlm_service
