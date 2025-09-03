import logging
from typing import Optional
import pandas as pd

try:
    from edgar import Company as EdgarCompany, set_identity
except ImportError:
    logging.error("EdgarTools not installed. Run: pip install edgartools")
    EdgarCompany = None
    set_identity = None

logger = logging.getLogger(__name__)

def setup_edgar_tools():
    """Setup EdgarTools identity (required by SEC)"""
    if set_identity:
        set_identity("YueXi Mo yueximo69@gmail.com")
        logger.info("EdgarTools identity set successfully")
    else:
        logger.warning("EdgarTools not available")

def create_edgar_company(cik: str) -> Optional[EdgarCompany]:
    """Create EdgarTools company object"""
    if not EdgarCompany:
        logger.error("EdgarTools not available")
        return None
    
    try:
        edgar_company = EdgarCompany(cik)
        logger.info(f"Successfully created EdgarTools company object for CIK {cik}")
        return edgar_company
    except Exception as e:
        logger.error(f"Failed to create EdgarTools company object for CIK {cik}: {e}")
        return None

def find_target_filing(edgar_company: EdgarCompany, accession: str):
    """Find specific filing by accession number from company filings"""
    try:
        filings = edgar_company.get_filings()
        target_filing = None
        
        for filing in filings:
            if filing.accession_number == accession:
                target_filing = filing
                break
        
        if target_filing:
            logger.info(f"Found target filing with accession {accession}")
        else:
            logger.warning(f"Filing with accession {accession} not found in EdgarTools")
        
        return target_filing
        
    except Exception as e:
        logger.error(f"Error getting filings from EdgarTools company: {e}")
        return None

def get_filing_processor(form_type: str):
    """Get the appropriate processor function based on filing form type"""
    from .financial_metrics_extractor import extract_financial_metrics
    from .insider_transactions_extractor import extract_insider_transactions
    from .corporate_events_extractor import extract_corporate_events
    
    processors = {
        "10-K": extract_financial_metrics,
        "10-Q": extract_financial_metrics,
        "4": extract_insider_transactions,
        "4/A": extract_insider_transactions,
        "8-K": extract_corporate_events,
        "6-K": extract_corporate_events
    }
    
    return processors.get(form_type)


def extract_metric(df: pd.DataFrame, labels: list) -> Optional[float]:
    """Extract a metric from DataFrame using multiple possible labels"""
    for label in labels:
        try:
            rows = df[df['label'].str.contains(label, case=False, na=False)]
            if not rows.empty:
                value = get_latest_numeric_value(df, rows)
                if value is not None:
                    return float(value)
        except Exception:
            continue
    return None


def get_latest_numeric_value(df: pd.DataFrame, rows: pd.DataFrame) -> Optional[float]:
    """Get the latest numeric value from the DataFrame"""
    try:
        date_columns = get_numeric_columns(df)
        if not date_columns:
            return None
            
        latest_col = sorted(date_columns)[-1]
        
        for _, row in rows.iterrows():
            value = row[latest_col]
            if is_valid_numeric_value(value):
                return value
                
    except Exception:
        pass
    return None


def get_numeric_columns(df: pd.DataFrame) -> list:
    """Get columns that contain numeric data"""
    numeric_columns = []
    for col in df.columns:
        if col not in ['label', 'concept', 'level', 'abstract', 'dimension']:
            try:
                for _, row in df.iterrows():
                    value = row[col]
                    if is_valid_numeric_value(value):
                        numeric_columns.append(col)
                        break
            except Exception:
                continue
    return numeric_columns


def is_valid_numeric_value(value) -> bool:
    """Check if a value is valid numeric data"""
    if value is None or value == '':
        return False
        
    if isinstance(value, (int, float)):
        return True
        
    if isinstance(value, str):
        try:
            cleaned = value.strip().replace('.', '').replace('-', '').replace('e', '').replace('E', '')
            return cleaned.isdigit()
        except:
            return False
            
    return False


def safe_float_conversion(value) -> Optional[float]:
    """Safely convert a value to float"""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def safe_int_conversion(value) -> Optional[int]:
    """Safely convert a value to int"""
    if value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None
