import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DB_USER = os.getenv("ACE_DB_USER", "aceuser")
DB_PASS = os.getenv("ACE_DB_PASS", "Arnold123")
DB_NAME = os.getenv("ACE_DB_NAME", "ace")
DB_HOST = os.getenv("ACE_DB_HOST", "localhost")
DB_PORT = os.getenv("ACE_DB_PORT", "5432")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

Base = declarative_base()
