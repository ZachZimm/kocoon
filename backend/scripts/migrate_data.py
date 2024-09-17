# This script migrates the financial data from the CSV files into our PostgreSQL database.

import psycopg2
import os
import pandas as pd
from dotenv import load_dotenv

def create_master_table(conn):
    """Create a master table to store metadata about each ticker and period."""
    cursor = conn.cursor()
    
    create_query = """
    CREATE TABLE IF NOT EXISTS financial_master (
        id SERIAL PRIMARY KEY,
        ticker TEXT,
        period_type TEXT,
        table_name TEXT
    );
    """
    
    cursor.execute(create_query)
    conn.commit()
    cursor.close()

def create_financial_table(table_name, columns, conn):
    """Create a table for storing financial data."""
    cursor = conn.cursor()

    # Create the financial data table if it doesn't exist
    create_query = f'CREATE TABLE IF NOT EXISTS "{table_name}" ('
    column_definitions = [f'"{col}" TEXT' for col in columns]  # Default all columns to TEXT
    create_query += ', '.join(column_definitions) + ');'

    cursor.execute(create_query)
    conn.commit()
    cursor.close()

def add_missing_columns(table_name, columns, conn):
    """Add missing columns to the table if they don't exist."""
    cursor = conn.cursor()

    # Get existing columns from the table
    cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}';")
    existing_columns = {row[0] for row in cursor.fetchall()}

    # Identify missing columns and alter the table
    for column in columns:
        if column not in existing_columns:
            alter_query = f'ALTER TABLE "{table_name}" ADD COLUMN "{column}" TEXT;'
            cursor.execute(alter_query)
    
    conn.commit()
    cursor.close()

def insert_financial_data(table_name, df, conn):
    """Insert data from a DataFrame into the specified financial data table."""
    cursor = conn.cursor()

    # Ensure table exists and add missing columns if needed
    create_financial_table(table_name, df.columns, conn)
    add_missing_columns(table_name, df.columns, conn)

    # Generate the insert statement
    columns = ', '.join([f'"{col}"' for col in df.columns])
    values_placeholders = ', '.join(['%s'] * len(df.columns))

    # Prepare the query for checking existing rows
    unique_key_columns = ['symbol', 'asOfDate', 'periodType']  # Define your unique key columns here
    unique_key_conditions = ' AND '.join([f'"{col}" = %s' for col in unique_key_columns])
    select_query = f'SELECT 1 FROM "{table_name}" WHERE {unique_key_conditions};'

    # Insert rows one by one, skipping duplicates
    for _, row in df.iterrows():
        unique_key_values = tuple(row[col] for col in unique_key_columns)

        # Check if the row already exists
        cursor.execute(select_query, unique_key_values)
        result = cursor.fetchone()

        if not result:
            # Row does not exist, insert it
            insert_query = f'INSERT INTO "{table_name}" ({columns}) VALUES ({values_placeholders});'
            cursor.execute(insert_query, list(row))

    conn.commit()
    cursor.close()

def insert_master_data(ticker, period_type, table_name, conn):
    """Insert data into the master table."""
    cursor = conn.cursor()

    # Check if entry already exists
    select_query = f"SELECT id FROM financial_master WHERE ticker = %s AND period_type = %s;"
    cursor.execute(select_query, (ticker, period_type))
    result = cursor.fetchone()

    if not result:
        # Insert a new record into the master table
        insert_query = "INSERT INTO financial_master (ticker, period_type, table_name) VALUES (%s, %s, %s);"
        cursor.execute(insert_query, (ticker, period_type, table_name))
    
    conn.commit()
    cursor.close()

load_dotenv()
database_host = os.getenv('DATABASE_HOST')
database_user = os.getenv('DATABASE_USER')
database_password = os.getenv('DATABASE_PASSWORD')

# Connect to the database
conn = psycopg2.connect(
    host=database_host,
    database="financials",
    user=database_user,
    password=database_password
)

data_dir = 'data'
tickers = os.listdir(data_dir)

# Create the master table for managing ticker and period metadata
create_master_table(conn)

for ticker in tickers:
    ticker_dir = os.path.join(data_dir, ticker)
    
    # Process both annual 'a' and quarterly 'q' data
    for period_type in ['a', 'q']:
        period_dir = os.path.join(ticker_dir, period_type)
        
        if os.path.isdir(period_dir):
            for filename in os.listdir(period_dir):
                if filename.endswith('.csv'):
                    # Generate the table name for this specific financial data
                    table_name = f"{ticker}_{period_type}_{filename.replace('.csv', '')}"
                    table_name = table_name.replace('income_statement', 'income')
                    file_path = os.path.join(period_dir, filename)
                    df = pd.read_csv(file_path)

                    # Insert metadata into the master table
                    insert_master_data(ticker, period_type, table_name, conn)

                    # Insert the financial data into the corresponding table
                    insert_financial_data(table_name, df, conn)

conn.close()

