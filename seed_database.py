#!/usr/bin/env python3
"""
Script to seed the OpeningBell database with initial data.
Run with: python seed_database.py
"""

import os
from sqlmodel import Session, create_engine
from app.models import Company, Article, EdgarFiling, Summary

def seed_database():
    """Seed database with initial data"""
    
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/opening_bell")
    engine = create_engine(database_url, echo=False)
    
    with Session(engine) as session:
        # Seed companies
        companies_data = [
            {
                "ticker": "NVDA",
                "name": "NVIDIA Corporation",
                "cik": "0001045810",
                "aliases": ["NVIDIA", "Nvidia Corp", "NVDA Corp", "Nvidia"],
                "product_terms": ["AI chips", "GPUs", "semiconductors", "artificial intelligence"]
            },
            {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "cik": "0000320193", 
                "aliases": ["Apple", "Apple Computer", "AAPL Inc"],
                "product_terms": ["iPhone", "iPad", "Mac", "iOS", "consumer electronics"]
            },
            {
                "ticker": "TSLA",
                "name": "Tesla, Inc.",
                "cik": "0001318605",
                "aliases": ["Tesla", "Tesla Motors", "Tesla Inc"],
                "product_terms": ["electric vehicles", "EVs", "autonomous driving", "batteries"]
            },
            {
                "ticker": "MSFT",
                "name": "Microsoft Corporation",
                "cik": "0000789019",
                "aliases": ["Microsoft", "MSFT Corp", "Microsoft Corp"],
                "product_terms": ["Windows", "Office", "Azure", "cloud computing", "software"]
            },
            {
                "ticker": "GOOGL",
                "name": "Alphabet Inc.",
                "cik": "0001652044",
                "aliases": ["Google", "Alphabet", "GOOGL Inc", "Google Inc"],
                "product_terms": ["search", "advertising", "YouTube", "Android", "cloud"]
            }
        ]
        
        print("🌱 Seeding companies...")
        for company_data in companies_data:
            existing = session.query(Company).filter(Company.ticker == company_data["ticker"]).first()
            if not existing:
                company = Company(**company_data)
                session.add(company)
                print(f"  Added: {company.ticker} - {company.name}")
            else:
                print(f"  Skipped: {company_data['ticker']} (already exists)")
        
        session.commit()
        print("✅ Database seeded successfully!")
        print(f"📊 Added {len(companies_data)} companies")

if __name__ == "__main__":
    seed_database()
