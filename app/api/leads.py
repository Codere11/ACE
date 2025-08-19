from fastapi import APIRouter
from app.models.lead import Lead
from app.services import lead_service

router = APIRouter()

@router.get("/", response_model=list[Lead])
def get_leads():
    return lead_service.get_all_leads()

@router.post("/", response_model=Lead)
def add_lead(lead: Lead):
    return lead_service.add_lead(lead)
