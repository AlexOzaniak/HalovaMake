import os
import json
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from enum import Enum

from groq import Groq
from dotenv import load_dotenv
from prompts import MATCHMAKING_SYSTEM_PROMPT, PARSE_REQUEST_SYSTEM_PROMPT

# -------------------------
# LOAD ENV
# -------------------------
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=api_key) if api_key else None

# -------------------------
# APP
# -------------------------
app = FastAPI(
    title="Startup Community Request API",
    description="API pre zadávanie žiadostí v startup komunite s AI matchmakingom (Groq)",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# ENUMS
# -------------------------
class UserType(str, Enum):
    startup = "startup"
    investor = "investor"
    service_provider = "service_provider"
    community_member = "community_member"

class RequestCategory(str, Enum):
    hladanie_zamestnanca = "hladanie_zamestnanca"
    hladanie_investora = "hladanie_investora"
    speaking_na_evente = "speaking_na_evente"
    zdielanie_marketingu = "zdielanie_marketingu"
    podpora_sales = "podpora_sales"
    hladanie_klientov = "hladanie_klientov"
    ine = "ine"

class RequestStatus(str, Enum):
    nova = "nova"
    v_rieseni = "v_rieseni"
    vyriesena = "vyriesena"
    zamietnuta = "zamietnuta"

# -------------------------
# MODELS
# -------------------------
class ChatInput(BaseModel):
    text: str = Field(..., min_length=5, max_length=2000, example="Hľadám investora pre náš fintech startup zameraný na AI.")

class RequestCreate(BaseModel):
    meno: str = Field(..., min_length=2, max_length=100, example="Ján Novák")
    email: str = Field(..., example="jan.novak@startup.sk")
    typ_pouzivatela: UserType
    nazov_organizacie: Optional[str] = Field(None, max_length=200, example="TechStartup s.r.o.")
    kategoria: RequestCategory
    nadpis: str = Field(..., min_length=5, max_length=200, example="Hľadám senior fullstack developera")
    popis: str = Field(..., min_length=20, max_length=2000, example="Naša startup hľadá skúseného fullstack developera s React a Node.js.")
    relevantne_informacie: Optional[str] = Field(None, max_length=1000, example="React, Node.js, 3+ roky skúseností")
    lokalita: Optional[str] = Field(None, max_length=100, example="Bratislava / Remote")
    budget: Optional[str] = Field(None, max_length=100, example="3000-4500 EUR/mesiac")
    urgentne: bool = Field(default=False)

class AIMatch(BaseModel):
    role: str
    swipe: int
    reason: str

class AIAnalysis(BaseModel):
    status: str
    category: Optional[str] = None
    intent: Optional[str] = None
    confidence: Optional[float] = None
    user_role: Optional[str] = None
    domain: Optional[str] = None
    worth_it : Optional[int] = None
    matches: Optional[List[AIMatch]] = None
    raw: Optional[str] = None

class RequestResponse(BaseModel):
    id: str
    meno: str
    email: str
    typ_pouzivatela: UserType
    nazov_organizacie: Optional[str]
    kategoria: RequestCategory
    nadpis: str
    popis: str
    relevantne_informacie: Optional[str]
    lokalita: Optional[str]
    budget: Optional[str]
    urgentne: bool
    status: RequestStatus
    vytvorene: datetime
    aktualizovane: datetime
    ai_analyza: Optional[AIAnalysis] = None

class StatusUpdate(BaseModel):
    status: RequestStatus
    poznamka: Optional[str] = None

# -------------------------
# IN-MEMORY DB
# -------------------------
requests_db: dict[str, dict] = {}

# -------------------------
# HELPERS
# -------------------------
def call_groq(system_prompt: str, user_text: str) -> str:
    """Zavolá Groq a vráti raw string odpoveď. Vyhodí výnimku ak zlyhá."""
    resp = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ],
        temperature=0.2,
        max_tokens=800
    )
    raw = resp.choices[0].message.content.strip()
    # Odstráň prípadné markdown backticks
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()


