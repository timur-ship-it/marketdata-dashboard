#!/usr/bin/env bash
mkdir -p "/Users/Timur/Documents/PythonProjects/MarketData/.streamlit"
mkdir -p "/Users/Timur/Documents/PythonProjects/MarketData/data/processed"

# --- secrets.toml with FRED key ---
cat << 'TOML' > "/Users/Timur/Documents/PythonProjects/MarketData/.streamlit/secrets.toml"
[general]
FRED_API_KEY = "3b57d7b812e6c795cdea2b16a2a68033"
TOML

# --- requirements.txt for Streamlit Cloud ---
cat << 'REQ' > "/Users/Timur/Documents/PythonProjects/MarketData/requirements.txt"
streamlit
pandas
plotly
fredapi
yfinance
REQ

# --- market_dashboard.py ---
cat << 'PY' > "/Users/Timur/Documents/PythonProjects/MarketData/market_dashboard.py"
import os, json, pandas as pd, streamlit as st, plotly.express as px
from fredapi import Fred
from datetime import datetime, timedelta

st.set_page_config(page_title="MarketData Dashboard", layout="wide")
st.title("📊 MarketData Dashboard")

DATA_DIR = "/Users/Timur/Documents/PythonProjects/MarketData/data/processed"
PULSE_PATH = "/Users/Timur/Documents/PythonProjects/PropertyFinder/data/dubai_pulse/processed"
PORTFOLIO_FILE = os.path.join(DATA_DIR, "portfolio.csv")

# ===== FRED: UST yields =====
fred = Fred(api_key=st.secrets["general"]["FRED_API_KEY"])
@st.cache_data(show_spinner=False)
def get_fred_series(series_id, years=5):
    end = datetime.now()
    start = end - timedelta(days=years*365)
    data = fred.get_series(series_id, observation_start=start)
    return pd.DataFrame({"Date": data.index, "Value": data.values})

try:
    dgs10 = get_fred_series("DGS10")
    dgs1m  = get_fred_series("DGS1MO")
    merged = pd.merge(dgs10, dgs1m, on="Date", suffixes=("_10Y","_1M"))
    merged["Spread"] = merged["Value_10Y"] - merged["Value_1M"]

    last10, last1m = dgs10.iloc[-1]["Value"], dgs1m.iloc[-1]["Value"]
    prev10, prev1m = dgs10.iloc[-2]["Value"], dgs1m.iloc[-2]["Value"]
    st.metric("UST 10-Year", f"{last10:.2f}%", f"{last10 - prev10:+.2f}")
    st.metric("UST 1-Month", f"{last1m:.2f}%", f"{last1m - prev1m:+.2f}")

    fig = px.area(merged, x="Date", y="Spread", title="UST 10Y - 1M Spread (5 Years)",
                  color_discrete_sequence=["#1f77b4"])
    fig.add_hline(y=0, line_color="red")
    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"UST section failed: {e}")

# ===== Equities =====
st.header("📈 Equity Indexes")
for name in ["sp500.csv","nasdaq.csv","djia.csv"]:
    path = os.path.join(DATA_DIR, name)
    if os.path.exists(path):
        df = pd.read_csv(path)
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            fig = px.line(df.tail(365), x="Date", y=df.columns[1],
                          title=name.replace(".csv","").upper())
            st.plotly_chart(fig, use_container_width=True)
st.divider()

# ===== Sukuk =====
st.header("🕌 Sukuk Bonds (Cbonds)")
cbonds_dir = os.path.join(DATA_DIR, "cbonds")
if os.path.exists(cbonds_dir):
    rows=[]
    for f in os.listdir(cbonds_dir):
        if f.endswith(".json"):
            with open(os.path.join(cbonds_dir,f)) as j: data=json.load(j)
            e=data.get("emissions",{}).get("data",[])
            if e: e=e[0]; rows.append({
                "ISIN":f[:-5],"Issuer":e.get("issuer_name_eng",""),
                "Coupon":e.get("coupon",""),"Maturity":e.get("maturity_date",""),
                "Currency":e.get("currency_code","")
            })
    if rows: st.dataframe(pd.DataFrame(rows), use_container_width=True)
else:
    st.info("No Sukuk data found.")
st.divider()

# ===== Real Estate Portfolio =====
st.header("🏘️ Property Portfolio vs Market")
pulse_file = os.path.join(PULSE_PATH, "latest.parquet")
if os.path.exists(pulse_file):
    pulse = pd.read_parquet(pulse_file)
    if "area_name_en" in pulse.columns and "actual_worth" in pulse.columns and "procedure_area" in pulse.columns:
        pulse["price_psf"] = pulse["actual_worth"] / pulse["procedure_area"]
        area_mean = pulse.groupby("area_name_en")["price_psf"].mean().dropna()

        if os.path.exists(PORTFOLIO_FILE):
            portfolio = pd.read_csv(PORTFOLIO_FILE)
        else:
            portfolio = pd.DataFrame(columns=["Location","Price","Area"])

        with st.form("add_property"):
            st.subheader("Add New Property")
            col1,col2,col3 = st.columns(3)
            with col1: location = st.selectbox("Location", sorted(area_mean.index.unique()))
            with col2: price = st.number_input("Purchase Price (AED)", min_value=0.0, step=10000.0)
            with col3: area = st.number_input("Unit Area (sqft)", min_value=0.0, step=10.0)
            submitted = st.form_submit_button("Add / Update")
            if submitted and location and price>0 and area>0:
                new_row = pd.DataFrame({"Location":[location],"Price":[price],"Area":[area]})
                portfolio = pd.concat([portfolio,new_row],ignore_index=True)
                portfolio.to_csv(PORTFOLIO_FILE,index=False)
                st.success("Property added!")

        if not portfolio.empty:
            portfolio["Your_PPSF"] = portfolio["Price"]/portfolio["Area"]
            portfolio["Market_PPSF"] = portfolio["Location"].map(area_mean)
            portfolio["Change_%"] = (portfolio["Your_PPSF"]/portfolio["Market_PPSF"] - 1)*100
            st.dataframe(portfolio, use_container_width=True)
            avg_gain = portfolio["Change_%"].mean()
            st.metric("Portfolio Avg Growth/Loss", f"{avg_gain:+.2f}%")
    else:
        st.warning("Pulse dataset missing expected columns.")
else:
    st.warning("Dubai Pulse dataset not found.")
st.caption("© 2025 MarketData | Sources: FRED · Yahoo · Cbonds · Dubai Pulse")
PY

# --- run dashboard ---
streamlit run "/Users/Timur/Documents/PythonProjects/MarketData/market_dashboard.py"
