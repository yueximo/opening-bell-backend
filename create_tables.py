#!/usr/bin/env python3
"""
Quick script to create OpeningBell database tables.
Run with: python create_tables.py
"""

import os
import sys
from sqlmodel import create_engine, SQLModel, text
from app.models import Company, Article, EdgarFiling, Summary
from app.models.filing_content import FinancialMetrics, InsiderTransaction, CorporateEvent, FilingSummary

def create_tables():
    """Create all database tables"""
    
    # Get database URL from environment or use default
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/opening_bell")
    
    print(f"Connecting to database: {database_url}")
    
    try:
        # Create engine
        engine = create_engine(database_url, echo=False)
        
        # Create all tables
        print("Creating tables...")
        SQLModel.metadata.create_all(engine)
        
        print("✅ Tables created successfully!")
        print("\nCreated tables:")
        print("  - companies")
        print("  - articles") 
        print("  - edgar_filings")
        print("  - summaries")
        print("  - edgar_financial_metrics")
        print("  - edgar_insider_transactions")
        print("  - edgar_corporate_events")
        print("  - edgar_filing_summaries")
        
        # Show table info
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name, column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name IN (
                    'companies', 'articles', 'edgar_filings', 'summaries',
                    'edgar_financial_metrics', 'edgar_insider_transactions', 
                    'edgar_corporate_events', 'edgar_filing_summaries'
                )
                ORDER BY table_name, ordinal_position
            """))
            
            print("\n📋 Table structure:")
            current_table = None
            for row in result:
                if row.table_name != current_table:
                    current_table = row.table_name
                    print(f"\n  {current_table}:")
                print(f"    - {row.column_name}: {row.data_type} ({'NULL' if row.is_nullable == 'YES' else 'NOT NULL'})")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_tables()
