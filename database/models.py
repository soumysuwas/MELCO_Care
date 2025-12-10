"""
MELCO-Care Database Models
SQLModel schemas for Users, Hospitals, Departments, Doctors, and Appointments
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship


# ============== ENUMS ==============

class UserRole(str, Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class DoctorStatus(str, Enum):
    AVAILABLE = "available"
    ON_BREAK = "on_break"
    OFF_DUTY = "off_duty"
    IN_CONSULTATION = "in_consultation"


class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EMERGENCY = "emergency"


class DepartmentType(str, Enum):
    GENERAL_MEDICINE = "General Medicine"
    PEDIATRICS = "Pediatrics"
    DERMATOLOGY = "Dermatology"
    GYNECOLOGY = "Gynecology"
    ORTHOPEDICS = "Orthopedics"
    ENT = "ENT"
    OPHTHALMOLOGY = "Ophthalmology"
    PSYCHIATRY = "Psychiatry"
    CARDIOLOGY = "Cardiology"
    PULMONOLOGY = "Pulmonology"
    DENTAL = "Dental"
    RADIOLOGY = "Radiology"
    EMERGENCY = "Emergency"
    HOMEOPATHY = "Homeopathy"
    NEUROLOGY = "Neurology"


# ============== MODELS ==============

class User(SQLModel, table=True):
    """User table - stores all users (patients, doctors, admins)"""
    __tablename__ = "users"
    
    user_id: Optional[int] = Field(default=None, primary_key=True)
    role: UserRole = Field(index=True)
    name: str = Field(max_length=100)
    email: Optional[str] = Field(default=None, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=15)
    city: str = Field(max_length=50, index=True)
    locality: Optional[str] = Field(default=None, max_length=100)
    age: int = Field(ge=0, le=120)
    gender: Gender
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    doctor_profile: Optional["Doctor"] = Relationship(back_populates="user")
    appointments_as_patient: List["Appointment"] = Relationship(
        back_populates="patient",
        sa_relationship_kwargs={"foreign_keys": "[Appointment.patient_id]"}
    )


class Hospital(SQLModel, table=True):
    """Hospital registry with location and capacity info"""
    __tablename__ = "hospitals"
    
    hospital_id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=200)
    city: str = Field(max_length=50, index=True)
    state: str = Field(max_length=50, default="Telangana")
    locality: str = Field(max_length=100)
    address: Optional[str] = Field(default=None, max_length=300)
    pincode: Optional[str] = Field(default=None, max_length=10)
    phone: Optional[str] = Field(default=None, max_length=15)
    total_beds: int = Field(ge=0, default=100)
    occupied_beds: int = Field(ge=0, default=0)
    is_government: bool = Field(default=True)
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    departments: List["Department"] = Relationship(back_populates="hospital")


class Department(SQLModel, table=True):
    """Hospital departments"""
    __tablename__ = "departments"
    
    dept_id: Optional[int] = Field(default=None, primary_key=True)
    hospital_id: int = Field(foreign_key="hospitals.hospital_id", index=True)
    name: DepartmentType
    is_emergency: bool = Field(default=False)
    floor: Optional[int] = Field(default=None)
    room_count: int = Field(default=5)
    is_active: bool = Field(default=True)
    
    # Relationships
    hospital: Optional[Hospital] = Relationship(back_populates="departments")
    doctors: List["Doctor"] = Relationship(back_populates="department")


class Doctor(SQLModel, table=True):
    """Doctor profiles linked to users and departments"""
    __tablename__ = "doctors"
    
    doctor_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.user_id", unique=True)
    dept_id: int = Field(foreign_key="departments.dept_id", index=True)
    specialization: str = Field(max_length=100)
    qualification: str = Field(max_length=200, default="MBBS")
    experience_years: int = Field(ge=0, default=5)
    queue_length: int = Field(ge=0, default=0)
    status: DoctorStatus = Field(default=DoctorStatus.AVAILABLE)
    consultation_fee: int = Field(default=0)  # 0 for government hospitals
    avg_consultation_time: int = Field(default=15)  # minutes
    
    # Relationships
    user: Optional[User] = Relationship(back_populates="doctor_profile")
    department: Optional[Department] = Relationship(back_populates="doctors")
    appointments: List["Appointment"] = Relationship(back_populates="doctor")


class Appointment(SQLModel, table=True):
    """Appointment records"""
    __tablename__ = "appointments"
    
    appointment_id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="users.user_id", index=True)
    doctor_id: int = Field(foreign_key="doctors.doctor_id", index=True)
    symptoms_raw: Optional[str] = Field(default=None, max_length=1000)  # Original user input
    symptoms_summary: Optional[str] = Field(default=None, max_length=500)  # AI-generated summary
    priority: Priority = Field(default=Priority.MEDIUM)
    status: AppointmentStatus = Field(default=AppointmentStatus.SCHEDULED)
    scheduled_date: datetime = Field(default_factory=datetime.utcnow)
    token_number: Optional[int] = Field(default=None)
    notes: Optional[str] = Field(default=None, max_length=1000)
    image_path: Optional[str] = Field(default=None, max_length=300)  # Path to uploaded medical image
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    patient: Optional[User] = Relationship(
        back_populates="appointments_as_patient",
        sa_relationship_kwargs={"foreign_keys": "[Appointment.patient_id]"}
    )
    doctor: Optional[Doctor] = Relationship(back_populates="appointments")


# ============== CHAT SESSION ==============

class ChatSession(SQLModel, table=True):
    """Chat session history for conversation context"""
    __tablename__ = "chat_sessions"
    
    session_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.user_id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)


class ChatMessage(SQLModel, table=True):
    """Individual chat messages"""
    __tablename__ = "chat_messages"
    
    message_id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="chat_sessions.session_id", index=True)
    role: str = Field(max_length=20)  # "user" or "assistant"
    content: str
    image_path: Optional[str] = Field(default=None, max_length=300)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
