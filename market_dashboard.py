import os, pandas as pd, streamlit as st, plotly.express as px
from datetime import datetime, timedelta
from fredapi import Fred
import yfinance as yf, requests

st.set_page_config(page_title="MarketData Dashboard", layout="wide")
st.markdown("<style>div.block-container{padding-top:1rem;padding-bottom:0.5rem;} .stMetric{gap:.25rem}</style>", unsafe_allow_html=True)
st.title("📊 MarketData Dashboard")

DATA_DIR   = "/Users/Timur/Documents/PythonProjects/MarketData/data/processed"
PULSE_DIR  = "/Users/Timur/Documents/PythonProjects/PropertyFinder/data/dubai_pulse/processed"
PORTFOLIO_FILE = os.path.join(DATA_DIR, "portfolio.csv")

fred = Fred(api_key=st.secrets["general"]["FRED_API_KEY"])

# ---------- helpers ----------
@st.cache_data(show_spinner=False)
def get_fred_series(series_id, years=5):
    end = datetime.now(); start = end - timedelta(days=years*365)
    s = fred.get_series(series_id, observation_start=start)
    return pd.DataFrame({"Date": s.index, "Value": s.values}).dropna()

@st.cache_data(show_spinner=False)
def get_equity(symbol):
    df = yf.download(symbol, period="5y", interval="1d", progress=False, auto_adjust=True)
    if df.empty: return pd.DataFrame()
    # flatten multiindex if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df.reset_index(inplace=True)
    if "Close" not in df.columns:
        close_col = next((c for c in df.columns if "close" in c.lower()), None)
        if not close_col: return pd.DataFrame()
        df.rename(columns={close_col:"Close"}, inplace=True)
    return df[["Date","Close"]].dropna()

@st.cache_data(show_spinner=False)
def cbonds_demo_emission(isin):
    url="https://ws.cbonds.info/services/json/demo/"
    params={"method":"get_emissions","ISIN":isin,"username":"Test","password":"Test"}
    try:
        r=requests.get(url,params=params,timeout=15)
        if not r.text.strip(): return None
        return r.json()
    except Exception:
        return None

def newest_parquet(folder):
    if not os.path.isdir(folder): return None
    files=[os.path.join(folder,f) for f in os.listdir(folder) if f.endswith(".parquet")]
    if not files: return None
    return max(files, key=os.path.getmtime)

# ========== UST ==========
try:
    d10 = get_fred_series("DGS10"); d1m = get_fred_series("DGS1MO")
    merged = pd.merge(d10, d1m, on="Date", suffixes=("_10Y","_1M"))
    merged["Spread"] = merged["Value_10Y"] - merged["Value_1M"]
    c1,c2,c3 = st.columns([1,1,3])
    with c1: st.metric("UST 10-Year", f"{d10.iloc[-1]['Value']:.2f}%", f"{d10.iloc[-1]['Value']-d10.iloc[-2]['Value']:+.02f}")
    with c2: st.metric("UST 1-Month", f"{d1m.iloc[-1]['Value']:.2f}%", f"{d1m.iloc[-1]['Value']-d1m.iloc[-2]['Value']:+.02f}")
    with c3:
        fig = px.line(merged, x="Date", y=["Value_10Y","Value_1M"], labels={"value":"Yield (%)"}, title="UST 10Y vs 1M (5y)")
        fig.update_layout(height=250, margin=dict(l=0,r=0,t=28,b=8), legend_title_text="")
        st.plotly_chart(fig, use_container_width=True)
    fig2 = px.area(merged, x="Date", y="Spread", title="UST 10Y − 1M Spread (5y)")
    fig2.add_hline(y=0, line_color="red"); fig2.update_layout(height=260, margin=dict(l=0,r=0,t=28,b=8))
    st.plotly_chart(fig2, use_container_width=True)
except Exception as e:
    st.error(f"UST failed: {e}")

st.divider()

# ========== Equities ==========
st.header("📈 Equity Indexes (live)")
symbols={"S&P 500":"^GSPC","NASDAQ":"^IXIC","DJIA":"^DJI"}
top = st.columns(3)
for (name,sym), col in zip(symbols.items(), top):
    df=get_equity(sym)
    if df.empty: 
        col.warning(f"{name} unavailable"); 
        continue
    last, prev = float(df["Close"].iloc[-1]), float(df["Close"].iloc[-2])
    col.metric(name, f"{last:,.0f}", f"{(last/prev-1)*100:+.2f}%")
