# This file contains an implementation of the CAPM model, the Fama-French Three-Factor model, and the Carhart Four-Factor model

import os
import pandas as pd
import yfinance as yf
from fredapi import Fred
import datetime
import numpy as np
from statsmodels.api import OLS, add_constant
from db_interface import DBInterface

class CAPMModel:
    def __init__(self, ticker, fred_api_key, db_interface: DBInterface):
        self.ticker = ticker
        self.db_interface = db_interface
        self.fred_api_key = fred_api_key
        self.fred = Fred(api_key=fred_api_key)
        # Initialize data storage
        self.asset_prices = None
        self.market_prices = None
        self.risk_free_rates = None
        self.asset_returns = None
        self.market_returns = None
        self.excess_returns_data = None
        self.portfolios = None
        self.portfolio_returns = None
        self.smb = None
        self.hml = None
        self.momentum = None
        self.all_prices = None  # To store historical prices for all tickers
        self.start_date = None
        self.end_date = None
        self.market_caps = None
        self.bm_ratios = None

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
            if self.asset_prices is not None and self.market_prices is not None and self.start_date == start_date and self.end_date == end_date:
                # Data already fetched
                return self.asset_prices, self.market_prices
            self.start_date = start_date
            self.end_date = end_date
            y_ticker = yf.Ticker(ticker)
            y_market_index = yf.Ticker(market_index)
            asset_prices = y_ticker.history(start=start_date, end=end_date)['Close']
            market_prices = y_market_index.history(start=start_date, end=end_date)['Close']
            # Make the data tz-naive
            asset_prices.index = asset_prices.index.tz_localize(None)
            market_prices.index = market_prices.index.tz_localize(None)
            self.asset_prices = asset_prices
            self.market_prices = market_prices
            return asset_prices, market_prices

    def fetch_risk_free_rate(self, asset_prices, start_date, end_date):
        if self.risk_free_rates is not None:
            return self.risk_free_rates
        # Fetch the TB3MS data
        start_date = asset_prices.index.min()
        end_date = asset_prices.index.max()
        tb3ms = self.fred.get_series('TB3MS', observation_start=start_date, observation_end=end_date)
        tb3ms = tb3ms.ffill()
        # Reindex to match asset_prices dates
        tb3ms = tb3ms.reindex(asset_prices.index, method='ffill')
        # Convert annual percentage rates to daily decimal rates
        tb3ms_daily = tb3ms / 100 / 252
        self.risk_free_rates = tb3ms_daily
        return tb3ms_daily

    def calculate_excess_returns(self, asset_prices, market_prices, risk_free_rates):
        # This function calculates excess returns for the asset and market
        if self.excess_returns_data is not None:
            return self.excess_returns_data
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
        self.asset_returns = asset_returns
        self.market_returns = market_returns
        self.excess_returns_data = data
        return data

    def calculate_beta(self, data):
        covariance = data[['Asset_Excess', 'Market_Excess']].cov().iloc[0,1]
        variance = data['Market_Excess'].var()
        beta = covariance / variance
        return beta

    def compute_market_cap_bm(self, date):
        # This function computes market capitalization and B/M (book to market) ratio for all tickers
        if self.market_caps is not None and self.bm_ratios is not None:
            return self.market_caps, self.bm_ratios
        self.market_caps = {}
        self.bm_ratios = {}
        for ticker in self.db_interface.all_tickers:
            financial_data = self.fetch_financial_data(ticker, date)
            if financial_data is None:
                continue
            shares_outstanding = float(financial_data.get('ShareIssued'))
            total_equity = float(financial_data.get('StockholdersEquity'))
            if shares_outstanding is None or total_equity is None:
                continue
            # Get stock price as of date
            y_ticker = yf.Ticker(ticker)
            try:
                price_data = y_ticker.history(start=date - datetime.timedelta(days=5), end=date + datetime.timedelta(days=1))
                stock_price = float(price_data['Close'].iloc[-1])
            except Exception:
                continue
            if stock_price is None or shares_outstanding == 0:
                continue # Skip if no price or shares outstanding
            # Calculate market cap and B/M ratio
            market_cap = shares_outstanding * stock_price
            book_value_per_share = total_equity / shares_outstanding
            bm_ratio = book_value_per_share / stock_price
            self.market_caps[ticker] = market_cap
            self.bm_ratios[ticker] = bm_ratio
        return self.market_caps, self.bm_ratios
    
    def compute_momentum_factor(self, start_date, end_date):
        # This function computes the momentum factor by calculating prior 11-month returns and forming Winner and Loser portfolios
        # Returns the difference in returns between the Winner and Loser portfolios as the momentum factor
            # These returns are assumed to be the market returns for 'having momentum' over 'not having momentum'
        if self.momentum is not None:
            return self.momentum
        # Determine the date range needed for momentum calculation
        momentum_start_date = start_date - datetime.timedelta(days=365)
        if self.all_prices is None:
            print("Fetching historical prices for all tickers for momentum calculation...")
            tickers = self.db_interface.all_tickers
            self.all_prices = yf.download(tickers, start=momentum_start_date, end=end_date)['Close']
            # Make the data tz-naive
            self.all_prices.index = self.all_prices.index.tz_localize(None)
        # Calculate prior returns for each stock at each month end
        month_ends = pd.date_range(start=start_date, end=end_date, freq='M')
        momentum_returns = []
        for formation_date in month_ends:
            # Check if we have enough data
            if formation_date - pd.DateOffset(months=12) < self.all_prices.index.min():
                continue
            # Calculate prior 11-month returns (t-12 to t-1)
            start_period = (formation_date - pd.DateOffset(months=12)).strftime('%Y-%m-%d')
            end_period = (formation_date - pd.DateOffset(months=1)).strftime('%Y-%m-%d')
            prior_prices = self.all_prices.loc[start_period:end_period]
            if prior_prices.empty:
                continue
            prior_returns = (prior_prices.iloc[-1] / prior_prices.iloc[0] - 1).dropna()
            # Rank stocks based on prior returns
            num_stocks = len(prior_returns)
            if num_stocks < 10:
                continue
            top_cutoff = prior_returns.quantile(0.7)
            bottom_cutoff = prior_returns.quantile(0.3)
            winners = prior_returns[prior_returns >= top_cutoff].index.tolist()
            losers = prior_returns[prior_returns <= bottom_cutoff].index.tolist()
            # Calculate returns of Winner and Loser portfolios over next month
            start_next_month = formation_date.strftime('%Y-%m-%d')
            end_next_month = (formation_date + pd.DateOffset(months=1) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')  # Adjust end date
            winner_prices = self.all_prices.loc[start_next_month:end_next_month, winners]
            loser_prices = self.all_prices.loc[start_next_month:end_next_month, losers]
            if winner_prices.empty or loser_prices.empty:
                continue
            # Calculate portfolio returns
            winner_returns = winner_prices.pct_change().mean(axis=1)
            loser_returns = loser_prices.pct_change().mean(axis=1)
            # Calculate momentum factor as difference
            mom_returns = winner_returns - loser_returns
            momentum_returns.append(mom_returns)
        if momentum_returns:
            # Concatenate momentum returns
            momentum = pd.concat(momentum_returns)
            # Handle duplicate indices by averaging
            momentum = momentum.groupby(momentum.index).mean()
            self.momentum = momentum
            return momentum
        else:
            print("Unable to compute momentum factor due to insufficient data.")
            self.momentum = None
            return None

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
        # This function computes the SMB (small minus big) and HML (High [B/M] minus low [B/M]) factors
        # HML is a measure of value, while SMB is a measure of size
        # This is done by forming portfolios based on size and value, and calculating the returns of these portfolios
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
        # The OLS model is used to perform the regression
        # The model is of the form: y = b0 + b1*X1 + b2*X2 + b3*X3
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
    
    def four_factor_model(self, ticker, market_index, start_date, end_date):
        # Fetch asset and market data
        asset_prices, market_prices = self.fetch_asset_market_data(ticker, market_index, start_date, end_date)
        asset_returns = asset_prices.pct_change()
        market_returns = market_prices.pct_change()
        # Fetch risk-free rate
        risk_free_rates = self.fetch_risk_free_rate(asset_prices, start_date, end_date)
        # Compute SMB and HML if not already computed
        if self.smb is None or self.hml is None:
            # Compute market caps and B/M ratios at the formation date
            formation_date = datetime.datetime(start_date.year, 6, 30)
            market_caps, bm_ratios = self.compute_market_cap_bm(formation_date)
            # Form portfolios
            portfolios = self.form_portfolios(market_caps, bm_ratios)
            # Calculate portfolio returns
            portfolio_returns = self.calculate_portfolio_returns(portfolios, start_date, end_date)
            # Compute SMB and HML factors
            smb, hml = self.compute_smb_hml(portfolio_returns)
            self.smb = smb
            self.hml = hml
        else:
            smb = self.smb
            hml = self.hml
        # Compute momentum factor
        momentum = self.compute_momentum_factor(start_date, end_date)
        if momentum is None:
            print("Momentum factor could not be computed.")
            return None
        # Align data
        data = pd.DataFrame({
            'Asset': asset_returns,
            'Market': market_returns,
            'Risk_Free': risk_free_rates,
            'SMB': smb,
            'HML': hml,
            'MOM': momentum
        })
        data['Asset_Excess'] = data['Asset'] - data['Risk_Free']
        data['Market_Excess'] = data['Market'] - data['Risk_Free']
        data.dropna(inplace=True)
        if data.empty:
            print("No data available after aligning for regression.")
            return None
        # Perform regression
        y = data['Asset_Excess']
        X = data[['Market_Excess', 'SMB', 'HML', 'MOM']]
        X = add_constant(X)
        model = OLS(y, X).fit()
        betas = model.params
        # Calculate expected return
        factor_means = data[['Market_Excess', 'SMB', 'HML', 'MOM']].mean()
        expected_return = risk_free_rates.iloc[-1] + \
                          betas['Market_Excess'] * factor_means['Market_Excess'] + \
                          betas['SMB'] * factor_means['SMB'] + \
                          betas['HML'] * factor_means['HML'] + \
                          betas['MOM'] * factor_means['MOM']
        return {
            'Betas': betas,
            'Expected_Return': float(expected_return),
            'Risk_Free_Rate': float(risk_free_rates.iloc[-1]),
            'Factor_Means': factor_means
        }

if __name__ == '__main__':
    db_interface = DBInterface()
    ticker = input("Enter a ticker: ")
    capm = CAPMModel(ticker=ticker, fred_api_key=os.getenv('FRED_API_KEY'), db_interface=db_interface)
    market_index = '^GSPC' # S&P 500
    # market_index = "^IXIC" # NASDAQ
    start_date = datetime.datetime(2018, 1, 1)
    end_date = datetime.datetime.now()
    
    result_capm = capm.capm_model(ticker, market_index, start_date, end_date)
    result_tf = capm.three_factor_model(ticker, market_index, start_date, end_date)
    result_four_factor = capm.four_factor_model(ticker, market_index, start_date, end_date)
    print("\n\n")
    print(f"Four-Factor Model Results for {ticker}:")
    print(f"Expected Return: {round(result_four_factor['Expected_Return'] * 100 * 252, 4)}%")
    print(f"Average Market Return ({market_index}): {round(result_capm['Average_Market_Return'] * 100 * 252, 4)}%")
    print(f"Risk-Free Rate: {round(result_four_factor['Risk_Free_Rate'] * 100 * 252, 4)}%")
    print("\nBetas:")
    for factor, beta in result_four_factor['Betas'].items():
        if factor != 'const':
            print(f"  {factor}: {round(beta, 4)}")
    print("\nFactor Means (Annualized):")
    for factor, mean in result_four_factor['Factor_Means'].items():
        print(f"  {factor}: {round(mean * 100 * 252, 4)}%")

    print(f"\n\nThree-Factor Model Results for {ticker}:")
    print(f"Expected Return: {round(result_tf['Expected_Return'] * 100 * 252, 4)}%")
    print(f"Average Market Return ({market_index}): {round(result_capm['Average_Market_Return'] * 100 * 252, 4)}%")
    print(f"Risk-Free Rate: {round(result_tf['Risk_Free_Rate'] * 100 * 252, 4)}%")
    print("\nBetas:")
    for factor, beta in result_tf['Betas'].items():
        if factor != 'const':
            print(f"  {factor}: {round(beta, 4)}")
    print("\nFactor Means (Annualized):")
    for factor, mean in result_tf['Factor_Means'].items():
        print(f"  {factor}: {round(mean * 100 * 252, 4)}%")
    
    print(f"\n\nCAPM Model Results for {ticker}:")
    for key, value in result_capm.items():
        if key == 'Beta':
            print(f'{key}: {round(value, 4)}')
        else:
            print(f'{key}: {round(value * 100 * 252, 4)}%')
    print("\n")