"""
MELCO-Care Synthetic Data Generator
Generates realistic healthcare data for Hyderabad region
"""

import random
from datetime import datetime, timedelta
from faker import Faker
from sqlmodel import Session

from database.models import (
    User, UserRole, Gender,
    Hospital, Department, DepartmentType,
    Doctor, DoctorStatus,
    Appointment, AppointmentStatus, Priority,
    ChatSession, ChatMessage
)
from database.connection import engine, create_db_and_tables

# Initialize Faker with Indian locale
fake = Faker('en_IN')

# Hyderabad localities for realistic addresses
HYDERABAD_LOCALITIES = [
    "Secunderabad", "Kukatpally", "Banjara Hills", "Jubilee Hills",
    "Gachibowli", "Madhapur", "Hitech City", "Kondapur", "Ameerpet",
    "Begumpet", "Somajiguda", "Lakdi-ka-pul", "Mehdipatnam", "Tolichowki",
    "LB Nagar", "Dilsukhnagar", "Uppal", "ECIL", "Miyapur", "Chandanagar",
    "Kompally", "Alwal", "Bowenpally", "Malkajgiri", "Tarnaka",
    "Sainikpuri", "AS Rao Nagar", "Habsiguda", "Nacharam", "Malakpet"
]

# Common Indian names by gender
MALE_FIRST_NAMES = [
    "Rahul", "Amit", "Vijay", "Suresh", "Rajesh", "Arun", "Kiran", "Praveen",
    "Sanjay", "Manoj", "Ravi", "Mohammed", "Venkat", "Krishna", "Ramesh",
    "Deepak", "Naresh", "Satish", "Harish", "Ganesh", "Sunil", "Ashok"
]

FEMALE_FIRST_NAMES = [
    "Priya", "Anjali", "Deepa", "Sunita", "Lakshmi", "Meera", "Kavitha",
    "Padma", "Swathi", "Divya", "Sneha", "Pooja", "Radha", "Sita", "Geeta",
    "Ayesha", "Fatima", "Rekha", "Shobha", "Jyothi", "Aruna", "Vasantha"
]

LAST_NAMES = [
    "Reddy", "Sharma", "Rao", "Kumar", "Singh", "Patel", "Naidu", "Chowdary",
    "Gupta", "Verma", "Iyer", "Nair", "Varma", "Prasad", "Das", "Sahu",
    "Khan", "Ahmed", "Joshi", "Pillai", "Menon", "Patil"
]

# Hospital names for Hyderabad
HOSPITAL_NAMES = [
    "Gandhi Hospital", "Osmania General Hospital", "NIMS", "Yashoda Hospital",
    "Apollo Hospital", "KIMS Hospital", "Care Hospital", "Continental Hospital",
    "Sunshine Hospital", "MaxCure Hospital", "Citizens Hospital", "Rainbow Hospital",
    "Star Hospital", "Medicover Hospital", "Global Hospital"
]

# Sample symptoms in English and Hinglish
SAMPLE_SYMPTOMS = [
    # Hinglish symptoms
    "pet me dard ho raha hai subah se",
    "sar me bahut dard hai",
    "bukhar aa raha hai 2 din se",
    "khansi ho rahi hai bahut teez",
    "haath me sujan aa gayi hai",
    "aankh me jalan ho rahi hai",
    "chakkar aa rahe hain",
    "neend nahi aati raat ko",
    "pet kharab hai",
    "gale me dard hai",
    # English symptoms
    "I have severe headache since morning",
    "Chest pain when breathing deeply",
    "Rash on my arms and legs",
    "Difficulty in sleeping for past week",
    "Joint pain in knees",
    "Persistent cough with fever",
    "Stomach ache after eating",
    "Eye redness and irritation",
    "Back pain since last month",
    "Feeling very anxious and stressed",
    "skin allergy from some food",
    "toothache on the right side",
    "ear pain and reduced hearing",
    "baby has fever since yesterday",
    "irregular periods for 3 months"
]

