from datetime import datetime
from sqlmodel import select, Session
import logging
import pandas as pd

from app.models.filing_content import InsiderTransaction
from .utils import safe_float_conversion, safe_int_conversion

logger = logging.getLogger(__name__)


def extract_insider_transactions(session: Session, filing_id: int, target_filing):
    """Extract insider trading data from Form 4 filings using EdgarTools API best practices"""
    try:
        existing_transactions = session.exec(
            select(InsiderTransaction).where(InsiderTransaction.filing_id == filing_id)
        ).all()
        
        if existing_transactions:
            valid_existing = [t for t in existing_transactions if t.shares > 0 and t.transaction_type != "UNKNOWN"]
            if valid_existing:
                logger.info(f"Valid insider transactions already exist for filing {filing_id}")
                return
            
            logger.info(f"Found {len(existing_transactions)} failed insider transactions for filing {filing_id}, deleting and reprocessing")
            for transaction in existing_transactions:
                session.delete(transaction)
            session.commit()
        
        try:
            form4 = target_filing.obj()
            logger.info(f"Processing insider transactions for filing {filing_id}")
            
            # Debug: Log what properties are actually available
            logger.info(f"Form4 object type: {type(form4)}")
            logger.info(f"Form4 object attributes: {dir(form4)}")
            
            insider_name = _get_insider_name(form4)
            insider_title = _get_insider_title(form4)
            insider_relationship = _determine_insider_relationship(insider_title)
            
            logger.info(f"Insider info - Name: {insider_name}, Title: {insider_title}, Relationship: {insider_relationship}")
            
            transaction_data = _extract_transaction_data_optimized(form4, insider_relationship)
            
            logger.info(f"Transaction data extracted: {transaction_data}")
            
            if transaction_data['shares'] and transaction_data['transaction_type'] != "UNKNOWN":
                transaction = InsiderTransaction(
                    filing_id=filing_id,
                    insider_name=str(insider_name),
                    insider_title=str(insider_title) if insider_title else None,
                    insider_relationship=str(insider_relationship) if insider_relationship else None,
                    transaction_type=str(transaction_data['transaction_type']),
                    shares=abs(transaction_data['shares']),
                    price_per_share=transaction_data['price_per_share'],
                    total_value=transaction_data['total_value'],
                    transaction_date=transaction_data['transaction_date'] or datetime.now(),
                    is_large_transaction=transaction_data['is_large_transaction'],
                    is_executive=transaction_data['is_executive'],
                    extracted_at=datetime.now()
                )
                
                session.add(transaction)
                session.commit()
                logger.info(f"Successfully extracted insider transaction for filing {filing_id}: {insider_name} {transaction_data['transaction_type']} {abs(transaction_data['shares'])} shares")
            else:
                logger.warning(f"No valid transaction data found for filing {filing_id}")
                _create_empty_transaction(session, filing_id, "No valid transaction data found")
            
        except Exception as e:
            logger.error(f"Error extracting insider transaction data for filing {filing_id}: {e}")
            _create_empty_transaction(session, filing_id, str(e))
        
    except Exception as e:
        logger.error(f"Error in extract_insider_transactions for filing {filing_id}: {e}")


def _create_empty_transaction(session: Session, filing_id: int, error_message: str):
    """Create empty transaction record with error message"""
    try:
        transaction = InsiderTransaction(
            filing_id=filing_id,
            insider_name="Unknown",
            insider_title=None,
            insider_relationship=None,
            transaction_type="UNKNOWN",
            shares=0,
            price_per_share=None,
            total_value=None,
            transaction_date=datetime.now(),
            is_large_transaction=False,
            is_executive=False,
            extracted_at=datetime.now(),
            extraction_error=error_message
        )
        session.add(transaction)
        session.commit()
        logger.info(f"Created empty insider transaction record for filing {filing_id} with error: {error_message}")
    except Exception as e:
        logger.error(f"Error creating empty insider transaction for filing {filing_id}: {e}")


