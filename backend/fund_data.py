# This script is used to get financial data from Yahoo Finance and save it to a 'data' directory of CSV files
# Some of this code is currently unused, but it is kept here for reference as we want it around in the near future

import sys
import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
import yahooquery as yq
import requests
import os
import re
import time
import numpy as np
import api_server

load_dotenv()
av_key = os.getenv('ALPHAVANTAGE_API_KEY')
# y_user = os.getenv('YAHOO_USER')
# y_pass = os.getenv('YAHOO_PASS')

def merge_close_ttm_rows(df):
    # Convert 'asOfDate' to datetime for comparison
    df['asOfDate'] = pd.to_datetime(df['asOfDate'])

    # Function to merge two rows
    def merge_rows(row1, row2):
        for col in df.columns:
            if pd.isna(row1[col]) and not pd.isna(row2[col]):
                row1[col] = row2[col]
        return row1

    # Filter for TTM data
    ttm = df['periodType'] == 'TTM'
    ttm_df = df[ttm].sort_values(by='asOfDate').reset_index(drop=True)
    rows_to_drop = []

    for i in range(len(ttm_df) - 1):
        # Check if asOfDate is within 10 days
        if abs((ttm_df.loc[i, 'asOfDate'] - ttm_df.loc[i + 1, 'asOfDate']).days) <= 10:
            ttm_df.loc[i] = merge_rows(ttm_df.loc[i], ttm_df.loc[i + 1])
            rows_to_drop.append(i + 1)

    ttm_df.drop(rows_to_drop, inplace=True)
    # Replace original TTM data with merged data
    df = pd.concat([df[~ttm], ttm_df]).sort_values(by='asOfDate').reset_index(drop=True)

    return df

def av_get_income_statement(ticker='AAPL'):
    url = f'https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol={ticker}&apikey={av_key}'
    r = requests.get(url)
    data = r.json()
    a_df = pd.DataFrame(data['annualReports'])
    q_df = pd.DataFrame(data['quarterlyReports'])
    print(q_df.head)
    print(q_df.tail)
    return a_df, q_df

def check_if_exists(ticker, frequency):
    if os.path.exists(f'data/{ticker}/{frequency}/income.csv') and os.path.exists(f'data/{ticker}/{frequency}/cash_flow.csv') and os.path.exists(f'data/{ticker}/{frequency}/balance_sheet.csv') and os.path.exists(f'data/{ticker}/{frequency}/valuation.csv'):
        return True
    else:
        return False


def get_historical_financials_yq(ticker='AAPL', frequency_list=['q'], long=False):
    all_exists = True
    if not os.path.exists(f'data/{ticker}'):
        os.makedirs(f'data/{ticker}')
    for frequency in frequency_list:
        if not os.path.exists(f'data/{ticker}/{frequency}'):
            os.makedirs(f'data/{ticker}/{frequency}')
        if not check_if_exists(ticker, frequency):
            all_exists = False
    if all_exists and long: 
        return 1 # should check whether they are up to date, or for a force flag
    if long == True:
        yq_ticker = yq.Ticker(ticker, username=y_user, password=y_pass)
    else:
        yq_ticker = yq.Ticker(ticker)
    for frequency in frequency_list:
        frequency_word = 'quarterly' if frequency == 'q' else 'annual'
        
        try:
            print(f'retrieving {frequency_word} historical financials for {ticker}')

            def retrieve_and_save_financial_data(ticker, frequency, file_type, yq_ticker, long):
                file_path = f'data/{ticker}/{frequency}/{file_type}.csv'
                # file_path += '_short.csv' if not long else '.csv'

                if not os.path.exists(file_path) or not long:
                    # Check if the attribute is a method or a DataFrame
                    if hasattr(yq_ticker, f"p_{file_type}") and long:
                        data_method = getattr(yq_ticker, f"p_{file_type}")
                        data = data_method(frequency=frequency)
                    elif hasattr(yq_ticker, file_type):
                        data_method = getattr(yq_ticker, file_type)
                        # Call the method if it's callable, otherwise assign the DataFrame directly
                        data = data_method(frequency=frequency) if callable(data_method) else data_method
                    else:
                        print(f"Error: {file_type} not found in yq_ticker")
                        return False

                    data.to_csv(file_path)
                    print(f'retrieved {frequency_word} {file_type} for {ticker}')
                    return False
                return True

            # Assuming 'ticker', 'frequency', 'yq_ticker', and 'long' are defined
            financial_data_types = ['income_statement', 'cash_flow', 'balance_sheet', 'valuation_measures']
            for data_type in financial_data_types:
                all_exists &= retrieve_and_save_financial_data(ticker, frequency, data_type, yq_ticker, long)

            print()
            
            if (long) and not os.path.exists(f'data/{ticker}/{frequency}/income.csv') and os.path.exists(f'data/{ticker}/{frequency}/cash_flow.csv') and os.path.exists(f'data/{ticker}/{frequency}/balance_sheet.csv') and os.path.exists(f'data/{ticker}/{frequency}/valuation.csv'):
                return -1
        except Exception as e:
            print(e)
            return -1
            
    return 0