# Department to symptom mapping (for realistic data)
DEPT_SYMPTOM_MAP = {
    DepartmentType.GENERAL_MEDICINE: ["bukhar", "fever", "weakness", "dard"],
    DepartmentType.DERMATOLOGY: ["rash", "skin", "allergy", "khujli"],
    DepartmentType.ENT: ["ear", "kaan", "gala", "throat", "nose"],
    DepartmentType.OPHTHALMOLOGY: ["eye", "aankh", "vision"],
    DepartmentType.ORTHOPEDICS: ["joint", "bone", "knee", "back"],
    DepartmentType.PEDIATRICS: ["baby", "child", "baccha"],
    DepartmentType.GYNECOLOGY: ["periods", "pregnancy"],
    DepartmentType.PSYCHIATRY: ["anxiety", "sleep", "depression", "stress"],
    DepartmentType.CARDIOLOGY: ["chest pain", "heart", "breathless"],
    DepartmentType.DENTAL: ["tooth", "daant", "gums"],
}


def generate_name(gender: Gender) -> str:
    """Generate an Indian name based on gender"""
    if gender == Gender.MALE:
        first = random.choice(MALE_FIRST_NAMES)
    else:
        first = random.choice(FEMALE_FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    return f"{first} {last}"


def generate_phone() -> str:
    """Generate an Indian mobile number"""
    prefixes = ["98", "99", "97", "96", "95", "94", "93", "91", "90", "89", "88", "87", "86", "85"]
    return f"+91{random.choice(prefixes)}{random.randint(10000000, 99999999)}"


def seed_users(session: Session) -> list[User]:
    """Generate 50 users: 40 patients, 8 doctors, 2 admins"""
    users = []
    
    # Create admins (2)
    for i in range(2):
        gender = random.choice([Gender.MALE, Gender.FEMALE])
        user = User(
            role=UserRole.ADMIN,
            name=generate_name(gender),
            email=f"admin{i+1}@melcocare.in",
            phone=generate_phone(),
            city="Hyderabad",
            locality=random.choice(HYDERABAD_LOCALITIES),
            age=random.randint(30, 50),
            gender=gender
        )
        users.append(user)
    
    # Create doctors (8)
    for i in range(8):
        gender = random.choice([Gender.MALE, Gender.FEMALE])
        user = User(
            role=UserRole.DOCTOR,
            name="Dr. " + generate_name(gender),
            email=f"doctor{i+1}@melcocare.in",
            phone=generate_phone(),
            city="Hyderabad",
            locality=random.choice(HYDERABAD_LOCALITIES),
            age=random.randint(30, 60),
            gender=gender
        )
        users.append(user)
    
    # Create patients (40)
    for i in range(40):
        gender = random.choice([Gender.MALE, Gender.FEMALE, Gender.OTHER])
        if gender == Gender.OTHER:
            gender = Gender.MALE  # Simplify for name generation
        user = User(
            role=UserRole.PATIENT,
            name=generate_name(gender),
            email=f"patient{i+1}@example.com" if random.random() > 0.5 else None,
            phone=generate_phone(),
            city="Hyderabad",
            locality=random.choice(HYDERABAD_LOCALITIES),
            age=random.randint(5, 85),
            gender=gender
        )
        users.append(user)
    
    session.add_all(users)
    session.commit()
    
    # Refresh to get IDs
    for user in users:
        session.refresh(user)
    
    return users


def seed_hospitals(session: Session) -> list[Hospital]:
    """Generate 15 hospitals in Hyderabad"""
    hospitals = []
    used_localities = random.sample(HYDERABAD_LOCALITIES, 15)
    
    for i, name in enumerate(HOSPITAL_NAMES):
        locality = used_localities[i]
        is_govt = i < 5  # First 5 are government hospitals
        
        hospital = Hospital(
            name=name,
            city="Hyderabad",
            state="Telangana",
            locality=locality,
            address=f"{random.randint(1, 500)}, Main Road, {locality}, Hyderabad",
            pincode=f"5000{random.randint(10, 99)}",
            phone=generate_phone(),
            total_beds=random.randint(50, 500) if is_govt else random.randint(100, 300),
            occupied_beds=0,  # Will be set later
            is_government=is_govt,
            latitude=17.385 + random.uniform(-0.1, 0.1),
            longitude=78.486 + random.uniform(-0.1, 0.1)
        )
        # Set occupied beds as a percentage
        hospital.occupied_beds = int(hospital.total_beds * random.uniform(0.4, 0.9))
        hospitals.append(hospital)
    
    session.add_all(hospitals)
    session.commit()
    
    for hospital in hospitals:
        session.refresh(hospital)
    
    return hospitals


def seed_departments(session: Session, hospitals: list[Hospital]) -> list[Department]:
    """Create departments for each hospital"""
    departments = []
    
    # Core departments every hospital has
    core_depts = [
        DepartmentType.GENERAL_MEDICINE,
        DepartmentType.EMERGENCY,
        DepartmentType.PEDIATRICS,
        DepartmentType.GYNECOLOGY,
        DepartmentType.ORTHOPEDICS
    ]
    
    # Additional departments for larger hospitals
    additional_depts = [
        DepartmentType.DERMATOLOGY,
        DepartmentType.ENT,
        DepartmentType.OPHTHALMOLOGY,
        DepartmentType.PSYCHIATRY,
        DepartmentType.CARDIOLOGY,
        DepartmentType.PULMONOLOGY,
        DepartmentType.DENTAL,
        DepartmentType.RADIOLOGY,
        DepartmentType.NEUROLOGY
    ]
    
    for hospital in hospitals:
        # All hospitals get core departments
        for dept_type in core_depts:
            dept = Department(
                hospital_id=hospital.hospital_id,
                name=dept_type,
                is_emergency=(dept_type == DepartmentType.EMERGENCY),
                floor=random.randint(0, 4),
                room_count=random.randint(3, 15),
                is_active=True
            )
            departments.append(dept)
        
        # Larger hospitals (beds > 150) get more departments
        if hospital.total_beds > 150:
            extra_count = random.randint(3, 6)
            extra_depts = random.sample(additional_depts, extra_count)
            for dept_type in extra_depts:
                dept = Department(
                    hospital_id=hospital.hospital_id,
                    name=dept_type,
                    is_emergency=False,
                    floor=random.randint(1, 5),
                    room_count=random.randint(2, 8),
                    is_active=True
                )
                departments.append(dept)
    
    session.add_all(departments)
    session.commit()
    
    for dept in departments:
        session.refresh(dept)
    
    return departments


def seed_doctors(session: Session, users: list[User], departments: list[Department]) -> list[Doctor]:
    """Link doctor users to departments"""
    doctors = []
    doctor_users = [u for u in users if u.role == UserRole.DOCTOR]
    
    # Specialization mapping
    specializations = {
        DepartmentType.GENERAL_MEDICINE: "General Physician",
        DepartmentType.DERMATOLOGY: "Dermatologist",
        DepartmentType.ENT: "ENT Specialist",
        DepartmentType.OPHTHALMOLOGY: "Ophthalmologist",
        DepartmentType.ORTHOPEDICS: "Orthopedic Surgeon",
        DepartmentType.PEDIATRICS: "Pediatrician",
        DepartmentType.GYNECOLOGY: "Gynecologist",
        DepartmentType.PSYCHIATRY: "Psychiatrist",
        DepartmentType.CARDIOLOGY: "Cardiologist",
        DepartmentType.DENTAL: "Dental Surgeon",
        DepartmentType.EMERGENCY: "Emergency Medicine",
        DepartmentType.PULMONOLOGY: "Pulmonologist",
        DepartmentType.NEUROLOGY: "Neurologist",
        DepartmentType.RADIOLOGY: "Radiologist",
        DepartmentType.HOMEOPATHY: "Homeopathic Doctor"
    }
    
    # Qualifications
    qualifications = [
        "MBBS", "MBBS, MD", "MBBS, MS", "MBBS, DNB", 
        "MBBS, DM", "BDS", "MBBS, FRCS", "MBBS, MD, DM"
    ]
    
    # Filter out emergency and radiology departments for doctor assignments
    assignable_depts = [d for d in departments 
                       if d.name not in [DepartmentType.EMERGENCY, DepartmentType.RADIOLOGY]]
    
    for i, user in enumerate(doctor_users):
        dept = random.choice(assignable_depts)
        
        # Create queue with some doctors overloaded (stress test)
        if random.random() < 0.3:  # 30% are overloaded
            queue = random.randint(25, 45)
        else:
            queue = random.randint(0, 12)
        
        doctor = Doctor(
            user_id=user.user_id,
            dept_id=dept.dept_id,
            specialization=specializations.get(dept.name, "General Physician"),
            qualification=random.choice(qualifications),
            experience_years=random.randint(2, 25),
            queue_length=queue,
            status=random.choice([DoctorStatus.AVAILABLE, DoctorStatus.AVAILABLE, 
                                 DoctorStatus.AVAILABLE, DoctorStatus.IN_CONSULTATION]),
            consultation_fee=0 if dept.hospital.is_government else random.choice([300, 500, 700, 1000]),
            avg_consultation_time=random.randint(10, 25)
        )
        doctors.append(doctor)
    
    session.add_all(doctors)
    session.commit()
    
    for doc in doctors:
        session.refresh(doc)
    
    return doctors


def seed_sample_appointments(session: Session, users: list[User], doctors: list[Doctor]) -> list[Appointment]:
    """Create some sample historical appointments"""
    appointments = []
    patient_users = [u for u in users if u.role == UserRole.PATIENT]
    
    # Create 20 sample appointments
    for i in range(20):
        patient = random.choice(patient_users)
        doctor = random.choice(doctors)
        symptom = random.choice(SAMPLE_SYMPTOMS)
        
        # Random date in past 30 days
        days_ago = random.randint(0, 30)
        scheduled_date = datetime.now() - timedelta(days=days_ago)
        
        # Status based on date
        if days_ago > 7:
            status = random.choice([AppointmentStatus.COMPLETED, AppointmentStatus.NO_SHOW])
        elif days_ago > 0:
            status = random.choice([AppointmentStatus.COMPLETED, AppointmentStatus.SCHEDULED])
        else:
            status = AppointmentStatus.SCHEDULED
        
        appointment = Appointment(
            patient_id=patient.user_id,
            doctor_id=doctor.doctor_id,
            symptoms_raw=symptom,
            symptoms_summary=f"Patient reports: {symptom[:50]}...",
            priority=random.choice([Priority.LOW, Priority.MEDIUM, Priority.MEDIUM, Priority.HIGH]),
            status=status,
            scheduled_date=scheduled_date,
            token_number=random.randint(1, 50),
            notes=None
        )
        appointments.append(appointment)
    
    session.add_all(appointments)
    session.commit()
    
    return appointments


def seed_database():
    """Main function to seed the entire database"""
    print("🏥 MELCO-Care Synthetic Data Generator")
    print("=" * 50)
    
    # Create tables
    create_db_and_tables()
    
    with Session(engine) as session:
        # Generate data in order (maintaining referential integrity)
        print("\n👥 Creating users...")
        users = seed_users(session)
        print(f"   ✅ Created {len(users)} users (Admins: 2, Doctors: 8, Patients: 40)")
        
        print("\n🏨 Creating hospitals...")
        hospitals = seed_hospitals(session)
        print(f"   ✅ Created {len(hospitals)} hospitals in Hyderabad")
        
        print("\n🏥 Creating departments...")
        departments = seed_departments(session, hospitals)
        print(f"   ✅ Created {len(departments)} departments across all hospitals")
        
        print("\n👨‍⚕️ Assigning doctors to departments...")
        doctors = seed_doctors(session, users, departments)
        print(f"   ✅ Assigned {len(doctors)} doctors to departments")
        
        print("\n📋 Creating sample appointments...")
        appointments = seed_sample_appointments(session, users, doctors)
        print(f"   ✅ Created {len(appointments)} sample appointments")
        
        print("\n" + "=" * 50)
        print("✅ Database seeded successfully!")
        print(f"   📊 Total records: {len(users) + len(hospitals) + len(departments) + len(doctors) + len(appointments)}")


if __name__ == "__main__":
    seed_database()