def _get_insider_name(form4):
    """Get insider name using EdgarTools API best practices"""
    if hasattr(form4, 'insider_name') and form4.insider_name:
        logger.info(f"Got insider name from insider_name: {form4.insider_name}")
        return form4.insider_name
    
    if hasattr(form4, 'reporting_owner_name') and form4.reporting_owner_name:
        logger.info(f"Got insider name from reporting_owner_name: {form4.reporting_owner_name}")
        return form4.reporting_owner_name
    
    if hasattr(form4, 'reporting_owners') and form4.reporting_owners:
        if hasattr(form4.reporting_owners, 'name'):
            logger.info(f"Got insider name from reporting_owners.name: {form4.reporting_owners.name}")
            return form4.reporting_owners.name
        elif hasattr(form4.reporting_owners, '__getitem__') and len(form4.reporting_owners) > 0:
            first_owner = form4.reporting_owners[0]
            if hasattr(first_owner, 'name'):
                logger.info(f"Got insider name from first reporting_owner: {first_owner.name}")
                return first_owner.name
    
    logger.warning("No insider name found, using 'Unknown'")
    return "Unknown"


def _get_insider_title(form4):
    """Get insider title using EdgarTools API best practices"""
    if hasattr(form4, 'position') and form4.position:
        logger.info(f"Got insider title from position: {form4.position}")
        return form4.position
    
    if hasattr(form4, 'reporting_owner_relationship') and form4.reporting_owner_relationship:
        logger.info(f"Got insider title from reporting_owner_relationship: {form4.reporting_owner_relationship}")
        return form4.reporting_owner_relationship
    
    if hasattr(form4, 'reporting_owners') and form4.reporting_owners:
        if hasattr(form4.reporting_owners, 'title'):
            logger.info(f"Got insider title from reporting_owners.title: {form4.reporting_owners.title}")
            return form4.reporting_owners.title
        elif hasattr(form4.reporting_owners, '__getitem__') and len(form4.reporting_owners) > 0:
            first_owner = form4.reporting_owners[0]
            if hasattr(first_owner, 'title'):
                logger.info(f"Got insider title from first reporting_owner: {first_owner.title}")
                return first_owner.title
    
    logger.warning("No insider title found")
    return None


def _determine_insider_relationship(position):
    """Determine the insider relationship based on position"""
    if not position:
        return None
        
    position_lower = position.lower()
    if 'ceo' in position_lower or 'chief executive' in position_lower:
        return "CEO"
    elif 'cfo' in position_lower or 'chief financial' in position_lower:
        return "CFO"
    elif 'director' in position_lower:
        return "DIRECTOR"
    elif 'president' in position_lower:
        return "PRESIDENT"
    elif 'chairman' in position_lower:
        return "CHAIRMAN"
    else:
        return position.upper()


