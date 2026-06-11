from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import smtplib
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

class LeadCreate(BaseModel):
    kind: str = Field(..., min_length=2, max_length=40)
    name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=40)
    child_age: Optional[str] = Field(default=None, max_length=40)
    insurance: Optional[str] = Field(default=None, max_length=120)
    city: Optional[str] = Field(default=None, max_length=80)
    message: Optional[str] = Field(default=None, max_length=1500)

class LeadResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    kind: str
    name: str
    email: EmailStr
    phone: Optional[str] = None
    child_age: Optional[str] = None
    insurance: Optional[str] = None
    city: Optional[str] = None
    message: Optional[str] = None
    created_at: str
    destination_email: EmailStr
    notification_sent: bool

def get_contact_email() -> str:
    return os.environ['CONTACT_EMAIL']

def email_notifications_configured() -> bool:
    required_keys = ['SMTP_HOST', 'SMTP_PORT', 'SMTP_USERNAME', 'SMTP_PASSWORD', 'CONTACT_EMAIL']
    return all(os.environ.get(key) for key in required_keys)

def build_lead_email(lead_doc: dict[str, object]) -> EmailMessage:
    destination = get_contact_email()
    kind = str(lead_doc.get('kind', 'lead')).title()
    subject = f"New Au-Some Teacher {kind} Form Submission"
    lines = [
        f"Form type: {lead_doc.get('kind', '')}",
        f"Name: {lead_doc.get('name', '')}",
        f"Email: {lead_doc.get('email', '')}",
        f"Phone: {lead_doc.get('phone', '')}",
        f"Child age: {lead_doc.get('child_age', '')}",
        f"Insurance: {lead_doc.get('insurance', '')}",
        f"City: {lead_doc.get('city', '')}",
        f"Message: {lead_doc.get('message', '')}",
        f"Submitted at: {lead_doc.get('created_at', '')}",
    ]
    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = os.environ.get('SMTP_FROM_EMAIL', destination)
    message['To'] = destination
    message['Reply-To'] = str(lead_doc.get('email', destination))
    message.set_content('\n'.join(lines))
    return message

def send_lead_notification(lead_doc: dict[str, object]) -> bool:
    if not email_notifications_configured():
        logger.warning('Lead email notification skipped because SMTP settings are not configured')
        return False

    message = build_lead_email(lead_doc)
    smtp_host = os.environ['SMTP_HOST']
    smtp_port = int(os.environ['SMTP_PORT'])
    with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as smtp:
        smtp.starttls()
        smtp.login(os.environ['SMTP_USERNAME'], os.environ['SMTP_PASSWORD'])
        smtp.send_message(message)
    return True

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate) -> StatusCheck:
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks() -> List[StatusCheck]:
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

@api_router.post("/leads", response_model=LeadResponse)
async def create_lead(input: LeadCreate) -> dict[str, object]:
    lead_doc = input.model_dump()
    lead_doc["id"] = str(uuid.uuid4())
    lead_doc["created_at"] = datetime.now(timezone.utc).isoformat()
    lead_doc["destination_email"] = get_contact_email()
    lead_doc["notification_sent"] = False
    await db.leads.insert_one(lead_doc.copy())
    try:
        notification_sent = send_lead_notification(lead_doc)
        lead_doc["notification_sent"] = notification_sent
        await db.leads.update_one(
            {"id": lead_doc["id"]},
            {"$set": {"notification_sent": notification_sent}}
        )
    except Exception:
        logger.exception('Lead saved, but email notification failed')
    return lead_doc

@api_router.get("/contact-routing")
async def get_contact_routing() -> dict[str, object]:
    return {
        "contact_email": get_contact_email(),
        "forms_save_to_database": True,
        "email_notifications_configured": email_notifications_configured(),
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ['CORS_ORIGINS'].split(','),
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
async def shutdown_db_client() -> None:
    client.close()