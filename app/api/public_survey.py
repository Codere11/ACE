# app/api/public_survey.py
"""
Public survey API endpoints.
These are accessible without authentication for customers to fill out surveys.
"""

import random
from typing import Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.orm import Survey, SurveyResponse as SurveyResponseModel
from app.models.schemas import SurveyResponseCreate, SurveyResponseUpdate, SurveyResponseDetail

from app.models.orm import Organization

router = APIRouter(prefix="/s", tags=["public-surveys"])


@router.get("/", include_in_schema=False)
def list_public_surveys(db: Session = Depends(get_db)):
    """
    List all live surveys (for dev/testing only).
    Returns basic info without the flow.
    Ordered by most recently published first.
    """
    surveys = db.query(Survey).join(Organization).filter(
        Survey.status == "live",
        Organization.active == True
    ).order_by(
        Survey.published_at.desc()
    ).all()
    
    return [
        {
            "id": s.id,
            "name": s.name,
            "slug": s.slug,
            "org_slug": s.organization.slug,
            "survey_type": s.survey_type,
            "published_at": s.published_at.isoformat() if s.published_at else None
        }
        for s in surveys
    ]


@router.get("/{org_slug}/{survey_slug}")
def get_survey_by_slug(
    org_slug: str,
    survey_slug: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get survey flow by organization slug and survey slug.
    Returns the survey flow JSON for the customer to fill out.
    """
    # Find organization by slug
    org = db.query(Organization).filter(
        Organization.slug == org_slug,
        Organization.active == True
    ).first()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Find survey by slug (must be live and belong to org)
    survey = db.query(Survey).filter(
        Survey.slug == survey_slug,
        Survey.organization_id == org.id,
        Survey.status == "live"
    ).first()
    
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found or not active")
    
    # For A/B tests, randomly assign variant
    if survey.survey_type == "ab_test":
        variant = random.choice(["a", "b"])
        flow = survey.variant_a_flow if variant == "a" else survey.variant_b_flow
        
        return {
            "survey_id": survey.id,
            "name": survey.name,
            "slug": survey.slug,
            "org_slug": org.slug,
            "survey_type": survey.survey_type,
            "variant": variant,
            "flow": flow
        }
    
    # Regular survey
    return {
        "survey_id": survey.id,
        "name": survey.name,
        "slug": survey.slug,
        "org_slug": org.slug,
        "survey_type": survey.survey_type,
        "variant": None,
        "flow": survey.flow_json
    }


@router.get("/{org_slug}/{survey_slug}/a")
def get_survey_variant_a(
    org_slug: str,
    survey_slug: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get A/B test variant A explicitly.
    """
    # Find organization
    org = db.query(Organization).filter(
        Organization.slug == org_slug,
        Organization.active == True
    ).first()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    survey = db.query(Survey).filter(
        Survey.slug == survey_slug,
        Survey.organization_id == org.id,
        Survey.status == "live",
        Survey.survey_type == "ab_test"
    ).first()
    
    if not survey:
        raise HTTPException(status_code=404, detail="A/B test survey not found or not active")
    
    if not survey.variant_a_flow:
        raise HTTPException(status_code=500, detail="Variant A not configured")
    
    return {
        "survey_id": survey.id,
        "name": survey.name,
        "slug": survey.slug,
        "org_slug": org.slug,
        "survey_type": survey.survey_type,
        "variant": "a",
        "flow": survey.variant_a_flow
    }


@router.get("/{org_slug}/{survey_slug}/b")
def get_survey_variant_b(
    org_slug: str,
    survey_slug: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get A/B test variant B explicitly.
    """
    # Find organization
    org = db.query(Organization).filter(
        Organization.slug == org_slug,
        Organization.active == True
    ).first()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    survey = db.query(Survey).filter(
        Survey.slug == survey_slug,
        Survey.organization_id == org.id,
        Survey.status == "live",
        Survey.survey_type == "ab_test"
    ).first()
    
    if not survey:
        raise HTTPException(status_code=404, detail="A/B test survey not found or not active")
    
    if not survey.variant_b_flow:
        raise HTTPException(status_code=500, detail="Variant B not configured")
    
    return {
        "survey_id": survey.id,
        "name": survey.name,
        "slug": survey.slug,
        "org_slug": org.slug,
        "survey_type": survey.survey_type,
        "variant": "b",
        "flow": survey.variant_b_flow
    }


@router.post("/{org_slug}/{survey_slug}/submit", response_model=SurveyResponseDetail, status_code=201)
def submit_survey_response(
    org_slug: str,
    survey_slug: str,
    payload: SurveyResponseCreate,
    db: Session = Depends(get_db)
):
    """
    Submit a survey response.
    Creates a new response or updates existing one based on SID.
    """
    # Find organization
    org = db.query(Organization).filter(
        Organization.slug == org_slug,
        Organization.active == True
    ).first()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Find survey by slug
    survey = db.query(Survey).filter(
        Survey.slug == survey_slug,
        Survey.organization_id == org.id,
        Survey.status == "live"
    ).first()
    
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found or not active")
    
    # Verify survey_id matches
    if payload.survey_id != survey.id:
        raise HTTPException(
            status_code=400,
            detail="Survey ID mismatch"
        )
    
    # Check if response already exists for this SID
    existing_response = db.query(SurveyResponseModel).filter(
        SurveyResponseModel.survey_id == survey.id,
        SurveyResponseModel.sid == payload.sid
    ).first()
    
    if existing_response:
        # Update existing response
        if payload.survey_answers:
            existing_response.survey_answers = payload.survey_answers
        if payload.name:
            existing_response.name = payload.name
        if payload.email:
            existing_response.email = payload.email
        if payload.phone:
            existing_response.phone = payload.phone
        
        # Calculate score based on answers
        score = calculate_survey_score(payload.survey_answers)
        existing_response.score = score
        existing_response.interest = calculate_interest_level(score)
        
        # Update progress
        total_questions = count_survey_questions(survey)
        answered_questions = len(payload.survey_answers)
        existing_response.survey_progress = int((answered_questions / total_questions) * 100) if total_questions > 0 else 0
        
        db.commit()
        db.refresh(existing_response)
        
        return existing_response
    
    # Create new response
    score = calculate_survey_score(payload.survey_answers)
    interest = calculate_interest_level(score)
    
    total_questions = count_survey_questions(survey)
    answered_questions = len(payload.survey_answers)
    progress = int((answered_questions / total_questions) * 100) if total_questions > 0 else 0
    
    response = SurveyResponseModel(
        survey_id=survey.id,
        organization_id=survey.organization_id,
        sid=payload.sid,
        variant=payload.variant,
        survey_answers=payload.survey_answers,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        score=score,
        interest=interest,
        survey_started_at=datetime.utcnow(),
        survey_progress=progress
    )
    
    db.add(response)
    db.commit()
    db.refresh(response)
    
    return response


@router.post("/{survey_slug}/complete", response_model=SurveyResponseDetail)
def complete_survey(
    survey_slug: str,
    sid: str,
    db: Session = Depends(get_db)
):
    """
    Mark a survey as completed.
    """
    # Find survey
    survey = db.query(Survey).filter(
        Survey.slug == survey_slug,
        Survey.status == "live"
    ).first()
    
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found or not active")
    
    # Find response
    response = db.query(SurveyResponseModel).filter(
        SurveyResponseModel.survey_id == survey.id,
        SurveyResponseModel.sid == sid
    ).first()
    
    if not response:
        raise HTTPException(status_code=404, detail="Survey response not found")
    
    # Mark as completed
    response.survey_completed_at = datetime.utcnow()
    response.survey_progress = 100
    
    db.commit()
    db.refresh(response)
    
    return response


# Helper functions

def calculate_survey_score(answers: Dict[str, Any]) -> int:
    """
    Calculate score from survey answers.
    Looks for numeric values or scores in answer data.
    """
    if not answers:
        return 0
    
    total_score = 0
    answer_count = 0
    
    for node_id, answer_data in answers.items():
        # If answer has a 'score' field
        if isinstance(answer_data, dict) and 'score' in answer_data:
            total_score += answer_data['score']
            answer_count += 1
        # If answer is directly a number
        elif isinstance(answer_data, (int, float)):
            total_score += answer_data
            answer_count += 1
    
    # Return average score normalized to 0-100
    if answer_count > 0:
        avg = total_score / answer_count
        # Assuming scores are -100 to +100, normalize to 0-100
        return max(0, min(100, int((avg + 100) / 2)))
    
    return 0


def calculate_interest_level(score: int) -> str:
    """Calculate interest level based on score"""
    if score >= 70:
        return "High"
    elif score >= 40:
        return "Medium"
    else:
        return "Low"


def count_survey_questions(survey: Survey) -> int:
    """Count number of questions in a survey flow"""
    if survey.survey_type == "regular" and survey.flow_json:
        flow = survey.flow_json
    elif survey.survey_type == "ab_test":
        # Use variant A for counting (both should have same number)
        flow = survey.variant_a_flow
    else:
        return 0
    
    if not flow or not isinstance(flow, dict):
        return 0
    
    # Count nodes (questions)
    nodes = flow.get("nodes", [])
    if isinstance(nodes, list):
        return len(nodes)
    elif isinstance(nodes, dict):
        return len(nodes)
    
    return 0
