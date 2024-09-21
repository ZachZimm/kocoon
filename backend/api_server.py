# This file contains a FastAPI server that serves financial data from the PostgreSQL database
# TODO: Consider some kind of authentication for the API, even if it's just a token in the header saved in the frontend code for now

import sys
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn
from db_interface import DBInterface
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

load_dotenv()
db_interface = DBInterface() # Consider a different name for this object as it is the same as the file name

@app.get("/api/balance_sheet/{period_type}/{ticker}")
def get_balance_sheet(period_type: str, ticker: str):
    if db_interface.verify_query_input(period_type, ticker) == False:
        return {"error": "Invalid input"}
    data: list = db_interface.query(ticker=ticker.upper(), period_type=period_type, report_type='balance_sheet')
    data = [data for data in data if data['periodType'] != 'TTM']
    return data

@app.get("/api/income/{period_type}/{ticker}")
def get_income_statement(period_type: str, ticker: str):
    if db_interface.verify_query_input(period_type, ticker) == False:
        return {"error": "Invalid input"}
    data: list = db_interface.query(ticker=ticker.upper(), period_type=period_type, report_type='income')
    data = [data for data in data if data['periodType'] != 'TTM']
    return data

@app.get("/api/cash_flow/{period_type}/{ticker}")
def get_cash_flow(period_type: str, ticker: str):
    if db_interface.verify_query_input(period_type, ticker) == False:
        return {"error": "Invalid input"}
    data: list = db_interface.query(ticker=ticker.upper(), period_type=period_type, report_type='cash_flow')
    data = [data for data in data if data['periodType'] != 'TTM']
    return data

@app.get("/api/price_history/{period}/{ticker}")
def get_price_history(period: str, ticker: str):
    if db_interface.verify_price_history_input(period, ticker) == False:
        return {"error": "Invalid input"}
    data: list = db_interface.query_stock_history(ticker=ticker.upper(), period_type=period, start_date='1900-01-01')
    return data

@app.get("/api/multifactor_model/{years}y/{ticker}/{num_factors}")
def get_multifactor_model(years: int, ticker: str, num_factors: int):
    # if db_interface.verify_multifactor_model_input(ticker, years, num_factors) == False:
    #     return {"error": "Invalid input"}
    # TODO: Implement input verification for multifactor model
    # for now it just returns an empty dict if the input is invalid
    data: list = db_interface.query_multifactor_model(ticker=ticker.upper(), years=years, num_factors=num_factors)
    return data

@app.get("/api/tickers")
def get_all_tickers() -> list:
    return db_interface.get_all_tickers()

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

            data = db_interface.query(ticker=ticker, period_type=period_type, report_type=report_type)
            print(json.dumps(data, indent=2))
        elif sys.argv[1] in ['test', '--test', '-t']:
            get_multifactor_model('AAPL', years=10, factors=5)

    # Or if there are no arguments, run the server for the API 
    else:
        uvicorn.run(app, host="0.0.0.0", port=5090)