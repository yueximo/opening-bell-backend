#!/usr/bin/env python3
"""
SQLite migration script to remove YOY growth columns from FinancialMetrics table.
This script recreates the table without the YOY columns.
"""

import sqlite3
from pathlib import Path

def migrate_remove_yoy_columns():
    """Remove YOY growth columns by recreating the table"""
    
    # Find the database file
    db_path = Path("opening_bell.db")
    if not db_path.exists():
        print("Database file not found. Please run this script from the project root directory.")
        return
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Connected to database successfully.")
        
        # Check if the table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='edgar_financial_metrics'")
        if not cursor.fetchone():
            print("Table 'edgar_financial_metrics' does not exist. Nothing to migrate.")
            conn.close()
            return
        
        # Check current table structure
        cursor.execute("PRAGMA table_info(edgar_financial_metrics)")
        columns = cursor.fetchall()
        print(f"Current table has {len(columns)} columns")
        
        # Check if YOY columns exist
        yoy_columns = ['revenue_growth_yoy', 'net_income_growth_yoy', 'eps_growth_yoy']
        existing_yoy = [col[1] for col in columns if col[1] in yoy_columns]
        
        if not existing_yoy:
            print("No YOY columns found. Table is already up to date.")
            conn.close()
            return
        
        print(f"Found YOY columns to remove: {existing_yoy}")
        
        # Get all data from the current table
        cursor.execute("SELECT * FROM edgar_financial_metrics")
        data = cursor.fetchall()
        print(f"Found {len(data)} rows to migrate")
        
        # Create new table without YOY columns
        new_columns = []
        for col in columns:
            if col[1] not in yoy_columns:
                new_columns.append(col)
        
        # Build CREATE TABLE statement
        create_sql = "CREATE TABLE edgar_financial_metrics_new ("
        for col in new_columns:
            col_def = f"{col[1]} {col[2]}"
            if col[3]:  # NOT NULL
                col_def += " NOT NULL"
            if col[4]:  # DEFAULT
                col_def += f" DEFAULT {col[4]}"
            if col[5]:  # PRIMARY KEY
                col_def += " PRIMARY KEY"
            create_sql += col_def + ", "
        
        create_sql = create_sql.rstrip(", ") + ")"
        
        print("Creating new table structure...")
        cursor.execute(create_sql)
        
        # Copy data to new table (excluding YOY columns)
        if data:
            # Build INSERT statement
            col_names = [col[1] for col in new_columns]
            placeholders = ", ".join(["?" for _ in new_columns])
            insert_sql = f"INSERT INTO edgar_financial_metrics_new ({', '.join(col_names)}) VALUES ({placeholders})"
            
            # Extract data for new columns
            new_data = []
            for row in data:
                new_row = []
                for i, col in enumerate(columns):
                    if col[1] not in yoy_columns:
                        new_row.append(row[i])
                new_data.append(new_row)
            
            # Insert data
            cursor.executemany(insert_sql, new_data)
            print(f"Migrated {len(new_data)} rows to new table")
        
        # Drop old table and rename new one
        cursor.execute("DROP TABLE edgar_financial_metrics")
        cursor.execute("ALTER TABLE edgar_financial_metrics_new RENAME TO edgar_financial_metrics")
        
        # Verify the new structure
        cursor.execute("PRAGMA table_info(edgar_financial_metrics)")
        new_columns = cursor.fetchall()
        print(f"New table has {len(new_columns)} columns")
        
        # Commit changes
        conn.commit()
        print("Migration completed successfully!")
        
        conn.close()
        print("Database connection closed.")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
    except Exception as e:
        print(f"Error: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()

if __name__ == "__main__":
    print("Starting YOY columns removal migration...")
    print("This will recreate the table without YOY growth columns.")
    print("Make sure you have a backup of your database before proceeding.")
    
    response = input("Do you want to continue? (y/N): ")
    if response.lower() in ['y', 'yes']:
        migrate_remove_yoy_columns()
    else:
        print("Migration cancelled.")
    
    print("Migration script completed.")
