import gc
from datetime import datetime
from typing import Dict, List, Any
from sqlmodel import select, Session
import logging

from app.database.database import engine
from app.models.edgar_filing import EdgarFiling
from app.workers.celery_app import celery_app
from app.workers.content_processing import (
    generate_filing_summary,
    setup_edgar_tools,
    create_edgar_company,
    find_target_filing,
    get_filing_processor
)


logger = logging.getLogger(__name__)

setup_edgar_tools()


@celery_app.task(bind=True)
def process_filing_content(self, filing_id: int) -> Dict[str, Any]:
    """Process filing content using EdgarTools and extract structured data for OpeningBell cards"""
    try:
        with Session(engine) as session:
            filing = session.exec(select(EdgarFiling).where(EdgarFiling.id == filing_id)).first()
            if not filing:
                logger.error(f"Filing {filing_id} not found")
                return {"status": "error", "message": "Filing not found"}
            
            logger.info(f"Processing filing {filing_id} ({filing.form} - {filing.accession})")
            
            if filing.is_processed:
                logger.info(f"Filing {filing_id} already processed")
                return {"status": "success", "message": "Already processed"}
            
            result = _process_filing_content(session, filing)
            
            if result["status"] == "success":
                session.commit()
                logger.info(f"Session committed for filing {filing_id}")
            else:
                session.rollback()
                logger.warning(f"Session rolled back for filing {filing_id} due to error")
            
            return result
            
    except Exception as e:
        logger.error(f"Error in process_filing_content task: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        gc.collect()


def _process_filing_content(session: Session, filing: EdgarFiling) -> Dict[str, Any]:
    """Internal method to process filing content"""
    try:
        edgar_company = create_edgar_company(filing.cik)
        if not edgar_company:
            return {"status": "error", "message": "Failed to create EdgarTools company object"}
        
        target_filing = find_target_filing(edgar_company, filing.accession)
        if not target_filing:
            return {"status": "error", "message": "Filing not found in EdgarTools"}
        
        logger.info(f"Processing filing {filing.id} with form type: {filing.form}")
        
        processor = get_filing_processor(filing.form)
        if processor:
            logger.info(f"Found processor for form {filing.form}: {processor.__name__}")
            processor(session, filing.id, target_filing)
        else:
            logger.warning(f"No processor found for form type: {filing.form}")
        
        generate_filing_summary(session, filing.id, filing, target_filing)
        
        filing.is_processed = True
        filing.processed_at = datetime.now()
        
        logger.info(f"Successfully processed filing {filing.id}")
        return {"status": "success", "filing_id": filing.id}
        
    except Exception as e:
        logger.error(f"Error processing filing {filing.id}: {e}")
        filing.processing_error = str(e)
        return {"status": "error", "message": str(e)}


@celery_app.task
def process_pending_filings() -> Dict[str, Any]:
    """Process content for all pending filings"""
    try:
        with Session(engine) as session:
            pending_filings = session.exec(
                select(EdgarFiling).where(EdgarFiling.is_processed == False)
            ).all()
            
            logger.info(f"Found {len(pending_filings)} pending filings to process")
            
            results = []
            for filing in pending_filings:
                result = process_filing_content.delay(filing.id)
                results.append(result)
            
            return {
                "status": "success",
                "pending_filings": len(pending_filings),
                "tasks_created": len(results)
            }
            
    except Exception as e:
        logger.error(f"Error in process_pending_filings task: {e}")
        return {"status": "error", "message": str(e)}
