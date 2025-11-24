from app.core.db import Base, engine
# Ensure models are imported so SQLAlchemy knows about them
from app import models  # noqa: F401

def create_all() -> None:
    """Create all tables if they don't exist yet."""
    Base.metadata.create_all(bind=engine)
