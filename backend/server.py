from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
import html
import resend
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone


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
    notification_error: Optional[str] = None
    email_provider_id: Optional[str] = None

def get_contact_email() -> str:
    return os.environ['CONTACT_EMAIL']

def email_notifications_configured() -> bool:
    required_keys = ['RESEND_API_KEY', 'SENDER_EMAIL', 'CONTACT_EMAIL']
    return all(os.environ.get(key) for key in required_keys)

def lead_value(lead_doc: dict[str, object], key: str) -> str:
    value = lead_doc.get(key)
    return "" if value is None else str(value)

def build_lead_email_html(lead_doc: dict[str, object]) -> str:
    fields = [
        ("Form type", "kind"),
        ("Name", "name"),
        ("Email", "email"),
        ("Phone", "phone"),
        ("Child age", "child_age"),
        ("Insurance", "insurance"),
        ("City", "city"),
        ("Message", "message"),
        ("Submitted at", "created_at"),
    ]
    rows = "".join(
        f"""
        <tr>
          <td style=\"padding:12px 16px;border-bottom:1px solid #E2E8F0;color:#4A627A;font-weight:700;width:160px;\">{label}</td>
          <td style=\"padding:12px 16px;border-bottom:1px solid #E2E8F0;color:#163A5F;\">{html.escape(lead_value(lead_doc, key))}</td>
        </tr>
        """
        for label, key in fields
    )
    return f"""
    <div style=\"font-family:Arial,sans-serif;background:#F7F9FC;padding:24px;\">
      <div style=\"max-width:680px;margin:0 auto;background:#FFFFFF;border-radius:18px;overflow:hidden;border:1px solid #E2E8F0;\">
        <div style=\"background:#163A5F;padding:24px;color:#FFFFFF;\">
          <h1 style=\"margin:0;font-size:24px;\">New Au-Some Teacher Form Submission</h1>
          <p style=\"margin:8px 0 0;color:#D7E7F0;\">A website visitor submitted the {html.escape(lead_value(lead_doc, 'kind'))} form.</p>
        </div>
        <table style=\"width:100%;border-collapse:collapse;\">{rows}</table>
      </div>
    </div>
    """

async def send_lead_notification(lead_doc: dict[str, object]) -> bool:
    if not email_notifications_configured():
        logger.warning('Lead email notification skipped because Resend settings are not configured')
        return False

    resend.api_key = os.environ['RESEND_API_KEY']
    kind = lead_value(lead_doc, 'kind').title() or 'Lead'
    params = {
        "from": os.environ['SENDER_EMAIL'],
        "to": [get_contact_email()],
        "reply_to": lead_value(lead_doc, 'email'),
        "subject": f"New Au-Some Teacher {kind} Form Submission",
        "html": build_lead_email_html(lead_doc),
    }
    response = await asyncio.to_thread(resend.Emails.send, params)
    lead_doc["email_provider_id"] = response.get("id") if isinstance(response, dict) else None
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
    lead_doc["notification_error"] = None
    lead_doc["email_provider_id"] = None
    await db.leads.insert_one(lead_doc.copy())
    try:
        notification_sent = await send_lead_notification(lead_doc)
        lead_doc["notification_sent"] = notification_sent
        await db.leads.update_one(
            {"id": lead_doc["id"]},
            {"$set": {
                "notification_sent": notification_sent,
                "email_provider_id": lead_doc.get("email_provider_id"),
            }}
        )
    except Exception as exc:
        lead_doc["notification_error"] = str(exc)
        await db.leads.update_one(
            {"id": lead_doc["id"]},
            {"$set": {"notification_error": lead_doc["notification_error"]}}
        )
        logger.exception('Lead saved, but email notification failed')
    return lead_doc

@api_router.get("/contact-routing")
async def get_contact_routing() -> dict[str, object]:
    return {
        "contact_email": get_contact_email(),
        "sender_email": os.environ.get('SENDER_EMAIL'),
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