from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import JSON, Column, Text

if TYPE_CHECKING:
    from .edgar_filing import EdgarFiling


class FinancialMetrics(SQLModel, table=True):
    __tablename__ = "edgar_financial_metrics"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    filing_id: Optional[int] = Field(default=None, foreign_key="edgar_filings.id", index=True)
    
    # Key financial metrics for event detection
    revenue: Optional[float] = Field(default=None)
    net_income: Optional[float] = Field(default=None)
    eps: Optional[float] = Field(default=None)
    
    # Balance sheet highlights
    total_assets: Optional[float] = Field(default=None)
    total_liabilities: Optional[float] = Field(default=None)
    cash_and_equivalents: Optional[float] = Field(default=None)
    
    # Cash flow highlights
    operating_cash_flow: Optional[float] = Field(default=None)
    
    # Processing metadata
    extracted_at: Optional[datetime] = Field(default=None)
    extraction_error: Optional[str] = Field(default=None)
    
    # Relationships
    filing: Optional["EdgarFiling"] = Relationship(back_populates="financial_metrics")


class InsiderTransaction(SQLModel, table=True):
    __tablename__ = "edgar_insider_transactions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    filing_id: Optional[int] = Field(default=None, foreign_key="edgar_filings.id", index=True)
    
    # Insider details
    insider_name: str = Field(index=True)
    insider_title: Optional[str] = Field(default=None)
    insider_relationship: Optional[str] = Field(default=None)  # "CEO", "CFO", "DIRECTOR", etc.
    
    # Transaction details
    transaction_type: str = Field(index=True)  # "PURCHASE", "SALE", "GRANT", "EXERCISE"
    shares: int = Field(index=True)
    price_per_share: Optional[float] = Field(default=None)
    total_value: Optional[float] = Field(default=None)
    transaction_date: datetime = Field(index=True)
    
    # Significance indicators
    is_large_transaction: bool = Field(default=False, index=True)  # >$100k or >10k shares
    is_executive: bool = Field(default=False, index=True)  # CEO, CFO, etc.
    
    # Processing metadata
    extracted_at: Optional[datetime] = Field(default=None)
    extraction_error: Optional[str] = Field(default=None)
    
    # Relationships
    filing: Optional["EdgarFiling"] = Relationship(back_populates="insider_transactions")


class CorporateEvent(SQLModel, table=True):
    __tablename__ = "edgar_corporate_events"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    filing_id: Optional[int] = Field(default=None, foreign_key="edgar_filings.id", index=True)
    
    # Event details
    event_type: str = Field(index=True)  # "CEO_CHANGE", "MERGER", "DIVIDEND", "STOCK_SPLIT", "LAYOFFS"
    event_date: Optional[datetime] = Field(default=None, index=True)
    effective_date: Optional[datetime] = Field(default=None)
    
    # Event specifics
    title: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # Impact indicators
    is_material: bool = Field(default=False, index=True)
    affects_operations: bool = Field(default=False)
    affects_financials: bool = Field(default=False)
    
    # Processing metadata
    extracted_at: Optional[datetime] = Field(default=None)
    extraction_error: Optional[str] = Field(default=None)
    
    # Relationships
    filing: Optional["EdgarFiling"] = Relationship(back_populates="corporate_events")


class FilingSummary(SQLModel, table=True):
    __tablename__ = "edgar_filing_summaries"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    filing_id: Optional[int] = Field(default=None, foreign_key="edgar_filings.id", index=True)
    
    # AI-generated content for OpeningBell cards
    headline: str = Field(sa_column=Column(Text))  # "Apple Reports 15% Revenue Growth"
    summary: str = Field(sa_column=Column(Text))  # 2-3 sentence digest
    impact_analysis: str = Field(sa_column=Column(Text))  # Why this matters for investors
    
    # Card metadata
    importance_score: float = Field(index=True)  # 0.0-1.0, for ranking
    event_category: str = Field(index=True)  # "EARNINGS", "INSIDER_TRADE", "CORPORATE_EVENT"
    sentiment: Optional[str] = Field(default=None, index=True)  # "POSITIVE", "NEGATIVE", "NEUTRAL"
    
    # Key metrics for card display
    key_metrics: Optional[dict] = Field(default=None, sa_column=Column(JSON))  # {"revenue": "$100B", "growth": "15%"}
    
    # Processing metadata
    generated_at: Optional[datetime] = Field(default=None)
    generation_error: Optional[str] = Field(default=None)
    model_version: Optional[str] = Field(default=None)
    
    # Relationships
    filing: Optional["EdgarFiling"] = Relationship(back_populates="filing_summary")
