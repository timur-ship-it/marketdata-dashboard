#!/usr/bin/env python3
import os
from fredapi import Fred
import yfinance as yf
import pandas as pd
from datetime import datetime

# ======== CONFIG ========
BASE_DIR = os.path.expanduser("~/Documents/PythonProjects/MarketData")
DATA_DIR = os.path.join(BASE_DIR, "data/processed")
os.makedirs(DATA_DIR, exist_ok=True)

# FRED API key (set once: export FRED_API_KEY="your_key")
FRED_API_KEY = os.getenv("FRED_API_KEY")

if not FRED_API_KEY or len(FRED_API_KEY) != 32:
    raise ValueError("❌ Invalid or missing FRED API key. Set it using: export FRED_API_KEY=your_32char_key")

fred = Fred(api_key=FRED_API_KEY)

UST_SERIES = ["DGS1MO","DGS3MO","DGS6MO","DGS1","DGS2","DGS5","DGS7","DGS10","DGS20","DGS30"]
INDEX_SERIES = {"SP500": "SP500", "NASDAQ": "NASDAQCOM", "DJIA": "DJIA"}

def fetch_fred_series(series_id):
    """Fetch a single FRED series safely."""
    try:
        data = fred.get_series(series_id)
    except Exception as e:
        print(f"[ERROR] FRED request failed for {series_id}: {e}")
        return pd.DataFrame(columns=["date","value","series"])
    df = pd.DataFrame(data, columns=["value"])
    df.index.name = "date"
    df.reset_index(inplace=True)
    df["series"] = series_id
    return df

def fetch_ust():
    dfs = [fetch_fred_series(s) for s in UST_SERIES]
    ust_df = pd.concat(dfs, ignore_index=True)
    file = os.path.join(DATA_DIR, "ust_yields.csv")
    ust_df.to_csv(file, index=False)
    print(f"[UST] Saved {len(ust_df)} rows → {file}")

def fetch_indices():
    for name, code in INDEX_SERIES.items():
        df = fetch_fred_series(code)
        df.rename(columns={"value": "close"}, inplace=True)
        file = os.path.join(DATA_DIR, f"{name.lower()}.csv")
        df.to_csv(file, index=False)
        print(f"[{name}] Saved {len(df)} rows → {file}")

def fetch_yahoo(symbol, name):
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="max")[["Close"]].reset_index()
    df.columns = ["date", "close"]
    file = os.path.join(DATA_DIR, f"{name.lower()}_yahoo.csv")
    df.to_csv(file, index=False)
    print(f"[Yahoo {name}] Saved {len(df)} rows → {file}")

def update_all():
    fetch_ust()
    fetch_indices()
    # Uncomment for fresher Yahoo data
    # fetch_yahoo("^GSPC", "SP500")
    # fetch_yahoo("^IXIC", "NASDAQ")
    # fetch_yahoo("^DJI", "DJIA")

if __name__ == "__main__":
    update_all()

