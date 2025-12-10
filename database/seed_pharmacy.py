"""
MELCO-Care Pharmacy Synthetic Data Generator
Generates pharmacies, medicines, inventory, and doctor signatures
"""

import random
from datetime import datetime, timedelta
from typing import List, Tuple

from sqlmodel import Session, select

from database.connection import get_engine
from database.models import (
    Pharmacy, Inventory, DoctorSignature, MedicineCategory,
    Hospital, Doctor
)


# Hyderabad pharmacy data
STANDALONE_PHARMACIES = [
    ("MedPlus Pharmacy", "Banjara Hills", "Road No. 12, Banjara Hills", 17.4126, 78.4440),
    ("Apollo Pharmacy", "Jubilee Hills", "Opposite City Center Mall, Jubilee Hills", 17.4239, 78.4096),
    ("NetMeds Store", "Hitech City", "Cyber Towers, Hitech City", 17.4485, 78.3763),
    ("Wellness Forever", "Gachibowli", "DLF Cyber City, Gachibowli", 17.4400, 78.3489),
    ("MedPlus", "Madhapur", "Ayyappa Society, Madhapur", 17.4477, 78.3915),
    ("Apollo Pharmacy", "Kondapur", "Kothaguda X Roads, Kondapur", 17.4624, 78.3506),
    ("PharmEasy Store", "Kukatpally", "JNTU Road, Kukatpally", 17.4948, 78.3996),
    ("MedPlus", "Ameerpet", "SR Nagar, Ameerpet", 17.4375, 78.4482),
    ("Generic Aadhaar", "Dilsukhnagar", "Main Road, Dilsukhnagar", 17.3687, 78.5275),
    ("Jan Aushadhi Kendra", "Secunderabad", "MG Road, Secunderabad", 17.4399, 78.4983),
    ("Wellness Pharmacy", "LB Nagar", "Near LB Nagar Metro, LB Nagar", 17.3457, 78.5522),
    ("HealthKart Store", "Kompally", "ECIL Road, Kompally", 17.5355, 78.4832),
]