def update_financials_yq(ticker='AAPL', frequency_list=['q']):
    all_exists = True
    if not os.path.exists(f'data/{ticker}'):
        os.makedirs(f'data/{ticker}')
    for frequency in frequency_list:
        if not os.path.exists(f'data/{ticker}/{frequency}'):
            os.makedirs(f'data/{ticker}/{frequency}')
        if not check_if_exists(ticker, frequency):
            all_exists = False
   
    else:
        yq_ticker = yq.Ticker(ticker)
    for frequency in frequency_list:
        frequency_word = 'quarterly' if frequency == 'q' else 'annual'
        
        try:
            print(f'retrieving {frequency_word} historical financials for {ticker}')

            def retrieve_and_update_financial_data(ticker, frequency, file_type, yq_ticker):
                file_path = f'data/{ticker}/{frequency}/{file_type}.csv'
                
                # Check if the attribute is a method or a DataFrame
                if hasattr(yq_ticker, f"p_{file_type}"):
                    data_method = getattr(yq_ticker, f"p_{file_type}")
                    data = data_method(frequency=frequency)
                elif hasattr(yq_ticker, file_type):
                    data_method = getattr(yq_ticker, file_type)
                    # Call the method if it's callable, otherwise assign the DataFrame directly
                    data = data_method(frequency=frequency) if callable(data_method) else data_method
                else:
                    print(f"Error: {file_type} not found in yq_ticker")
                    return False
                
                if not os.path.exists(file_path):
                    data.to_csv(file_path)
                    print(f'retrieved new {frequency_word} report {file_type} for {ticker}')
                    original_data = data.copy()

                original_data['asOfDate'] = pd.to_datetime(original_data['asOfDate'])
                original_data = original_data.set_index('asOfDate')
                data['asOfDate'] = pd.to_datetime(data['asOfDate'])
                data = data.set_index('asOfDate')
                original_data = original_data.iloc[:-1]
                if file_type != 'balance_sheet':
                    if data.iloc[-1]['periodType'] == 'TTM':
                        data.at[data.index[-1], 'asOfDate'] = pd.Timestamp.today().normalize()
                else:
                    # Change date and index of final row to today's date
                    data.at[data.index[-1], 'asOfDate'] = pd.Timestamp.today().normalize()
                    data.index = pd.to_datetime(data['asOfDate'])
                    # data = data[~data.index.duplicated(keep='second')]
                
                # merge any TTM rows in the new data 
                merged_data = pd.concat([original_data, data])
                merged_data = merge_close_ttm_rows(merged_data)
                merged_data.to_csv(file_path)

                print(f'retrieved {frequency_word} {file_type} for {ticker}')
                return False

            # Assuming 'ticker', 'frequency', 'yq_ticker', and 'long' are defined
            financial_data_types = ['income_statement', 'cash_flow', 'balance_sheet', 'valuation_measures']
            for data_type in financial_data_types:
                all_exists &= retrieve_and_update_financial_data(ticker, frequency, data_type, yq_ticker)

            print()
            
            if not os.path.exists(f'data/{ticker}/{frequency}/income.csv') and os.path.exists(f'data/{ticker}/{frequency}/cash_flow.csv') and os.path.exists(f'data/{ticker}/{frequency}/balance_sheet.csv') and os.path.exists(f'data/{ticker}/{frequency}/valuation.csv'):
                return -1
        except Exception as e:
            print(e)
            return -1
            
    return 0

