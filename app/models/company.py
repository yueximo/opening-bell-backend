from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field
from sqlalchemy import Column
from sqlalchemy import JSON


class Company(SQLModel, table=True):
    __tablename__ = "companies"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(unique=True, index=True)
    name: str = Field(index=True)
    cik: Optional[str] = Field(default=None, index=True)
    aliases: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
