# This file contains an implementation of the CAPM model, the Fama-French Three-Factor model, Carhart Four-Factor model, Fam-French Five-Factor model, and Fama-French Six-Factor model

import os
import pandas as pd
import yfinance as yf
from fredapi import Fred
import datetime
import numpy as np
from statsmodels.api import OLS, add_constant
from db_interface import DBInterface
from dateutil.relativedelta import relativedelta

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
        self.all_prices = None
        self.start_date = None
        self.end_date = None
        self.market_caps = None
        self.bm_ratios = None
        self.profitability = None
        self.investment = None

    def fetch_financial_data(self, ticker, date, report_type='balance_sheet', period_type='q'):
        ticker = ticker.strip().upper()
        financial_data = self.db_interface.query(ticker=ticker, period_type=period_type, report_type=report_type)
        # Filter data up to the given date
        time_format = '%Y-%m-%d'
        financial_data = [item for item in financial_data if datetime.datetime.strptime(item['asOfDate'], time_format) <= date]
        # drop rows where periodType == 'TTM'
        financial_data = [item for item in financial_data if item['periodType'] != 'TTM']
        if financial_data:
            return financial_data[-1]  # Return the latest data before the date
        else:
            return None
    
    def fetch_asset_market_data(self, ticker, market_index, start_date, end_date):
            # if self.asset_prices is not None and self.market_prices is not None and self.start_date == start_date and self.end_date == end_date:
                # Data already fetched
                # return self.asset_prices, self.market_prices
            self.start_date = start_date
            self.end_date = end_date
            y_market_index = yf.Ticker(market_index)
            asset_prices = self.db_interface.query_stock_history(ticker=ticker, start_date=start_date, end_date=end_date)
            market_prices = y_market_index.history(start=start_date, end=end_date)['Close']
            # Make a Series of the asset prices using date and close price
            asset_prices = pd.Series([float(item['close']) for item in asset_prices], index=[pd.to_datetime(item['date']) for item in asset_prices])
            asset_prices.rename('Close', inplace=True)
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
        asset_returns = asset_prices.pct_change(fill_method=None).dropna()
        market_returns = market_prices.pct_change(fill_method=None).dropna()
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
            try:
                price_data = self.db_interface.query_stock_history(ticker=ticker, end_date=date)
                stock_price = float(price_data[-1]['close'])
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
            # self.all_prices = yf.download(tickers, start=momentum_start_date, end=end_date)['Close']
            self.all_prices = self.db_interface.query_batch_stock_history(tickers, start_date=momentum_start_date, end_date=end_date)['close']
            # Make the data tz-naive
            self.all_prices.index = self.all_prices.index.tz_localize(None)
        # Calculate prior returns for each stock at each month end
        month_ends = pd.date_range(start=start_date, end=end_date, freq='ME')
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
            winner_returns = winner_prices.pct_change(fill_method=None).mean(axis=1)
            loser_returns = loser_prices.pct_change(fill_method=None).mean(axis=1)
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
    
    def compute_profitability(self, date):
        # This function computes operating profitability for all tickers
        if self.profitability is not None:
            return self.profitability
        self.profitability = {}
        for ticker in self.db_interface.all_tickers:
            income_statement = self.fetch_financial_data(ticker, date, report_type='income')
            balance_sheet = self.fetch_financial_data(ticker, date, report_type='balance_sheet')

            if income_statement is None or balance_sheet is None:
                continue
            
            # Safely extract and convert financial data
            def get_float(value):
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return np.nan
            
            revenue = get_float(income_statement.get('TotalRevenue'))
            cogs = get_float(income_statement.get('CostOfRevenue'))
            sga = get_float(income_statement.get('SellingGeneralAndAdministration'))
            total_equity = get_float(balance_sheet.get('StockholdersEquity'))
            
            # Handle InterestExpense: if None or NaN, set to zero
            interest_expense = income_statement.get('InterestExpense')
            if interest_expense is None or pd.isna(interest_expense):
                interest_expense = 0.0
            else:
                interest_expense = get_float(interest_expense)

            # Check for missing or invalid values
            if np.isnan(revenue) or np.isnan(cogs) or np.isnan(sga) or np.isnan(interest_expense) or np.isnan(total_equity) or total_equity == 0:
                continue  # Skip if any required value is missing or invalid

            # Calculate operating profit and profitability
            operating_profit = revenue - cogs - sga - interest_expense
            profitability = operating_profit / total_equity
            self.profitability[ticker] = profitability
        print(f"Total tickers with profitability data: {len(self.profitability)}")
        return self.profitability

    def compute_investment(self, date):
        # This function computes investment (asset growth) for all tickers
        if self.investment is not None:
            return self.investment
        self.investment = {}
        for ticker in self.db_interface.all_tickers:
            balance_sheet_current = self.fetch_financial_data(ticker, date, report_type='balance_sheet')
            balance_sheet_prior = self.fetch_financial_data(ticker, date - relativedelta(years=1), report_type='balance_sheet')
            if balance_sheet_current is None or balance_sheet_prior is None:
                continue
            total_assets_current = float(balance_sheet_current.get('TotalAssets', np.nan))
            total_assets_prior = float(balance_sheet_prior.get('TotalAssets', np.nan))
            if np.isnan(total_assets_current) or np.isnan(total_assets_prior) or total_assets_prior == 0:
                continue
            investment = (total_assets_current - total_assets_prior) / total_assets_prior
            self.investment[ticker] = investment
        return self.investment

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

    def form_profitability_portfolios(self, market_caps, profitability):
        df = pd.DataFrame({
            'Ticker': list(market_caps.keys()),
            'Market_Cap': list(market_caps.values()),
            'Profitability': [profitability.get(ticker, np.nan) for ticker in market_caps.keys()]
        })
        df.dropna(inplace=True)
        # Size breakpoints
        size_median = df['Market_Cap'].median()
        # Profitability breakpoints
        prof30 = df['Profitability'].quantile(0.3)
        prof70 = df['Profitability'].quantile(0.7)
        # Assign Size
        df['Size'] = np.where(df['Market_Cap'] <= size_median, 'Small', 'Big')
        # Assign Profitability
        conditions = [
            (df['Profitability'] <= prof30),
            (df['Profitability'] > prof30) & (df['Profitability'] <= prof70),
            (df['Profitability'] > prof70)
        ]
        choices = ['Weak', 'Neutral', 'Robust']
        df['Profitability_Group'] = np.select(conditions, choices, default='Unknown')
        # Create portfolio labels
        df['Portfolio'] = df['Size'] + '/' + df['Profitability_Group']

        # Print portfolio counts
        print("\nProfitability Portfolios Formed:")
    
        return df

    def form_investment_portfolios(self, market_caps, investment):
        df = pd.DataFrame({
            'Ticker': list(market_caps.keys()),
            'Market_Cap': list(market_caps.values()),
            'Investment': [investment.get(ticker, np.nan) for ticker in market_caps.keys()]
        })
        df.dropna(inplace=True)
        # Size breakpoints
        size_median = df['Market_Cap'].median()
        # Investment breakpoints
        inv30 = df['Investment'].quantile(0.3)
        inv70 = df['Investment'].quantile(0.7)
        # Assign Size
        df['Size'] = np.where(df['Market_Cap'] <= size_median, 'Small', 'Big')
        # Assign Investment
        conditions = [
            (df['Investment'] <= inv30),
            (df['Investment'] > inv30) & (df['Investment'] <= inv70),
            (df['Investment'] > inv70)
        ]
        choices = ['Conservative', 'Neutral', 'Aggressive']
        df['Investment_Group'] = np.select(conditions, choices, default='Unknown')
        # Create portfolio labels
        df['Portfolio'] = df['Size'] + '/' + df['Investment_Group']
        return df
    
    def calculate_portfolio_returns(self, portfolios, start_date, end_date):
        # Map portfolios to tickers
        print(f"Calculating portfolio returns for {len(portfolios)} portfolios...")
        portfolio_groups = portfolios.groupby('Portfolio')['Ticker'].apply(list)
        portfolio_returns = {}
        for portfolio, tickers in portfolio_groups.items():
            try:
                # Fetch adjusted close prices for tickers
                prices = self.db_interface.query_batch_stock_history(tickers, start_date=start_date, end_date=end_date)['close']
                # Make the data tz-naive
                prices.index = prices.index.tz_localize(None)
                # Handle single ticker case
                if isinstance(prices, pd.Series):
                    returns = prices.pct_change(fill_method=None)
                else:
                    # Calculate equal-weighted returns
                    returns = prices.pct_change(fill_method=None).mean(axis=1)
                portfolio_returns[portfolio] = returns
            except Exception as e:
                print(f"Error fetching prices for {portfolio} portfolio:\n{e}")
                continue
        print(f"Portfolio returns calculated for {len(portfolio_returns)} portfolios.")
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
    
    def compute_rmw(self, portfolio_returns):
        # Compute RMW (Robust Minus Weak) factor
        robust_ports = ['Small/Robust', 'Big/Robust']
        weak_ports = ['Small/Weak', 'Big/Weak']
        robust_returns = pd.concat([portfolio_returns[port] for port in robust_ports if port in portfolio_returns], axis=1).mean(axis=1)
        weak_returns = pd.concat([portfolio_returns[port] for port in weak_ports if port in portfolio_returns], axis=1).mean(axis=1)
        rmw = robust_returns - weak_returns
        return rmw

    def compute_cma(self, portfolio_returns):
        # Compute CMA (Conservative Minus Aggressive) factor
        conservative_ports = ['Small/Conservative', 'Big/Conservative']
        aggressive_ports = ['Small/Aggressive', 'Big/Aggressive']
        conservative_returns = pd.concat([portfolio_returns[port] for port in conservative_ports if port in portfolio_returns], axis=1).mean(axis=1)
        aggressive_returns = pd.concat([portfolio_returns[port] for port in aggressive_ports if port in portfolio_returns], axis=1).mean(axis=1)
        cma = conservative_returns - aggressive_returns
        return cma
    
    def calculate_regression(self, data, factors=['Market_Excess', 'SMB', 'HML']):
        y = data['Asset_Excess']
        X = data[factors]
        X = add_constant(X)
        # The OLS model is used to perform the regression
        # The model is of the form: y = b0 + b1*X1 + b2*X2 + b3*X3
        model = OLS(y, X).fit()
        return model
    
    def calculate_expected_return(self, risk_free_rate_latest, betas, factor_means):
        if isinstance(factor_means, np.float64):
            expected_return = risk_free_rate_latest + betas * factor_means
        else:
            expected_return = risk_free_rate_latest
            for factor in factor_means.index:
                expected_return += betas[factor] * factor_means[factor]
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
            'ticker': ticker,
            'model_name': 'CAPM',
            'start_date': start_date,
            'end_date': end_date,
            'beta': float(beta),
            'expected_return': float(expected_return),
            'risk_free_rate': float(risk_free_rate_latest),
            'average_market_return': float(market_return_avg),
        }

    def three_factor_model(self, ticker, market_index, start_date, end_date):
        # Fetch asset and market data
        asset_prices, market_prices = self.fetch_asset_market_data(ticker, market_index, start_date, end_date)
        asset_returns = asset_prices.pct_change(fill_method=None)
        market_returns = market_prices.pct_change(fill_method=None)
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
            'ticker': ticker,
            'model_name': 'Fama-French Three-Factor',
            'start_date': start_date,
            'end_date': end_date,
            'betas': betas,
            'expected_return': float(expected_return),
            'risk_free_rate': float(risk_free_rates.iloc[-1]),
            'market_index': market_index,
            'average_market_return': float(data['Market'].mean()),
            'factor_means': factor_means,
            'p_values': model.pvalues
        }
    
    def four_factor_model(self, ticker, market_index, start_date, end_date):
        # Fetch asset and market data
        asset_prices, market_prices = self.fetch_asset_market_data(ticker, market_index, start_date, end_date)
        asset_returns = asset_prices.pct_change(fill_method=None)
        market_returns = market_prices.pct_change(fill_method=None)
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
            'ticker': ticker,
            'model_name': 'Carhart Four-Factor',
            'start_date': start_date,
            'end_date': end_date,
            'betas': betas,
            'expected_return': float(expected_return),
            'risk_free_rate': float(risk_free_rates.iloc[-1]),
            'market_index': market_index,
            'average_market_return': float(data['Market'].mean()),
            'factor_means': factor_means,
            'p_values': model.pvalues
        }
    
    def five_factor_model(self, ticker, market_index, start_date, end_date):
        # Fetch asset and market data
        asset_prices, market_prices = self.fetch_asset_market_data(ticker, market_index, start_date, end_date)
        asset_returns = asset_prices.pct_change(fill_method=None)
        market_returns = market_prices.pct_change(fill_method=None)
        # Fetch risk-free rate
        risk_free_rates = self.fetch_risk_free_rate(asset_prices, start_date, end_date)
        # Compute market caps, B/M ratios, profitability, and investment at the formation date
        formation_date = datetime.datetime(start_date.year, 6, 30)
        market_caps, bm_ratios = self.compute_market_cap_bm(formation_date)
        profitability = self.compute_profitability(formation_date)
        investment = self.compute_investment(formation_date)
        # Form portfolios
        portfolios_sv = self.form_portfolios(market_caps, bm_ratios)
        portfolios_sp = self.form_profitability_portfolios(market_caps, profitability)
        portfolios_si = self.form_investment_portfolios(market_caps, investment)
        # Merge portfolios
        portfolios_all = pd.concat([portfolios_sv, portfolios_sp, portfolios_si])
        # Calculate portfolio returns
        portfolio_returns = self.calculate_portfolio_returns(portfolios_all, start_date, end_date)
        # Compute SMB and HML factors
        smb, hml = self.compute_smb_hml(portfolio_returns)
        self.smb = smb
        self.hml = hml
        # Compute RMW and CMA factors
        rmw = self.compute_rmw(portfolio_returns)
        cma = self.compute_cma(portfolio_returns)
        self.rmw = rmw
        self.cma = cma
        # Align data
        data = pd.DataFrame({
            'Asset': asset_returns,
            'Market': market_returns,
            'Risk_Free': risk_free_rates,
            'SMB': smb,
            'HML': hml,
            'RMW': rmw,
            'CMA': cma
        })
        data['Asset_Excess'] = data['Asset'] - data['Risk_Free']
        data['Market_Excess'] = data['Market'] - data['Risk_Free']
        data.dropna(inplace=True)
        # Perform regression
        model = self.calculate_regression(data, factors=['Market_Excess', 'SMB', 'HML', 'RMW', 'CMA'])
        betas = model.params
        # Calculate expected return
        factor_means = data[['Market_Excess', 'SMB', 'HML', 'RMW', 'CMA']].mean()
        expected_return = self.calculate_expected_return(risk_free_rates.iloc[-1], betas, factor_means)
        return {
            'ticker': ticker,
            'model_name': 'Fama-French Five-Factor',
            'start_date': start_date,
            'end_date': end_date,
            'betas': betas,
            'expected_return': float(expected_return),
            'risk_free_rate': float(risk_free_rates.iloc[-1]),
            'market_index': market_index,
            'average_market_return': float(data['Market'].mean()),
            'factor_means': factor_means,
            'p_values': model.pvalues
        }

    def six_factor_model(self, ticker, market_index, start_date, end_date):
        # Fetch asset and market data
        asset_prices, market_prices = self.fetch_asset_market_data(ticker, market_index, start_date, end_date)
        asset_returns = asset_prices.pct_change(fill_method=None)
        market_returns = market_prices.pct_change(fill_method=None)
        # Fetch risk-free rate
        risk_free_rates = self.fetch_risk_free_rate(asset_prices, start_date, end_date)
        # Compute factors if not already computed
        if self.smb is None or self.hml is None or self.rmw is None or self.cma is None:
            # Compute market caps, B/M ratios, profitability, and investment at the formation date
            formation_date = datetime.datetime(start_date.year, 6, 30)
            market_caps, bm_ratios = self.compute_market_cap_bm(formation_date)
            profitability = self.compute_profitability(formation_date)
            investment = self.compute_investment(formation_date)
            # Form portfolios
            portfolios_sv = self.form_portfolios(market_caps, bm_ratios)
            portfolios_sp = self.form_profitability_portfolios(market_caps, profitability)
            portfolios_si = self.form_investment_portfolios(market_caps, investment)
            # Merge portfolios
            portfolios_all = pd.concat([portfolios_sv, portfolios_sp, portfolios_si]).drop_duplicates(subset='Ticker')
            # Calculate portfolio returns
            portfolio_returns = self.calculate_portfolio_returns(portfolios_all, start_date, end_date)
            # Compute SMB and HML factors
            smb, hml = self.compute_smb_hml(portfolio_returns)
            self.smb = smb
            self.hml = hml
            # Compute RMW and CMA factors
            rmw = self.compute_rmw(portfolio_returns)
            cma = self.compute_cma(portfolio_returns)
            self.rmw = rmw
            self.cma = cma
        else:
            smb = self.smb
            hml = self.hml
            rmw = self.rmw
            cma = self.cma
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
            'RMW': rmw,
            'CMA': cma,
            'MOM': momentum
        })
        data['Asset_Excess'] = data['Asset'] - data['Risk_Free']
        data['Market_Excess'] = data['Market'] - data['Risk_Free']
        data.dropna(inplace=True)
        if data.empty:
            print("No data available after aligning for regression.")
            return None
        # Perform regression
        model = self.calculate_regression(data, factors=['Market_Excess', 'SMB', 'HML', 'RMW', 'CMA', 'MOM'])
        betas = model.params
        # Calculate expected return
        factor_means = data[['Market_Excess', 'SMB', 'HML', 'RMW', 'CMA', 'MOM']].mean()
        expected_return = self.calculate_expected_return(risk_free_rates.iloc[-1], betas, factor_means)
        return {
            'ticker': ticker,
            'model_name': 'Fama-French Six-Factor',
            'start_date': start_date,
            'end_date': end_date,
            'betas': betas,
            'expected_return': float(expected_return),
            'risk_free_rate': float(risk_free_rates.iloc[-1]),
            'market_index': market_index,
            'average_market_return': float(data['Market'].mean()),
            'factor_means': factor_means,
            'p_values': model.pvalues
        }
    
    def multifactor_results_to_string(self, results, include_factors=False):
        string = f"{len(list(results['betas'].items()))-1}-Factor Model Results for {results['ticker']}:\n"
        string += f"Expected Return: {round(results['expected_return'] * 100 * 252, 4)}%\n"
        string += f"Average Market Return ({results['market_index']}): {round(results['average_market_return'] * 100 * 252, 4)}%\n"
        string += f"Risk-Free Rate: {round(results['risk_free_rate'] * 100 * 252, 4)}%\n"

        for factor, value in results.items():
            if factor == 'betas':
                string += "\nBetas:\n"
                for factor, beta in value.items():
                    if factor != 'const':
                        string += f"  {factor}: {round(beta, 4)}, p: {round(results['p_values'][factor],12)}\n"
            elif factor == 'factor_means' and include_factors:
                string += "\nFactor Means (Annualized):\n"
                for factor, mean in value.items():
                    string += f"  {factor}: {round(mean * 100 * 252, 4)}%\n"
            else:
                # string += f"{factor}: {value}\n"
                pass
        return string