def parse_json_safe(raw: str) -> Optional[dict]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def parse_chat_to_request(text: str) -> RequestCreate:
    """
    Použije Groq na parsovanie voľného textu do štruktúrovaného RequestCreate.
    Ak Groq nie je dostupný alebo zlyhá, vráti fallback s rozumnými defaultmi.
    """
    if not groq_client:
        return RequestCreate(
            meno="Neznámy",
            email="neznamy@example.sk",
            typ_pouzivatela=UserType.startup,
            kategoria=RequestCategory.ine,
            nadpis=text[:100],
            popis=text if len(text) >= 20 else text + " (doplňte popis)",
        )

    try:
        raw = call_groq(PARSE_REQUEST_SYSTEM_PROMPT, text)
        data = parse_json_safe(raw)
        if data:
            return RequestCreate(**data)
    except Exception:
        pass

    # Fallback
    return RequestCreate(
        meno="Neznámy",
        email="neznamy@example.sk",
        typ_pouzivatela=UserType.startup,
        kategoria=RequestCategory.ine,
        nadpis=text[:100],
        popis=text if len(text) >= 20 else text + " (doplňte popis)",
    )


def run_groq_analysis(request: RequestCreate) -> Optional[AIAnalysis]:
    """Spustí AI matchmaking analýzu pre danú žiadosť."""
    if not groq_client:
        return None

    user_text = f"""
Meno: {request.meno}
Typ používateľa: {request.typ_pouzivatela}
Organizácia: {request.nazov_organizacie or 'N/A'}
Kategória: {request.kategoria}
Nadpis: {request.nadpis}
Popis: {request.popis}
Relevantné info: {request.relevantne_informacie or 'N/A'}
Lokalita: {request.lokalita or 'N/A'}
Budget: {request.budget or 'N/A'}
Urgentné: {request.urgentne}
""".strip()

    try:
        raw = call_groq(MATCHMAKING_SYSTEM_PROMPT, user_text)
        data = parse_json_safe(raw)
        if data:
            matches = [AIMatch(**m) for m in data.get("matches", [])]
            return AIAnalysis(
                status=data.get("status", "ok"),
                category=data.get("category"),
                intent=data.get("intent"),
                confidence=data.get("confidence"),
                user_role=data.get("user_role"),
                domain=data.get("domain"),
                matches=matches
            )
        return AIAnalysis(status="parse_error", raw=raw)
    except Exception as e:
        return AIAnalysis(status="error", raw=str(e))


def get_request_or_404(request_id: str) -> dict:
    if request_id not in requests_db:
        raise HTTPException(status_code=404, detail=f"Žiadosť '{request_id}' nebola nájdená")
    return requests_db[request_id]

# -------------------------
# ROUTES
# -------------------------
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root():
    groq_status = "✅ Groq AI aktívny" if groq_client else "⚠️ Groq AI neaktívny – nastav GROQ_API_KEY v .env"
    return f"""
    <html><body style="font-family:sans-serif;padding:2rem;background:#0f0f0f;color:#fff">
    <h1>🚀 Startup Community Request API v2</h1>
    <p>{groq_status}</p>
    <p>Dokumentácia: <a href="/docs" style="color:#6ee7b7">/docs</a></p>
    </body></html>
    """


@app.post("/ziadosti", response_model=RequestResponse, status_code=201, tags=["Žiadosti"])
def vytvorit_ziadost(data: ChatInput):
    """
    Prijme voľný text, Groq ho parsuje do štruktúry a spustí AI matchmaking.
    """
    # 1. Voľný text → štruktúrovaná žiadosť
    parsed_request = parse_chat_to_request(data.text)

    # 2. AI matchmaking
    ai_analyza = run_groq_analysis(parsed_request)

    # 3. Ulož
    now = datetime.utcnow()
    rid = str(uuid.uuid4())
    record = {
        "id": rid,
        **parsed_request.model_dump(),
        "status": RequestStatus.nova,
        "vytvorene": now,
        "aktualizovane": now,
        "ai_analyza": ai_analyza.model_dump() if ai_analyza else None,
    }
    requests_db[rid] = record
    return record


