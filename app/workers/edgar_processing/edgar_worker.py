import httpx
import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict
from celery import current_task
from sqlmodel import select, Session
import logging

from app.database.database import engine
from app.models.company import Company
from app.models.edgar_filing import EdgarFiling
from app.workers.celery_app import celery_app


logger = logging.getLogger(__name__)

def construct_sec_url(cik: str, accession_number: str, primary_doc: str) -> str:
    """Construct the complete SEC filing URL"""
    # Remove dashes from accession number for URL
    clean_accession = accession_number.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{clean_accession}/{primary_doc}"

@celery_app.task
def fetch_company_filings(company_id: int, days_back: int = 30):
    session = None
    try:
        session = Session(engine)
        company = session.exec(select(Company).where(Company.id == company_id)).first()
        if not company or not company.cik:
            logger.warning(f"Company {company_id} not found or missing CIK")
            return {"status": "error", "message": "Company not found or missing CIK"}
        
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        url = f"https://data.sec.gov/submissions/CIK{company.cik.zfill(10)}.json"
        headers = {
            "User-Agent": "YueXi Mo (yueximo69@gmail.com)",
            "Accept": "application/json",
        }
        
        response = httpx.get(url, headers=headers)
        response.raise_for_status()
        
        try:
            data = response.json()
        except Exception as e:
            logger.error(f"Failed to parse JSON for company {company_id} ({company.ticker}): {response.text[:500]}")
            return {"status": "error", "message": f"Invalid JSON response: {str(e)}"}
        
        if not isinstance(data, dict):
            logger.error(f"Expected dict response for company {company_id} ({company.ticker}), got: {type(data)}")
            return {"status": "error", "message": "Invalid response format"}
        
        filings_data = data.get("filings", {})
        recent_filings = filings_data.get("recent", {})
        
        if not isinstance(recent_filings, dict):
            logger.error(f"Expected recent filings to be dict for company {company_id} ({company.ticker})")
            return {"status": "error", "message": "Invalid recent filings format"}
        
        accession_numbers = recent_filings.get("accessionNumber", [])
        filing_dates = recent_filings.get("filingDate", [])
        forms = recent_filings.get("form", [])
        primary_docs = recent_filings.get("primaryDocument", [])
        items = recent_filings.get("items", [])
        
        if not all(isinstance(arr, list) for arr in [accession_numbers, filing_dates, forms]):
            logger.error(f"Expected arrays for filing data for company {company_id} ({company.ticker})")
            return {"status": "error", "message": "Invalid filing data format"}
        
        new_filings_count = 0
        
        for i in range(len(accession_numbers)):
            if i >= len(filing_dates) or i >= len(forms):
                break
            
            filing_date = filing_dates[i]
            accession_number = accession_numbers[i]
            form_type = forms[i]
            primary_doc = primary_docs[i] if i < len(primary_docs) else None
            filing_items = items[i] if i < len(items) else None
            
            if filing_date and start_date <= filing_date <= end_date:
                existing_filing = session.exec(
                    select(EdgarFiling).where(EdgarFiling.accession == accession_number)
                ).first()
                
                if not existing_filing:
                    # Construct the complete SEC URL
                    sec_url = construct_sec_url(company.cik, accession_number, primary_doc) if primary_doc else None
                    
                    filing_obj = EdgarFiling(
                        company_id=company_id,
                        cik=company.cik,
                        form=form_type,
                        accession=accession_number,
                        filing_date=datetime.strptime(filing_date, "%Y-%m-%d"),
                        primary_doc_url=sec_url,
                        items=filing_items,
                        raw={
                            'accessionNumber': accession_number,
                            'filingDate': filing_date,
                            'form': form_type,
                            'primaryDocument': primary_doc,
                            'items': filing_items,
                        }
                    )
                    session.add(filing_obj)
                    new_filings_count += 1
                    logger.info(f"Added new filing: {form_type} - {filing_date} for company {company_id} ({company.ticker}) - URL: {sec_url}")
        
        # Commit all changes at once
        session.commit()
        
        logger.info(f"Company {company_id} ({company.ticker}): {new_filings_count} new filings")
        return {
            "status": "success",
            "company_id": company_id,
            "new_filings": new_filings_count
        }
        
    except Exception as e:
        logger.error(f"Error in fetch_company_filings task: {e}")
        if session:
            session.rollback()
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}
    finally:
        if session:
            session.close()

@celery_app.task
def fetch_all_companies_filings(days_back: int = 30):
    try:
        with Session(engine) as session:
            companies = session.exec(select(Company).where(Company.cik.is_not(None))).all()
            
            logger.info(f"Starting fetch for {len(companies)} companies")
            
            for i, company in enumerate(companies):
                result = fetch_company_filings.delay(company.id, days_back)
                logger.info(f"Queued task for company {company.id} ({company.ticker}) - task {i+1}/{len(companies)}")
                
                time.sleep(0.1)
            
            logger.info(f"Created tasks for {len(companies)} companies")
            return {
                "status": "success",
                "total_companies": len(companies),
                "tasks_created": len(companies)
            }
            
    except Exception as e:
        logger.error(f"Error in fetch_all_companies_filings task: {e}")
        return {"status": "error", "message": str(e)}
