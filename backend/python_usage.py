# This file contains a FastAPI server that serves financial data from the PostgreSQL database
# TODO: Consider some kind of authentication for the API, even if it's just a token in the header saved in the frontend code for now

import sys
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import psycopg2
import json

app = FastAPI()
origins = [ "http://192.168.1.193:5173",
            "http://localhost:5173",
            "http://host.zzimm.com:5173",
            "https://host.zzimm.com",
            ]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

conn = psycopg2.connect(
    host="lab",
    database="financials",
    user="myuser",
    password="letmein"
)
all_tickers = []

def query(conn, ticker='AAPL', period_type='q', report_type='balance_sheet') -> list:
    cursor = conn.cursor()
    sql_string = f'SELECT * FROM "{ticker}_{period_type}_{report_type}"'
    cursor.execute(sql_string)
    financial_data = cursor.fetchall()
    column_names = [desc[0] for desc in cursor.description]
    data_dict_list = [dict(zip(column_names, row)) for row in financial_data]

    return data_dict_list

def _get_all_tickers(conn) -> list:
    cursor = conn.cursor()
    # Query to get distinct tickers from the financial_master table
    cursor.execute("SELECT DISTINCT ticker FROM financial_master;")
    tickers = cursor.fetchall()
    # Extract tickers from tuples and print them
    ticker_list = [ticker[0] for ticker in tickers]
    cursor.close()
    return ticker_list

def verify_query_input(period_type, ticker) -> bool:
    if period_type not in ['q', 'a']:
        return False
    if ticker not in all_tickers:
        return False
    return True # valid input

@app.get("/api/balance_sheet/{period_type}/{ticker}")
def get_balance_sheet(period_type: str, ticker: str):
    if verify_query_input(period_type, ticker) == False:
        return {"error": "Invalid input"}
    return query(conn, ticker=ticker.upper(), period_type=period_type, report_type='balance_sheet')

@app.get("/api/income/{period_type}/{ticker}")
def get_income_statement(period_type: str, ticker: str):
    if verify_query_input(period_type, ticker) == False:
        return {"error": "Invalid input"}
    return query(conn, ticker=ticker.upper(), period_type=period_type, report_type='income')

@app.get("/api/cash_flow/{period_type}/{ticker}")
def get_cash_flow(period_type: str, ticker: str):
    if verify_query_input(period_type, ticker) == False:
        return {"error": "Invalid input"}
    return query(conn, ticker=ticker.upper(), period_type=period_type, report_type='cash_flow')

@app.get("/api/tickers")
def get_all_tickers() -> list:
    return _get_all_tickers(conn)

# period types are 'q' for quarterly and 'a' for annual
# report types are 'balance_sheet', 'income_statement', 'cash_flow'

if __name__ == '__main__':
    if len(sys.argv) > 1:
        # Append cli, --cli, or -c to the command to run the CLI which tests the connection and queries
        if sys.argv[1] in ['cli', '--cli', '-c']:
            ticker = 'AAPL'
            ticker_in = input('Enter a ticker (default AAPL): ')
            if len(ticker_in.strip()) > 0:
                ticker = ticker_in
            period_type = "q"
            period_type_in = input('Enter a period type (q or a, default q): ')
            if period_type_in.strip() in ['q', 'a']:
                period_type = period_type_in
            report_type = "balance_sheet"
            report_type_in = input('Enter a report type (balance_sheet, income_statement, cash_flow, default balance_sheet): ')
            if report_type_in.strip() in ['balance_sheet', 'income', 'cash_flow']:
                report_type = report_type_in

            data = query(conn, ticker=ticker, period_type=period_type, report_type=report_type)
            print(json.dumps(data, indent=2))
    # Or if there are no arguments, run the server for the API 
    else:
        all_tickers = _get_all_tickers(conn)
        uvicorn.run(app, host="0.0.0.0", port=5090)

    conn.close()