# Medicine database with brand names and compositions
MEDICINES_DATA = [
    # Painkillers
    ("Dolo 650", "Paracetamol 650mg", "Micro Labs", MedicineCategory.PAINKILLER, 32.0, False),
    ("Crocin Advance", "Paracetamol 500mg", "GSK", MedicineCategory.PAINKILLER, 25.0, False),
    ("Combiflam", "Ibuprofen 400mg + Paracetamol 325mg", "Sanofi", MedicineCategory.PAINKILLER, 45.0, False),
    ("Disprin", "Aspirin 350mg", "Reckitt", MedicineCategory.PAINKILLER, 15.0, False),
    ("Voveran SR", "Diclofenac Sodium 100mg", "Novartis", MedicineCategory.PAINKILLER, 85.0, True),
    
    # Antibiotics
    ("Augmentin 625", "Amoxicillin + Clavulanate", "GSK", MedicineCategory.ANTIBIOTIC, 245.0, True),
    ("Azithral 500", "Azithromycin 500mg", "Alembic", MedicineCategory.ANTIBIOTIC, 95.0, True),
    ("Cifran 500", "Ciprofloxacin 500mg", "Sun Pharma", MedicineCategory.ANTIBIOTIC, 120.0, True),
    ("Moxikind CV 625", "Amoxicillin + Clavulanate", "Mankind", MedicineCategory.ANTIBIOTIC, 210.0, True),
    ("Monocef 200", "Cefixime 200mg", "Aristo", MedicineCategory.ANTIBIOTIC, 180.0, True),
    
    # Antihistamines
    ("Cetrizine", "Cetirizine 10mg", "Various", MedicineCategory.ANTIHISTAMINE, 12.0, False),
    ("Allegra 120", "Fexofenadine 120mg", "Sanofi", MedicineCategory.ANTIHISTAMINE, 145.0, False),
    ("Montair LC", "Montelukast + Levocetirizine", "Cipla", MedicineCategory.ANTIHISTAMINE, 165.0, True),
    ("Levocet M", "Levocetirizine + Montelukast", "Dr Reddy's", MedicineCategory.ANTIHISTAMINE, 155.0, True),
    
    # Antacids
    ("Pan 40", "Pantoprazole 40mg", "Alkem", MedicineCategory.ANTACID, 85.0, False),
    ("Omez 20", "Omeprazole 20mg", "Dr Reddy's", MedicineCategory.ANTACID, 65.0, False),
    ("Rantac 150", "Ranitidine 150mg", "JB Chemicals", MedicineCategory.ANTACID, 35.0, False),
    ("Digene Gel", "Antacid Gel", "Abbott", MedicineCategory.ANTACID, 95.0, False),
    
    # Diabetes
    ("Glycomet 500", "Metformin 500mg", "USV", MedicineCategory.DIABETES, 35.0, True),
    ("Glycomet GP 1", "Metformin + Glimepiride", "USV", MedicineCategory.DIABETES, 125.0, True),
    ("Janumet 50/500", "Sitagliptin + Metformin", "MSD", MedicineCategory.DIABETES, 680.0, True),
    ("Galvus Met", "Vildagliptin + Metformin", "Novartis", MedicineCategory.DIABETES, 550.0, True),
    
    # Cardiac
    ("Ecosprin 75", "Aspirin 75mg", "USV", MedicineCategory.CARDIAC, 18.0, True),
    ("Atorva 10", "Atorvastatin 10mg", "Zydus", MedicineCategory.CARDIAC, 95.0, True),
    ("Telma 40", "Telmisartan 40mg", "Glenmark", MedicineCategory.CARDIAC, 145.0, True),
    ("Concor 5", "Bisoprolol 5mg", "Merck", MedicineCategory.CARDIAC, 165.0, True),
    ("Amlodac 5", "Amlodipine 5mg", "Zydus", MedicineCategory.CARDIAC, 55.0, True),
    
    # Vitamins
    ("Becosules", "B-Complex + Vitamin C", "Pfizer", MedicineCategory.VITAMIN, 35.0, False),
    ("Shelcal 500", "Calcium + Vitamin D3", "Torrent", MedicineCategory.VITAMIN, 165.0, False),
    ("Revital H", "Multivitamin + Ginseng", "Sun Pharma", MedicineCategory.VITAMIN, 245.0, False),
    ("Supradyn", "Multivitamin", "Bayer", MedicineCategory.VITAMIN, 125.0, False),
    ("Neurobion Forte", "B1, B6, B12", "Merck", MedicineCategory.VITAMIN, 45.0, False),
    
    # Cough & Cold
    ("Benadryl Cough Syrup", "Diphenhydramine", "JnJ", MedicineCategory.COUGH_COLD, 85.0, False),
    ("Grilinctus", "Dextromethorphan", "Franco-Indian", MedicineCategory.COUGH_COLD, 95.0, False),
    ("Sinarest", "Paracetamol + Phenylephrine", "Centaur", MedicineCategory.COUGH_COLD, 45.0, False),
    ("Vicks Action 500", "Paracetamol + Caffeine", "P&G", MedicineCategory.COUGH_COLD, 35.0, False),
    
    # Antiseptic
    ("Betadine Solution", "Povidone Iodine 10%", "Win-Medicare", MedicineCategory.ANTISEPTIC, 125.0, False),
    ("Dettol Antiseptic", "Chloroxylenol", "Reckitt", MedicineCategory.ANTISEPTIC, 85.0, False),
    ("Soframycin Cream", "Framycetin", "Sanofi", MedicineCategory.ANTISEPTIC, 65.0, False),
    
    # Antifungal
    ("Candid Cream", "Clotrimazole 1%", "Glenmark", MedicineCategory.ANTIFUNGAL, 95.0, False),
    ("Fluconazole 150", "Fluconazole 150mg", "Cipla", MedicineCategory.ANTIFUNGAL, 65.0, True),
]


