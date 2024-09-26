Example 5-factor model retrieved with `curl https://host.zzimm.com/api/multifactor_model/10y/AAPL/5`
fields are of mixed type so schema is included

Schema:
```
{
  "betas": dict{ string : float },
  "ticker": string,
  "end_date": string,
  "p_values": dict{ string : float },
  "model_name": string,
  "start_date": string,
  "factor_means": dict{ string : float },
  "market_index": string,
  "risk_free_rate": float,
  "expected_return": float,
  "average_market_return": float 
}
```

Example:
```
{
  "betas": {
    "CMA": -0.2969807730829956,
    "HML": -0.12022479737192729,
    "RMW": 0.2584175832845224,
    "SMB": 0.18140291964491115,
    "const": 0.00045509992725889086,
    "Market_Excess": 1.1454255712569734
  },
  "ticker": "AAPL",
  "end_date": "2024-09-22",
  "p_values": {
    "CMA": 0.0003283180621520302,
    "HML": 0.13511955171838008,
    "RMW": 0.001311918877518101,
    "SMB": 0.005524248622336387,
    "const": 0.05268618260339622,
    "Market_Excess": 0.0
  },
  "model_name": "Fama-French Five-Factor",
  "start_date": "2014-09-25",
  "factor_means": {
    "CMA": 0.00001947767592091732,
    "HML": -0.000042130248060381316,
    "RMW": 0.000014791736790731466,
    "SMB": 0.00024003340036260094,
    "Market_Excess": 0.00042173942822001795
  },
  "market_index": "^GSPC",
  "risk_free_rate": 0.0002003968253968254,
  "expected_return": 0.0007301137606828764,
  "average_market_return": 0.00048745027151741126
}
```