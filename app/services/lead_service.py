import time
from typing import List, Optional
from collections import Counter
from app.models.lead import Lead

# In-memory lead store
_leads: List[Lead] = []


def _now() -> int:
    return int(time.time())


def _find(sid: Optional[str]) -> Optional[Lead]:
    if not sid:
        return None
    return next((l for l in _leads if l.id == sid), None)


def _ensure(sid: str) -> Lead:
    lead = _find(sid)
    if lead:
        return lead
    lead = Lead(
        id=sid,
        name="Unknown",
        industry="Unknown",
        score=50,
        stage="Pogovori",
        compatibility=True,
        interest="Medium",
        phone=False,
        email=False,
        adsExp=False,
        lastMessage="",
        lastSeenSec=_now(),
        notes=""
    )
    _leads.append(lead)
    return lead


# -------------------
# Lead ingestion
# -------------------
def ingest_from_deepseek(user_message: str, classification: dict, sid: str = None):
    """
    Create a new lead entry from DeepSeek classification.
    If sid is passed, link it as id.
    """
    score = 90 if classification["category"] == "good_fit" else \
            70 if classification["category"] == "could_fit" else 40

    stage = "Interested" if classification["category"] == "good_fit" else \
            "Discovery" if classification["category"] == "could_fit" else "Cold"

    interest = "High" if classification["category"] == "good_fit" else \
               "Medium" if classification["category"] == "could_fit" else "Low"

    # prevent duplicates
    existing = _find(sid) if sid else None
    if existing:
        return existing

    lead = Lead(
        id=sid or f"lead_{int(time.time())}",
        name="Unknown",
        industry="Unknown",
        score=score,
        stage=stage,
        compatibility=(classification["category"] != "bad_fit"),
        interest=interest,
        phone=False,
        email=False,
        adsExp=False,
        phoneText="",          # NEW
        emailText="",          # NEW
        lastMessage=user_message,
        lastSeenSec=int(time.time()),
        notes=classification.get("reasons", "")
    )
    _leads.append(lead)
    return lead


def add_lead(lead: Lead):
    """Append a lead to the global store if not already present."""
    if not any(l.id == lead.id for l in _leads):
        _leads.append(lead)
    return lead


# -------------------
# Contact upsert (NEW)
# -------------------
def upsert_contact(sid: str, *, name: str = "", email: str = "", phone: str = "", channel: str = "email") -> Lead:
    """
    Store phone/email strings and set legacy flags for compatibility.
    Also bumps stage/score minimally.
    """
    lead = _ensure(sid)
    if name and (not lead.name or lead.name == "Unknown"):
        lead.name = name

    if email:
        lead.emailText = email.strip()
        lead.email = True
    if phone:
        lead.phoneText = phone.strip()
        lead.phone = True

    # Simple promotion if contact present
    if lead.email or lead.phone:
        lead.stage = "Interested" if lead.stage in ("Awareness", "Cold", "Discovery") else lead.stage
        if lead.score < 50:
            lead.score = 50

    lead.lastSeenSec = _now()
    return lead


# -------------------
# Lead access
# -------------------
def get_all_leads() -> List[Lead]:
    """Return all leads sorted by score descending."""
    return sorted(_leads, key=lambda l: l.score, reverse=True)


def delete_lead(sid: str) -> bool:
    """Delete a lead by ID. Returns True if deleted, False if not found."""
    global _leads
    initial_count = len(_leads)
    _leads = [l for l in _leads if l.id != sid]
    return len(_leads) < initial_count


# -------------------
# KPI calculations
# -------------------
def get_kpis():
    total = len(_leads)
    contacts = sum(1 for l in _leads if l.phone or l.email)
    interactions = sum(1 for l in _leads if l.lastMessage)
    active_leads = sum(1 for l in _leads if l.stage in ["Interested", "Discovery", "Pogovori"])

    # avg response simulated as fixed for now
    avg_response = 30 if total == 0 else 25

    return {
        "visitors": total,
        "interactions": interactions,
        "contacts": contacts,
        "avgResponseSec": avg_response,
        "activeLeads": active_leads,
    }


# -------------------
# Funnel analysis
# -------------------
def get_funnel():
    """
    Simple funnel stats: counts by stage.
    Awareness: all leads
    Interest: stage=Interested
    Meeting: leads with high score
    Close: leads with notes containing 'close' or 'deal'
    """
    total = len(_leads) or 1

    awareness = 100
    interest = int(100 * sum(1 for l in _leads if l.stage == "Interested") / total)
    meeting = int(100 * sum(1 for l in _leads if l.score >= 85) / total)
    close = int(100 * sum(1 for l in _leads if "close" in l.notes.lower() or "deal" in l.notes.lower()) / total)

    return {
        "awareness": awareness,
        "interest": interest,
        "meeting": meeting,
        "close": close
    }


# -------------------
# Objection analysis
# -------------------
def get_objections():
    """
    Collect objections from lead notes.
    Returns top 5 most common reasons.
    """
    texts = [l.notes.lower() for l in _leads if l.notes]
    words = []

    for t in texts:
        if "price" in t:
            words.append("💸 Price too high")
        if "partner" in t or "approval" in t:
            words.append("👥 Need partner approval")
        if "agency" in t:
            words.append("🏢 Already working with agency")
        if "time" in t or "timing" in t:
            words.append("⏳ Timing not right")

    counts = Counter(words)
    ranked = [f"{k} ({v})" for k, v in counts.most_common(5)]
    return ranked


# -------------------
# Survey tracking (NEW)
# -------------------
def start_survey(sid: str) -> Lead:
    """
    Mark survey as started for this lead.
    """
    from datetime import datetime
    lead = _ensure(sid)
    if not lead.survey_started_at:
        lead.survey_started_at = datetime.utcnow().isoformat()
    lead.lastSeenSec = _now()
    return lead


def update_survey_answer(sid: str, node_id: str, answer: any) -> Lead:
    """
    Store a single survey answer for a lead.
    """
    lead = _ensure(sid)
    if not lead.survey_answers:
        lead.survey_answers = {}
    lead.survey_answers[node_id] = answer
    lead.lastSeenSec = _now()
    return lead


def update_survey_progress(sid: str, progress: int, answers: dict = None) -> Lead:
    """
    Update survey completion percentage and optionally merge answers.
    """
    from datetime import datetime
    lead = _ensure(sid)
    
    if not lead.survey_started_at:
        lead.survey_started_at = datetime.utcnow().isoformat()
    
    lead.survey_progress = max(0, min(100, progress))
    
    if answers:
        if not lead.survey_answers:
            lead.survey_answers = {}
        lead.survey_answers.update(answers)
    
    if progress >= 100 and not lead.survey_completed_at:
        lead.survey_completed_at = datetime.utcnow().isoformat()
        lead.stage = "Qualified" if lead.stage in ("Awareness", "Cold", "Discovery") else lead.stage
        if lead.score < 60:
            lead.score = 60
    
    lead.lastSeenSec = _now()
    return lead


def get_survey_answers(sid: str) -> dict:
    """
    Retrieve survey answers for a lead.
    """
    lead = _find(sid)
    return lead.survey_answers if lead and lead.survey_answers else {}
