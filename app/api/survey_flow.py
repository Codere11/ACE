"""
Survey flow management API endpoints.
Allows managers to create/update survey flows that customers see.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

logger = logging.getLogger("ace.api.survey_flow")
router = APIRouter()

# Path to the flow file
FLOW_FILE = Path(__file__).parent.parent.parent / "data" / "conversation_flow.json"


@router.get("/api/survey/flow")
def get_survey_flow() -> Dict[str, Any]:
    """Get the current survey flow."""
    try:
        if FLOW_FILE.exists():
            with open(FLOW_FILE, "r", encoding="utf-8") as f:
                flow = json.load(f)
            logger.info("Survey flow loaded from file")
            return flow
        else:
            logger.warning("Survey flow file not found, returning default")
            return get_default_flow()
    except Exception as e:
        logger.exception("Error loading survey flow")
        raise HTTPException(status_code=500, detail=f"Failed to load survey: {e}")


@router.post("/api/survey/flow")
def save_survey_flow(flow: Dict[str, Any]) -> Dict[str, str]:
    """Save/update the survey flow."""
    try:
        # Ensure data directory exists
        FLOW_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to file
        with open(FLOW_FILE, "w", encoding="utf-8") as f:
            json.dump(flow, f, indent=2, ensure_ascii=False)
        
        logger.info("Survey flow saved successfully")
        return {"status": "success", "message": "Survey saved successfully"}
    
    except Exception as e:
        logger.exception("Error saving survey flow")
        raise HTTPException(status_code=500, detail=f"Failed to save survey: {e}")


def get_default_flow() -> Dict[str, Any]:
    """Return a default survey flow if none exists."""
    return {
        "version": "1.0.0",
        "start": "contact",
        "nodes": [
            {
                "id": "contact",
                "texts": ["Prosimo vnesite kontaktne podatke:"],
                "openInput": True,
                "inputType": "dual-contact",
                "next": "thank_you"
            },
            {
                "id": "thank_you",
                "texts": ["Hvala za izpolnitev! Kmalu se oglasimo."],
                "terminal": True
            }
        ]
    }