if __name__ == '__main__':
    db_interface = DBInterface()
    ticker = input("Enter a ticker: ")
    ticker2 = input("Enter a second ticker: ")
    capm = CAPMModel(ticker=ticker, fred_api_key=os.getenv('FRED_API_KEY'), db_interface=db_interface)
    market_index = '^GSPC' # S&P 500
    # market_index = "^IXIC" # NASDAQ
    # start_date = datetime.datetime(2014, 1, 1)
    end_date = datetime.datetime.now() - datetime.timedelta(days=1)
    _days = 10 * 365
    start_date = end_date - datetime.timedelta(days=_days)
    
    import time
    start = time.time()
    # result_capm = capm.capm_model(ticker, market_index, start_date, end_date)
    # result_tf = capm.three_factor_model(ticker, market_index, start_date, end_date)
    # result_four_factor = capm.four_factor_model(ticker, market_index, start_date, end_date)
    result_five_factor = capm.five_factor_model(ticker, market_index, start_date, end_date)
    # result_six_factor = capm.six_factor_model(ticker, market_index, start_date, end_date)
    result_1_str = capm.multifactor_results_to_string(result_five_factor, include_factors=False)
    # result_1_str_2 = capm.multifactor_results_to_string(result_six_factor, include_factors=False)
    first_finish = time.time()

    # result_five_factor_2 = capm.five_factor_model(ticker2, market_index, start_date, end_date)
    # result_six_factor_2 = capm.six_factor_model(ticker2, market_index, start_date, end_date)
    # result_2_str = capm.multifactor_results_to_string(result_five_factor_2, include_factors=False)
    # result_2_str_2 = capm.multifactor_results_to_string(result_six_factor_2, include_factors=False)
    # second_finish = time.time()

    print("\n")
    print(result_1_str + "\n")
    # print(result_1_str_2 + "\n")
    # print(result_2_str + "\n")
    # print(result_2_str_2)
    print(f"Time taken for first ticker: {round(first_finish - start, 2)} seconds")
    # print(f"Time taken for second ticker: {round(second_finish - first_finish, 2)} seconds")