import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../backend'))

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
import bcrypt
from datetime import datetime, timedelta
import random

# Load environment
ROOT_DIR = Path(__file__).parent.parent / 'backend'
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']

# Indian names
first_names = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Arnav", "Ayaan", "Krishna", "Ishaan",
    "Shaurya", "Atharv", "Advik", "Pranav", "Reyansh", "Muhammad", "Siddharth", "Kiaan", "Advait", "Vedant",
    "Aadhya", "Diya", "Ananya", "Saanvi", "Aarohi", "Pari", "Anvi", "Navya", "Angel", "Anika",
    "Prisha", "Myra", "Sara", "Pihu", "Riya", "Avni", "Siya", "Kiara", "Ira", "Shanaya",
    "Rajesh", "Priya", "Amit", "Sneha", "Rahul", "Pooja", "Suresh", "Kavita", "Vijay", "Meera"
]

last_names = [
    "Sharma", "Verma", "Patel", "Kumar", "Singh", "Reddy", "Nair", "Iyer", "Joshi", "Mehta",
    "Gupta", "Agarwal", "Desai", "Kulkarni", "Rao", "Pillai", "Menon", "Chopra", "Malhotra", "Bhat",
    "Das", "Sen", "Chatterjee", "Banerjee", "Mukherjee", "Khan", "Ahmed", "Ali", "Sheikh", "Siddiqui"
]

departments = [
    "Computer Science", "Electronics", "Mechanical", "Civil", "Information Technology",
    "Business Administration", "Management Studies", "Finance", "Human Resources", "Marketing",
    "Library", "Administration", "Sports", "Cultural Activities", "Research & Development"
]

faculty_designations = [
    "Professor", "Associate Professor", "Assistant Professor", "Senior Lecturer", "Lecturer"
]

management_designations = [
    "Director", "Dean", "HOD", "Assistant Director", "Manager", "Assistant Manager",
    "Administrative Officer", "Senior Clerk", "Office Assistant", "Librarian"
]

courses = [
    "B.Tech Computer Science", "B.Tech Electronics", "B.Tech Mechanical", "B.Tech Civil",
    "BBA", "MBA", "B.Com", "M.Com", "B.Sc", "M.Sc",
    "B.A Economics", "M.A Economics", "B.Ed", "M.Ed"
]

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def generate_email(name, domain="sgsu.edu.in"):
    return f"{name.lower().replace(' ', '.')}{random.randint(1, 999)}@{domain}"

def generate_phone():
    return f"+91-{random.randint(7000000000, 9999999999)}"

