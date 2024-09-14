import os
import pandas as pd
import yfinance as yf
from fredapi import Fred
import datetime
import numpy as np
from statsmodels.api import OLS, add_constant
from backend.db_interface import DBInterface

class CAPMModel:
    def __init__(self, ticker, fred_api_key, db_interface: DBInterface):
        self.ticker = ticker
        self.db_interface = db_interface
        self.fred_api_key = fred_api_key
        self.fred = Fred(api_key=fred_api_key)
        self.all_tickers = self.get_all_tickers()

    def fetch_financial_data(self, ticker, date, report_type='balance_sheet', period_type='q'):
        ticker = ticker.strip().upper()
        print(f"Fetching financial data for {ticker}")
        financial_data = self.db_interface.query(ticker=ticker, period_type=period_type, report_type=report_type)
        # Filter data up to the given date
        time_format = '%Y-%m-%d'
        financial_data = [item for item in financial_data if datetime.datetime.strptime(item['asOfDate'], time_format) <= date]
        if financial_data:
            return financial_data[0]  # Return the latest data before the date
        else:
            return None
    
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

    def compute_market_cap_bm(self, date):
        market_caps = {}
        bm_ratios = {}
        for ticker in self.all_tickers:
            financial_data = self.fetch_financial_data(ticker, date)
            if financial_data is None:
                continue
            shares_outstanding = float(financial_data.get('ShareIssued'))
            total_equity = float(financial_data.get('StockholdersEquity'))
            if shares_outstanding is None or total_equity is None:
                print(f"Missing data for {ticker} in database")
                print("Or field names are incorrect")
                continue
            # Get stock price as of date
            y_ticker = yf.Ticker(ticker)
            try:
                price_data = y_ticker.history(start=date - datetime.timedelta(days=5), end=date + datetime.timedelta(days=1))
                stock_price = float(price_data['Close'].iloc[-1])
            except Exception as e:
                print(f"Error fetching stock price for {ticker}")
                print(e)
                continue
            if stock_price is None or shares_outstanding == 0:
                print(f"Error fetching stock price for {ticker}")
                continue
            # Calculate market cap and B/M ratio
            market_cap = shares_outstanding * stock_price
            book_value_per_share = total_equity / shares_outstanding
            bm_ratio = book_value_per_share / stock_price
            market_caps[ticker] = market_cap
            bm_ratios[ticker] = bm_ratio
        return market_caps, bm_ratios

    def form_portfolios(self, market_caps, bm_ratios):
        df = pd.DataFrame({
            'Ticker': list(market_caps.keys()),
            'Market_Cap': list(market_caps.values()),
            'BM_Ratio': [bm_ratios[ticker] for ticker in market_caps.keys()]
        })
        # Remove missing values
        df.dropna(inplace=True)
        # Size breakpoints
        size_median = df['Market_Cap'].median()
        # Value breakpoints
        bm30 = df['BM_Ratio'].quantile(0.3)
        bm70 = df['BM_Ratio'].quantile(0.7)
        # Assign Size
        df['Size'] = np.where(df['Market_Cap'] <= size_median, 'Small', 'Big')
        # Assign Value
        conditions = [
            (df['BM_Ratio'] <= bm30),
            (df['BM_Ratio'] > bm30) & (df['BM_Ratio'] <= bm70),
            (df['BM_Ratio'] > bm70)
        ]
        choices = ['Low', 'Medium', 'High']
        df['Value'] = np.select(conditions, choices, default='Unknown')
        # Create portfolio labels
        df['Portfolio'] = df['Size'] + '/' + df['Value']
        return df
    
    def calculate_portfolio_returns(self, portfolios, start_date, end_date):
        # Map portfolios to tickers
        portfolio_groups = portfolios.groupby('Portfolio')['Ticker'].apply(list)
        portfolio_returns = {}
        for portfolio, tickers in portfolio_groups.items():
            try:
                # Fetch adjusted close prices for tickers
                prices = yf.download(tickers, start=start_date, end=end_date)['Close']
                # Make the data tz-naive
                prices.index = prices.index.tz_localize(None)
                # Handle single ticker case
                if isinstance(prices, pd.Series):
                    returns = prices.pct_change()
                else:
                    # Calculate equal-weighted returns
                    returns = prices.pct_change().mean(axis=1)
                portfolio_returns[portfolio] = returns
            except Exception as e:
                continue
        return portfolio_returns
    
    def compute_smb_hml(self, portfolio_returns):
        # SMB calculation
        small_ports = ['Small/Low', 'Small/Medium', 'Small/High']
        big_ports = ['Big/Low', 'Big/Medium', 'Big/High']
        small_returns = pd.concat([portfolio_returns[port] for port in small_ports if port in portfolio_returns], axis=1).mean(axis=1)
        big_returns = pd.concat([portfolio_returns[port] for port in big_ports if port in portfolio_returns], axis=1).mean(axis=1)
        smb = small_returns - big_returns
        # HML calculation
        value_ports = ['Small/High', 'Big/High']
        growth_ports = ['Small/Low', 'Big/Low']
        value_returns = pd.concat([portfolio_returns[port] for port in value_ports if port in portfolio_returns], axis=1).mean(axis=1)
        growth_returns = pd.concat([portfolio_returns[port] for port in growth_ports if port in portfolio_returns], axis=1).mean(axis=1)
        hml = value_returns - growth_returns
        return smb, hml
    
    def calculate_regression(self, data):
        y = data['Asset_Excess']
        X = data[['Market_Excess', 'SMB', 'HML']]
        X = add_constant(X)
        model = OLS(y, X).fit()
        return model
    
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

    def three_factor_model(self, ticker, market_index, start_date, end_date):
        # Fetch asset and market data
        asset_prices, market_prices = self.fetch_asset_market_data(ticker, market_index, start_date, end_date)
        asset_returns = asset_prices.pct_change()
        market_returns = market_prices.pct_change()
        # Fetch risk-free rate
        risk_free_rates = self.fetch_risk_free_rate(asset_prices, start_date, end_date)
        # Compute market caps and B/M ratios at the formation date
        formation_date = datetime.datetime(start_date.year, 6, 30)
        market_caps, bm_ratios = self.compute_market_cap_bm(formation_date)
        # Form portfolios
        portfolios = self.form_portfolios(market_caps, bm_ratios)
        # Calculate portfolio returns
        portfolio_returns = self.calculate_portfolio_returns(portfolios, start_date, end_date)
        # Compute SMB and HML factors
        smb, hml = self.compute_smb_hml(portfolio_returns)
        # Align data
        data = pd.DataFrame({
            'Asset': asset_returns,
            'Market': market_returns,
            'Risk_Free': risk_free_rates,
            'SMB': smb,
            'HML': hml
        })
        data['Asset_Excess'] = data['Asset'] - data['Risk_Free']
        data['Market_Excess'] = data['Market'] - data['Risk_Free']
        data.dropna(inplace=True)
        # Perform regression
        model = self.calculate_regression(data)
        betas = model.params
        # Calculate expected return
        factor_means = data[['Market_Excess', 'SMB', 'HML']].mean()
        expected_return = risk_free_rates.iloc[-1] + betas['Market_Excess'] * factor_means['Market_Excess'] + \
                          betas['SMB'] * factor_means['SMB'] + betas['HML'] * factor_means['HML']
        return {
            'Betas': betas,
            'Expected_Return': float(expected_return),
            'Risk_Free_Rate': float(risk_free_rates.iloc[-1]),
            'Factor_Means': factor_means
        }