row = st.columns(3)
for (name,sym), col in zip(symbols.items(), row):
    df=get_equity(sym)
    if df.empty: continue
    fig=px.line(df, x="Date", y="Close", title=f"{name} — 5y")
    fig.update_layout(height=240, margin=dict(l=0,r=0,t=32,b=18))
    col.plotly_chart(fig, use_container_width=True)

st.divider()

# ========== Sukuk (Cbonds demo) ==========
st.header("🕌 Sukuk Bonds (Cbonds demo: login=Test/password=Test)")
demo_isins=["XS0975256683","XS2595679111","XS1809986734"]
rows=[]
for isin in demo_isins:
    data=cbonds_demo_emission(isin)
    if data and "emissions" in data and data["emissions"].get("data"):
        e=data["emissions"]["data"][0]
        rows.append({"ISIN":isin,"Issuer":e.get("issuer_name_eng",""),
                     "Coupon":e.get("coupon",""),"Maturity":e.get("maturity_date",""),
                     "Currency":e.get("currency_code","")})
if rows:
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
else:
    st.info("Demo endpoint often returns empty payloads. As soon as you have real credentials, data will appear here automatically.")

st.divider()

# ========== Real Estate Portfolio ==========

# ========== Real Estate Portfolio ==========
st.header("🏘️ Property Portfolio vs Market")

pulse_file = newest_parquet(PULSE_DIR)
if pulse_file and os.path.exists(pulse_file):
    try:
        pulse = pd.read_parquet(pulse_file)
        location_col = next(
            (c for c in ["area_name_en", "community_name_en", "project_name_en"]
             if c in pulse.columns and pulse[c].notna().any()),
            None
        )
        price_col = "actual_worth"
        size_col = "procedure_area"

        if not location_col or price_col not in pulse.columns or size_col not in pulse.columns:
            st.error("Dubai Pulse file missing required columns.")
        else:
            pulse = pulse.dropna(subset=[location_col, price_col, size_col])
            pulse = pulse[pulse[location_col].astype(str).str.strip() != ""]
            pulse["price_psf"] = pulse[price_col] / pulse[size_col]
            area_mean = pulse.groupby(location_col)["price_psf"].mean().dropna().sort_values()

            if os.path.exists(PORTFOLIO_FILE):
                portfolio = pd.read_csv(PORTFOLIO_FILE)
            else:
                portfolio = pd.DataFrame(columns=["Location", "Price", "Area"])

            with st.form("add_property"):
                st.subheader("Add New Property")
                c1, c2, c3 = st.columns(3)
                with c1:
                    locations = sorted(area_mean.index.tolist())
                    if not locations:
                        st.warning("No valid locations found in dataset.")
                        location = None
                    else:
                        location = st.selectbox("Location", locations)
                with c2:
                    price = st.number_input("Purchase Price (AED)", min_value=0.0, step=10000.0)
                with c3:
                    area = st.number_input("Unit Area (sqft)", min_value=0.0, step=10.0)

                if st.form_submit_button("Add / Update") and location and price > 0 and area > 0:
                    new = pd.DataFrame({"Location": [location], "Price": [price], "Area": [area]})
                    portfolio = pd.concat([portfolio, new], ignore_index=True)
                    os.makedirs(os.path.dirname(PORTFOLIO_FILE), exist_ok=True)
                    portfolio.to_csv(PORTFOLIO_FILE, index=False)
                    st.success("Property added successfully.")

            if not portfolio.empty:
                portfolio["Your_PPSF"] = portfolio["Price"] / portfolio["Area"]
                portfolio["Market_PPSF"] = portfolio["Location"].map(area_mean)
                portfolio["Change_%"] = (portfolio["Market_PPSF"] / portfolio["Your_PPSF"] - 1) * 100
                st.dataframe(portfolio, use_container_width=True)
                st.metric("Portfolio Avg Growth/Loss", f"{portfolio['Change_%'].mean():+.2f}%")
            else:
                st.info("Add a property above to see portfolio performance.")

    except Exception as e:
        st.error(f"Failed to process Dubai Pulse file: {e}")

else:
    st.warning("No Dubai Pulse file found in processed folder.")

st.caption("© 2025 MarketData | Sources: FRED · Yahoo · Cbonds (demo) · Dubai Pulse")
