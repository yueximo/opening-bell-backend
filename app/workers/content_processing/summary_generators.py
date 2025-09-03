import logging
from datetime import datetime
from typing import Dict
from sqlmodel import select, Session

from app.models.edgar_filing import EdgarFiling
from app.models.filing_content import FinancialMetrics, InsiderTransaction, CorporateEvent, FilingSummary

logger = logging.getLogger(__name__)

def generate_filing_summary(session: Session, filing_id: int, filing: EdgarFiling, target_filing):
    """Generate AI summary for OpeningBell cards"""
    try:
        existing_summary = session.exec(
            select(FilingSummary).where(FilingSummary.filing_id == filing_id)
        ).first()
        
        if existing_summary:
            return
        
        financial_metrics = session.exec(
            select(FinancialMetrics).where(FinancialMetrics.filing_id == filing_id)
        ).first()
        
        insider_transactions = session.exec(
            select(InsiderTransaction).where(InsiderTransaction.filing_id == filing_id)
        ).all()
        
        corporate_events = session.exec(
            select(CorporateEvent).where(CorporateEvent.filing_id == filing_id)
        ).all()
        
        if filing.form in ["10-K", "10-Q"] and financial_metrics:
            summary = generate_earnings_summary(filing, financial_metrics)
        elif filing.form in ["4", "4/A"] and insider_transactions:
            summary = generate_insider_summary(filing, insider_transactions[0])
        elif filing.form in ["8-K", "6-K"] and corporate_events:
            summary = generate_event_summary(filing, corporate_events[0])
        else:
            summary = generate_generic_summary(filing)
        
        filing_summary = FilingSummary(
            filing_id=filing_id,
            headline=summary["headline"],
            summary=summary["summary"],
            impact_analysis=summary["impact_analysis"],
            importance_score=summary["importance_score"],
            event_category=summary["event_category"],
            sentiment=summary["sentiment"],
            key_metrics=summary["key_metrics"],
            generated_at=datetime.now(),
            model_version="1.0"
        )
        
        session.add(filing_summary)
        logger.info(f"Generated filing summary for filing {filing_id}")
        
    except Exception as e:
        logger.error(f"Error generating filing summary for filing {filing_id}: {e}")

def generate_earnings_summary(filing: EdgarFiling, metrics: FinancialMetrics) -> Dict:
    """Generate earnings summary for financial filings"""
    if metrics.revenue and metrics.net_income and metrics.eps:
        sentiment = "POSITIVE"
        importance_score = 0.8
    elif metrics.revenue or metrics.net_income or metrics.eps:
        sentiment = "NEUTRAL"
        importance_score = 0.6
    else:
        sentiment = "NEUTRAL"
        importance_score = 0.4
    
    # Safe formatting with null checks
    revenue_str = f"${metrics.revenue/1e9:.1f}B" if metrics.revenue is not None else "N/A"
    net_income_str = f"${metrics.net_income/1e9:.1f}B" if metrics.net_income is not None else "N/A"
    eps_str = f"${metrics.eps:.2f}" if metrics.eps is not None else "N/A"
    
    return {
        "headline": f"{filing.form} Filing - Financial Metrics Available",
        "summary": f"Company submitted {filing.form} filing with financial data including revenue, net income, and EPS.",
        "impact_analysis": f"Financial filings provide transparency into company performance and compliance with regulatory requirements.",
        "importance_score": importance_score,
        "event_category": "EARNINGS",
        "sentiment": sentiment,
        "key_metrics": {
            "revenue": revenue_str,
            "net_income": net_income_str,
            "eps": eps_str
        }
    }

def generate_insider_summary(filing: EdgarFiling, transaction: InsiderTransaction) -> Dict:
    """Generate insider trading summary"""
    is_bullish = transaction.transaction_type == "PURCHASE"
    sentiment = "POSITIVE" if is_bullish else "NEGATIVE"
    importance_score = 0.7 if transaction.is_executive else 0.5
    
    # Safe formatting with null checks
    shares_str = f"{transaction.shares:,}" if transaction.shares is not None else "0"
    price_str = f"${transaction.price_per_share:.2f}" if transaction.price_per_share is not None else "N/A"
    value_str = f"${transaction.total_value/1e6:.1f}M" if transaction.total_value is not None else "N/A"
    
    return {
        "headline": f"{transaction.insider_name} {transaction.transaction_type.lower()}s {shares_str} shares",
        "summary": f"{transaction.insider_name} ({transaction.insider_title or 'Unknown'}) {transaction.transaction_type.lower()}ed {shares_str} shares at {price_str} per share.",
        "impact_analysis": f"Insider {transaction.transaction_type.lower()}s can signal confidence in company direction and future performance.",
        "importance_score": importance_score,
        "event_category": "INSIDER_TRADE",
        "sentiment": sentiment,
        "key_metrics": {
            "shares": shares_str,
            "value": value_str,
            "price": price_str
        }
    }

def generate_event_summary(filing: EdgarFiling, event: CorporateEvent) -> Dict:
    """Generate corporate event summary"""
    importance_score = 0.8 if event.is_material else 0.5
    sentiment = "NEUTRAL"
    
    return {
        "headline": f"Corporate Event: {event.title or event.event_type}",
        "summary": f"Company announced {event.event_type.lower().replace('_', ' ')}: {event.description or 'No description available'}.",
        "impact_analysis": f"This {event.event_type.lower().replace('_', ' ')} may impact company operations and future financial performance.",
        "importance_score": importance_score,
        "event_category": "CORPORATE_EVENT",
        "sentiment": sentiment,
        "key_metrics": {
            "event_type": event.event_type,
            "is_material": event.is_material
        }
    }

def generate_generic_summary(filing: EdgarFiling) -> Dict:
    """Generate generic summary for unclassified filings"""
    return {
        "headline": f"{filing.form} Filing Submitted",
        "summary": f"Company submitted {filing.form} filing to SEC on {filing.filing_date.strftime('%Y-%m-%d')}.",
        "impact_analysis": f"Regular SEC filings provide transparency and compliance with regulatory requirements.",
        "importance_score": 0.3,
        "event_category": "REGULATORY",
        "sentiment": "NEUTRAL",
        "key_metrics": {
            "filing_date": filing.filing_date.strftime('%Y-%m-%d'),
            "form_type": filing.form
        }
    }
