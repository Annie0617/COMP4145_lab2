# MSFT Trading Strategy Dashboard

The dashboard displays the five-year MSFT golden-cross backtest in three pages:

- **Price chart** — daily closing price, 50-day and 200-day moving averages, and
  buy/sell markers.
- **Trade statistics** — overall trade outcomes and return statistics. Trades
  with missing price data are counted separately and excluded from return
  calculations.
- **Detailed trades** — entry/exit dates, prices, holding periods, and returns.

## Run locally

From this folder, install the requirements and launch Streamlit:

```bash
python3 -m pip install -r requirements.txt
streamlit run app.py
```

The dashboard fetches current historical prices from Yahoo Finance and caches
the calculated results for one hour.
