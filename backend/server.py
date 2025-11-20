from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

# Create the main app
app = FastAPI(title="SGSU HR Management System")
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# Enums
class UserRole(str, Enum):
    ADMIN = "admin"
    HR = "hr"
    ACCOUNTS = "accounts"
    FACULTY = "faculty"
    STUDENT = "student"

class EmployeeType(str, Enum):
    FACULTY = "faculty"
    MANAGEMENT = "management"

class AttendanceStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LEAVE = "leave"
    HALF_DAY = "half_day"

# Models
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    password: str
    name: str
    role: UserRole
    employee_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: UserRole
    employee_id: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]

class Employee(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    name: str
    email: EmailStr
    phone: str
    department: str
    designation: str
    employee_type: EmployeeType
    joining_date: str
    basic_salary: float
    ctc: float
    allowances: Dict[str, float] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EmployeeCreate(BaseModel):
    employee_id: str
    name: str
    email: EmailStr
    phone: str
    department: str
    designation: str
    employee_type: EmployeeType
    joining_date: str
    basic_salary: float
    ctc: float
    allowances: Dict[str, float] = Field(default_factory=dict)

class Student(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    name: str
    email: EmailStr
    phone: str
    course: str
    year: int
    semester: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StudentCreate(BaseModel):
    student_id: str
    name: str
    email: EmailStr
    phone: str
    course: str
    year: int
    semester: int

class Attendance(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    person_id: str  # employee_id or student_id
    person_type: str  # employee or student
    date: str
    status: AttendanceStatus
    remarks: Optional[str] = None
    marked_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AttendanceCreate(BaseModel):
    person_id: str
    person_type: str
    date: str
    status: AttendanceStatus
    remarks: Optional[str] = None
    marked_by: Optional[str] = None

class Payroll(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    month: str
    year: int
    basic_salary: float
    allowances: Dict[str, float]
    deductions: Dict[str, float]
    epf_employee: float
    epf_employer: float
    gross_salary: float
    net_salary: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PayrollCreate(BaseModel):
    employee_id: str
    month: str
    year: int

class Budget(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    fiscal_year: str
    category: str
    allocated_amount: float
    spent_amount: float = 0
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BudgetCreate(BaseModel):
    fiscal_year: str
    category: str
    allocated_amount: float
    description: Optional[str] = None

class Transaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    transaction_date: str
    category: str
    amount: float
    transaction_type: str  # credit or debit
    description: str
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TransactionCreate(BaseModel):
    transaction_date: str
    category: str
    amount: float
    transaction_type: str
    description: str
    created_by: str

# Helper Functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

def calculate_epfo(basic_salary: float) -> tuple:
    """Calculate EPF as per 7th pay commission - 12% employee, 12% employer"""
    epf_employee = basic_salary * 0.12
    epf_employer = basic_salary * 0.12
    return epf_employee, epf_employer

# Authentication Routes
@api_router.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    # Check if user exists
    existing = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    hashed_pw = hash_password(user_data.password)
    user_dict = user_data.model_dump()
    user_dict['password'] = hashed_pw
    user = User(**user_dict)
    
    doc = user.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.users.insert_one(doc)
    
    # Create token
    token = create_access_token({"sub": user.id, "role": user.role})
    user_response = user.model_dump()
    del user_response['password']
    
    return {"access_token": token, "token_type": "bearer", "user": user_response}

@api_router.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user['password']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": user['id'], "role": user['role']})
    del user['password']
    return {"access_token": token, "token_type": "bearer", "user": user}

@api_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user

# Employee Routes
@api_router.post("/employees", response_model=Employee)
async def create_employee(employee: EmployeeCreate, current_user: dict = Depends(get_current_user)):
    # Check if employee_id exists
    existing = await db.employees.find_one({"employee_id": employee.employee_id}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Employee ID already exists")
    
    emp_obj = Employee(**employee.model_dump())
    doc = emp_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.employees.insert_one(doc)
    return emp_obj

@api_router.get("/employees", response_model=List[Employee])
async def get_employees(current_user: dict = Depends(get_current_user)):
    employees = await db.employees.find({}, {"_id": 0}).to_list(1000)
    return employees

@api_router.get("/employees/{employee_id}", response_model=Employee)
async def get_employee(employee_id: str, current_user: dict = Depends(get_current_user)):
    employee = await db.employees.find_one({"employee_id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee

@api_router.put("/employees/{employee_id}", response_model=Employee)
async def update_employee(employee_id: str, employee_data: EmployeeCreate, current_user: dict = Depends(get_current_user)):
    existing = await db.employees.find_one({"employee_id": employee_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    update_data = employee_data.model_dump()
    await db.employees.update_one({"employee_id": employee_id}, {"$set": update_data})
    updated = await db.employees.find_one({"employee_id": employee_id}, {"_id": 0})
    return updated

@api_router.delete("/employees/{employee_id}")
async def delete_employee(employee_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.employees.delete_one({"employee_id": employee_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Employee not found")
    return {"message": "Employee deleted successfully"}

# Student Routes
@api_router.post("/students", response_model=Student)
async def create_student(student: StudentCreate, current_user: dict = Depends(get_current_user)):
    existing = await db.students.find_one({"student_id": student.student_id}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Student ID already exists")
    
    student_obj = Student(**student.model_dump())
    doc = student_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.students.insert_one(doc)
    return student_obj

@api_router.get("/students", response_model=List[Student])
async def get_students(current_user: dict = Depends(get_current_user)):
    students = await db.students.find({}, {"_id": 0}).to_list(1000)
    return students

@api_router.get("/students/{student_id}", response_model=Student)
async def get_student(student_id: str, current_user: dict = Depends(get_current_user)):
    student = await db.students.find_one({"student_id": student_id}, {"_id": 0})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student

@api_router.put("/students/{student_id}", response_model=Student)
async def update_student(student_id: str, student_data: StudentCreate, current_user: dict = Depends(get_current_user)):
    existing = await db.students.find_one({"student_id": student_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Student not found")
    
    update_data = student_data.model_dump()
    await db.students.update_one({"student_id": student_id}, {"$set": update_data})
    updated = await db.students.find_one({"student_id": student_id}, {"_id": 0})
    return updated

@api_router.delete("/students/{student_id}")
async def delete_student(student_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.students.delete_one({"student_id": student_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": "Student deleted successfully"}

# Attendance Routes
@api_router.post("/attendance", response_model=Attendance)
async def mark_attendance(attendance: AttendanceCreate, current_user: dict = Depends(get_current_user)):
    # Check for duplicate
    existing = await db.attendance.find_one({
        "person_id": attendance.person_id,
        "date": attendance.date
    }, {"_id": 0})
    
    if existing:
        # Update existing
        update_data = attendance.model_dump()
        await db.attendance.update_one(
            {"person_id": attendance.person_id, "date": attendance.date},
            {"$set": update_data}
        )
        updated = await db.attendance.find_one({
            "person_id": attendance.person_id,
            "date": attendance.date
        }, {"_id": 0})
        return updated
    
    att_obj = Attendance(**attendance.model_dump())
    doc = att_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.attendance.insert_one(doc)
    return att_obj

@api_router.get("/attendance")
async def get_attendance(
    person_id: Optional[str] = None,
    person_type: Optional[str] = None,
    date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if person_id:
        query["person_id"] = person_id
    if person_type:
        query["person_type"] = person_type
    if date:
        query["date"] = date
    
    attendance = await db.attendance.find(query, {"_id": 0}).to_list(1000)
    return attendance

# Payroll Routes
@api_router.post("/payroll/generate", response_model=Payroll)
async def generate_payroll(payroll_data: PayrollCreate, current_user: dict = Depends(get_current_user)):
    # Get employee
    employee = await db.employees.find_one({"employee_id": payroll_data.employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Check if payroll exists
    existing = await db.payroll.find_one({
        "employee_id": payroll_data.employee_id,
        "month": payroll_data.month,
        "year": payroll_data.year
    }, {"_id": 0})
    
    if existing:
        raise HTTPException(status_code=400, detail="Payroll already generated for this period")
    
    basic_salary = employee['basic_salary']
    allowances = employee.get('allowances', {})
    
    # Calculate EPFO
    epf_employee, epf_employer = calculate_epfo(basic_salary)
    
    # Calculate totals
    total_allowances = sum(allowances.values())
    gross_salary = basic_salary + total_allowances
    total_deductions = epf_employee
    net_salary = gross_salary - total_deductions
    
    payroll = Payroll(
        employee_id=payroll_data.employee_id,
        month=payroll_data.month,
        year=payroll_data.year,
        basic_salary=basic_salary,
        allowances=allowances,
        deductions={"epf": epf_employee},
        epf_employee=epf_employee,
        epf_employer=epf_employer,
        gross_salary=gross_salary,
        net_salary=net_salary
    )
    
    doc = payroll.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.payroll.insert_one(doc)
    return payroll

@api_router.get("/payroll", response_model=List[Payroll])
async def get_payrolls(
    employee_id: Optional[str] = None,
    month: Optional[str] = None,
    year: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if employee_id:
        query["employee_id"] = employee_id
    if month:
        query["month"] = month
    if year:
        query["year"] = year
    
    payrolls = await db.payroll.find(query, {"_id": 0}).to_list(1000)
    return payrolls

# Budget Routes
@api_router.post("/budgets", response_model=Budget)
async def create_budget(budget: BudgetCreate, current_user: dict = Depends(get_current_user)):
    budget_obj = Budget(**budget.model_dump())
    doc = budget_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.budgets.insert_one(doc)
    return budget_obj

@api_router.get("/budgets", response_model=List[Budget])
async def get_budgets(fiscal_year: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {}
    if fiscal_year:
        query["fiscal_year"] = fiscal_year
    budgets = await db.budgets.find(query, {"_id": 0}).to_list(1000)
    return budgets

@api_router.put("/budgets/{budget_id}", response_model=Budget)
async def update_budget(budget_id: str, budget_data: BudgetCreate, current_user: dict = Depends(get_current_user)):
    existing = await db.budgets.find_one({"id": budget_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    update_data = budget_data.model_dump()
    await db.budgets.update_one({"id": budget_id}, {"$set": update_data})
    updated = await db.budgets.find_one({"id": budget_id}, {"_id": 0})
    return updated

# Transaction Routes
@api_router.post("/transactions", response_model=Transaction)
async def create_transaction(transaction: TransactionCreate, current_user: dict = Depends(get_current_user)):
    trans_obj = Transaction(**transaction.model_dump())
    doc = trans_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.transactions.insert_one(doc)
    
    # Update budget if category matches
    if transaction.transaction_type == "debit":
        await db.budgets.update_one(
            {"category": transaction.category},
            {"$inc": {"spent_amount": transaction.amount}}
        )
    
    return trans_obj

@api_router.get("/transactions", response_model=List[Transaction])
async def get_transactions(
    category: Optional[str] = None,
    transaction_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if category:
        query["category"] = category
    if transaction_type:
        query["transaction_type"] = transaction_type
    
    transactions = await db.transactions.find(query, {"_id": 0}).to_list(1000)
    return transactions

# Dashboard Stats
@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    total_employees = await db.employees.count_documents({})
    total_students = await db.students.count_documents({})
    total_faculty = await db.employees.count_documents({"employee_type": "faculty"})
    total_management = await db.employees.count_documents({"employee_type": "management"})
    
    # Get today's attendance
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_attendance = await db.attendance.count_documents({"date": today, "status": "present"})
    
    # Get this month's payroll total
    current_month = datetime.now(timezone.utc).strftime("%B")
    current_year = datetime.now(timezone.utc).year
    payroll_pipeline = [
        {"$match": {"month": current_month, "year": current_year}},
        {"$group": {"_id": None, "total": {"$sum": "$net_salary"}}}
    ]
    payroll_result = await db.payroll.aggregate(payroll_pipeline).to_list(1)
    total_payroll = payroll_result[0]['total'] if payroll_result else 0
    
    return {
        "total_employees": total_employees,
        "total_students": total_students,
        "total_faculty": total_faculty,
        "total_management": total_management,
        "today_attendance": today_attendance,
        "monthly_payroll": total_payroll
    }

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
