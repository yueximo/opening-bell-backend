import csv
import json
import requests
from typing import List, Dict, Optional
from sqlmodel import Session
from app.models import Company
from app.database import engine


class CompanyLoader:
    """Service to load companies from various data sources"""
    
    def __init__(self):
        self.session = Session(engine)
    
    def load_from_sec_api(self, limit: int = 1000) -> int:
        """Load companies from SEC API (free tier) with product terms extraction"""
        companies_added = 0
        
        # SEC API endpoint for company tickers
        url = "https://www.sec.gov/files/company_tickers.json"
        
        try:
            response = requests.get(url, headers={
                'User-Agent': 'YueXi Moyueximo69@gmail.com)'
            })
            response.raise_for_status()
            
            data = response.json()
            
            for cik_str, company_data in data.items():
                if companies_added >= limit:
                    break
                    
                ticker = company_data.get('ticker', '').upper()
                name = company_data.get('title', '')
                cik_int = company_data.get('cik_str', 0)
                
                # Skip if no ticker
                if not ticker or ticker == '':
                    continue
                
                # Convert CIK integer to 10-digit string format
                cik_formatted = str(cik_int).zfill(10)
                
                company = Company(
                    ticker=ticker,
                    name=name,
                    cik=cik_formatted,
                    aliases=[name]
                )
                    
                existing = self.session.query(Company).filter(
                    Company.ticker == company.ticker
                ).first()
                
                if not existing:
                    self.session.add(company)
                    companies_added += 1
                    print(f"Added: {company.ticker} - {company.name}")
                else:
                    print(f"Skipped: {company.ticker} (already exists)")
        
        except Exception as e:
            print(f"Error loading from SEC API: {e}")
        
        self.session.commit()
        return companies_added
    
    
    def close(self):
        """Close the database session"""
        self.session.close()
