from datetime import datetime
from sqlmodel import select, Session
import logging
import pandas as pd
import re

from app.models.filing_content import InsiderTransaction
from .utils import safe_float_conversion, safe_int_conversion

logger = logging.getLogger(__name__)


def extract_insider_transactions(session: Session, filing_id: int, target_filing):
    """Extract insider trading data from Form 4 filings using proper EdgarTools API"""
    try:
        existing_transactions = session.exec(
            select(InsiderTransaction).where(InsiderTransaction.filing_id == filing_id)
        ).all()
        
        # Check if we have valid existing transactions (not failed ones)
        valid_existing = [t for t in existing_transactions if t.shares > 0 and t.transaction_type != "UNKNOWN"]
        
        if valid_existing:
            logger.info(f"Valid insider transactions already exist for filing {filing_id}")
            return
        
        # If we have failed transactions, delete them and reprocess
        if existing_transactions:
            logger.info(f"Found {len(existing_transactions)} failed insider transactions for filing {filing_id}, deleting and reprocessing")
            for transaction in existing_transactions:
                session.delete(transaction)
            session.commit()
        
        try:
            form4 = target_filing.obj()
            logger.info(f"Processing insider transactions for filing {filing_id}")
            
            # Get insider information using correct EdgarTools API
            insider_name = None
            insider_title = None
            
            logger.info(f"Form4 object type: {type(form4)}")
            logger.info(f"Form4 object attributes: {dir(form4)}")
            
            # Use the correct EdgarTools attributes we discovered
            if hasattr(form4, 'insider_name'):
                insider_name = form4.insider_name
                logger.info(f"Got insider name from insider_name: {insider_name}")
            
            if hasattr(form4, 'position'):
                insider_title = form4.position
                logger.info(f"Got insider title from position: {insider_title}")
            
            # Fallback to old attribute names if new ones don't exist
            if not insider_name:
                insider_name = getattr(form4, 'reporting_owner_name', None)
                if insider_name:
                    logger.info(f"Got insider name from fallback reporting_owner_name: {insider_name}")
            if not insider_title:
                insider_title = getattr(form4, 'reporting_owner_relationship', None)
                if insider_title:
                    logger.info(f"Got insider title from fallback reporting_owner_relationship: {insider_title}")
            
            # Additional fallback: try to get from reporting_owners if available
            if not insider_name and hasattr(form4, 'reporting_owners') and form4.reporting_owners:
                if hasattr(form4.reporting_owners, 'name'):
                    insider_name = form4.reporting_owners.name
                    logger.info(f"Got insider name from reporting_owners.name: {insider_name}")
                elif hasattr(form4.reporting_owners, '__getitem__'):
                    # If it's a list/iterable, get the first one
                    first_owner = form4.reporting_owners[0] if len(form4.reporting_owners) > 0 else None
                    if first_owner and hasattr(first_owner, 'name'):
                        insider_name = first_owner.name
                        logger.info(f"Got insider name from first reporting_owner: {insider_name}")
            
            if not insider_title and hasattr(form4, 'reporting_owners') and form4.reporting_owners:
                if hasattr(form4.reporting_owners, 'title'):
                    insider_title = form4.reporting_owners.title
                    logger.info(f"Got insider title from reporting_owners.title: {insider_title}")
                elif hasattr(form4.reporting_owners, '__getitem__'):
                    first_owner = form4.reporting_owners[0] if len(form4.reporting_owners) > 0 else None
                    if first_owner and hasattr(first_owner, 'title'):
                        insider_title = first_owner.title
                        logger.info(f"Got insider title from first reporting_owner: {insider_title}")
            
            # Final fallback: try to get from to_dataframe() method
            if (not insider_name or not insider_title) and hasattr(form4, 'to_dataframe'):
                try:
                    df = form4.to_dataframe()
                    logger.info(f"DataFrame from to_dataframe(): {df}")
                    
                    # Look for insider name and position in the DataFrame
                    if not insider_name and 'Insider' in df.columns:
                        insider_name = df['Insider'].iloc[0] if len(df) > 0 else None
                        if insider_name:
                            logger.info(f"Got insider name from DataFrame: {insider_name}")
                    
                    if not insider_title and 'Position' in df.columns:
                        insider_title = df['Position'].iloc[0] if len(df) > 0 else None
                        if insider_title:
                            logger.info(f"Got insider title from DataFrame: {insider_title}")
                            
                except Exception as e:
                    logger.warning(f"Could not extract from DataFrame: {e}")
            
            if not insider_name:
                insider_name = "Unknown"
                logger.warning("⚠️ No insider name found, using 'Unknown'")
            
            logger.info(f"Final insider info - Name: {insider_name}, Title: {insider_title}")
            
            insider_relationship = _determine_insider_relationship(insider_title)
            logger.info(f"Determined relationship: {insider_relationship}")
            
            transaction_data = _extract_transaction_data(form4, insider_relationship)
            
            # Validate transaction data - shares should exist and be a valid number
            shares = transaction_data['shares']
            transaction_type = transaction_data['transaction_type']
            
            # Check if we have valid transaction data
            if (shares is not None and 
                transaction_type != "UNKNOWN" and 
                (isinstance(shares, (int, float)) and shares != 0)):
                
                transaction = InsiderTransaction(
                    filing_id=filing_id,
                    insider_name=str(insider_name),
                    insider_title=str(insider_title) if insider_title else None,
                    insider_relationship=str(insider_relationship) if insider_relationship else None,
                    transaction_type=str(transaction_data['transaction_type']),
                    shares=abs(shares),  # Always store positive share count
                    price_per_share=transaction_data['price_per_share'],
                    total_value=transaction_data['total_value'],
                    transaction_date=transaction_data['transaction_date'] or datetime.now(),
                    is_large_transaction=transaction_data['is_large_transaction'],
                    is_executive=transaction_data['is_executive'],
                    extracted_at=datetime.now()
                )
                
                session.add(transaction)
                session.commit()
                logger.info(f"Successfully extracted insider transaction for filing {filing_id}: {insider_name} {transaction_data['transaction_type']} {abs(shares)} shares")
            else:
                logger.warning(f"No valid shares data found for filing {filing_id}. Shares: {shares}, Type: {transaction_type}")
                _create_empty_transaction(session, filing_id, f"No valid shares data found. Shares: {shares}, Type: {transaction_type}")
            
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


