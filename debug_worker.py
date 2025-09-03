#!/usr/bin/env python3
"""
Debug script for OpeningBell worker and financial metrics extraction
"""

import sys
import os
from datetime import datetime, timedelta
from sqlmodel import select, Session
import logging

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.database import engine
from app.models.edgar_filing import EdgarFiling
from app.models.filing_content import FinancialMetrics
from app.models.company import Company
from app.workers.celery_app import celery_app
from app.workers.content_worker import process_filing_content, process_pending_filings
from app.workers.edgar_processing.edgar_worker import fetch_all_companies_filings
from app.models.filing_content import InsiderTransaction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_database_status():
    """Check the current state of the database"""
    print("\n" + "="*60)
    print("DATABASE STATUS CHECK")
    print("="*60)
    
    with Session(engine) as session:
        # Check companies
        companies = session.exec(select(Company)).all()
        print(f"📊 Total companies in database: {len(companies)}")
        
        if companies:
            print("   Sample companies:")
            for company in companies[:5]:
                print(f"   - {company.ticker} ({company.name})")
        
        # Check filings
        filings = session.exec(select(EdgarFiling)).all()
        print(f"\n📄 Total filings in database: {len(filings)}")
        
        if filings:
            # Group by form type
            form_counts = {}
            for filing in filings:
                form_counts[filing.form] = form_counts.get(filing.form, 0) + 1
            
            print("   Filings by form type:")
            for form, count in form_counts.items():
                print(f"   - {form}: {count}")
            
            # Check processing status
            unprocessed = session.exec(select(EdgarFiling).where(EdgarFiling.is_processed == False)).all()
            processed = session.exec(select(EdgarFiling).where(EdgarFiling.is_processed == True)).all()
            
            print(f"\n   Processing status:")
            print(f"   - Unprocessed: {len(unprocessed)}")
            print(f"   - Processed: {len(processed)}")
            
            # Check for 10-K/10-Q filings specifically
            financial_filings = session.exec(
                select(EdgarFiling).where(EdgarFiling.form.in_(["10-K", "10-Q"]))
            ).all()
            
            print(f"\n   Financial filings (10-K/10-Q): {len(financial_filings)}")
            
            if financial_filings:
                print("   Sample financial filings:")
                for filing in financial_filings[:3]:
                    print(f"   - {filing.form} for {filing.cik} on {filing.filing_date}")
        
        # Check financial metrics
        metrics = session.exec(select(FinancialMetrics)).all()
        print(f"\n💰 Financial metrics records: {len(metrics)}")
        
        if metrics:
            print("   Sample metrics:")
            for metric in metrics[:3]:
                print(f"   - Filing ID {metric.filing_id}: Revenue=${metric.revenue}, Net Income=${metric.net_income}")

def check_worker_status():
    """Check if the worker is running and responding"""
    print("\n" + "="*60)
    print("WORKER STATUS CHECK")
    print("="*60)
    
    try:
        # Check if Celery is connected to Redis
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        registered_tasks = inspect.registered()
        
        if active_workers:
            print("✅ Celery workers are active:")
            for worker, tasks in active_workers.items():
                print(f"   - {worker}: {len(tasks)} active tasks")
        else:
            print("❌ No active Celery workers found")
        
        if registered_tasks:
            print("\n📋 Registered tasks:")
            for worker, tasks in registered_tasks.items():
                print(f"   - {worker}: {tasks}")
        else:
            print("❌ No registered tasks found")
            
    except Exception as e:
        print(f"❌ Error checking worker status: {e}")

