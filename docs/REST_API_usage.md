## Retrieve fundemental data

### Get balance sheet for a company
#### `/api/balnce_sheet/{period_type}/{ticker}`

### Get income sheet for a company
#### `/api/income/{period_type}/{ticker}`

### Get cash flow for a company
#### `/api/cash_flow/{period_type}/{ticker}`

- Options for `period_type` are `q` for quarterly and `a` for annual
- Each of these return the full histories for the specified ticker as a list of JSON objects
- See `balance_sheet.md`, `income.md` and `cash_flow.md` for detailed examples

## Retrieve historical stock price data
#### `/api/price_history/{period}/{ticker}`
- The only valid option for `period` currently is '1d'
    - We will support longer time frames in the future
- Returns a list of JSON objects, one for each day.
```
{
    "date": str,
    "open": float,
    "high": float,
    "low": float,
    "close" float,
    "volume: float,
    "adj_close": float
}
```
- Returns the full history stored in the database


## Retrieve multifactor model data
#### `/api/multifactor_model/{num_years}y/{ticker}/{num_factors}`
- Currently, the only valid option for `num_years` is 10
    - 5 will be an option in the future
- Don't forget the 'y' after the `num_years`

- The only valid options for `num_factors` are 5 and 6

- See `multifactor_examples.md` for detailed information about what is returned

