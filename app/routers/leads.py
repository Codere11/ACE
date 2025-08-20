from fastapi import APIRouter
from typing import List, Dict

router = APIRouter()

# Start with empty data – new ACE instance means no leads yet
leads_data: List[Dict] = []

@router.get("/leads")
def get_leads() -> List[Dict]:
    return leads_data

@router.get("/kpis")
def get_kpis() -> Dict:
    return {
        "visitors": 0,
        "interactions": 0,
        "contacts": 0,
        "avgResponseSec": 0,
        "activeLeads": 0
    }

@router.get("/funnel")
def get_funnel() -> Dict:
    return {
        "awareness": 0,
        "interest": 0,
        "meeting": 0,
        "close": 0
    }

@router.get("/objections")
def get_objections() -> List[str]:
    return []
