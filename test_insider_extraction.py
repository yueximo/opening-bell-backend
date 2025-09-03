#!/usr/bin/env python3
"""
Test script for insider transaction extraction
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.workers.content_processing.utils import setup_edgar_tools, create_edgar_company, find_target_filing
from app.workers.content_processing.insider_transactions_extractor import extract_insider_transactions
from app.database.database import get_session
from app.models.edgar_filing import EdgarFiling
from sqlmodel import select

def test_insider_extraction():
    """Test insider transaction extraction on a single Form 4 filing"""
    
    setup_edgar_tools()
    
    with next(get_session()) as session:
        # Get a Form 4 filing that hasn't been processed yet
        filing = session.exec(
            select(EdgarFiling).where(EdgarFiling.form == "4").limit(1)
        ).first()
        
        if not filing:
            print("No Form 4 filings found in database")
            return
        
        print(f"Testing insider extraction on filing:")
        print(f"  ID: {filing.id}")
        print(f"  CIK: {filing.cik}")
        print(f"  Accession: {filing.accession}")
        print(f"  Filing Date: {filing.filing_date}")
        
        # Create EdgarTools company object
        edgar_company = create_edgar_company(filing.cik)
        if not edgar_company:
            print("Failed to create EdgarTools company object")
            return
        
        # Find the target filing
        target_filing = find_target_filing(edgar_company, filing.accession)
        if not target_filing:
            print("Failed to find target filing in EdgarTools")
            return
        
        print(f"\nTarget filing found, testing extraction...")
        
        # Test the extraction
        try:
            extract_insider_transactions(session, filing.id, target_filing)
            print("✅ Extraction completed successfully!")
            
            # Check what was created
            from app.models.filing_content import InsiderTransaction
            transactions = session.exec(
                select(InsiderTransaction).where(InsiderTransaction.filing_id == filing.id)
            ).all()
            
            print(f"\nCreated {len(transactions)} insider transaction(s):")
            for t in transactions:
                print(f"  - {t.insider_name} ({t.insider_title}): {t.transaction_type} {t.shares} shares at ${t.price_per_share}")
                if hasattr(t, 'extraction_error') and t.extraction_error:
                    print(f"    Error: {t.extraction_error}")
            
        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_insider_extraction()
