"""
CommunityHub - Backend API
FastAPI application for community request management with AI categorization,
prioritization, matchmaking, Notion integration, and email automation.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid
import json
import os

#dotenv is optional but recommended for .env management
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("[WARN] python-dotenv is not installed; .env support unavailable")

# Optional integrations (if installed)
try:
    from notion_client import AsyncClient
except ImportError:
    AsyncClient = None
    print("[WARN] notion-client not installed; Notion sync disabled")

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
except ImportError:
    SendGridAPIClient = None
    Mail = None
    print("[WARN] sendgrid not installed; SendGrid email disabled")

try:
    import resend
except ImportError:
    resend = None
    print("[WARN] resend not installed; Resend email disabled")

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
GROQ_API_TOKEN = os.getenv("GROQ_API_TOKEN")
GROQ_PROJECT_ID = os.getenv("GROQ_PROJECT_ID")
GROQ_DATASET = os.getenv("GROQ_DATASET", "production")

app = FastAPI(
    title="CommunityHub API",
    description="Community request management system with AI-powered categorization and matchmaking",
    version="1.0.0"
)


class GroqQuery(BaseModel):
    query: str
    params: Optional[dict] = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# ENUMS & CONSTANTS
# ─────────────────────────────────────────────

class RequestCategory(str, Enum):
    HIRING = "hiring"
    INVESTMENT = "investment"
    SPEAKING = "speaking"
    MARKETING = "marketing"
    SALES = "sales"
    CLIENT_SEARCH = "client_search"
    MENTORSHIP = "mentorship"
    PARTNERSHIP = "partnership"
    TECHNICAL = "technical"
    OTHER = "other"

class RequestStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

class RequesterType(str, Enum):
    STARTUP = "startup"
    INVESTOR = "investor"
    SERVICE_PROVIDER = "service_provider"

class PriorityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

CATEGORY_LABELS = {
    RequestCategory.HIRING: "Hľadanie zamestnanca",
    RequestCategory.INVESTMENT: "Hľadanie investora",
    RequestCategory.SPEAKING: "Speaking na evente",
    RequestCategory.MARKETING: "Marketingová podpora",
    RequestCategory.SALES: "Podpora v sales",
    RequestCategory.CLIENT_SEARCH: "Hľadanie klientov",
    RequestCategory.MENTORSHIP: "Mentorstvo",
    RequestCategory.PARTNERSHIP: "Partnerstvo",
    RequestCategory.TECHNICAL: "Technická pomoc",
    RequestCategory.OTHER: "Iné",
}

CATEGORY_KEYWORDS = {
    RequestCategory.HIRING: ["zamestnanec", "developer", "hire", "hiring", "pozícia", "job", "CTO", "frontend", "backend", "recruit"],
    RequestCategory.INVESTMENT: ["investor", "funding", "seed", "round", "investícia", "kapitál", "VC", "angel"],
    RequestCategory.SPEAKING: ["speaker", "event", "konferencia", "talk", "prednáška", "panel", "keynote"],
    RequestCategory.MARKETING: ["marketing", "social media", "brand", "content", "PR", "reklama", "kampaň"],
    RequestCategory.SALES: ["sales", "predaj", "pipeline", "closing", "CRM", "obchod", "deals"],
    RequestCategory.CLIENT_SEARCH: ["klient", "client", "zákazník", "customer", "B2B", "lead"],
    RequestCategory.MENTORSHIP: ["mentor", "rada", "poradenstvo", "coaching", "guidance", "experience"],
    RequestCategory.PARTNERSHIP: ["partner", "spolupráca", "integration", "joint venture", "collaboration"],
    RequestCategory.TECHNICAL: ["technický", "bug", "infrastructure", "API", "cloud", "AWS", "databáza"],
}

ROLE_FOR_CATEGORY = {
    RequestCategory.HIRING: "HR Director",
    RequestCategory.INVESTMENT: "Partner",
    RequestCategory.SPEAKING: "Ecosystem Lead",
    RequestCategory.MARKETING: "CMO",
    RequestCategory.SALES: "Sales Director",
    RequestCategory.CLIENT_SEARCH: "Account Executive",
    RequestCategory.MENTORSHIP: "Mentor",
    RequestCategory.PARTNERSHIP: "Partnerships Lead",
    RequestCategory.TECHNICAL: "CTO",
    RequestCategory.OTHER: "Community Manager",
}

# ─────────────────────────────────────────────
# IN-MEMORY DATABASE (replace with PostgreSQL/Supabase in production)
# ─────────────────────────────────────────────

db_requests: dict = {}
db_members: dict = {}

# Seed some community members for matchmaking demo
SEED_MEMBERS = [
    {
        "id": "m1", "name": "Jana Kováčová", "role": "HR Director", "company": "TechCorp SK",
        "expertise": [RequestCategory.HIRING], "email": "jana@techcorp.sk",
        "availability": True, "matches_resolved": 12
    },
    {
        "id": "m2", "name": "Marek Novák", "role": "Partner", "company": "Credo Ventures",
        "expertise": [RequestCategory.INVESTMENT, RequestCategory.MENTORSHIP], "email": "marek@credo.vc",
        "availability": True, "matches_resolved": 8
    },  
    {
        "id": "m3", "name": "Lucia Horáková", "role": "CMO", "company": "GrowthLab",
        "expertise": [RequestCategory.MARKETING, RequestCategory.SALES], "email": "lucia@growthlab.sk",
        "availability": True, "matches_resolved": 15
    },
    {
        "id": "m4", "name": "Peter Blaho", "role": "Ecosystem Lead", "company": "Startup Grind Bratislava",
        "expertise": [RequestCategory.SPEAKING, RequestCategory.PARTNERSHIP], "email": "peter@startupgrind.sk",
        "availability": True, "matches_resolved": 6
    },
    {
        "id": "m5", "name": "Zuzana Mináčová", "role": "CTO", "company": "SaaS Studio",
        "expertise": [RequestCategory.TECHNICAL, RequestCategory.MENTORSHIP], "email": "zuzana@saasstudio.sk",
        "availability": False, "matches_resolved": 20
    },
    {
        "id": "m6", "name": "Tomáš Ferko", "role": "Sales Director", "company": "B2B Pros",
        "expertise": [RequestCategory.SALES, RequestCategory.CLIENT_SEARCH], "email": "tomas@b2bpros.sk",
        "availability": True, "matches_resolved": 18
    },
]

for m in SEED_MEMBERS:
    db_members[m["id"]] = m

# Start with roles from category routing map for role-level focus (not person-level)
db_roles: dict = {}
for cat, role_name in ROLE_FOR_CATEGORY.items():
    db_roles[role_name] = {
        "role": role_name,
        "categories": [cat],
        "description": f"Auto-generated role for category {cat.value}",
    }

# ─────────────────────────────────────────────
# PYDANTIC MODELS
# ─────────────────────────────────────────────

class RequestCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=200, description="Short title of the request")
    description: str = Field(..., min_length=20, description="Detailed description")
    requester_name: str = Field(..., min_length=2)
    requester_email: EmailStr
    requester_type: Optional[RequesterType] = None
    company: Optional[str] = None
    urgency_self_reported: Optional[PriorityLevel] = PriorityLevel.MEDIUM
    tags: Optional[List[str]] = []
    desired_role: Optional[str] = None

class RequestUpdate(BaseModel):
    status: Optional[RequestStatus] = None
    assigned_to: Optional[str] = None
    assigned_role: Optional[str] = None
    internal_notes: Optional[str] = None
    value_delivered: Optional[bool] = None
    value_description: Optional[str] = None

class MatchFeedback(BaseModel):
    request_id: str
    member_id: str
    accepted: bool
    note: Optional[str] = None

class RoleAssignment(BaseModel):
    role: str
    member_id: Optional[str] = None

class RoleConfig(BaseModel):
    role: str
    categories: List[RequestCategory]
    description: Optional[str] = None

class RoleUpdate(BaseModel):
    categories: Optional[List[RequestCategory]] = None
    description: Optional[str] = None

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

class MemberCreate(BaseModel):
    name: str = Field(..., min_length=2)
    role: str
    company: str
    expertise: List[RequestCategory]
    email: EmailStr
    availability: bool = True
    matches_resolved: int = 0

class MemberUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    company: Optional[str] = None
    expertise: Optional[List[RequestCategory]] = None
    email: Optional[EmailStr] = None
    availability: Optional[bool] = None
    matches_resolved: Optional[int] = None

# ─────────────────────────────────────────────
# AI LOGIC (deterministic rules — swap for Claude API in production)
# ─────────────────────────────────────────────

def categorize_request(title: str, description: str) -> RequestCategory:
    """Rule-based categorization. In production: call Claude API."""
    text = (title + " " + description).lower()
    scores = {cat: 0 for cat in RequestCategory}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text:
                scores[cat] += 1
    best = max(scores, key=lambda c: scores[c])
    return best if scores[best] > 0 else RequestCategory.OTHER


def infer_requester_type(title: str, description: str) -> RequesterType:
    """Infer requestor type from keywords / category."""
    text = (title + " " + description).lower()

    investor_words = ["investor", "invest", "funding", "seed", "round", "vc", "angel", "kapitál", "investícia"]
    startup_words = ["startup", "scale", "team", "venture", "growth", "hiring", "developer", "cto", "recruit"]
    service_words = ["agency", "service", "support", "consult", "consulting", "marketing", "sales", "technical", "infrastructure", "api"]
    community_words = ["community", "network", "mentor", "event", "conference", "panel", "session", "speaking"]

    if any(w in text for w in investor_words):
        return RequesterType.INVESTOR
    if any(w in text for w in startup_words):
        return RequesterType.STARTUP
    if any(w in text for w in service_words):
        return RequesterType.SERVICE_PROVIDER
    if any(w in text for w in community_words):
        return RequesterType.SERVICE_PROVIDER

    category = categorize_request(title, description)
    category_map = {
        RequestCategory.INVESTMENT: RequesterType.INVESTOR,
        RequestCategory.HIRING: RequesterType.STARTUP,
        RequestCategory.CLIENT_SEARCH: RequesterType.STARTUP,
        RequestCategory.MARKETING: RequesterType.SERVICE_PROVIDER,
        RequestCategory.SALES: RequesterType.SERVICE_PROVIDER,
        RequestCategory.TECHNICAL: RequesterType.SERVICE_PROVIDER,
        RequestCategory.MENTORSHIP: RequesterType.SERVICE_PROVIDER,
        RequestCategory.SPEAKING: RequesterType.SERVICE_PROVIDER,
        RequestCategory.PARTNERSHIP: RequesterType.SERVICE_PROVIDER,
        RequestCategory.OTHER: RequesterType.SERVICE_PROVIDER,
    }
    return category_map.get(category, RequesterType.COMMUNITY_MEMBER)


def calculate_priority(
    category: RequestCategory,
    urgency_self_reported: PriorityLevel,
    requester_type: RequesterType,
    description: str
) -> PriorityLevel:
    """Score-based priority engine."""
    score = 0

    # Category weights
    category_weights = {
        RequestCategory.INVESTMENT: 4,
        RequestCategory.HIRING: 3,
        RequestCategory.SALES: 3,
        RequestCategory.CLIENT_SEARCH: 3,
        RequestCategory.SPEAKING: 2,
        RequestCategory.MARKETING: 2,
        RequestCategory.MENTORSHIP: 1,
        RequestCategory.PARTNERSHIP: 2,
        RequestCategory.TECHNICAL: 2,
        RequestCategory.OTHER: 1,
    }
    score += category_weights.get(category, 1)

    # Self-reported urgency
    urgency_score = {PriorityLevel.LOW: 0, PriorityLevel.MEDIUM: 1, PriorityLevel.HIGH: 2, PriorityLevel.URGENT: 3}
    score += urgency_score.get(urgency_self_reported, 1)

    # Requester type boost
    if requester_type == RequesterType.STARTUP:
        score += 2
    elif requester_type == RequesterType.INVESTOR:
        score += 3

    # Urgency keywords
    urgent_words = ["asap", "urgentne", "okamžite", "dnes", "deadline", "critical", "immediately"]
    if any(w in description.lower() for w in urgent_words):
        score += 2

    if score >= 9:
        return PriorityLevel.URGENT
    elif score >= 6:
        return PriorityLevel.HIGH
    elif score >= 3:
        return PriorityLevel.MEDIUM
    else:
        return PriorityLevel.LOW

def find_matches(category: RequestCategory, description: str, limit: int = 3) -> List[dict]:
    """Return top matching community members for a request."""
    matches = []
    for member in db_members.values():
        if category in member["expertise"] and member["availability"]:
            score = member["matches_resolved"]  # weight by track record
            matches.append({**member, "_score": score})
    matches.sort(key=lambda x: x["_score"], reverse=True)
    return matches[:limit]


def find_role_matches(category: RequestCategory) -> List[dict]:
    """Return top matching roles for a request and count available members."""
    role_matches = []
    for role_config in db_roles.values():
        if category in role_config["categories"]:
            available_members = sum(
                1
                for m in db_members.values()
                if m["role"].lower() == role_config["role"].lower() and m["availability"]
            )
            role_matches.append({
                "role": role_config["role"],
                "categories": [c.value for c in role_config["categories"]],
                "available_members": available_members,
            })
    role_matches.sort(key=lambda x: x["available_members"], reverse=True)
    return role_matches


def generate_email_response(request_data: dict) -> dict:
    """Generate automated email content for the requester."""
    priority_emoji = {
        PriorityLevel.URGENT: "🔴",
        PriorityLevel.HIGH: "🟠",
        PriorityLevel.MEDIUM: "🟡",
        PriorityLevel.LOW: "🟢",
    }
    category = request_data.get("category")
    if isinstance(category, RequestCategory):
        cat_label = CATEGORY_LABELS.get(category, str(category))
    else:
        cat_label = CATEGORY_LABELS.get(category, str(category))

    priority = request_data.get("priority")
    if isinstance(priority, PriorityLevel):
        priority_value = priority.value
        emoji = priority_emoji.get(priority, "")
    else:
        priority_value = str(priority)
        emoji = priority_emoji.get(PriorityLevel(priority_value) if priority_value in PriorityLevel._value2member_map_ else None, "")

    subject = f"✅ Vaša žiadosť bola prijatá – {request_data['title']}"
    body = f"""Dobrý deň {request_data['requester_name']},