def get_insider_reports(): # This function needs to be fixed and tested without the y_user and y_pass - It doesn't work without a premium account
    r = None
    if y_user == '' or y_pass == '':
       r = yq.Research()
    else:
        r = yq.Research(username=y_user, password=y_pass)
    reports = r.reports(
        report_type='Analyst Report, Insider Activity',
        report_date='Last Week'
    )
    print(reports)
    if not os.path.exists('data'):
        os.makedirs('data')
    reports.to_csv(f'data/insider_reports.csv')

def save_financials_loop(tickers, frequency_list):
    if not os.path.exists('data'):
        os.makedirs('data')

    failed_tickers = []
    time_start = time.time()

    tickers_1 = list(set(tickers)) # This is a poor name
    sleep_time = 40
    long = False
    num_tickers = len(tickers)
    success = 0
    i = 0
    for ticker in tickers_1:
        try:
            code = get_historical_financials_yq(ticker, frequency_list, long=long)
            if code == 0:
                print(f'sleeping for {sleep_time} seconds')
                print()
                success += 1
            if code == 1:
                print(f'data for {ticker} already exists')
                pass
            elif code == -1:
                print(f'failed to retrieve {ticker}')
                failed_tickers.append(ticker)
                print(f'sleeping for {sleep_time} seconds')
                print()
        except KeyboardInterrupt:
            print()
            print('keyboard interrupt')
            print(f'successful tickers: {success}')
            print(f'failed tickers: {list(set(failed_tickers))}')
            print(f'time elapsed: {round((time.time() - time_start)/60,1)} minutes')
            exit(0)
        except Exception as e:
            print(e)
            print(f'failed to retrieve {ticker}')
            failed_tickers.append(ticker)
            print(f'sleeping for {sleep_time} seconds')
            print()

        i += 1
        time_elapsed = round((time.time() - time_start)/60,1)
        eta = round((time_elapsed/i) * (num_tickers - i),1)

        print(f'-- processed {i} of {num_tickers} tickers ({round((i/num_tickers)*100,2)}%)')
        print(f'-- time elapsed: {round((time.time() - time_start)/60,1)} minutes')
        print(f'-- estimated time remaining: {eta} minutes')
        if i < num_tickers:
            time.sleep(sleep_time)

    # get_insider_reports() # this function is broken without y_user and y_pass
    print(f'successful tickers: {success}')
    print(f'failed tickers: {list(set(failed_tickers))}')
    print(f'total time elapsed: {round((time.time() - time_start)/60,1)} minutes')

def use_screener(sectors, num_stocks=50):
    s = yq.Screener()
    # print(s.available_screeners)
    symbols = []
    for sector in sectors:
        data = s.get_screeners(sector, count=num_stocks)
        data = data[sector]['quotes']
        for d in data:
            symbols.append(d['symbol'])
    # Keep symbols with '-' in them if the second part is only one character
    # As in, BRK-B as those are class B shares, but there are plenty on different exchanges
    # which are only differentiated by the second character as in SHR-HK
    symbols = [s for s in symbols if len(s.split('-')) == 1 or len(s.split('-')[1]) == 1]
    return list(set(symbols))

