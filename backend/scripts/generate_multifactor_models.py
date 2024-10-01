import sys
import os
import datetime
from dotenv import load_dotenv

sys.path.append("..")
from db_interface import DBInterface
from capm_model import CAPMModel

# TODO Implement a multiprocessing version of this script to speed up the process as it is currently very slow
def generate_multifactor_models(ticker_list=None):
    # Generate multifactor models for all tickers and push them to the database
    db_interface = DBInterface()

    if not ticker_list:
        ticker_list = db_interface.get_all_tickers()
    tickers_complete = 0
    failed_tickers = []
    tickers_total = len(ticker_list)
    years = [10, 5]
    market_index = "^GSPC" # S&P 500 index
    model = CAPMModel(fred_api_key=os.getenv('FRED_API_KEY'), db_interface=db_interface)
    print(f"Generating multifactor models for {tickers_total} tickers")
    for year in years:
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=365 * year)
        for ticker in ticker_list:
            # Generate the five and six factor models
            try:
                five_factor_result = model.five_factor_model(ticker, market_index, start_date, end_date)
                six_factor_result = model.six_factor_model(ticker, market_index, start_date, end_date)

                # Push the results to the database
                for result in [five_factor_result, six_factor_result]:
                    if result:
                        db_interface.push_multifactor_model_summary(result)
            except Exception as e:
                print(f"Failed to generate multifactor model for {ticker}")
                print(e)
                failed_tickers.append(ticker)

            tickers_complete += 1
            print(f"{round((tickers_complete / tickers_total) * 100, 2)}% complete")
    if len(failed_tickers) > 0:
        print(f"Failed to generate multifactor models for the following tickers: {failed_tickers}")
if __name__ == '__main__':
    load_dotenv()
    import time
    start = time.time()
    generate_multifactor_models()
    print(f"Time elapsed: {round(time.time() - start, 2)} seconds")