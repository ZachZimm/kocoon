import psycopg2
import os

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