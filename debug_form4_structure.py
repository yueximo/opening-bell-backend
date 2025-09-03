#!/usr/bin/env python3
"""
Debug script to examine EdgarTools Form4 object structure
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.workers.content_processing.utils import setup_edgar_tools, create_edgar_company, find_target_filing
from app.database.database import get_session
from app.models.edgar_filing import EdgarFiling
from sqlmodel import select

def debug_form4_structure():
    """Debug the structure of a Form4 filing from EdgarTools"""
    
    setup_edgar_tools()
    
    with next(get_session()) as session:
        # Get a Form 4 filing
        filing = session.exec(
            select(EdgarFiling).where(EdgarFiling.form == "4").limit(1)
        ).first()
        
        if not filing:
            print("No Form 4 filings found in database")
            return
        
        print(f"Debugging Form 4 filing:")
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
        
        print(f"\nTarget filing type: {type(target_filing)}")
        print(f"Target filing class: {target_filing.__class__.__name__}")
        print(f"Target filing module: {target_filing.__class__.__module__}")
        
        # Get the Form4 object
        try:
            form4 = target_filing.obj()
            print(f"\nForm4 object type: {type(form4)}")
            print(f"Form4 class: {form4.__class__.__name__}")
            print(f"Form4 module: {form4.__class__.__module__}")
            
            # List all attributes
            print(f"\nForm4 object attributes:")
            for attr in dir(form4):
                if not attr.startswith('_'):
                    try:
                        value = getattr(form4, attr)
                        if callable(value):
                            print(f"  {attr}: callable")
                        else:
                            print(f"  {attr}: {type(value)} = {repr(str(value)[:100]) if value else 'None'}")
                    except Exception as e:
                        print(f"  {attr}: error accessing - {e}")
            
            # Try to get insider information
            print(f"\n--- Insider Information ---")
            insider_attrs = ['insider_name', 'position', 'reporting_owner_name', 'reporting_owner_relationship']
            for attr in insider_attrs:
                if hasattr(form4, attr):
                    value = getattr(form4, attr)
                    print(f"  {attr}: {type(value)} = {value}")
                else:
                    print(f"  {attr}: not found")
            
            # Try to get transaction information
            print(f"\n--- Transaction Information ---")
            transaction_attrs = ['transactions', 'non_derivative_table', 'market_trades', 'shares_traded', 'get_net_shares_traded']
            for attr in transaction_attrs:
                if hasattr(form4, attr):
                    value = getattr(form4, attr)
                    if callable(value):
                        try:
                            result = value()
                            print(f"  {attr}(): {type(result)} = {result}")
                        except Exception as e:
                            print(f"  {attr}(): error calling - {e}")
                    else:
                        print(f"  {attr}: {type(value)} = {value}")
                else:
                    print(f"  {attr}: not found")
            
            # Try to get filing date
            print(f"\n--- Filing Date Information ---")
            date_attrs = ['filing_date', 'reporting_period']
            for attr in date_attrs:
                if hasattr(form4, attr):
                    value = getattr(form4, attr)
                    print(f"  {attr}: {type(value)} = {value}")
                else:
                    print(f"  {attr}: not found")
            
            # Try to get DataFrame representation
            print(f"\n--- DataFrame Representation ---")
            if hasattr(form4, 'to_dataframe'):
                try:
                    df = form4.to_dataframe()
                    print(f"  DataFrame shape: {df.shape}")
                    print(f"  DataFrame columns: {list(df.columns)}")
                    if not df.empty:
                        print(f"  First row: {df.iloc[0].to_dict()}")
                except Exception as e:
                    print(f"  to_dataframe() error: {e}")
            else:
                print("  to_dataframe(): not found")
                
        except Exception as e:
            print(f"Error getting Form4 object: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_form4_structure()
