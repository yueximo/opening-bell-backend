from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import JSON, Column

if TYPE_CHECKING:
    from .filing_content import FinancialMetrics, InsiderTransaction, CorporateEvent, FilingSummary


class EdgarFiling(SQLModel, table=True):
    __tablename__ = "edgar_filings"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: Optional[int] = Field(default=None, foreign_key="companies.id", index=True)
    cik: str = Field(index=True)
    form: str
    accession: str = Field(unique=True, index=True)
    filing_date: datetime = Field(index=True)
    accepted_at: datetime = Field(default_factory=datetime.now)
    items: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    primary_doc_url: Optional[str] = Field(default=None)
    raw: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    
    # Processing status
    is_processed: bool = Field(default=False, index=True)
    processed_at: Optional[datetime] = Field(default=None)
    processing_error: Optional[str] = Field(default=None)
    
    # Relationships to streamlined content models
    financial_metrics: Optional["FinancialMetrics"] = Relationship(back_populates="filing")
    insider_transactions: List["InsiderTransaction"] = Relationship(back_populates="filing")
    corporate_events: List["CorporateEvent"] = Relationship(back_populates="filing")
    filing_summary: Optional["FilingSummary"] = Relationship(back_populates="filing")
