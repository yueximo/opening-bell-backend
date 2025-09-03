from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship


class Summary(SQLModel, table=True):
    __tablename__ = "summaries"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    article_id: int = Field(foreign_key="articles.id", index=True)
    model: str
    lang: str = Field(default="en")
    summary: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