@app.get("/ziadosti", response_model=List[RequestResponse], tags=["Žiadosti"])
def zoznam_ziadosti(
    kategoria: Optional[RequestCategory] = Query(None, description="Filter podľa kategórie"),
    typ_pouzivatela: Optional[UserType] = Query(None, description="Filter podľa typu používateľa"),
    status: Optional[RequestStatus] = Query(None, description="Filter podľa stavu"),
    urgentne: Optional[bool] = Query(None, description="Iba urgentné"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Vráti zoznam žiadostí s voliteľným filtrovaním."""
    items = list(requests_db.values())
    if kategoria:
        items = [i for i in items if i["kategoria"] == kategoria]
    if typ_pouzivatela:
        items = [i for i in items if i["typ_pouzivatela"] == typ_pouzivatela]
    if status:
        items = [i for i in items if i["status"] == status]
    if urgentne is not None:
        items = [i for i in items if i["urgentne"] == urgentne]
    items.sort(key=lambda x: x["vytvorene"], reverse=True)
    return items[offset: offset + limit]


@app.get("/ziadosti/{request_id}", response_model=RequestResponse, tags=["Žiadosti"])
def detail_ziadosti(request_id: str):
    """Detail žiadosti vrátane AI analýzy."""
    return get_request_or_404(request_id)


@app.post("/ziadosti/{request_id}/ai-analyza", response_model=AIAnalysis, tags=["AI"])
def rerun_ai_analyza(request_id: str):
    """Znovu spustí AI matchmaking pre existujúcu žiadosť."""
    if not groq_client:
        raise HTTPException(
            status_code=503,
            detail="Groq AI nie je nakonfigurovaný. Nastav GROQ_API_KEY v .env súbore."
        )
    record = get_request_or_404(request_id)
    request_data = RequestCreate(**{k: v for k, v in record.items() if k in RequestCreate.model_fields})
    analyza = run_groq_analysis(request_data)
    record["ai_analyza"] = analyza.model_dump() if analyza else None
    record["aktualizovane"] = datetime.utcnow()
    return analyza


@app.patch("/ziadosti/{request_id}/status", response_model=RequestResponse, tags=["Žiadosti"])
def aktualizovat_status(request_id: str, update: StatusUpdate):
    """Zmení stav žiadosti."""
    record = get_request_or_404(request_id)
    record["status"] = update.status
    record["aktualizovane"] = datetime.utcnow()
    if update.poznamka:
        record["poznamka"] = update.poznamka
    return record


@app.delete("/ziadosti/{request_id}", status_code=204, tags=["Žiadosti"])
def zmazat_ziadost(request_id: str):
    """Zmaže žiadosť."""
    get_request_or_404(request_id)
    del requests_db[request_id]


@app.get("/ai/status", tags=["AI"])
def ai_status():
    """Stav Groq AI integrácie."""
    return {
        "groq_aktivny": groq_client is not None,
        "model": "llama-3.1-8b-instant",
        "info": "Nastav GROQ_API_KEY v .env pre aktiváciu." if not groq_client else "AI matchmaking je aktívny."
    }


@app.get("/statistiky", tags=["Štatistiky"])
def statistiky():
    """Prehľad štatistík."""
    items = list(requests_db.values())
    return {
        "celkom_ziadosti": len(items),
        "urgentne": sum(1 for i in items if i["urgentne"]),
        "s_ai_analyzou": sum(1 for i in items if i.get("ai_analyza")),
        "podla_kategorie": {cat.value: sum(1 for i in items if i["kategoria"] == cat) for cat in RequestCategory},
        "podla_statusu": {s.value: sum(1 for i in items if i["status"] == s) for s in RequestStatus},
        "podla_typu_pouzivatela": {ut.value: sum(1 for i in items if i["typ_pouzivatela"] == ut) for ut in UserType},
    }


@app.get("/kategorie", tags=["Pomocné"])
def zoznam_kategorii():
    """Zoznam kategórií žiadostí."""
    return [{"hodnota": k, "popis": v} for k, v in {
        "hladanie_zamestnanca": "Hľadanie zamestnanca",
        "hladanie_investora": "Hľadanie investora",
        "speaking_na_evente": "Možnosť speakovať na evente",
        "zdielanie_marketingu": "Zdieľanie marketingových podkladov",
        "podpora_sales": "Podpora v oblasti sales",
        "hladanie_klientov": "Hľadanie klientov",
        "ine": "Iné",
    }.items()]