def load_fund_data(ticker):
    return_data = []
    for _data in ['income', 'cash_flow', 'balance_sheet', 'valuation']:
        data = pd.read_csv(f'data/{ticker}/q/{_data}.csv')
        data['asOfDate'] = pd.to_datetime(data['asOfDate'])

        # Update the last row's 'asOfDate' to today's date if it's a TTM entry and not already today's date
        if data.iloc[-1]['periodType'] == 'TTM' and data.iloc[-1]['asOfDate'].date() != pd.Timestamp.today().date() or _data == 'balance_sheet': # balance_sheet does not have TTM
            if _data == 'balance_sheet':
                # Create a copy of the last row and update its asOfDate
                new_row = data.iloc[-1].copy()
                new_row['asOfDate'] = pd.Timestamp.today().normalize()

                # Check if today's date already exists in the DataFrame
                if not (data['asOfDate'] == new_row['asOfDate']).any():
                    data = pd.concat([data, pd.DataFrame([new_row])], ignore_index=True)
                
            else:
                # For other financial data, update the last row's asOfDate to today's date if it's a TTM entry
                if data.iloc[-1]['periodType'] == 'TTM':
                    data.at[data.index[-1], 'asOfDate'] = pd.Timestamp.today().normalize()

        # Drop non-current TTM rows, keeping the latest TTM row
        ttm_rows = data[data['periodType'] == 'TTM']
        if not ttm_rows.empty:
            latest_ttm_index = ttm_rows['asOfDate'].idxmax()
            data = data.drop(ttm_rows[ttm_rows.index != latest_ttm_index].index)
        
        data['asOfDate'] = pd.to_datetime(data['asOfDate'])
        data = data.set_index('asOfDate')
        data.index = pd.to_datetime(data.index)
        try:
            data = data.drop(columns=['currencyCode','symbol'])
        except:
            pass
        data = data.replace(np.nan, 0)
        data = data.replace(np.inf, 0)
        return_data.append(data)
    return return_data

def build_fund_data(ticker, frequency='q'): # This function is not used, but we may want to use it in the future when building a training set
    df = pd.DataFrame()
    data = load_fund_data(ticker)
    for d in data:
        new_rows = [col for col in d.columns if col not in df.columns]
        df = pd.concat([df, d[new_rows]], axis=1)
        # df = pd.concat([df, d], axis=1)
        df.index = pd.to_datetime(df.index)
    df = df.replace(np.nan, 0)
    df = df.replace(np.inf, 0)
    
    # df.drop(columns=['periodType'], inplace=True)
    df.to_csv(f'data/{ticker}/{frequency}/fund_data.csv')

def create_earnings_directory(tickers):
    for ticker in tickers:
        if not os.path.exists(f'data'):
            os.makedirs(f'data')
        if not os.path.exists(f'data/{ticker}'):
            os.makedirs(f'data/{ticker}')
        if not os.path.exists(f'data/{ticker}/earnings'):
            os.makedirs(f'data/{ticker}/earnings')
    
    
def manage_next_earnings_date(_tickers):
    tickers = yq.Ticker(' '.join(_tickers))
    return_list = []
    for _ticker in _tickers:
        earnings_date_list = tickers.calendar_events[_ticker]["earnings"]["earningsDate"]
        if len(earnings_date_list) == 0:
            print(f'no earnings date found for {_ticker}')
            continue
        earnings_date = earnings_date_list[0][:-2]
        data = ''
        is_past_earnings = True
        if os.path.exists('data/earnings/earnings_date.csv'):
            with open('data/earnings/earnings_date.csv', 'r') as f:
                data = f.read()
                # compare read datetime to current date
                if pd.to_datetime(data) > pd.Timestamp.today():
                    is_past_earnings = False
                    return_list.append(_ticker)
        if is_past_earnings:
            with open(f'data/{_ticker}/earnings/earnings_date.csv', 'w') as f:
                f.write(f'{earnings_date}')
    return return_list

def get_earnings_date(ticker):
    earnings_date = ''
    if os.path.exists(f'data/{ticker}/earnings/earnings_date.csv'):
        with open(f'data/{ticker}/earnings/earnings_date.csv', 'r') as f:
            earnings_date = f.read()
    return earnings_date

def manage_upcoming_earnings(tickers,days=30):
    upcoming_earnings = [] # [[ticker, date], [ticker, date]]
    for ticker in tickers:
        earnings_date = get_earnings_date(ticker)
        # check whether date is this week
        if pd.to_datetime(earnings_date) > pd.Timestamp.today() and pd.to_datetime(earnings_date) < pd.Timestamp.today() + pd.Timedelta(days=days):
                upcoming_earnings.append([ticker, earnings_date])
    return upcoming_earnings