def _extract_transaction_data(form4, insider_relationship):
    """Extract transaction data from Form4 object using proper EdgarTools API"""
    transaction_type = "UNKNOWN"
    shares = 0
    price_per_share = None
    total_value = None
    transaction_date = None
    
    try:
        logger.info(f"Extracting transaction data from Form4 object: {type(form4)}")
        logger.info(f"Form4 object attributes: {dir(form4)}")
        
        # Debug: Check if this is actually a Form4 object
        if hasattr(form4, '__class__'):
            logger.info(f"Form4 class: {form4.__class__.__name__}")
            logger.info(f"Form4 module: {form4.__class__.__module__}")
        
        # Log key EdgarTools attributes for debugging
        key_attrs = ['market_trades', 'shares_traded', 'reporting_period', 'to_dataframe']
        for attr in key_attrs:
            if hasattr(form4, attr):
                attr_value = getattr(form4, attr)
                if isinstance(attr_value, pd.DataFrame):
                    logger.info(f"Found {attr}: DataFrame with shape {attr_value.shape}")
                else:
                    logger.info(f"Found {attr}: {type(attr_value)} = {attr_value}")
            else:
                logger.info(f"Missing {attr}")
        
        # Try to get shares traded first (most reliable method)
        if hasattr(form4, 'shares_traded') and form4.shares_traded is not None:
            shares = abs(form4.shares_traded)
            transaction_type = "PURCHASE" if form4.shares_traded > 0 else "SALE"
            logger.info(f"Determined transaction type from shares_traded: {transaction_type}, shares: {shares}")
        
        # Try to get transaction details from market_trades DataFrame (most reliable method)
        if hasattr(form4, 'market_trades') and form4.market_trades is not None:
            trades_df = form4.market_trades
            logger.info(f"Found market_trades DataFrame with shape: {trades_df.shape}")
            
            if isinstance(trades_df, pd.DataFrame) and not trades_df.empty:
                # Get the first transaction row
                first_row = trades_df.iloc[0]
                logger.info(f"Processing first transaction row: {first_row.to_dict()}")
                
                # Get shares from the row
                if shares == 0:
                    shares = abs(first_row.get('Shares', 0))
                
                # Get price per share
                if not price_per_share:
                    price_per_share = first_row.get('Price', None)
                
                # Get transaction date
                if not transaction_date:
                    date_value = first_row.get('Date', None)
                    if date_value:
                        transaction_date = pd.to_datetime(date_value)
                
                # Get transaction type from the row
                if transaction_type == "UNKNOWN":
                    row_transaction_type = first_row.get('TransactionType', None)
                    if row_transaction_type:
                        transaction_type = row_transaction_type.upper()
                
                # Get transaction code
                transaction_code = first_row.get('Code', None)
                logger.info(f"Transaction code: {transaction_code}")
                
                # Determine transaction type from code if not already set
                if transaction_type == "UNKNOWN" and transaction_code:
                    if transaction_code == 'P':
                        transaction_type = "PURCHASE"
                    elif transaction_code == 'S':
                        transaction_type = "SALE"
                    elif transaction_code == 'A':
                        transaction_type = "GRANT"
                    elif transaction_code == 'M':
                        transaction_type = "EXERCISE"
                    elif transaction_code == 'D':
                        transaction_type = "DISPOSITION"
                    elif transaction_code == 'G':
                        transaction_type = "GIFT"
                    elif transaction_code == 'V':
                        transaction_type = "VOLUNTARY"
                    else:
                        transaction_type = transaction_code.upper()
                
                logger.info(f"Extracted from market_trades: shares={shares}, price={price_per_share}, date={transaction_date}, code={transaction_code}, type={transaction_type}")
                
                # Calculate total value
                if shares and price_per_share:
                    total_value = shares * price_per_share
        
        # Try to get data from to_dataframe() method as fallback
        if (shares == 0 or transaction_type == "UNKNOWN") and hasattr(form4, 'to_dataframe'):
            try:
                df = form4.to_dataframe()
                logger.info(f"Using to_dataframe() fallback, shape: {df.shape}")
                
                if not df.empty:
                    first_row = df.iloc[0]
                    logger.info(f"First row from DataFrame: {first_row.to_dict()}")
                    
                    # Get shares from DataFrame
                    if shares == 0:
                        shares = abs(first_row.get('Shares', 0))
                    
                    # Get price per share from DataFrame
                    if not price_per_share:
                        price_per_share = first_row.get('Price', None)
                    
                    # Get transaction type from DataFrame
                    if transaction_type == "UNKNOWN":
                        df_transaction_type = first_row.get('Transaction Type', None)
                        if df_transaction_type:
                            transaction_type = df_transaction_type.upper()
                    
                    # Get transaction date from DataFrame
                    if not transaction_date:
                        df_date = first_row.get('Date', None)
                        if df_date:
                            transaction_date = pd.to_datetime(df_date)
                    
                    # Calculate total value
                    if shares and price_per_share:
                        total_value = shares * price_per_share
                        
                    logger.info(f"Extracted from DataFrame: shares={shares}, price={price_per_share}, date={transaction_date}, type={transaction_type}")
                    
            except Exception as e:
                logger.warning(f"Could not extract from DataFrame: {e}")
        
        # Try to get data from shares_traded as final fallback
        if shares == 0 and hasattr(form4, 'shares_traded') and form4.shares_traded is not None:
            logger.info("Using shares_traded as final fallback")
            shares = abs(form4.shares_traded)
            if transaction_type == "UNKNOWN":
                transaction_type = "PURCHASE" if form4.shares_traded > 0 else "SALE"
        
        # Get filing date as fallback for transaction date
        if not transaction_date and hasattr(form4, 'reporting_period') and form4.reporting_period is not None:
            try:
                transaction_date = pd.to_datetime(form4.reporting_period)
                logger.info(f"Using reporting_period as transaction date: {transaction_date}")
            except Exception as e:
                logger.warning(f"Could not parse reporting_period date: {e}")
        
        if not transaction_date and hasattr(form4, 'filing_date') and form4.filing_date is not None:
            transaction_date = form4.filing_date
            logger.info(f"Using filing_date as transaction date: {transaction_date}")
        
        # Ensure shares are positive for sales
        if transaction_type == "SALE" and shares < 0:
            shares = abs(shares)
        
        # Convert and validate data
        shares = safe_int_conversion(shares) or 0
        price_per_share = safe_float_conversion(price_per_share)
        total_value = safe_float_conversion(total_value)
        
        # Calculate total value if we have shares and price but no total
        if shares and price_per_share and not total_value:
            total_value = shares * price_per_share
        
        is_large_transaction = (total_value and total_value > 100000) or (shares and shares > 10000)
        is_executive = insider_relationship in ["CEO", "CFO", "DIRECTOR", "PRESIDENT", "CHAIRMAN"] if insider_relationship else False
        
        logger.info(f"Final transaction data: type={transaction_type}, shares={shares}, price={price_per_share}, value={total_value}, date={transaction_date}")
        
        # Log extraction results
        if shares == 0:
            logger.warning("⚠️ No shares data found - transaction will show as 'Unknown' with 0 shares")
        if transaction_type == "UNKNOWN":
            logger.warning("⚠️ No transaction type found - transaction will show as 'UNKNOWN'")
        if not price_per_share:
            logger.warning("⚠️ No price per share found")
        if not total_value:
            logger.warning("⚠️ No total value calculated")
        
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
        logger.error(f"Error in _extract_transaction_data: {e}")
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


