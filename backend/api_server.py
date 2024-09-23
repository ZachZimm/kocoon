# This file contains a FastAPI server that serves financial data from the PostgreSQL database
# TODO: Consider some kind of authentication for the API, even if it's just a token in the header saved in the frontend code for now
import os
import sys
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn
from db_interface import DBInterface
import json
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth, OAuthError

load_dotenv()
app = FastAPI()
oauth = OAuth()
oauth.register(
    name='github',
    client_id=os.getenv('GITHUB_CLIENT_ID'),
    client_secret=os.getenv('GITHUB_CLIENT_SECRET'),
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
    authorize_state=os.getenv('AUTH_SECRET_KEY')
)
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
app.add_middleware(
    SessionMiddleware, secret_key=os.getenv('AUTH_SECRET_KEY')
)

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
async def get_all_tickers() -> list:
    return db_interface.get_all_tickers()

@app.get('/api/github_login')
async def github_login(request: Request):
    redirect_uri = request.url_for('github_auth')
    return await oauth.github.authorize_redirect(request, redirect_uri)

@app.get('/api/auth/github_callback')
async def github_auth(request: Request):
    # try to get the token from the request
    try:
        token = await oauth.github.authorize_access_token(request)
    except OAuthError as e:
        print(f"OAuthError:\n{e}")
        return RedirectResponse(url='/')
    
    user_info = await oauth.github.get('user', token=token)
    user_data = user_info.json()

    github_id = user_data['id'] 
    username = user_data['login']
    email = user_data['email']

    # save or update user in the database
    db_interface.push_github_user(github_id, username, email)
    
    # redirect to the home page after login
    response = RedirectResponse(url='/')
    # add "user_id={github_id}" to the cookie
    response.set_cookie(key='user_id', value=str(github_id))

    return response

@app.get('/api/user/{user_id}')
def get_user(user_id: int):
    return db_interface.get_github_user(user_id)

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