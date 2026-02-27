import random
from typing import Iterator

first_names = [
    # Indian
    "Aarav","Vivaan","Aditya","Arjun","Ishaan","Kabir","Vihaan","Atharv","Reyansh","Krish",
    "Rudra","Om","Aadi","Advait","Armaan","Rohan","Rohit","Nikhil","Siddharth","Dhruv",
    # Arabic
    "Ahmed","Muhammad","Mohammed","Ahmad","Omar","Umar","Ali","Hassan","Hussein","Yusuf",
    "Youssef","Yasin","Ibrahim","Ismail","Khalid","Khaled","Saad","Faisal","Fahad","Imran",
    # US
    "James","John","Robert","Michael","William","David","Richard","Joseph","Thomas","Charles",
    "Christopher","Daniel","Matthew","Anthony","Mark","Steven","Paul","Andrew","Joshua","Kevin"
]

last_names = [
    # Indian
    "Sharma","Verma","Gupta","Agarwal","Mehta","Shah","Patel","Singh","Kaur","Kumar",
    "Reddy","Rao","Iyer","Iyengar","Menon","Nair","Pillai","Shetty",
    # Arabic
    "Mohammed","Ali","Hassan","Hussein","Ibrahim","Ismail","Khalid","Khalil","Karim",
    "Saleh","Salem","Said","Saeed","Hamdan","Hamid","Farah",
    # US
    "Smith","Johnson","Williams","Brown","Jones","Miller","Davis","Garcia","Rodriguez","Martinez",
    "Hernandez","Lopez","Gonzalez","Wilson","Anderson","Thomas"
]

departments = [
    "d0000001-0000-0000-0000-000000000001",  # CS
    "d0000002-0000-0000-0000-000000000002",  # Math
    "d0000003-0000-0000-0000-000000000003",  # Physics
    "d0000004-0000-0000-0000-000000000004",  # EE
    "d0000005-0000-0000-0000-000000000005"   # ME
]

def generate_students(count: int) -> Iterator[dict]:
    import uuid
    from datetime import datetime
    
    now_iso = datetime.utcnow().isoformat()
    
    for _ in range(count):
        fname = random.choice(first_names)
        lname = random.choice(last_names)
        email = f"{fname.lower()}.{lname.lower()}.{random.randint(1000, 99999)}@university.edu"
        dept = random.choice(departments)
        
        yield {
            "id": str(uuid.uuid4()),
            "first_name": fname,
            "last_name": lname,
            "email": email,
            "date_of_birth": "2000-01-01",
            "enrollment_date": now_iso[:10],
            "department_id": dept,
            "status": "active",
            "gpa": round(random.uniform(2.0, 4.0), 2),
            "enrolled_course_ids": [],
            "completed_course_ids": [],
            "created_at": now_iso,
            "updated_at": now_iso
        }