def generate_pharmacies(session: Session) -> List[Pharmacy]:
    """Generate pharmacy data - hospital-attached and standalone"""
    pharmacies = []
    
    # Get existing hospitals
    hospitals = session.exec(select(Hospital)).all()
    
    # Create hospital-attached pharmacies
    for hospital in hospitals[:8]:  # First 8 hospitals get pharmacies
        pharmacy = Pharmacy(
            hospital_id=hospital.hospital_id,
            name=f"{hospital.name} Pharmacy",
            address=hospital.address or f"{hospital.locality}, {hospital.city}",
            locality=hospital.locality,
            city=hospital.city,
            latitude=hospital.latitude or (17.38 + random.uniform(-0.1, 0.1)),
            longitude=hospital.longitude or (78.48 + random.uniform(-0.1, 0.1)),
            operating_hours="Open 24 Hours" if random.random() > 0.7 else "8:00 AM - 10:00 PM",
            license_number=f"TS-PH-{random.randint(10000, 99999)}",
            is_24hr=random.random() > 0.7,
            phone=f"+91 {random.randint(7000000000, 9999999999)}"
        )
        session.add(pharmacy)
        pharmacies.append(pharmacy)
    
    # Create standalone pharmacies
    for name, locality, address, lat, lon in STANDALONE_PHARMACIES:
        pharmacy = Pharmacy(
            hospital_id=None,  # Standalone
            name=name,
            address=address,
            locality=locality,
            city="Hyderabad",
            latitude=lat,
            longitude=lon,
            operating_hours=random.choice([
                "9:00 AM - 9:00 PM",
                "8:00 AM - 10:00 PM",
                "Open 24 Hours"
            ]),
            license_number=f"TS-PH-{random.randint(10000, 99999)}",
            is_24hr=random.random() > 0.8,
            phone=f"+91 {random.randint(7000000000, 9999999999)}"
        )
        session.add(pharmacy)
        pharmacies.append(pharmacy)
    
    session.commit()
    
    # Refresh to get IDs
    for p in pharmacies:
        session.refresh(p)
    
    return pharmacies


def generate_inventory(session: Session, pharmacies: List[Pharmacy]) -> int:
    """Generate inventory data for all pharmacies"""
    count = 0
    
    for pharmacy in pharmacies:
        # Each pharmacy stocks 60-90% of medicines
        num_medicines = int(len(MEDICINES_DATA) * random.uniform(0.6, 0.9))
        selected_medicines = random.sample(MEDICINES_DATA, num_medicines)
        
        for med_name, salt, manufacturer, category, price, requires_rx in selected_medicines:
            # Vary stock levels
            if category in [MedicineCategory.ANTIBIOTIC, MedicineCategory.DIABETES, MedicineCategory.CARDIAC]:
                # Specialized medicines - lower stock
                stock = random.randint(5, 30)
            else:
                # Common medicines - higher stock
                stock = random.randint(20, 150)
            
            # Some items occasionally out of stock
            if random.random() < 0.1:
                stock = 0
            
            inventory = Inventory(
                pharmacy_id=pharmacy.pharmacy_id,
                medicine_name=med_name,
                salt_composition=salt,
                manufacturer=manufacturer,
                category=category,
                stock_count=stock,
                price_inr=price * random.uniform(0.95, 1.1),  # Slight price variation
                requires_prescription=requires_rx,
                last_restocked=datetime.utcnow() - timedelta(days=random.randint(1, 30))
            )
            session.add(inventory)
            count += 1
    
    session.commit()
    return count


def generate_doctor_signatures(session: Session) -> int:
    """Generate doctor registration numbers for existing doctors"""
    doctors = session.exec(select(Doctor)).all()
    count = 0
    
    councils = [
        "Telangana Medical Council",
        "Andhra Pradesh Medical Council",
        "Medical Council of India"
    ]
    
    for doctor in doctors:
        # Check if signature already exists
        existing = session.exec(
            select(DoctorSignature).where(DoctorSignature.doctor_id == doctor.doctor_id)
        ).first()
        
        if not existing:
            reg_number = f"TS-{random.randint(10000, 99999)}"
            signature = DoctorSignature(
                doctor_id=doctor.doctor_id,
                medical_reg_number=reg_number,
                council_name=random.choice(councils),
                is_verified=True
            )
            session.add(signature)
            count += 1
    
    session.commit()
    return count


def seed_pharmacy_data():
    """Main function to seed all pharmacy-related data"""
    engine = get_engine()
    
    with Session(engine) as session:
        print("🏪 Generating pharmacies...")
        pharmacies = generate_pharmacies(session)
        print(f"   Created {len(pharmacies)} pharmacies")
        
        print("💊 Generating medicine inventory...")
        inv_count = generate_inventory(session, pharmacies)
        print(f"   Created {inv_count} inventory entries")
        
        print("✍️ Generating doctor signatures...")
        sig_count = generate_doctor_signatures(session)
        print(f"   Created {sig_count} doctor signatures")
        
        print("\n✅ Pharmacy data seeding complete!")
        print(f"   Pharmacies: {len(pharmacies)}")
        print(f"   Inventory: {inv_count}")
        print(f"   Doctor Signatures: {sig_count}")


if __name__ == "__main__":
    seed_pharmacy_data()