def check_form4_status():
    """Check the status of Form 4 filings and insider transactions in the database"""
    print("\n" + "="*60)
    print("CHECKING FORM 4 FILINGS STATUS")
    print("="*60)
    
    with Session(engine) as session:
        # Check Form 4 filings
        form4_filings = session.exec(
            select(EdgarFiling).where(EdgarFiling.form.in_(["4", "4/A"]))
        ).all()
        
        print(f"📄 Total Form 4 filings found: {len(form4_filings)}")
        
        if form4_filings:
            # Group by processing status
            processed = [f for f in form4_filings if f.is_processed]
            unprocessed = [f for f in form4_filings if not f.is_processed]
            
            print(f"   ✅ Processed: {len(processed)}")
            print(f"   ⏳ Unprocessed: {len(unprocessed)}")
            
            # Show sample filings
            print("\n   Sample Form 4 filings:")
            for filing in form4_filings[:5]:
                status = "✅" if filing.is_processed else "⏳"
                print(f"   {status} {filing.form} - {filing.cik} - {filing.filing_date} - {filing.accession}")
                if filing.processing_error:
                    print(f"      Error: {filing.processing_error}")
        
        # Check insider transactions
        insider_transactions = session.exec(select(InsiderTransaction)).all()
        print(f"\n💰 Total insider transactions: {len(insider_transactions)}")
        
        if insider_transactions:
            # Analyze transaction types
            transaction_types = {}
            for transaction in insider_transactions:
                tx_type = transaction.transaction_type
                transaction_types[tx_type] = transaction_types.get(tx_type, 0) + 1
            
            print("   Transaction types:")
            for tx_type, count in transaction_types.items():
                print(f"     - {tx_type}: {count}")
            
            # Check for problematic transactions
            problematic = [t for t in insider_transactions if t.transaction_type in ["UNKNOWN", "none"] or t.shares == 0]
            if problematic:
                print(f"\n   ⚠️ Problematic transactions: {len(problematic)}")
                for transaction in problematic[:3]:
                    print(f"     - Filing {transaction.filing_id}: {transaction.transaction_type}, {transaction.shares} shares")
                    if transaction.extraction_error:
                        print(f"       Error: {transaction.extraction_error}")
        else:
            print("   ❌ No insider transactions found")

def test_filing_processing():
    """Test processing a specific filing"""
    print("\n" + "="*60)
    print("TESTING FILING PROCESSING")
    print("="*60)
    
    with Session(engine) as session:
        # Find an unprocessed 10-K or 10-Q filing
        unprocessed_financial = session.exec(
            select(EdgarFiling).where(
                EdgarFiling.form.in_(["10-K", "10-Q"]),
                EdgarFiling.is_processed == False
            )
        ).first()
        
        if not unprocessed_financial:
            print("❌ No unprocessed 10-K/10-Q filings found")
            return
        
        print(f"🧪 Testing processing for filing ID {unprocessed_financial.id}")
        print(f"   Form: {unprocessed_financial.form}")
        print(f"   CIK: {unprocessed_financial.cik}")
        print(f"   Date: {unprocessed_financial.filing_date}")
        
        try:
            # Process the filing
            result = process_filing_content(unprocessed_financial.id)
            print(f"✅ Processing result: {result}")
            
            # Check if metrics were created
            metrics = session.exec(
                select(FinancialMetrics).where(FinancialMetrics.filing_id == unprocessed_financial.id)
            ).first()
            
            if metrics:
                print(f"✅ Financial metrics created:")
                print(f"   - Revenue: ${metrics.revenue}")
                print(f"   - Net Income: ${metrics.net_income}")
                print(f"   - EPS: ${metrics.eps}")
            else:
                print("❌ No financial metrics created")
                
        except Exception as e:
            print(f"❌ Error processing filing: {e}")

def test_manual_task_execution():
    """Test manually executing the pending filings task"""
    print("\n" + "="*60)
    print("TESTING MANUAL TASK EXECUTION")
    print("="*60)
    
    try:
        # Execute the task manually
        result = process_pending_filings()
        print(f"✅ Manual task execution result: {result}")
        
        # Check if any new metrics were created
        with Session(engine) as session:
            total_metrics = session.exec(select(FinancialMetrics)).all()
            print(f"💰 Total financial metrics after manual execution: {len(total_metrics)}")
            
    except Exception as e:
        print(f"❌ Error executing manual task: {e}")