ďakujeme za zaslanie žiadosti do CommunityHub systému.

📋 Detaily žiadosti:
• ID: {request_data['id']}
• Kategória: {cat_label}
• Priorita: {emoji} {priority_value.upper()}
• Stav: Otvorená

Naši koordinátori sa vám ozvú čo najskôr. Priemerne riešime žiadosti do 48 hodín.

Sledovať stav žiadosti môžete tu: https://communityhub.sk/request/{request_data['id']}

S pozdravom,
CommunityHub Team
"""
    return {"subject": subject, "body": body, "to": request_data["requester_email"]}


def local_chat_response(messages: List[ChatMessage]) -> str:
    """Fallback chat agent if GROQ is unavailable; uses rule-based suggestions."""
    latest = messages[-1].content.lower().strip() if messages else ""

    if "hiring" in latest or "zamestnanec" in latest or "developer" in latest:
        return "Pre hiring potreby odporúčame vytvoriť jasný profil pozície + výberový proces, potom priradiť HR manažéra. Pomôžem vám zostaviť job post, ak chcete."

    if "invest" in latest or "funding" in latest or "investor" in latest:
        return "Zamerajte sa na prehľad finančných metrík a dohodu, potom zacielte investorov na startupové výzvy. Môžem vygenerovať investor deck šablónu."

    if "marketing" in latest or "social" in latest:
        return "Investujte do konzistentnej značky a dátovo vedených kampaní. Navrhujem sekundárne A/B testovanie kreatív."

    if "technical" in latest or "api" in latest or "bug" in latest:
        return "Začnite vysvetlením aktuálnej architektúry a problémov, následne definujte priority úloh. Vyplním vám návrh troubleshooting postupu."

    if "hello" in latest or "hi" in latest or "ahoj" in latest:
        return "Ahoj! Ja som CommunityHub AI asistent. Opíšte mi svoju potrebu a pomôžem s routovaním/odhadom priority."

    return "Ďakujem, prijal som otázku. Prosím, poskytnite viac detailov a ja zaistím konkrétnejšiu odpoveď a akčný plán."


def groq_chat_response(message: str) -> str:
    """Try to get a response from a GROQ dataset; fallback to local AI if nothing found."""
    if not GROQ_API_TOKEN or not GROQ_PROJECT_ID:
        return local_chat_response([ChatMessage(role="user", content=message)])

    import httpx
    base_url = f"https://{GROQ_PROJECT_ID}.api.sanity.io/v2024-01-26/data/query/{GROQ_DATASET}"
    headers = {
        "Authorization": f"Bearer {GROQ_API_TOKEN}",
        "Accept": "application/json",
    }

    # Generic FAQ lookup pattern; adjust dataset schema accordingly.
    sanitized = message.replace('"', '').replace("'", "")
    query = f'*[_type == "faq" && (lower(question) match "*{sanitized.lower()}*" || lower(answer) match "*{sanitized.lower()}*")][0]{{answer}}'

    params = {"query": query}
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(base_url, headers=headers, params=params)
        if resp.status_code == 200:
            body = resp.json()
            if body.get("result") and isinstance(body["result"], dict):
                answer = body["result"].get("answer")
                if answer:
                    return answer
    except Exception:
        pass

    return local_chat_response([ChatMessage(role="user", content=message)])


# ─────────────────────────────────────────────
# NOTION INTEGRATION (stub — requires notion-client in production)
# ─────────────────────────────────────────────

async def sync_to_notion(request_data: dict):
    """Sync a request to Notion database (if configured), otherwise logs stub."""
    if not AsyncClient:
        print("[Notion Sync] Skipping because notion-client isn't installed")
        return False

    if NOTION_TOKEN and NOTION_DATABASE_ID:
        try:
            notion = AsyncClient(auth=NOTION_TOKEN)
            await notion.pages.create(
                parent={"database_id": NOTION_DATABASE_ID},
                properties={
                    "Title": {"title": [{"text": {"content": request_data["title"]}}]},
                    "Category": {"select": {"name": CATEGORY_LABELS.get(request_data["category"], str(request_data["category"]))}},
                    "Priority": {"select": {"name": request_data["priority"].value if hasattr(request_data["priority"], 'value') else request_data["priority"]}},
                    "Status": {"status": {"name": request_data["status"].value if hasattr(request_data["status"], 'value') else request_data["status"]}},
                    "Requester": {"rich_text": [{"text": {"content": request_data["requester_name"]}}]},
                    "Email": {"email": request_data["requester_email"]},
                    "Company": {"rich_text": [{"text": {"content": request_data.get("company", "")}}]},
                    "Created": {"date": {"start": request_data["created_at"]}},
                }
            )
            print(f"[Notion Sync] Synced request {request_data['id']} to Notion database")
            return True
        except Exception as e:
            print(f"[Notion Sync] Failed to sync request {request_data['id']}: {e}")
            return False
    else:
        print(f"[Notion Sync] Staging mode enabled, skipping real sync for request {request_data['id']}")
        return True

# ─────────────────────────────────────────────
# EMAIL AUTOMATION (stub — requires sendgrid/resend in production)
# ─────────────────────────────────────────────

async def send_automated_email(email_data: dict):
    """Send automated email to requester (SendGrid/Resend if configured)."""
    if SENDGRID_API_KEY and SendGridAPIClient and Mail:
        try:
            sg = SendGridAPIClient(api_key=SENDGRID_API_KEY)
            message = Mail(
                from_email="noreply@communityhub.sk",
                to_emails=email_data["to"],
                subject=email_data["subject"],
                plain_text_content=email_data["body"]
            )
            sg.send(message)
            print(f"[Email] Sent via SendGrid to {email_data['to']}")
            return True
        except Exception as e:
            print(f"[Email] SendGrid send failed: {e}")
            return False
    elif RESEND_API_KEY and resend:
        try:
            resend.api_key = RESEND_API_KEY
            resend.Emails.send({
                "from": "CommunityHub <noreply@communityhub.sk>",
                "to": [email_data["to"]],
                "subject": email_data["subject"],
                "text": email_data["body"],
            })
            print(f"[Email] Sent via Resend to {email_data['to']}")
            return True
        except Exception as e:
            print(f"[Email] Resend send failed: {e}")
            return False
    else:
        print(f"[Email] No transactional provider configured or client lib missing, skip email to {email_data['to']}.")
        print(f"[Email] Preview subject={email_data['subject']} body height {len(email_data['body'])}")
        return True

# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "service": "CommunityHub API", "version": "1.0.0"}

@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy", "requests_count": len(db_requests), "members_count": len(db_members)}


# ── REQUESTS ──────────────────────────────────

@app.post("/requests", tags=["Requests"], summary="Submit a new community request")
async def create_request(payload: RequestCreate, background_tasks: BackgroundTasks):
    """
    Submit a new request. The system will:
    1. Auto-categorize using AI
    2. Calculate priority score
    3. Find matching community members
    4. Sync to Notion (background)
    5. Send automated email confirmation (background)
    """
    request_id = str(uuid.uuid4())[:8].upper()
    
    # AI pipeline
    category = categorize_request(payload.title, payload.description)
    inferred_type = infer_requester_type(payload.title, payload.description)
    requester_type = payload.requester_type or inferred_type

    priority = calculate_priority(category, payload.urgency_self_reported, requester_type, payload.description)
    role_matches = find_role_matches(category)

    suggested_role = payload.desired_role or ROLE_FOR_CATEGORY.get(category, "Community Manager")
    if suggested_role not in [r["role"] for r in role_matches]:
        # fallback to the most typical role for category, add if missing
        suggested_role = ROLE_FOR_CATEGORY.get(category, suggested_role)

    # assign role automatically from AI; no hard individual assign yet
    assigned_role = suggested_role

    members_for_assigned = [m for m in db_members.values() if m["role"].lower() == assigned_role.lower() and m["availability"]]

    email_data = generate_email_response({
        "id": request_id,
        "title": payload.title,
        "category": category,
        "priority": priority,
        "requester_name": payload.requester_name,
        "requester_email": payload.requester_email,
    })

    request_obj = {
        "id": request_id,
        "title": payload.title,
        "description": payload.description,
        "requester_name": payload.requester_name,
        "requester_email": payload.requester_email,
        "requester_type": requester_type,
        "company": payload.company,
        "tags": payload.tags,
        "category": category,
        "priority": priority,
        "status": RequestStatus.OPEN,
        "suggested_roles": role_matches,
        "suggested_role": suggested_role,
        "assigned_role": assigned_role,
        "assigned_to": None,
        "assigned_role_members": members_for_assigned,
        "internal_notes": None,
        "value_delivered": None,
        "value_description": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    
    db_requests[request_id] = request_obj

    # Background jobs
    background_tasks.add_task(sync_to_notion, request_obj)
    background_tasks.add_task(send_automated_email, email_data)

    return {
        "success": True,
        "request_id": request_id,
        "category": category,
        "category_label": CATEGORY_LABELS[category],
        "priority": priority,
        "suggested_role": suggested_role,
        "suggested_roles": request_obj["suggested_roles"],
        "assigned_role_members": request_obj["assigned_role_members"],
        "email_preview": email_data,
        "message": "Žiadosť bola prijatá. Potvrdzovací email bol odoslaný."
    }


@app.get("/requests", tags=["Requests"], summary="List all requests with filtering")
def list_requests(
    status: Optional[RequestStatus] = None,
    category: Optional[RequestCategory] = None,
    priority: Optional[PriorityLevel] = None,
    requester_type: Optional[RequesterType] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    items = list(db_requests.values())

    if status:
        items = [r for r in items if r["status"] == status]
    if category:
        items = [r for r in items if r["category"] == category]
    if priority:
        items = [r for r in items if r["priority"] == priority]
    if requester_type:
        items = [r for r in items if r["requester_type"] == requester_type]

    # Sort: URGENT first, then by created_at desc
    priority_order = {PriorityLevel.URGENT: 0, PriorityLevel.HIGH: 1, PriorityLevel.MEDIUM: 2, PriorityLevel.LOW: 3}
    items.sort(
        key=lambda r: (
            priority_order.get(r["priority"], 9),
            datetime.fromisoformat(r["created_at"] if isinstance(r["created_at"], str) else r["created_at"]),
        ),
        reverse=False
    )
    items = list(reversed(items))  # newest first among same priority

    total = len(items)
    start = (page - 1) * limit
    paginated = items[start:start + limit]

    return {"total": total, "page": page, "limit": limit, "items": paginated}


@app.get("/requests/{request_id}", tags=["Requests"], summary="Get request detail")
def get_request(request_id: str):
    r = db_requests.get(request_id.upper())
    if not r:
        raise HTTPException(status_code=404, detail="Request not found")
    return r


@app.patch("/requests/{request_id}", tags=["Requests"], summary="Update request status or assignment")
def update_request(request_id: str, payload: RequestUpdate):
    r = db_requests.get(request_id.upper())
    if not r:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if payload.status is not None:
        r["status"] = payload.status
    if payload.assigned_to is not None:
        r["assigned_to"] = payload.assigned_to
    if payload.assigned_role is not None:
        r["assigned_role"] = payload.assigned_role
    if payload.internal_notes is not None:
        r["internal_notes"] = payload.internal_notes
    if payload.value_delivered is not None:
        r["value_delivered"] = payload.value_delivered
    if payload.value_description is not None:
        r["value_description"] = payload.value_description

    r["updated_at"] = datetime.utcnow().isoformat()
    db_requests[request_id.upper()] = r
    return r


@app.delete("/requests/{request_id}", tags=["Requests"], summary="Delete a request")
def delete_request(request_id: str):
    if request_id.upper() not in db_requests:
        raise HTTPException(status_code=404, detail="Request not found")
    del db_requests[request_id.upper()]
    return {"success": True, "message": "Request deleted"}


# ── MATCHMAKING ───────────────────────────────

@app.get("/requests/{request_id}/matches", tags=["Matchmaking"])
def get_matches(request_id: str):
    r = db_requests.get(request_id.upper())
    if not r:
        raise HTTPException(status_code=404, detail="Request not found")
    member_matches = find_matches(r["category"], r["description"], limit=5)
    role_matches = find_role_matches(r["category"])
    return {
        "request_id": request_id,
        "category": r["category"],
        "suggested_roles": role_matches,
        "members": member_matches,
    }


@app.get("/roles", tags=["Matchmaking"], summary="List role-to-category routing map")
def list_roles():
    return {"total": len(db_roles), "roles": list(db_roles.values())}


@app.get("/roles/{role_name}/members", tags=["Matchmaking"], summary="Get members currently assigned to role")
def get_role_members(role_name: str):
    if role_name not in db_roles:
        raise HTTPException(status_code=404, detail="Role not found")
    members = [m for m in db_members.values() if m["role"].lower() == role_name.lower()]
    return {"role": role_name, "members": members, "count": len(members)}


@app.post("/roles/{role_name}/members", tags=["Matchmaking"], summary="Assign a member to role")
def add_role_member(role_name: str, payload: RoleAssignment):
    if role_name not in db_roles:
        raise HTTPException(status_code=404, detail="Role not found")
    if not payload.member_id:
        raise HTTPException(status_code=400, detail="member_id is required")

    member = db_members.get(payload.member_id.upper())
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    member["role"] = role_name
    db_members[member["id"]] = member
    return {"success": True, "role": role_name, "member": member}


@app.delete("/roles/{role_name}/members/{member_id}", tags=["Matchmaking"], summary="Remove a member from a role")
def remove_role_member(role_name: str, member_id: str):
    if role_name not in db_roles:
        raise HTTPException(status_code=404, detail="Role not found")
    member = db_members.get(member_id.upper())
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    if member["role"].lower() != role_name.lower():
        raise HTTPException(status_code=400, detail="Member is not assigned to this role")

    member["role"] = ""
    db_members[member["id"]] = member
    return {"success": True, "message": f"Member {member_id} removed from role {role_name}"}


@app.post("/roles", tags=["Matchmaking"], summary="Create a new role routing definition")
def create_role(payload: RoleConfig):
    normalized_role = payload.role.strip()
    if normalized_role in db_roles:
        raise HTTPException(status_code=400, detail="Role already exists")
    db_roles[normalized_role] = {
        "role": normalized_role,
        "categories": payload.categories,
        "description": payload.description or "",
    }
    return {"success": True, "role": db_roles[normalized_role]}


@app.patch("/roles/{role_name}", tags=["Matchmaking"], summary="Update a role mapping")
def update_role(role_name: str, payload: RoleUpdate):
    existing = db_roles.get(role_name)
    if not existing:
        raise HTTPException(status_code=404, detail="Role not found")
    if payload.categories is not None:
        existing["categories"] = payload.categories
    if payload.description is not None:
        existing["description"] = payload.description
    db_roles[role_name] = existing
    return {"success": True, "role": existing}


@app.delete("/roles/{role_name}", tags=["Matchmaking"], summary="Delete a role mapping")
def delete_role(role_name: str):
    if role_name not in db_roles:
        raise HTTPException(status_code=404, detail="Role not found")
    del db_roles[role_name]
    return {"success": True, "message": f"Role {role_name} removed."}


@app.post("/requests/{request_id}/assign-role", tags=["Matchmaking"], summary="Assign a request to a role (and optionally a specific member)")
def assign_role(request_id: str, payload: RoleAssignment):
    r = db_requests.get(request_id.upper())
    if not r:
        raise HTTPException(status_code=404, detail="Request not found")

    selected_role = payload.role.strip()
    r["assigned_role"] = selected_role

    if payload.member_id:
        member = db_members.get(payload.member_id.upper())
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        if member["role"].lower() != selected_role.lower():
            raise HTTPException(status_code=400, detail="Member role mismatch with assigned role")
        r["assigned_to"] = member["id"]
        r["status"] = RequestStatus.IN_PROGRESS
    else:
        # Find available member matching role
        candidate = next((m for m in db_members.values() if m["role"].lower() == selected_role.lower() and m["availability"]), None)
        if candidate:
            r["assigned_to"] = candidate["id"]
            r["status"] = RequestStatus.IN_PROGRESS
        else:
            r["assigned_to"] = None
            r["status"] = RequestStatus.OPEN

    r["updated_at"] = datetime.utcnow().isoformat()
    db_requests[request_id.upper()] = r
    return {"success": True, "request_id": request_id, "assigned_role": r["assigned_role"], "assigned_to": r.get("assigned_to"), "status": r["status"]}


@app.post("/requests/{request_id}/claim", tags=["Matchmaking"], summary="Claim the assigned role as a member and start progress")
def claim_assigned_role(request_id: str, payload: RoleAssignment):
    r = db_requests.get(request_id.upper())
    if not r:
        raise HTTPException(status_code=404, detail="Request not found")

    if not r.get("assigned_role"):
        raise HTTPException(status_code=400, detail="No role is assigned to this request yet")

    member = db_members.get(payload.member_id.upper()) if payload.member_id else None
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    if member["role"].lower() != r.get("assigned_role", "").lower():
        raise HTTPException(status_code=400, detail="Member role does not match the assigned role")

    if not member.get("availability", False):
        raise HTTPException(status_code=400, detail="Member is not available")

    r["assigned_to"] = member["id"]
    r["status"] = RequestStatus.IN_PROGRESS
    r["updated_at"] = datetime.utcnow().isoformat()
    db_requests[request_id.upper()] = r

    return {"success": True, "request_id": request_id, "assigned_role": r["assigned_role"], "assigned_to": r["assigned_to"], "status": r["status"]}


@app.post("/requests/{request_id}/match-feedback", tags=["Matchmaking"])
def submit_match_feedback(request_id: str, payload: MatchFeedback):
    if payload.request_id.upper() != request_id.upper():
        raise HTTPException(status_code=400, detail="Mismatched request ID")

    r = db_requests.get(request_id.upper())
    if not r:
        raise HTTPException(status_code=404, detail="Request not found")
    # In production: store feedback to improve matching algorithm
    if payload.accepted and payload.member_id in db_members:
        r["assigned_to"] = db_members[payload.member_id]["name"]
        r["status"] = RequestStatus.IN_PROGRESS
        r["updated_at"] = datetime.utcnow().isoformat()
    return {"success": True, "accepted": payload.accepted}


# ── MEMBERS ───────────────────────────────────

@app.get("/members", tags=["Members"])
def list_members(available_only: bool = False):
    members = list(db_members.values())
    if available_only:
        members = [m for m in members if m["availability"]]
    return {"total": len(members), "items": members}


@app.post("/members", tags=["Members"], summary="Add a community member")
def create_member(payload: MemberCreate):
    member_id = str(uuid.uuid4())[:8].upper()
    member = {"id": member_id, **payload.dict()}
    db_members[member_id] = member
    return {"success": True, "member": member}


@app.patch("/members/{member_id}", tags=["Members"], summary="Update community member")
def update_member(member_id: str, payload: MemberUpdate):
    existing = db_members.get(member_id.upper())
    if not existing:
        raise HTTPException(status_code=404, detail="Member not found")

    updated = existing.copy()
    update_data = payload.dict(exclude_unset=True)
    updated.update(update_data)

    db_members[member_id.upper()] = updated
    return {"success": True, "member": updated}


@app.delete("/members/{member_id}", tags=["Members"], summary="Delete community member")
def delete_member(member_id: str):
    if member_id.upper() not in db_members:
        raise HTTPException(status_code=404, detail="Member not found")
    del db_members[member_id.upper()]
    return {"success": True, "message": "Member deleted"}


# ── ANALYTICS / DASHBOARD ─────────────────────

@app.post("/groq", tags=["Integrations"], summary="Run GROQ query against Sanity-like API")
async def run_groq(query_payload: GroqQuery):
    if not GROQ_API_TOKEN or not GROQ_PROJECT_ID:
        raise HTTPException(status_code=400, detail="GROQ_API_TOKEN and GROQ_PROJECT_ID must be set in .env")

    if not query_payload.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # This is a sample implementation for Sanity-style GROQ.
    base_url = f"https://{GROQ_PROJECT_ID}.api.sanity.io/v2024-01-26/data/query/{GROQ_DATASET}"
    headers = {
        "Authorization": f"Bearer {GROQ_API_TOKEN}",
        "Accept": "application/json",
    }
    params = {"query": query_payload.query}
    if query_payload.params:
        for k, v in query_payload.params.items():
            params[f"${k}"] = v

    try:
        import httpx
    except ImportError:
        raise HTTPException(status_code=503, detail="httpx is required for GROQ endpoint; install httpx")

    async with httpx.AsyncClient() as client:
        resp = await client.get(base_url, headers=headers, params=params, timeout=15.0)

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=f"GROQ query failed: {resp.text}")

    return resp.json()


@app.post("/chat", tags=["Chat"], summary="Generates an AI chat response")
def chat_endpoint(payload: ChatRequest):
    last_user = next((m for m in reversed(payload.messages) if m.role == "user"), None)
    message = last_user.content if last_user else (payload.messages[-1].content if payload.messages else "")

    if GROQ_API_TOKEN and GROQ_PROJECT_ID:
        answer = groq_chat_response(message)
        return {"source": "groq", "answer": answer}

    # Fallback to local rule-based chat if GROQ is not configured
    return {"source": "local", "answer": local_chat_response(payload.messages)}


@app.get("/analytics", tags=["Analytics"], summary="Dashboard stats")
def get_analytics():
    all_requests = list(db_requests.values())
    
    by_status = {}
    for s in RequestStatus:
        by_status[s] = sum(1 for r in all_requests if r["status"] == s)
    
    by_category = {}
    for cat in RequestCategory:
        by_category[cat] = sum(1 for r in all_requests if r["category"] == cat)
    
    by_priority = {}
    for p in PriorityLevel:
        by_priority[p] = sum(1 for r in all_requests if r["priority"] == p)

    resolved = [r for r in all_requests if r["status"] == RequestStatus.RESOLVED]
    value_delivered_count = sum(1 for r in resolved if r.get("value_delivered"))

    return {
        "total_requests": len(all_requests),
        "by_status": by_status,
        "by_category": by_category,
        "by_priority": by_priority,
        "resolved_count": len(resolved),
        "value_delivered_count": value_delivered_count,
        "active_members": sum(1 for m in db_members.values() if m["availability"]),
    }


# ── NOTION WEBHOOK (for incoming Notion updates) ───

@app.post("/webhooks/notion", tags=["Integrations"])
async def notion_webhook(payload: dict):
    """
    Receive updates from Notion automations.
    Configure in Notion: Settings → Integrations → Webhooks
    Point to: POST /webhooks/notion
    """
    print(f"[Notion Webhook] Received: {json.dumps(payload)[:200]}")
    # Parse Notion property changes and update local DB
    return {"received": True}


# ── EMAIL INBOUND (for email-to-request) ──────

@app.post("/webhooks/email-inbound", tags=["Integrations"])
async def email_inbound(payload: dict, background_tasks: BackgroundTasks):
    """
    Process inbound emails and auto-create requests.
    
    Configure with SendGrid Inbound Parse or Mailgun Routes:
    - Webhook URL: POST /webhooks/email-inbound
    - Forward all emails to: requests@communityhub.sk
    
    Expected payload fields: from, subject, text, html
    """
    from_email = payload.get("from", "unknown@example.com")
    subject = payload.get("subject", "No subject")
    body = payload.get("text", payload.get("html", ""))
    
    # Auto-create request from email
    request_id = str(uuid.uuid4())[:8].upper()
    category = categorize_request(subject, body)
    
    request_obj = {
        "id": request_id,
        "title": f"[Email] {subject[:100]}",
        "description": body[:1000],
        "requester_name": from_email.split("@")[0],
        "requester_email": from_email,
        "requester_type": RequesterType.SERVICE_PROVIDER,
        "company": None,
        "tags": ["email-inbound"],
        "category": category,
        "priority": PriorityLevel.MEDIUM,
        "status": RequestStatus.OPEN,
        "suggested_matches": [],
        "assigned_to": None,
        "internal_notes": "Created from inbound email",
        "value_delivered": None,
        "value_description": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    
    db_requests[request_id] = request_obj
    background_tasks.add_task(sync_to_notion, request_obj)

    return {"success": True, "request_id": request_id, "category": category}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)