from app.services.db import Base, engine
# make sure models are imported so metadata knows them
from app import models  # noqa: F401

def create_all() -> None:
    Base.metadata.create_all(bind=engine)
