from datetime import datetime
from sqlmodel import select, Session

from app.models.filing_content import CorporateEvent


def extract_corporate_events(session: Session, filing_id: int, target_filing):
    """Extract corporate events from 8-K/6-K filings"""
    try:
        existing_events = session.exec(
            select(CorporateEvent).where(CorporateEvent.filing_id == filing_id)
        ).all()
        
        if existing_events:
            return
        
        try:
            events_data = target_filing.obj()
            
            event_type = getattr(events_data, 'event_type', None) or getattr(events_data, 'type', None) or "CORPORATE_EVENT"
            event_date = getattr(events_data, 'event_date', None) or getattr(events_data, 'date', None)
            effective_date = getattr(events_data, 'effective_date', None) or getattr(events_data, 'effective', None)
            title = getattr(events_data, 'title', None) or getattr(events_data, 'subject', None)
            description = getattr(events_data, 'description', None) or getattr(events_data, 'summary', None)
            
            is_material = getattr(events_data, 'is_material', None)
            if is_material is None:
                is_material = True
            
            affects_operations = getattr(events_data, 'affects_operations', None)
            if affects_operations is None:
                affects_operations = event_type in ["CEO_CHANGE", "MERGER", "LAYOFFS", "RESTRUCTURING"]
            
            affects_financials = getattr(events_data, 'affects_financials', None)
            if affects_financials is None:
                affects_financials = event_type in ["EARNINGS", "DIVIDEND", "STOCK_SPLIT", "FINANCING"]
            
            event = CorporateEvent(
                filing_id=filing_id,
                event_type=str(event_type),
                event_date=event_date,
                effective_date=effective_date,
                title=str(title) if title else None,
                description=str(description) if description else None,
                is_material=bool(is_material),
                affects_operations=bool(affects_operations),
                affects_financials=bool(affects_financials),
                extracted_at=datetime.utcnow()
            )
            
            session.add(event)
            
        except Exception as e:
            pass
        
    except Exception as e:
        pass