def _extract_transaction_data_optimized(form4, insider_relationship):
    """Extract transaction data using EdgarTools API best practices"""
    try:
        transaction_type = "UNKNOWN"
        shares = 0
        price_per_share = None
        total_value = None
        transaction_date = None
        
        logger.info("Starting transaction data extraction...")
        
        # Primary method: Use transactions property (most reliable)
        if hasattr(form4, 'transactions') and form4.transactions:
            logger.info(f"Found transactions property with {len(form4.transactions)} transactions")
            
            for i, transaction in enumerate(form4.transactions):
                logger.info(f"Processing transaction {i+1}: {transaction}")
                logger.info(f"Transaction attributes: {dir(transaction)}")
                
                # Get transaction type from code
                if hasattr(transaction, 'transaction_code') and transaction.transaction_code:
                    code = transaction.transaction_code
                    transaction_type = _map_transaction_code(code)
                    logger.info(f"Got transaction code: {code} -> {transaction_type}")
                
                # Get shares
                if hasattr(transaction, 'shares') and transaction.shares is not None:
                    shares = abs(transaction.shares)
                    logger.info(f"Got shares from transaction: {shares}")
                
                # Get price per share
                if hasattr(transaction, 'price_per_share') and transaction.price_per_share is not None:
                    price_per_share = transaction.price_per_share
                    logger.info(f"Got price per share from transaction: {price_per_share}")
                
                # Get transaction date
                if hasattr(transaction, 'transaction_date') and transaction.transaction_date is not None:
                    transaction_date = transaction.transaction_date
                    logger.info(f"Got transaction date from transaction: {transaction_date}")
                
                # Get total value
                if hasattr(transaction, 'value') and transaction.value is not None:
                    total_value = transaction.value
                    logger.info(f"Got total value from transaction: {total_value}")
                
                # Process only first transaction for now
                break
        else:
            logger.info("No transactions property found, trying fallback methods")
        
        # Fallback: Use built-in methods if available
        if shares == 0 and hasattr(form4, 'get_net_shares_traded'):
            try:
                net_shares = form4.get_net_shares_traded()
                if net_shares and net_shares != 0:
                    shares = abs(net_shares)
                    if transaction_type == "UNKNOWN":
                        transaction_type = "PURCHASE" if net_shares > 0 else "SALE"
                    logger.info(f"Got shares from get_net_shares_traded: {shares}")
            except Exception as e:
                logger.warning(f"get_net_shares_traded failed: {e}")
        
        # Fallback: Use shares_traded property
        if shares == 0 and hasattr(form4, 'shares_traded') and form4.shares_traded is not None:
            shares = abs(form4.shares_traded)
            logger.info(f"Got shares from shares_traded: {shares}")
        
        # Fallback: Try market_trades DataFrame
        if (shares == 0 or not price_per_share) and hasattr(form4, 'market_trades') and form4.market_trades is not None:
            logger.info("Trying market_trades DataFrame fallback")
            trades_df = form4.market_trades
            
            if isinstance(trades_df, pd.DataFrame) and not trades_df.empty:
                logger.info(f"Market trades DataFrame shape: {trades_df.shape}")
                logger.info(f"Market trades columns: {list(trades_df.columns)}")
                
                first_row = trades_df.iloc[0]
                logger.info(f"First row: {first_row.to_dict()}")
                
                # Try to extract data from DataFrame
                if shares == 0:
                    for col in ['Shares', 'shares', 'Amount', 'amount', 'Quantity', 'quantity']:
                        if col in trades_df.columns:
                            shares = abs(first_row.get(col, 0))
                            if shares > 0:
                                logger.info(f"Got shares from market_trades column '{col}': {shares}")
                                break
                
                if not price_per_share:
                    for col in ['Price', 'price', 'PricePerShare', 'price_per_share']:
                        if col in trades_df.columns:
                            price_per_share = first_row.get(col, None)
                            if price_per_share is not None:
                                logger.info(f"Got price from market_trades column '{col}': {price_per_share}")
                                break
                
                if not transaction_date:
                    for col in ['Date', 'date', 'TransactionDate', 'transaction_date']:
                        if col in trades_df.columns:
                            date_value = first_row.get(col, None)
                            if date_value:
                                try:
                                    transaction_date = pd.to_datetime(date_value)
                                    logger.info(f"Got date from market_trades column '{col}': {transaction_date}")
                                    break
                                except Exception as e:
                                    logger.warning(f"Could not parse date from column '{col}': {e}")
        
        # Fallback: Try to_dataframe() method
        if (shares == 0 or not price_per_share or transaction_type == "UNKNOWN") and hasattr(form4, 'to_dataframe'):
            logger.info("Trying to_dataframe() fallback")
            try:
                df = form4.to_dataframe()
                logger.info(f"DataFrame shape: {df.shape}")
                logger.info(f"DataFrame columns: {list(df.columns)}")
                
                if not df.empty:
                    first_row = df.iloc[0]
                    logger.info(f"First DataFrame row: {first_row.to_dict()}")
                    
                    # Extract from DataFrame
                    if shares == 0:
                        for col in ['Shares', 'shares', 'Amount', 'amount', 'Quantity', 'quantity']:
                            if col in df.columns:
                                shares = abs(first_row.get(col, 0))
                                if shares > 0:
                                    logger.info(f"Got shares from DataFrame column '{col}': {shares}")
                                    break
                    
                    if not price_per_share:
                        for col in ['Price', 'price', 'PricePerShare', 'price_per_share']:
                            if col in df.columns:
                                price_per_share = first_row.get(col, None)
                                if price_per_share is not None:
                                    logger.info(f"Got price from DataFrame column '{col}': {price_per_share}")
                                    break
                    
                    if transaction_type == "UNKNOWN" and 'Code' in df.columns:
                        code = first_row.get('Code', '')
                        if code:
                            transaction_type = _map_transaction_code(code)
                            logger.info(f"Got transaction type from DataFrame code '{code}': {transaction_type}")
                    
                    if not transaction_date:
                        for col in ['Date', 'date', 'TransactionDate', 'transaction_date']:
                            if col in df.columns:
                                date_value = first_row.get(col, None)
                                if date_value:
                                    try:
                                        transaction_date = pd.to_datetime(date_value)
                                        logger.info(f"Got date from DataFrame column '{col}': {transaction_date}")
                                        break
                                    except Exception as e:
                                        logger.warning(f"Could not parse date from DataFrame column '{col}': {e}")
                        
            except Exception as e:
                logger.warning(f"to_dataframe() fallback failed: {e}")
        
        # Fallback: Use filing date for transaction date
        if not transaction_date and hasattr(form4, 'filing_date') and form4.filing_date is not None:
            transaction_date = form4.filing_date
            logger.info(f"Using filing_date as transaction date: {transaction_date}")
        
        # Calculate total value if we have shares and price but no total
        if shares and price_per_share is not None and not total_value:
            total_value = shares * price_per_share
            logger.info(f"Calculated total value: {shares} * {price_per_share} = {total_value}")
        
        # Set price to 0 for grants/awards
        if transaction_type in ["GRANT", "AWARD"] and price_per_share is None:
            price_per_share = 0.0
            logger.info(f"Set price to 0 for {transaction_type} transaction")
        
        # Convert and validate data
        shares = safe_int_conversion(shares) or 0
        price_per_share = safe_float_conversion(price_per_share)
        total_value = safe_float_conversion(total_value)
        
        is_large_transaction = (total_value and total_value > 100000) or (shares and shares > 10000)
        is_executive = insider_relationship in ["CEO", "CFO", "DIRECTOR", "PRESIDENT", "CHAIRMAN"] if insider_relationship else False
        
        logger.info(f"Final transaction data: type={transaction_type}, shares={shares}, price={price_per_share}, value={total_value}, date={transaction_date}")
        
        return {
            'transaction_type': transaction_type,
            'shares': shares,
            'price_per_share': price_per_share,
            'total_value': total_value,
            'transaction_date': transaction_date,
            'is_large_transaction': is_large_transaction,
            'is_executive': is_executive
        }
        
    except Exception as e:
        logger.error(f"Error in _extract_transaction_data_optimized: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            'transaction_type': "UNKNOWN",
            'shares': 0,
            'price_per_share': None,
            'total_value': None,    
            'transaction_date': None,
            'is_large_transaction': False,
            'is_executive': False
        }


def _map_transaction_code(code):
    """Map transaction codes to readable transaction types"""
    code_mapping = {
        'P': 'PURCHASE',
        'S': 'SALE',
        'A': 'GRANT',
        'M': 'EXERCISE',
        'D': 'DISPOSITION',
        'G': 'GIFT',
        'V': 'VOLUNTARY'
    }
    return code_mapping.get(code, code.upper() if code else "UNKNOWN")
