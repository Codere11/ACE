# app/services/leads_repo.py
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.orm import Lead

def list_leads(db: Session, client_id: int, limit: int = 100) -> list[Lead]:
    stmt = select(Lead).where(Lead.client_id == client_id).order_by(Lead.updated_at.desc()).limit(limit)
    return list(db.scalars(stmt))

def upsert_lead_by_sid(
    db: Session,
    *,
    client_id: int,
    sid: str,
    **fields,
) -> Lead:
    stmt = select(Lead).where(Lead.client_id == client_id, Lead.sid == sid).limit(1)
    obj: Optional[Lead] = db.scalars(stmt).first()
    if obj is None:
        obj = Lead(client_id=client_id, sid=sid, **fields)
        db.add(obj)
    else:
        for k, v in fields.items():
            setattr(obj, k, v)
    db.flush()  # get ids
    return obj
