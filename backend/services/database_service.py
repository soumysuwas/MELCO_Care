"""
MELCO-Care Database Service
Handles all database operations for agents and routers
"""

from typing import Optional, List
from sqlmodel import Session, select
from database.connection import get_db_session
from database.models import (
    User, UserRole,
    Hospital, Department, DepartmentType,
    Doctor, DoctorStatus,
    Appointment, AppointmentStatus, Priority,
    ChatSession, ChatMessage
)


class DatabaseService:
    """Service class for database operations"""
    
    def __init__(self, session: Optional[Session] = None):
        self._session = session
    
    @property
    def session(self) -> Session:
        if self._session is None:
            self._session = get_db_session()
        return self._session
    
    def close(self):
        if self._session:
            self._session.close()
    
    # ============== USER OPERATIONS ==============
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.session.get(User, user_id)
    
    def get_users_by_role(self, role: UserRole) -> List[User]:
        """Get all users with a specific role"""
        statement = select(User).where(User.role == role)
        return list(self.session.exec(statement).all())
    
    def create_user(self, user: User) -> User:
        """Create a new user"""
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user
    
    # ============== HOSPITAL OPERATIONS ==============
    
    def get_all_hospitals(self) -> List[Hospital]:
        """Get all hospitals"""
        statement = select(Hospital)
        return list(self.session.exec(statement).all())
    
    def get_hospitals_by_city(self, city: str) -> List[Hospital]:
        """Get hospitals in a specific city"""
        statement = select(Hospital).where(Hospital.city == city)
        return list(self.session.exec(statement).all())
    
    def get_hospital_by_id(self, hospital_id: int) -> Optional[Hospital]:
        """Get hospital by ID"""
        return self.session.get(Hospital, hospital_id)
    
    def update_hospital_beds(self, hospital_id: int, occupied: int) -> Optional[Hospital]:
        """Update occupied beds count"""
        hospital = self.session.get(Hospital, hospital_id)
        if hospital:
            hospital.occupied_beds = occupied
            self.session.commit()
            self.session.refresh(hospital)
        return hospital
    
    # ============== DEPARTMENT OPERATIONS ==============
    
    def get_departments_by_hospital(self, hospital_id: int) -> List[Department]:
        """Get all departments in a hospital"""
        statement = select(Department).where(Department.hospital_id == hospital_id)
        return list(self.session.exec(statement).all())
    
    def get_departments_by_type(self, dept_type: DepartmentType) -> List[Department]:
        """Get all departments of a specific type across all hospitals"""
        statement = select(Department).where(Department.name == dept_type)
        return list(self.session.exec(statement).all())
    
    def get_departments_by_city_and_type(self, city: str, dept_type: DepartmentType) -> List[dict]:
        """Get departments of a type in a city with hospital info"""
        statement = (
            select(Department, Hospital)
            .join(Hospital)
            .where(Hospital.city == city)
            .where(Department.name == dept_type)
            .where(Department.is_active == True)
        )
        results = self.session.exec(statement).all()
        return [
            {
                "department": dept,
                "hospital": hosp
            }
            for dept, hosp in results
        ]
    
    # ============== DOCTOR OPERATIONS ==============
    
    def get_doctors_by_department(self, dept_id: int) -> List[Doctor]:
        """Get all doctors in a department"""
        statement = select(Doctor).where(Doctor.dept_id == dept_id)
        return list(self.session.exec(statement).all())
    
    def get_available_doctors_by_specialty(
        self, 
        city: str, 
        dept_type: DepartmentType
    ) -> List[dict]:
        """Get available doctors for a specialty in a city, sorted by queue length"""
        statement = (
            select(Doctor, Department, Hospital, User)
            .join(Department, Doctor.dept_id == Department.dept_id)
            .join(Hospital, Department.hospital_id == Hospital.hospital_id)
            .join(User, Doctor.user_id == User.user_id)
            .where(Hospital.city == city)
            .where(Department.name == dept_type)
            .where(Doctor.status.in_([DoctorStatus.AVAILABLE, DoctorStatus.IN_CONSULTATION]))
            .order_by(Doctor.queue_length)
        )
        results = self.session.exec(statement).all()
        return [
            {
                "doctor": doc,
                "doctor_name": user.name,
                "department": dept,
                "hospital": hosp,
                "queue_length": doc.queue_length,
                "estimated_wait": doc.queue_length * doc.avg_consultation_time
            }
            for doc, dept, hosp, user in results
        ]
    
    def increment_doctor_queue(self, doctor_id: int) -> Optional[Doctor]:
        """Increment doctor queue when appointment is booked"""
        doctor = self.session.get(Doctor, doctor_id)
        if doctor:
            doctor.queue_length += 1
            self.session.commit()
            self.session.refresh(doctor)
        return doctor
    
    def decrement_doctor_queue(self, doctor_id: int) -> Optional[Doctor]:
        """Decrement doctor queue when appointment is completed"""
        doctor = self.session.get(Doctor, doctor_id)
        if doctor and doctor.queue_length > 0:
            doctor.queue_length -= 1
            self.session.commit()
            self.session.refresh(doctor)
        return doctor
    
    # ============== APPOINTMENT OPERATIONS ==============
    
    def create_appointment(
        self,
        patient_id: int,
        doctor_id: int,
        symptoms_raw: str,
        symptoms_summary: str,
        priority: Priority = Priority.MEDIUM,
        image_path: Optional[str] = None
    ) -> Appointment:
        """Create a new appointment and update doctor queue"""
        # Get next token number for the doctor
        doctor = self.session.get(Doctor, doctor_id)
        token_number = doctor.queue_length + 1 if doctor else 1
        
        appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            symptoms_raw=symptoms_raw,
            symptoms_summary=symptoms_summary,
            priority=priority,
            status=AppointmentStatus.SCHEDULED,
            token_number=token_number,
            image_path=image_path
        )
        
        self.session.add(appointment)
        self.increment_doctor_queue(doctor_id)
        self.session.commit()
        self.session.refresh(appointment)
        
        return appointment
    
    def get_patient_appointments(self, patient_id: int) -> List[Appointment]:
        """Get all appointments for a patient"""
        statement = (
            select(Appointment)
            .where(Appointment.patient_id == patient_id)
            .order_by(Appointment.scheduled_date.desc())
        )
        return list(self.session.exec(statement).all())
    
    def get_doctor_queue(self, doctor_id: int) -> List[Appointment]:
        """Get current queue for a doctor"""
        statement = (
            select(Appointment)
            .where(Appointment.doctor_id == doctor_id)
            .where(Appointment.status == AppointmentStatus.SCHEDULED)
            .order_by(Appointment.token_number)
        )
        return list(self.session.exec(statement).all())
    
    # ============== CHAT OPERATIONS ==============
    
    def get_or_create_chat_session(self, user_id: int) -> ChatSession:
        """Get active chat session or create new one"""
        statement = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .where(ChatSession.is_active == True)
        )
        session = self.session.exec(statement).first()
        
        if not session:
            session = ChatSession(user_id=user_id, is_active=True)
            self.session.add(session)
            self.session.commit()
            self.session.refresh(session)
        
        return session
    
    def add_chat_message(
        self, 
        session_id: int, 
        role: str, 
        content: str,
        image_path: Optional[str] = None
    ) -> ChatMessage:
        """Add a message to chat session"""
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            image_path=image_path
        )
        self.session.add(message)
        self.session.commit()
        self.session.refresh(message)
        return message
    
    def get_chat_history(self, session_id: int, limit: int = 10) -> List[ChatMessage]:
        """Get recent chat history"""
        statement = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.timestamp.desc())
            .limit(limit)
        )
        messages = list(self.session.exec(statement).all())
        return list(reversed(messages))  # Return in chronological order


# Singleton instance for convenience
def get_database_service() -> DatabaseService:
    """Get a database service instance"""
    return DatabaseService()
