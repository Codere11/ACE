# app/api/surveys.py
"""
Survey management API endpoints.
Supports regular surveys and A/B testing.
"""

from typing import List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, Float

from app.core.db import get_db
from app.models.orm import Survey, SurveyResponse
from app.models.schemas import (
    SurveyCreate,
    SurveyUpdate,
    SurveyResponse as SurveyResponseSchema,
    SurveyStats,
    SurveyResponseDetail
)
from app.auth.permissions import AuthContext, require_org_admin, require_org_user

router = APIRouter(prefix="/api/organizations/{org_id}/surveys", tags=["surveys"])


@router.get("", response_model=List[SurveyResponseSchema])
def list_surveys(
    org_id: int,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
    auth: AuthContext = Depends(require_org_user),
    db: Session = Depends(get_db)
):
    """
    List all surveys in an organization.
    Accessible by any authenticated user in the organization.
    
    Filters:
    - status: draft, live, archived
    """
    # Verify user belongs to the organization
    if auth.organization_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="You can only access surveys in your own organization"
        )
    
    query = db.query(Survey).filter(Survey.organization_id == org_id)
    
    if status:
        if status not in ["draft", "live", "archived"]:
            raise HTTPException(status_code=400, detail="Invalid status filter")
        query = query.filter(Survey.status == status)
    
    surveys = query.offset(skip).limit(limit).all()
    
    return surveys


@router.post("", response_model=SurveyResponseSchema, status_code=201)
def create_survey(
    org_id: int,
    payload: SurveyCreate,
    auth: AuthContext = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new survey.
    Only accessible by org admins.
    """
    # Verify user belongs to the organization
    if auth.organization_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="You can only create surveys in your own organization"
        )
    
    # Verify organization_id matches
    if payload.organization_id != org_id:
        raise HTTPException(
            status_code=400,
            detail="Organization ID in payload must match URL"
        )
    
    # Check if slug already exists in this organization
    existing = db.query(Survey).filter(
        Survey.organization_id == org_id,
        Survey.slug == payload.slug
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Survey with slug '{payload.slug}' already exists in this organization"
        )
    
    # Validate A/B test has both variants
    if payload.survey_type == "ab_test":
        if not payload.variant_a_flow or not payload.variant_b_flow:
            raise HTTPException(
                status_code=400,
                detail="A/B test surveys must have both variant_a_flow and variant_b_flow"
            )
    
    # Create survey
    survey = Survey(
        organization_id=org_id,
        name=payload.name,
        slug=payload.slug,
        survey_type=payload.survey_type,
        status=payload.status,
        flow_json=payload.flow_json,
        variant_a_flow=payload.variant_a_flow,
        variant_b_flow=payload.variant_b_flow
    )
    
    db.add(survey)
    db.commit()
    db.refresh(survey)
    
    return survey


@router.get("/{survey_id}", response_model=SurveyResponseSchema)
def get_survey(
    org_id: int,
    survey_id: int,
    auth: AuthContext = Depends(require_org_user),
    db: Session = Depends(get_db)
):
    """Get survey details"""
    # Verify user belongs to the organization
    if auth.organization_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="You can only access surveys in your own organization"
        )
    
    survey = db.query(Survey).filter(
        Survey.id == survey_id,
        Survey.organization_id == org_id
    ).first()
    
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    return survey


@router.put("/{survey_id}", response_model=SurveyResponseSchema)
def update_survey(
    org_id: int,
    survey_id: int,
    payload: SurveyUpdate,
    auth: AuthContext = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Update survey details.
    Only accessible by org admins.
    """
    # Verify user belongs to the organization
    if auth.organization_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="You can only update surveys in your own organization"
        )
    
    survey = db.query(Survey).filter(
        Survey.id == survey_id,
        Survey.organization_id == org_id
    ).first()
    
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    # Prevent editing live surveys (must archive first)
    if survey.status == "live" and payload.flow_json:
        raise HTTPException(
            status_code=400,
            detail="Cannot edit flow of a live survey. Archive it first."
        )
    
    # Update fields
    if payload.name is not None:
        survey.name = payload.name
    
    if payload.slug is not None:
        # Check slug uniqueness
        existing = db.query(Survey).filter(
            Survey.organization_id == org_id,
            Survey.slug == payload.slug,
            Survey.id != survey_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Survey with slug '{payload.slug}' already exists"
            )
        survey.slug = payload.slug
    
    if payload.survey_type is not None:
        survey.survey_type = payload.survey_type
    
    if payload.status is not None:
        survey.status = payload.status
        # Set published_at when status changes to live
        if payload.status == "live" and not survey.published_at:
            survey.published_at = datetime.utcnow()
    
    if payload.flow_json is not None:
        survey.flow_json = payload.flow_json
    
    if payload.variant_a_flow is not None:
        survey.variant_a_flow = payload.variant_a_flow
    
    if payload.variant_b_flow is not None:
        survey.variant_b_flow = payload.variant_b_flow
    
    db.commit()
    db.refresh(survey)
    
    return survey