def get_tickers_past_earnings(tickers, days=90):
    upcoming_earnings = [] # [[ticker, date], [ticker, date]]
    for ticker in tickers:
        earnings_date = get_earnings_date(ticker)
        # check whether date has passed
        if pd.to_datetime(earnings_date) < pd.Timestamp.today():
                # check whether earnings date is within 6 months
                if pd.to_datetime(earnings_date) > pd.Timestamp.today() - pd.Timedelta(days=days):
                    upcoming_earnings.append([ticker, earnings_date])
    return upcoming_earnings

def get_todays_earnings(tickers):
    upcoming_earnings = [] # [[ticker, date], [ticker, date]]
    for ticker in tickers:
        earnings_date = get_earnings_date(ticker)
        # check whether date has passed
        if pd.to_datetime(earnings_date).date() == pd.Timestamp.today().date():
                upcoming_earnings.append([ticker, earnings_date])
    return upcoming_earnings

def manage_earnings_history(_tickers):
    tickers = yq.Ticker(' '.join(_tickers))
    for ticker in _tickers:
        earnings_history = tickers.earning_history
        # take only the rows where 'ticker' is in row.name
        filtered_data = earnings_history.loc[earnings_history.index.get_level_values(0) == ticker]
        if filtered_data.empty or filtered_data.iloc[0]['quarter'] == {}:
            print(f'no earnings history found for {ticker}')
            continue
        filtered_data.index = pd.to_datetime(filtered_data['quarter'])
        if not os.path.exists(f'data/{ticker}/earnings/earnings_history.csv'):
            filtered_data.to_csv(f'data/{ticker}/earnings/earnings_history.csv')
        else:
            existing_data = pd.read_csv(f'data/{ticker}/earnings/earnings_history.csv', index_col=0)
            existing_data.index = pd.to_datetime(existing_data.index)
            existing_data = pd.concat([existing_data, filtered_data])
            existing_data = existing_data[~existing_data.index.duplicated(keep='first')]
            #drop columns quarter and period
            drop_cols = [col for col in existing_data.columns if col in ['quarter','quarter.1','quarter.2','period']]
            existing_data.drop(columns=drop_cols, inplace=True)
            existing_data.to_csv(f'data/{ticker}/earnings/earnings_history.csv')

def find_tickers_missing_earnings_history(tickers):
    missing_earnings_history = []
    for ticker in tickers:
        if not os.path.exists(f'data/{ticker}/earnings/earnings_history.csv'):
            missing_earnings_history.append(ticker)
    return missing_earnings_history

def find_tickers_missing_earnings_date(tickers):
    missing_earnings_history = []
    for ticker in tickers:
        if not os.path.exists(f'data/{ticker}/earnings/earnings_date.csv'):
            missing_earnings_history.append(ticker)
    return missing_earnings_history

def get_insider_purchase_activity():
    ticker = yq.Ticker('AAPL')
    return ticker.share_purchase_activity

def get_price_history(ticker):
    # using yfinance
    t = yf.Ticker(ticker)
    start_date = '1900-01-01' # Get full price history
    history = t.history(start=start_date)
    print(history)
    print(f'history shape: {history.shape}')
    return history

