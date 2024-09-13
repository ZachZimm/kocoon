# This file will eventually contain a 5-factor model implementation
# I am trying to decide how to go about creating the additional factors
# Historical data is available at mba.tuck.dartmouth.edu but it is a few months out of date
# So we could attempt to train a model to predict the values using their data plus some more easily available up to date data
# Or we could calculate the factors ourselves using the data we have available

import os
import pandas as pd
import yfinance as yf
from fredapi import Fred
import datetime
import dotenv

dotenv.load_dotenv()

class CAPMModel:
    def __init__(self, ticker, fred_api_key):
        self.ticker = ticker
        self.fred_api_key = fred_api_key
        self.fred = Fred(api_key=fred_api_key)
    
    def fetch_asset_market_data(self, ticker, market_index, start_date, end_date):
        y_ticker = yf.Ticker(ticker)
        y_market_index = yf.Ticker(market_index)
        asset_prices = y_ticker.history(start=start_date, end=end_date)['Close']
        market_prices = y_market_index.history(start=start_date, end=end_date)['Close']
        # Make the data tz-naive
        asset_prices.index = asset_prices.index.tz_localize(None)
        market_prices.index = market_prices.index.tz_localize(None)
        return asset_prices, market_prices

    def fetch_risk_free_rate(self, asset_prices, start_date, end_date):
        # Fetch the TB3MS data
        start_date = asset_prices.index.min()
        end_date = asset_prices.index.max()
        tb3ms = self.fred.get_series('TB3MS', observation_start=start_date, observation_end=end_date)
        tb3ms = tb3ms.ffill()
        # Reindex to match asset_prices dates
        tb3ms = tb3ms.reindex(asset_prices.index, method='ffill')
        # Convert annual percentage rates to daily decimal rates
        tb3ms_daily = tb3ms / 100 / 252
        return tb3ms_daily 

    def calculate_excess_returns(self, asset_prices, market_prices, risk_free_rates):
        asset_returns = asset_prices.pct_change().dropna()
        market_returns = market_prices.pct_change().dropna()
        # Align dates
        data = pd.DataFrame({
            'Asset': asset_returns,
            'Market': market_returns,
            'Risk_Free': risk_free_rates
        }).dropna()
        data['Asset_Excess'] = data['Asset'] - data['Risk_Free']
        data['Market_Excess'] = data['Market'] - data['Risk_Free']
        return data

    def calculate_beta(self, data):
        covariance = data[['Asset_Excess', 'Market_Excess']].cov().iloc[0,1]
        variance = data['Market_Excess'].var()
        beta = covariance / variance
        return beta
    
    def calculate_expected_return(self, risk_free_rate_latest, beta, market_return_avg):
        expected_return = risk_free_rate_latest + beta * (market_return_avg - risk_free_rate_latest)
        return expected_return

    def capm_model(self, ticker, market_index, start_date, end_date):
        # Fetch data
        asset_prices, market_prices = self.fetch_asset_market_data(ticker, market_index, start_date, end_date)
        risk_free_rates = self.fetch_risk_free_rate(asset_prices, start_date, end_date)
        
        # Calculate excess returns
        data = self.calculate_excess_returns(asset_prices, market_prices, risk_free_rates)
        
        # Calculate beta
        beta = self.calculate_beta(data)
        
        # Calculate average market return and latest risk-free rate
        market_return_avg = data['Market'].mean()
        risk_free_rate_latest = risk_free_rates.iloc[-1]
        
        # Calculate expected return
        expected_return = self.calculate_expected_return(risk_free_rate_latest, beta, market_return_avg)
        
        return {
            'Beta': float(beta),
            'Expected_Return': float(expected_return),
            'Risk_Free_Rate': float(risk_free_rate_latest),
            'Average_Market_Return': float(market_return_avg)
        }

if __name__ == '__main__':
    capm = CAPMModel(ticker='AAPL', fred_api_key=os.getenv('FRED_API_KEY'))
    ticker = 'AAPL'
    market_index = '^GSPC' # S&P 500
    # market_index = "^IXIC" # NASDAQ
    start_date = datetime.datetime(2017, 1, 1)
    end_date = datetime.datetime.now()

    result = capm.capm_model(ticker, market_index, start_date, end_date)
    for key, value in result.items():
        if key == 'Beta':
            print(f'{key}: {round(value, 4)}')
        else:
            print(f'{key}: {round(value * 100 * 252, 4)}%')