async def seed_database():
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print("🌱 Starting database seeding...")
    
    # Clear existing data
    print("Clearing existing data...")
    await db.users.delete_many({})
    await db.employees.delete_many({})
    await db.students.delete_many({})
    await db.attendance.delete_many({})
    await db.payroll.delete_many({})
    await db.budgets.delete_many({})
    await db.transactions.delete_many({})
    
    # Create admin user
    print("Creating admin user...")
    admin_user = {
        "id": "admin-001",
        "email": "admin@sgsu.edu.in",
        "password": hash_password("admin123"),
        "name": "Admin User",
        "role": "admin",
        "created_at": datetime.now().isoformat()
    }
    await db.users.insert_one(admin_user)
    print("✅ Admin user created (email: admin@sgsu.edu.in, password: admin123)")
    
    # Create Faculty (20)
    print("Creating faculty members...")
    faculty_list = []
    for i in range(1, 21):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        basic_salary = random.randint(50000, 120000)
        allowances = {
            "hra": basic_salary * 0.2,
            "da": basic_salary * 0.15,
            "ta": basic_salary * 0.1
        }
        ctc = basic_salary + sum(allowances.values())
        
        faculty = {
            "id": f"fac-{i:03d}",
            "employee_id": f"FAC{i:04d}",
            "name": name,
            "email": generate_email(name),
            "phone": generate_phone(),
            "department": random.choice(departments[:5]),
            "designation": random.choice(faculty_designations),
            "employee_type": "faculty",
            "joining_date": (datetime.now() - timedelta(days=random.randint(365, 3650))).strftime("%Y-%m-%d"),
            "basic_salary": basic_salary,
            "ctc": ctc,
            "allowances": allowances,
            "created_at": datetime.now().isoformat()
        }
        faculty_list.append(faculty)
    
    await db.employees.insert_many(faculty_list)
    print(f"✅ Created {len(faculty_list)} faculty members")
    
    # Create Management Staff (30)
    print("Creating management staff...")
    management_list = []
    for i in range(1, 31):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        basic_salary = random.randint(30000, 80000)
        allowances = {
            "hra": basic_salary * 0.2,
            "da": basic_salary * 0.15,
            "ta": basic_salary * 0.1
        }
        ctc = basic_salary + sum(allowances.values())
        
        staff = {
            "id": f"mgmt-{i:03d}",
            "employee_id": f"MGMT{i:04d}",
            "name": name,
            "email": generate_email(name),
            "phone": generate_phone(),
            "department": random.choice(departments[5:]),
            "designation": random.choice(management_designations),
            "employee_type": "management",
            "joining_date": (datetime.now() - timedelta(days=random.randint(365, 3650))).strftime("%Y-%m-%d"),
            "basic_salary": basic_salary,
            "ctc": ctc,
            "allowances": allowances,
            "created_at": datetime.now().isoformat()
        }
        management_list.append(staff)
    
    await db.employees.insert_many(management_list)
    print(f"✅ Created {len(management_list)} management staff")
    
    # Create Students (200)
    print("Creating students...")
    students_list = []
    for i in range(1, 201):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        year = random.randint(1, 4)
        semester = random.randint(1, 8)
        
        student = {
            "id": f"stu-{i:04d}",
            "student_id": f"STU{2024}{i:04d}",
            "name": name,
            "email": generate_email(name, "student.sgsu.edu.in"),
            "phone": generate_phone(),
            "course": random.choice(courses),
            "year": year,
            "semester": semester,
            "created_at": datetime.now().isoformat()
        }
        students_list.append(student)
    
    await db.students.insert_many(students_list)
    print(f"✅ Created {len(students_list)} students")
    
    # Create sample attendance for today
    print("Creating sample attendance records...")
    today = datetime.now().strftime("%Y-%m-%d")
    attendance_list = []
    
    # Employee attendance
    all_employees = faculty_list + management_list
    for emp in all_employees:
        status = random.choice(["present", "present", "present", "absent", "leave"])  # 60% present
        attendance_list.append({
            "id": f"att-emp-{emp['employee_id']}",
            "person_id": emp["employee_id"],
            "person_type": "employee",
            "date": today,
            "status": status,
            "marked_by": "admin-001",
            "created_at": datetime.now().isoformat()
        })
    
    # Student attendance (sample 50 students)
    for i, student in enumerate(students_list[:50]):
        status = random.choice(["present", "present", "present", "absent"])  # 75% present
        attendance_list.append({
            "id": f"att-stu-{student['student_id']}",
            "person_id": student["student_id"],
            "person_type": "student",
            "date": today,
            "status": status,
            "marked_by": "admin-001",
            "created_at": datetime.now().isoformat()
        })
    
    await db.attendance.insert_many(attendance_list)
    print(f"✅ Created {len(attendance_list)} attendance records")
    
    # Create sample budgets
    print("Creating budget records...")
    budget_categories = [
        {"category": "Salaries", "amount": 50000000, "spent": 35000000},
        {"category": "Infrastructure", "amount": 20000000, "spent": 15000000},
        {"category": "Technology", "amount": 10000000, "spent": 7000000},
        {"category": "Research & Development", "amount": 15000000, "spent": 8000000},
        {"category": "Student Activities", "amount": 5000000, "spent": 3000000},
    ]
    
    budgets_list = []
    for i, budget_data in enumerate(budget_categories):
        budget = {
            "id": f"budget-{i+1:03d}",
            "fiscal_year": "2024-2025",
            "category": budget_data["category"],
            "allocated_amount": budget_data["amount"],
            "spent_amount": budget_data["spent"],
            "description": f"Budget allocation for {budget_data['category']}",
            "created_at": datetime.now().isoformat()
        }
        budgets_list.append(budget)
    
    await db.budgets.insert_many(budgets_list)
    print(f"✅ Created {len(budgets_list)} budget records")
    
    # Create sample transactions
    print("Creating transaction records...")
    transactions_list = []
    for i in range(1, 21):
        trans_type = random.choice(["credit", "debit", "debit"])
        category = random.choice([b["category"] for b in budget_categories])
        amount = random.randint(50000, 500000)
        
        transaction = {
            "id": f"trans-{i:04d}",
            "transaction_date": (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d"),
            "category": category,
            "amount": amount,
            "transaction_type": trans_type,
            "description": f"{'Income' if trans_type == 'credit' else 'Expense'} for {category}",
            "created_by": "admin-001",
            "created_at": datetime.now().isoformat()
        }
        transactions_list.append(transaction)
    
    await db.transactions.insert_many(transactions_list)
    print(f"✅ Created {len(transactions_list)} transaction records")
    
    print("\n🎉 Database seeding completed successfully!")
    print("\n📊 Summary:")
    print(f"   - Users: 1")
    print(f"   - Faculty: {len(faculty_list)}")
    print(f"   - Management: {len(management_list)}")
    print(f"   - Students: {len(students_list)}")
    print(f"   - Attendance: {len(attendance_list)}")
    print(f"   - Budgets: {len(budgets_list)}")
    print(f"   - Transactions: {len(transactions_list)}")
    print("\n🔐 Login Credentials:")
    print("   Email: admin@sgsu.edu.in")
    print("   Password: admin123")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_database())
