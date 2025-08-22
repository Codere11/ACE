import time
from typing import List
from collections import Counter
from app.models.lead import Lead

# In-memory lead store
_leads: List[Lead] = []


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
    existing = next((l for l in _leads if l.id == sid), None)
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
# Lead access
# -------------------
def get_all_leads() -> List[Lead]:
    """Return all leads sorted by score descending."""
    return sorted(_leads, key=lambda l: l.score, reverse=True)


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
