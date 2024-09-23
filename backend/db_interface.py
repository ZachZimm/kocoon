import os
import json
import pandas as pd
import psycopg2
from psycopg2 import sql
from datetime import datetime

def check_env_vars() -> bool:
    env_vars = ['DATABASE_HOST', 'DATABASE_USER', 'DATABASE_PASSWORD']
    all_present = True
    for var in env_vars:
        if (var not in os.environ) or (len(os.getenv(var)) == 0):
            all_present = False
            from dotenv import load_dotenv
            load_dotenv()
            return check_env_vars()
    return all_present

class DBInterface:
    def __init__(self):
        vars_present = check_env_vars()
        if vars_present == False:
            raise Exception("Database environment variables not set")

        self.conn = psycopg2.connect(
            host=os.getenv('DATABASE_HOST'),
            database='financials',
            user=os.getenv('DATABASE_USER'),
            password=os.getenv('DATABASE_PASSWORD')
        )
        self.all_tickers = self.get_all_tickers()

    def __del__(self):
        self.close_connection()

    def close_connection(self):
        self.conn.close()
    
    def get_connection(self): # this may not be necessary
        return self.conn
    
    def set_all_tickers(self):
        self.all_tickers = self.get_all_tickers()
    
    def query(self, ticker='AAPL', period_type='q', report_type='balance_sheet') -> list:
        cursor = self.conn.cursor()
        sql_string = f'SELECT * FROM "{ticker}_{period_type}_{report_type}"'
        cursor.execute(sql_string)
        financial_data = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        data_dict_list = [dict(zip(column_names, row)) for row in financial_data]

        return data_dict_list
    
    def parse_date(self, date):
        # dates can be of type str, datetime, or date
        if isinstance(date, str):
            try:
                date = datetime.strptime(date, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError("date must be in 'YYYY-MM-DD' format")
        elif isinstance(date, datetime):
            date = date.date()
        elif not isinstance(date, date):
            raise ValueError("date must be a date string, datetime, or date object")
        return date
    
    def query_stock_history(self, ticker='AAPL', period_type='1d', start_date=None, end_date=None):
        cursor = self.conn.cursor()
        table_name = f'{ticker}_{period_type}_price_history'
        sql_string = f'SELECT * FROM "{table_name}"'
        conditions = []
        params = []

        # parse and validate start_date
        # dates can be of type str, datetime, or date
        if start_date is not None:
            start_date = self.parse_date(start_date)
            conditions.append('date >= %s')
            params.append(start_date)

        # parse and validate end_date
        if end_date is not None:
            end_date = self.parse_date(end_date)
            conditions.append('date <= %s') # prevent SQL injection
            params.append(end_date)

        if conditions:
            sql_string += ' WHERE ' + ' AND '.join(conditions)
        # Order the results by date
        sql_string += ' ORDER BY date'

        try:
            cursor.execute(sql_string, params)
            price_data = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            data_dict_list = [dict(zip(column_names, row)) for row in price_data]
        except psycopg2.errors.UndefinedTable:
            print(f"Table {table_name} does not exist.")
            data_dict_list = []
        except Exception as e:
            print(f"An error occurred: {e}")
            data_dict_list = []
        finally:
            cursor.close()

        return data_dict_list
    
    def query_batch_stock_history(self, tickers, period_type='1d', start_date=None, end_date=None):
        dfs = []  # list to store dataframes
        for ticker in tickers:
            data = self.query_stock_history(ticker, period_type, start_date, end_date)
            if data:
                df = pd.DataFrame(data)
                # Ensure 'date' is in the dataframe
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)
                    # Create MultiIndex columns
                    df.columns = pd.MultiIndex.from_product([df.columns, [ticker]])
                    dfs.append(df)
                else:
                    print(f"No 'date' column for ticker {ticker}, skipping.")
            else:
                print(f"No data returned for ticker {ticker}, skipping.")
        if dfs:
            # Concatenate along columns
            combined_df = pd.concat(dfs, axis=1)

            # check for duplicate labels
            if combined_df.columns.duplicated().any():
                # Remove duplicate columns
                combined_df = combined_df.loc[:, ~combined_df.columns.duplicated()]

            # Define the order of fields
            fields_order = ['open', 'high', 'low', 'close', 'adj_close', 'volume']
            # Reindex the MultiIndex columns to match the field order
            combined_df = combined_df.reindex(fields_order, level=0, axis=1)

            # convert all rows to float
            combined_df = combined_df.astype(float)
            # Sort columns to match yf.download format
            combined_df.sort_index(axis=1, level=[0,1], inplace=True)
            return combined_df
        else:
            print("No data found for any tickers.")
            return pd.DataFrame()  # Return empty dataframe
    
    def query_multifactor_model(self, ticker='AAPL', years=10, num_factors=5):
        # TODO implement an input verification function
        # Returns the JSON object stored in the database
        cursor = self.conn.cursor()
        table_name = f"{ticker}_{years}y_{num_factors}_factor_model_summary"
        sql_string = f'SELECT * FROM "{table_name}"'
        try:
            cursor.execute(sql_string)
            data = cursor.fetchall()
            if data:
                model_data = data[-1][-1]
            else:   
                model_data = {}
        except psycopg2.errors.UndefinedTable:
            print(f"Table {table_name} does not exist.")
            model_data = {}
        cursor.close()
        return model_data

    def push_multifactor_model_summary(self, results: dict):
        cursor = self.conn.cursor()
        try:
            ticker = results['ticker']
            num_factors = len(results['betas']) - 1
            # Parse start_date and end_date if they are strings
            if isinstance(results['start_date'], str):
                start_date = datetime.strptime(results['start_date'], '%Y-%m-%d')
            else:
                start_date = results['start_date']
            if isinstance(results['end_date'], str):
                end_date = datetime.strptime(results['end_date'], '%Y-%m-%d')
            else:
                end_date = results['end_date']
            # Compute num_years
            num_years = round((end_date - start_date).days / 365)
            # Ensure at least 1 year
            num_years = max(num_years, 1)
            # Create table name
            table_name = f"{ticker}_{num_years}y_{num_factors}_factor_model_summary"
            # Ensure that all types are native Python types
            # Ensure start_date and end_date are strings
            if isinstance(results['start_date'], datetime):
                results['start_date'] = results['start_date'].strftime('%Y-%m-%d')
            if isinstance(results['end_date'], datetime):
                results['end_date'] = results['end_date'].strftime('%Y-%m-%d')
            # cast factor_means and p_value items to float
            for factor in results['betas'].index:
                if factor != 'const':
                    results['factor_means'][factor] = float(results['factor_means'][factor])
                    results['p_values'][factor] = float(results['p_values'][factor])
            # Convert any field that is a series to a dict
            for key in results:
                if isinstance(results[key], pd.Series):
                    results[key] = results[key].to_dict()
            
            # Create table if it doesn't exist
            create_table_query = sql.SQL("""
                CREATE TABLE IF NOT EXISTS {} (
                    id SERIAL PRIMARY KEY,
                    data JSONB
                )
            """).format(sql.Identifier(table_name))
            cursor.execute(create_table_query)
            self.conn.commit()
            # Delete existing entries to overwrite previous data
            delete_query = sql.SQL("DELETE FROM {}").format(sql.Identifier(table_name))
            cursor.execute(delete_query)
            # Insert new data
            data_json = json.dumps(results)
            insert_query = sql.SQL("INSERT INTO {} (data) VALUES (%s)").format(sql.Identifier(table_name))
            cursor.execute(insert_query, [data_json])
            self.conn.commit()
        except Exception as e:
            print(f"An error occurred: {e}")
            self.conn.rollback()
        finally:
            cursor.close()
            
    def get_all_tickers(self) -> list:
        cursor = self.conn.cursor()
        # Query to get distinct tickers from the financial_master table
        cursor.execute("SELECT DISTINCT ticker FROM financial_master;")
        tickers = cursor.fetchall()
        # Extract tickers from tuples
        ticker_list = [ticker[0] for ticker in tickers]
        cursor.close()
        return ticker_list

    def verify_query_input(self, period_type, ticker) -> bool:
        if period_type not in ['q', 'a']:
            return False
        if ticker not in self.all_tickers:
            return False
        return True # valid input
    
    def verify_price_history_input(self, period, ticker) -> bool:
        if period not in ['1d']:
            return False
        if ticker not in self.all_tickers:
            return False
        return True
    
    def get_github_user(self, github_id):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM github_users WHERE github_id = %s
        """, (github_id,))
        user = cursor.fetchone()
        # remove email from user data
        if user:
            user = user[:-1]
        return user

    def push_github_user(self, github_id, username, email):
        cursor = self.conn.cursor()
        # Create table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS github_users (
                github_id BIGINT PRIMARY KEY,
                username TEXT,
                email TEXT
            )
        """)
        try:
            cursor.execute("""
                INSERT INTO github_users (github_id, username, email)
                VALUES (%s, %s, %s)
                ON CONFLICT (github_id) DO UPDATE
                SET username = EXCLUDED.username, email = EXCLUDED.email;""", (github_id, username, email)
                
            )
            self.conn.commit()
        except Exception as e:
            print(f"An error occurred: {e}")
            self.conn.rollback()