if __name__ == '__main__':
    db_interface = DBInterface()
    ticker = 'AAPL'
    capm = CAPMModel(ticker=ticker, fred_api_key=os.getenv('FRED_API_KEY'), db_interface=db_interface)
    market_index = '^GSPC' # S&P 500
    # market_index = "^IXIC" # NASDAQ
    start_date = datetime.datetime(2017, 1, 1)
    end_date = datetime.datetime.now()
    
    result = capm.three_factor_model(ticker, market_index, start_date, end_date)
    print(f"Three-Factor Model Results for {ticker}:")
    # Print the results
    print(f"Expected Return: {round(result['Expected_Return'] * 100 * 252, 4)}%")
    print(f"Risk-Free Rate: {round(result['Risk_Free_Rate'] * 100 * 252, 4)}%")
    print("\nBetas:")
    for factor, beta in result['Betas'].items():
        if factor != 'const':
            print(f"  {factor}: {round(beta, 4)}")
    print("\nFactor Means (Annualized):")
    for factor, mean in result['Factor_Means'].items():
        print(f"  {factor}: {round(mean * 100 * 252, 4)}%")
    
    print(f"\n\nCAPM Model Results for {ticker}:")
    result_capm = capm.capm_model(ticker, market_index, start_date, end_date)
    for key, value in result_capm.items():
        if key == 'Beta':
            print(f'{key}: {round(value, 4)}')
        else:
            print(f'{key}: {round(value * 100 * 252, 4)}%')