def fetch_new_filings():
    """Fetch new filings to test the pipeline"""
    print("\n" + "="*60)
    print("FETCHING NEW FILINGS")
    print("="*60)
    
    try:
        # Fetch filings from the last 7 days
        result = fetch_all_companies_filings(days_back=7)
        print(f"✅ Fetch result: {result}")
        
        # Check if new filings were added
        with Session(engine) as session:
            total_filings = session.exec(select(EdgarFiling)).all()
            print(f"📄 Total filings after fetch: {len(total_filings)}")
            
    except Exception as e:
        print(f"❌ Error fetching filings: {e}")

def test_form4_processing():
    """Test processing a specific Form 4 filing for insider transactions"""
    print("\n" + "="*60)
    print("TESTING FORM 4 INSIDER TRANSACTION PROCESSING")
    print("="*60)
    
    with Session(engine) as session:
        # Find an unprocessed Form 4 filing
        unprocessed_form4 = session.exec(
            select(EdgarFiling).where(
                EdgarFiling.form.in_(["4", "4/A"]),
                EdgarFiling.is_processed == False
            )
        ).first()
        
        if not unprocessed_form4:
            print("❌ No unprocessed Form 4 filings found")
            return
        
        print(f"🧪 Testing Form 4 processing for filing ID {unprocessed_form4.id}")
        print(f"   Form: {unprocessed_form4.form}")
        print(f"   CIK: {unprocessed_form4.cik}")
        print(f"   Date: {unprocessed_form4.filing_date}")
        print(f"   Accession: {unprocessed_form4.accession}")
        
        try:
            # Process the filing
            result = process_filing_content(unprocessed_form4.id)
            print(f"✅ Processing result: {result}")
            
            # Check if insider transactions were created
            insider_transactions = session.exec(
                select(InsiderTransaction).where(InsiderTransaction.filing_id == unprocessed_form4.id)
            ).all()
            
            if insider_transactions:
                print(f"✅ Insider transactions created: {len(insider_transactions)}")
                for i, transaction in enumerate(insider_transactions):
                    print(f"   Transaction {i+1}:")
                    print(f"     - Insider: {transaction.insider_name}")
                    print(f"     - Title: {transaction.insider_title}")
                    print(f"     - Relationship: {transaction.insider_relationship}")
                    print(f"     - Type: {transaction.transaction_type}")
                    print(f"     - Shares: {transaction.shares}")
                    print(f"     - Price: ${transaction.price_per_share}")
                    print(f"     - Value: ${transaction.total_value}")
                    print(f"     - Date: {transaction.transaction_date}")
                    print(f"     - Large: {transaction.is_large_transaction}")
                    print(f"     - Executive: {transaction.is_executive}")
                    if transaction.extraction_error:
                        print(f"     - Error: {transaction.extraction_error}")
            else:
                print("❌ No insider transactions created")
                
        except Exception as e:
            print(f"❌ Error processing Form 4 filing: {e}")
            import traceback
            traceback.print_exc()

def main():
    """Run all debugging checks"""
    print("🔍 OpeningBell Worker Debug Script")
    print("="*60)
    
    # Check database status
    check_database_status()
    
    # Check worker status
    check_worker_status()
    
    # Check Form 4 status
    check_form4_status()
    
    # Test filing processing
    test_filing_processing()
    
    # Test Form 4 insider transaction processing
    test_form4_processing()
    
    # Test manual task execution
    test_manual_task_execution()
    
    # Fetch new filings automatically
    fetch_new_filings()
    
    print("\n" + "="*60)
    print("DEBUG COMPLETE")
    print("="*60)
    print("\nNext steps:")
    print("1. If no companies/filings: Run the company loading script")
    print("2. If worker not running: Start the worker with 'python start_worker.py'")
    print("3. If processing fails: Check the edgartools installation and API")
    print("4. If still no metrics: Check the filing content extraction logic")

if __name__ == "__main__":
    main()