@router.post("/{survey_id}/publish", response_model=SurveyResponseSchema)
def publish_survey(
    org_id: int,
    survey_id: int,
    auth: AuthContext = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Publish a survey (change status from draft to live).
    Only accessible by org admins.
    """
    # Verify user belongs to the organization
    if auth.organization_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="You can only publish surveys in your own organization"
        )
    
    survey = db.query(Survey).filter(
        Survey.id == survey_id,
        Survey.organization_id == org_id
    ).first()
    
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    if survey.status == "live":
        raise HTTPException(status_code=400, detail="Survey is already live")
    
    # Validate survey has content
    if survey.survey_type == "regular" and not survey.flow_json:
        raise HTTPException(
            status_code=400,
            detail="Cannot publish survey without flow_json"
        )
    
    if survey.survey_type == "ab_test":
        if not survey.variant_a_flow or not survey.variant_b_flow:
            raise HTTPException(
                status_code=400,
                detail="Cannot publish A/B test without both variants"
            )
    
    survey.status = "live"
    survey.published_at = datetime.utcnow()
    
    db.commit()
    db.refresh(survey)
    
    return survey


@router.post("/{survey_id}/archive", response_model=SurveyResponseSchema)
def archive_survey(
    org_id: int,
    survey_id: int,
    auth: AuthContext = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Archive a survey (change status to archived).
    Only accessible by org admins.
    """
    # Verify user belongs to the organization
    if auth.organization_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="You can only archive surveys in your own organization"
        )
    
    survey = db.query(Survey).filter(
        Survey.id == survey_id,
        Survey.organization_id == org_id
    ).first()
    
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    survey.status = "archived"
    
    db.commit()
    db.refresh(survey)
    
    return survey


@router.get("/{survey_id}/stats", response_model=SurveyStats)
def get_survey_stats(
    org_id: int,
    survey_id: int,
    auth: AuthContext = Depends(require_org_user),
    db: Session = Depends(get_db)
):
    """
    Get statistics for a survey.
    Includes A/B test comparison if applicable.
    """
    # Verify user belongs to the organization
    if auth.organization_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="You can only access surveys in your own organization"
        )
    
    survey = db.query(Survey).filter(
        Survey.id == survey_id,
        Survey.organization_id == org_id
    ).first()
    
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    # Get total responses
    total_responses = db.query(func.count(SurveyResponse.id)).filter(
        SurveyResponse.survey_id == survey_id
    ).scalar() or 0
    
    # Get completed responses
    completed_responses = db.query(func.count(SurveyResponse.id)).filter(
        SurveyResponse.survey_id == survey_id,
        SurveyResponse.survey_completed_at.isnot(None)
    ).scalar() or 0
    
    # Get average score
    avg_score = db.query(func.avg(SurveyResponse.score)).filter(
        SurveyResponse.survey_id == survey_id,
        SurveyResponse.survey_completed_at.isnot(None)
    ).scalar() or 0.0
    
    # Get average completion time
    avg_time_result = db.query(
        func.avg(
            func.cast(
                func.julianday(SurveyResponse.survey_completed_at) -
                func.julianday(SurveyResponse.survey_started_at),
                Float
            ) * 24 * 60
        )
    ).filter(
        SurveyResponse.survey_id == survey_id,
        SurveyResponse.survey_completed_at.isnot(None)
    ).scalar()
    
    avg_completion_time = float(avg_time_result) if avg_time_result else None
    
    stats = SurveyStats(
        survey_id=survey_id,
        total_responses=total_responses,
        completed_responses=completed_responses,
        avg_score=float(avg_score),
        avg_completion_time_minutes=avg_completion_time
    )
    
    # A/B test specific stats
    if survey.survey_type == "ab_test":
        # Variant A stats
        variant_a_count = db.query(func.count(SurveyResponse.id)).filter(
            SurveyResponse.survey_id == survey_id,
            SurveyResponse.variant == "a"
        ).scalar() or 0
        
        variant_a_avg = db.query(func.avg(SurveyResponse.score)).filter(
            SurveyResponse.survey_id == survey_id,
            SurveyResponse.variant == "a",
            SurveyResponse.survey_completed_at.isnot(None)
        ).scalar() or 0.0
        
        # Variant B stats
        variant_b_count = db.query(func.count(SurveyResponse.id)).filter(
            SurveyResponse.survey_id == survey_id,
            SurveyResponse.variant == "b"
        ).scalar() or 0
        
        variant_b_avg = db.query(func.avg(SurveyResponse.score)).filter(
            SurveyResponse.survey_id == survey_id,
            SurveyResponse.variant == "b",
            SurveyResponse.survey_completed_at.isnot(None)
        ).scalar() or 0.0
        
        stats.variant_a_responses = variant_a_count
        stats.variant_b_responses = variant_b_count
        stats.variant_a_avg_score = float(variant_a_avg)
        stats.variant_b_avg_score = float(variant_b_avg)
    
    return stats


@router.get("/{survey_id}/responses", response_model=List[SurveyResponseDetail])
def get_survey_responses(
    org_id: int,
    survey_id: int,
    skip: int = 0,
    limit: int = 100,
    auth: AuthContext = Depends(require_org_user),
    db: Session = Depends(get_db)
):
    """
    Get all responses for a survey.
    Accessible by any authenticated user in the organization.
    """
    # Verify user belongs to the organization
    if auth.organization_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="You can only access surveys in your own organization"
        )
    
    # Verify survey belongs to organization
    survey = db.query(Survey).filter(
        Survey.id == survey_id,
        Survey.organization_id == org_id
    ).first()
    
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    responses = db.query(SurveyResponse).filter(
        SurveyResponse.survey_id == survey_id
    ).order_by(SurveyResponse.created_at.desc()).offset(skip).limit(limit).all()
    
    return responses


@router.delete("/{survey_id}", status_code=204)
def delete_survey(
    org_id: int,
    survey_id: int,
    auth: AuthContext = Depends(require_org_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a survey.
    Only accessible by org admins.
    WARNING: This will cascade delete all survey responses!
    """
    # Verify user belongs to the organization
    if auth.organization_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete surveys in your own organization"
        )
    
    survey = db.query(Survey).filter(
        Survey.id == survey_id,
        Survey.organization_id == org_id
    ).first()
    
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    # Optionally prevent deletion of live surveys
    if survey.status == "live":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a live survey. Archive it first."
        )
    
    db.delete(survey)
    db.commit()
    
    return None