if __name__ == "__main__":
    # This update_dataset mess was my original go at keeping the data up to date
    # It needs to be refactored and cleaned up but does some useful things that we can keep around
    if 'update_dataset' in sys.argv:
        time_start = time.time()
        sectors = ['asset_management','most_actives','day_gainers','undervalued_large_caps','ms_basic_materials','ms_utilities','ms_communication_services','ms_consumer_cyclical','ms_consumer_defensive','ms_energy', 'ms_financial_services','ms_healthcare','ms_industrials','ms_real_estate','ms_technology','aerospace_defense','resorts_casinos','aggressive_small_caps','agricultural_inputs', 'airlines', 'airports_air_services','bearish_stocks_right_now','department_stores','fifty_two_wk_gainers','utilities_renewable', 'waste_management','uranium', 'utilities_diversified', 'utilities_independent_power_producers', 'utilities_regulated_electric', 'utilities_regulated_gas', 'utilities_regulated_water']
        frequency_list = ['q', 'a']
        tickers = use_screener(sectors, num_stocks=100) # 100
        tickers = list(set(tickers))
        data_dir = 'data'
        print(f'{len(tickers)} tickers')

        tickers = ['AAPL', 'AAL','A','AA'] # shortened list for testing
        tickers = tickers.sort()
        tickers_full = tickers.copy()

        no_earnings_available = ["PAM", "BCAT", "ERIC", "HDB", "MUFG", "RICFY", "DSCSY", "GFI", "STLA", "BST", "HSBC", "BIO-B", "KEP", "VLRS", "LBTYB", "HMY", "WPP", "KNF", "NTCO", "PAC", "SUZ", "ERJ", "TKC", "EDN", "CCOEY", 
    "E", "NGG", "SNN", "NVS", "ORAN", "EDVMF", "GDV", "BUR", "ANGPY", "BKKLY", "LVWR", "ARGX", "WXXWY", "DIDIY", ]
        tickers = [t for t in tickers if t not in no_earnings_available] 
        create_earnings_directory(tickers)
        missing_earnings_date = find_tickers_missing_earnings_date(tickers) 
        missing_earnings_history = find_tickers_missing_earnings_date(tickers)
        tickers = list(set(missing_earnings_history + missing_earnings_date))
        
        past_earnings = manage_next_earnings_date(tickers)

        frequency_list = ['a', 'q']
        upcoming_earnings = manage_upcoming_earnings(tickers, days=7)
        todays_earnings = get_todays_earnings(tickers)
        past_earnings = get_tickers_past_earnings(tickers, days=90)
        print(f'\nUpcoming earnings: {len(upcoming_earnings)}')
        print(upcoming_earnings)

        print(f'\nPast earnings: {len(past_earnings)}')
        print(past_earnings)
        print(f'{len(upcoming_earnings)} tickers past earnings')

        print(f'\nToday\'s earnings: {len(todays_earnings)}')
        print(todays_earnings)
        print(f'{len(todays_earnings)} tickers past earnings')
        

        will_run = True
        past_earnings = ['MS']
        t = yq.Ticker(past_earnings[0])
        print()
        print(t.calendar_events[past_earnings[0]]['earnings']['earningsDate'])
        print()
        print(t.earnings[past_earnings[0]]['earningsChart'])
        print()
        print()
        print(t.earning_history)
        print()
        print(t.cash_flow(frequency='q').tail())
        # manage_earnings_history(past_earnings)
        if not will_run: print(f'runtime: {round((time.time() - time_start)/60,1)} minutes'); exit()
        for ticker in past_earnings: # Maybe the yq.Ticker should be extracted from the function
            r = update_financials_yq(ticker, frequency_list)
            if r == -1:
                print(f'failed to update {ticker}')
            else:
                print(f'successfully updated {ticker}')
                manage_next_earnings_date([ticker])
                build_fund_data(ticker, frequency='q')

        print(f'runtime: {round((time.time() - time_start)/60,1)} minutes')
    # This function tests saving the financials for a couple of tickers
    elif 'limited_financials' in sys.argv:
        frequency_list = ['q', 'a']
        tickers = ["AAPL", "MSFT"]
        save_financials_loop(tickers, frequency_list)
    # And this function gets a list of all tickers from the database and saves their financials
    # This is not a quick operation as there is a 40 second sleep between each ticker to avoid rate limiting
    elif 'get_all_financials_data' in sys.argv:
        # We should really just ping the server for the tickers as this creates a wierd dependency on the relay server
        # Although, this does make for a tidy one-liner, and the environment already exists 
        all_tickers = api_server.get_all_tickers()
        frequency_list = ['q', 'a']
        save_financials_loop(all_tickers, frequency_list)
    elif 'insiders' in sys.argv:
        get_insider_purchase_activity()
    elif 'price_history' in sys.argv:
        get_price_history('AAPL')
    else:
        print("Usage:")
        print("python fund_data.py get_all_financials_data")
        print("\tThis will get the financial data for all tickers in the database")
        print("python fund_data.py limited_financials")
        print("\tThis will get the financial data for AAPL and MSFT as a demonstration")
        print("python fund_data.py update_dataset")
        print("\tOld and untested - This will update the dataset with the latest earnings and financials")
