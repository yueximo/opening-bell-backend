import os
from sqlmodel import create_engine, Session, SQLModel, text
from typing import Generator
import os
import logging

# Suppress SQLAlchemy engine logs
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)

from app.models import Company, Article, EdgarFiling, Summary

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/opening_bell")

engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# Dependency to get database session
def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
