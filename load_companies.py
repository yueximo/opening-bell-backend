#!/usr/bin/env python3
"""
Efficient company loading script for OpeningBell.
Supports multiple data sources for loading 100+ companies.
"""

import argparse
import sys
from app.utils.company_loader import CompanyLoader


def main():
    parser = argparse.ArgumentParser(description="Load companies into OpeningBell database")
    parser.add_argument(
        "--source", 
        choices=["sec", "yahoo", "sp500", "csv"], 
        required=True,
        help="Data source to load companies from"
    )
    parser.add_argument(
        "--csv-file", 
        type=str,
        help="CSV file path (required when source=csv)"
    )
    parser.add_argument(
        "--symbols", 
        nargs="+",
        help="List of stock symbols (required when source=yahoo)"
    )
    parser.add_argument(
        "--limit", 
        type=int, 
        default=1000,
        help="Maximum number of companies to load (for SEC API)"
    )
    
    args = parser.parse_args()
    
    loader = CompanyLoader()
    
    try:
        if args.source == "sec":
            print("📊 Loading companies from SEC API...")
            count = loader.load_from_sec_api(limit=args.limit)
            print(f"✅ Loaded {count} companies from SEC API")
            
        elif args.source == "yahoo":
            if not args.symbols:
                print("❌ Error: --symbols required for Yahoo Finance source")
                sys.exit(1)
            print(f"📊 Loading {len(args.symbols)} companies from Yahoo Finance...")
            count = loader.load_from_yahoo_finance(args.symbols)
            print(f"✅ Loaded {count} companies from Yahoo Finance")
            
        elif args.source == "sp500":
            print("📊 Loading S&P 500 companies...")
            count = loader.load_sp500_companies()
            print(f"✅ Loaded {count} S&P 500 companies")
            
        elif args.source == "csv":
            if not args.csv_file:
                print("❌ Error: --csv-file required for CSV source")
                sys.exit(1)
            print(f"📊 Loading companies from {args.csv_file}...")
            count = loader.load_from_csv(args.csv_file)
            print(f"✅ Loaded {count} companies from CSV")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        loader.close()


if __name__ == "__main__":
    main()
