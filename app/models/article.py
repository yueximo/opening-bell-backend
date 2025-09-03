from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON
from sqlalchemy import JSON


class Article(SQLModel, table=True):
    __tablename__ = "articles"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    source_domain: str = Field(index=True)
    source_type: str
    title: str
    url: str
    url_hash: str = Field(unique=True, index=True)
    title_hash: str = Field(index=True)
    published_at: datetime = Field(index=True)
    seen_at: datetime = Field(default_factory=datetime.utcnow)
    tickers: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    raw: Optional[dict] = Field(default=None, sa_column=Column(JSON))
