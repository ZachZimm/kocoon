# Script to add daily stock price history tables to the PostgreSQL database.

import psycopg2
import os
import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
from datetime import datetime
from psycopg2.extras import execute_values

def get_database_connection():
    """Establish a connection to the PostgreSQL database."""
    load_dotenv()
    database_host = os.getenv('DATABASE_HOST')
    database_user = os.getenv('DATABASE_USER')
    database_password = os.getenv('DATABASE_PASSWORD')
    database_name = os.getenv('DATABASE_NAME', 'financials')

    conn = psycopg2.connect(
        host=database_host,
        database=database_name,
        user=database_user,
        password=database_password
    )
    return conn

def get_all_tickers(conn):
    """Retrieve all distinct tickers from the financial_master table."""
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT ticker FROM financial_master;")
    tickers = cursor.fetchall()
    cursor.close()
    # Extract tickers from tuples
    tickers = [t[0] for t in tickers]
    return tickers

def create_price_history_table(conn, ticker):
    """Create a price history table for the given ticker if it doesn't exist."""
    cursor = conn.cursor()
    table_name = f"{ticker}_1d_price_history"
    create_query = f"""
    CREATE TABLE IF NOT EXISTS "{table_name}" (
        date DATE PRIMARY KEY,
        open NUMERIC,
        high NUMERIC,
        low NUMERIC,
        close NUMERIC,
        volume BIGINT,
        adj_close NUMERIC
    );
    """
    cursor.execute(create_query)
    conn.commit()
    cursor.close()

def get_last_date_in_db(conn, ticker):
    """Get the most recent date for which we have price data in the database."""
    cursor = conn.cursor()
    table_name = f"{ticker}_1d_price_history"
    # Check if table exists
    cursor.execute(f"SELECT to_regclass('{table_name}');")
    result = cursor.fetchone()
    if result[0] is None:
        last_date = None
    else:
        # Get the max date from the table
        cursor.execute(f'SELECT MAX(date) FROM "{table_name}";')
        result = cursor.fetchone()
        last_date = result[0]
    cursor.close()
    return last_date

def insert_price_data(conn, ticker, df):
    """Insert price data into the database."""
    cursor = conn.cursor()
    table_name = f"{ticker}_1d_price_history"

    # Prepare the insert query with ON CONFLICT to handle duplicates
    insert_query = f"""
    INSERT INTO "{table_name}" (date, open, high, low, close, volume, adj_close)
    VALUES %s
    ON CONFLICT (date) DO UPDATE SET
        open = EXCLUDED.open,
        high = EXCLUDED.high,
        low = EXCLUDED.low,
        close = EXCLUDED.close,
        volume = EXCLUDED.volume,
        adj_close = EXCLUDED.adj_close;
    """

    # Prepare the data to insert, converting NumPy data types to native Python types
    values = []
    for index, row in df.iterrows():
        values.append((
            index.date(),  # date
            float(row['Open']) if pd.notnull(row['Open']) else None,        # open
            float(row['High']) if pd.notnull(row['High']) else None,        # high
            float(row['Low']) if pd.notnull(row['Low']) else None,          # low
            float(row['Close']) if pd.notnull(row['Close']) else None,      # close
            int(row['Volume']) if pd.notnull(row['Volume']) else None,      # volume
            float(row['Adj Close']) if pd.notnull(row['Adj Close']) else None  # adj_close
        ))

    try:
        execute_values(cursor, insert_query, values)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error inserting data for {ticker}: {e}")
        raise e  # Re-raise the exception after rollback
    finally:
        cursor.close()

def update_price_history(conn, ticker):
    """Update the price history for the given ticker."""
    try:
        # Start a new transaction
        with conn:
            # Create the table if it doesn't exist
            create_price_history_table(conn, ticker)
            last_date = get_last_date_in_db(conn, ticker)

            # Get price data from yfinance
            if last_date is None:
                start_date = '1900-01-01'
            else:
                # Get data from the next day after the last date
                start_date = (last_date + pd.Timedelta(days=1)).strftime('%Y-%m-%d')

            end_date = datetime.now().strftime('%Y-%m-%d')
            data = yf.download(ticker, start=start_date, end=end_date, progress=False)

            if data.empty:
                print(f"No new data for {ticker}")
                return

            data.index = pd.to_datetime(data.index)
            insert_price_data(conn, ticker, data)
            print(f"Updated price history for {ticker}")
    except Exception as e:
        print(f"Failed to update price history for {ticker}: {e}")
        # Rollback the transaction in case of error
        conn.rollback()
        # raise e

def main():
    """Main function to update price history for all tickers."""
    # Connect to database
    conn = get_database_connection()

    tickers = get_all_tickers(conn)

    # For each ticker, update price history
    for ticker in tickers:
        print(f"Processing ticker: {ticker}")
        try:
            update_price_history(conn, ticker)
        except Exception as e:
            print(f"An error occurred for {ticker}: {e}")
            # Rollback the transaction to reset the connection state
            conn.rollback()

    # Close connection
    conn.close()

if __name__ == "__main__":
    main()