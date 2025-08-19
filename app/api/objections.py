from fastapi import APIRouter
from app.services import lead_service

router = APIRouter()

@router.get("/")
def get_objections():
    return lead_service.get_objections()
