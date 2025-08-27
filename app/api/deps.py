# app/api/deps.py
from sqlalchemy.orm import Session
from fastapi import Depends

from app.core.db import get_db

def db_session(db: Session = Depends(get_db)) -> Session:
    return db