def _parse_non_derivative_table(table_str):
    """Parse the non-derivative table string to extract transaction details"""
    try:
        logger.debug(f"Parsing non-derivative table: {repr(table_str[:200])}...")
        
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_str = ansi_escape.sub('', table_str)
        
        logger.debug(f"Cleaned string: {repr(clean_str[:200])}...")
        
        lines = clean_str.split('\n')
        logger.debug(f"Found {len(lines)} lines")
        
        for i, line in enumerate(lines):
            logger.debug(f"Processing line {i}: {repr(line)}")
            
            if 'Common Stock Transactions' in line:
                logger.debug("  -> Skipping Common Stock Transactions line")
                continue
            if 'Date' in line and 'Security' in line and 'Action' in line:
                logger.debug("  -> Skipping header line")
                continue
            if line.strip() == '':
                logger.debug("  -> Skipping empty line")
                continue
            
            parts = line.split()
            logger.debug(f"  -> Line has {len(parts)} parts: {parts}")
            
            if len(parts) >= 5:
                try:
                    date_part = None
                    for part in parts:
                        if re.match(r'\d{4}-\d{2}-\d{2}', part):
                            date_part = part
                            break
                    
                    if not date_part:
                        logger.debug(f"  -> No date found in parts")
                        continue
                    
                    date_str = date_part
                    logger.debug(f"  -> Found date: {date_str}")
                    
                    action_idx = None
                    for i, part in enumerate(parts):
                        if part in ['Award', 'Grant', 'Purchase', 'Sale', 'Exercise']:
                            action_idx = i
                            break
                    
                    if action_idx is None:
                        logger.debug("  -> No action found")
                        continue
                    
                    action = parts[action_idx]
                    logger.debug(f"  -> Found action: {action} at index {action_idx}")
                    
                    shares_idx = action_idx + 1
                    if shares_idx < len(parts):
                        shares_str = parts[shares_idx].replace(',', '')
                        try:
                            shares = int(shares_str)
                            logger.debug(f"  -> Found shares: {shares}")
                        except ValueError:
                            logger.debug(f"  -> Could not parse shares from '{shares_str}'")
                            continue
                    else:
                        logger.debug("  -> No shares found after action")
                        continue
                    
                    price = 0.0
                    for part in parts:
                        if part.startswith('$'):
                            price_str = part.replace('$', '').replace(',', '')
                            try:
                                price = float(price_str)
                                logger.debug(f"  -> Found price: {price}")
                                break
                            except ValueError:
                                logger.debug(f"  -> Could not parse price from '{price_str}'")
                                continue
                    
                    logger.debug(f"  -> Successfully parsed: date={date_str}, action={action}, shares={shares}, price={price}")
                    
                    return {
                        'date': date_str,
                        'action': action,
                        'shares': shares,
                        'price': price
                    }
                    
                except (ValueError, IndexError) as e:
                    logger.debug(f"  -> Parse error in line '{line}': {e}")
                    continue
        
        logger.debug("No transaction data found in table")
        return None
        
    except Exception as e:
        logger.error(f"Error parsing non-derivative table: {e}")
        return None
