from datetime import datetime
from sqlmodel import select, Session

from app.models.filing_content import FinancialMetrics
from .utils import extract_metric


def extract_financial_metrics(session: Session, filing_id: int, target_filing):
    """Extract key financial metrics from 10-K/10-Q filings"""
    try:
        existing_metrics = session.exec(
            select(FinancialMetrics).where(FinancialMetrics.filing_id == filing_id)
        ).first()
        
        if existing_metrics:
            return
        
        metrics = _extract_metrics_from_xbrl(target_filing)
        
        if not metrics:
            metrics = _extract_metrics_from_obj(target_filing)
        
        if metrics:
            metrics.filing_id = filing_id
            metrics.extracted_at = datetime.utcnow()
            session.add(metrics)
        else:
            _create_empty_metrics(session, filing_id)
            
    except Exception as e:
        _create_empty_metrics(session, filing_id, str(e))


def _extract_metrics_from_xbrl(target_filing):
    """Extract metrics using XBRL statements"""
    try:
        xbrl = target_filing.xbrl()
        statements = xbrl.statements
        
        income_df = statements.income_statement().to_dataframe()
        balance_df = statements.balance_sheet().to_dataframe()
        cash_flow_df = statements.cashflow_statement().to_dataframe()
        
        return FinancialMetrics(
            revenue=extract_metric(income_df, ['Revenue', 'Contract Revenue', 'Sales Revenue']),
            net_income=extract_metric(income_df, ['Net Income', 'Net Income Loss', 'Profit Loss']),
            eps=extract_metric(income_df, ['Earnings Per Share Basic', 'Earnings Per Share Diluted', 'Earnings Per Share']),
            total_assets=extract_metric(balance_df, ['Total Assets', 'Assets']),
            total_liabilities=extract_metric(balance_df, ['Total Liabilities', 'Liabilities']),
            cash_and_equivalents=extract_metric(balance_df, ['Cash and Cash Equivalents', 'Cash', 'Cash Equivalents']),
            operating_cash_flow=extract_metric(cash_flow_df, ['Net Cash from Operating Activities', 'Net Cash Provided by Operating Activities', 'Cash Flows from Operating Activities'])
        )
    except (AttributeError, Exception):
        return None


def _extract_metrics_from_obj(target_filing):
    """Extract metrics using obj() method as fallback"""
    try:
        financials_obj = target_filing.obj()
        if hasattr(financials_obj, 'financials'):
            financials = financials_obj.financials()
            return FinancialMetrics(
                revenue=getattr(financials, 'revenue', None),
                net_income=getattr(financials, 'net_income', None),
                eps=getattr(financials, 'eps', None),
                total_assets=getattr(financials, 'total_assets', None),
                total_liabilities=getattr(financials, 'total_liabilities', None),
                cash_and_equivalents=getattr(financials, 'cash_and_equivalents', None),
                operating_cash_flow=getattr(financials, 'operating_cash_flow', None)
            )
    except Exception:
        return None
    return None


def _create_empty_metrics(session, filing_id, error_message=None):
    """Create empty metrics record with optional error message"""
    try:
        metrics = FinancialMetrics(
            filing_id=filing_id,
            revenue=None,
            net_income=None,
            eps=None,
            total_assets=None,
            total_liabilities=None,
            cash_and_equivalents=None,
            operating_cash_flow=None,
            extracted_at=datetime.utcnow(),
            extraction_error=error_message
        )
        session.add(metrics)
    except Exception:
        pass
