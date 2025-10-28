import os, pandas as pd, streamlit as st, plotly.express as px
from datetime import datetime, timedelta
from fredapi import Fred
import yfinance as yf, requests
import difflib

def fuzzy_match(name, options):
    import difflib
    if not isinstance(name, str): return None
    options = list(options) if hasattr(options, "tolist") else list(options)
    if not options: return None
    name = name.strip().lower()
    matches = difflib.get_close_matches(name, [str(x).lower() for x in options], n=1, cutoff=0.5)
    if matches:
        match_index = [str(x).lower() for x in options].index(matches[0])
        return options[match_index]
    return None
    name = name.strip().lower()
    matches = difflib.get_close_matches(name, [str(x).lower() for x in options], n=1, cutoff=0.5)
    if matches:
        match_index = [str(x).lower() for x in options].index(matches[0])
        return options[match_index]
    return None


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

# ========== Sukuk (Cbonds API with secrets) ==========
st.header("🕌 Sukuk Bonds (Cbonds Live API)")

cb_user = st.secrets["cbonds"]["login"]
cb_pass = st.secrets["cbonds"]["password"]

isins = ["XS0975256683","XS2595679111","XS1809986734","XS2396609819","XS2506541443","XS2069132036"]
rows = []
for isin in isins:
    url = "https://ws.cbonds.info/services/json/get_emissions/"
    params = {"login": cb_user, "password": cb_pass, "ISIN": isin}
    try:
        r = requests.get(url, params=params, timeout=20)
        if r.status_code == 200:
            js = r.json()
            items = js.get("items") or []
            match = next((e for e in items if e.get("isin") == isin), None)
            if match:
                rows.append({
                    "ISIN": isin,
                    "Issuer": match.get("issuer_name_eng", ""),
                    "Coupon": match.get("coupon", ""),
                    "Maturity": match.get("maturity_date", ""),
                    "Currency": match.get("currency_name", "")
                })
        else:
            st.warning(f"{isin}: HTTP {r.status_code}")
    except Exception as e:
        st.error(f"{isin}: {e}")

if rows:
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
else:
    st.info("No Sukuk data retrieved — check credentials or ISIN list.")

st.divider()

# ---------- Real Estate Portfolio ----------
st.header("🏘️ Property Portfolio vs Market")

pulse_file = newest_parquet(PULSE_DIR)
if pulse_file and os.path.exists(pulse_file):
    pulse = pd.read_parquet(pulse_file)
    area_col = "area_name_en" if "area_name_en" in pulse.columns else None
    price_col = "meter_sale_price"

    pulse = pulse.dropna(subset=[area_col, price_col])
    pulse = pulse[pulse[area_col].astype(str).str.strip() != ""]

    pulse["price_psm"] = pulse[price_col]
    pulse["price_psf"] = pulse[price_col] / 10.7639
    area_mean_m2 = pulse.groupby(area_col)["price_psm"].mean().dropna()
    area_mean_ft2 = pulse.groupby(area_col)["price_psf"].mean().dropna()

    portfolio = (
        pd.read_csv(PORTFOLIO_FILE)
        if os.path.exists(PORTFOLIO_FILE)
        else pd.DataFrame(columns=["Location", "Price", "Area_ft2"])
    )

    with st.form("add_property"):
        st.subheader("Add New Property")
        c1, c2, c3 = st.columns(3)
        with c1:
            location = st.selectbox("Location", sorted(area_mean_m2.index))
        with c2:
            price = st.number_input("Purchase Price (AED)", min_value=0.0, step=10000.0)
        with c3:
            area_ft2 = st.number_input("Unit Area (ft²)", min_value=0.0, step=10.0)
        if st.form_submit_button("Add / Update") and location and price > 0 and area_ft2 > 0:
            portfolio = pd.concat(
                [portfolio, pd.DataFrame({"Location":[location],"Price":[price],"Area_ft2":[area_ft2]})],
                ignore_index=True,
            )
            os.makedirs(os.path.dirname(PORTFOLIO_FILE), exist_ok=True)
            portfolio.to_csv(PORTFOLIO_FILE, index=False)
            st.success("Property added."); st.experimental_rerun()

    if not portfolio.empty:
        portfolio["Area_m2"] = portfolio["Area_ft2"] / 10.7639
        portfolio["Your_PPSM"] = portfolio["Price"] / portfolio["Area_m2"]
        portfolio["Matched_Location"] = portfolio["Location"].apply(lambda x: fuzzy_match(x, area_mean_m2.index))
        portfolio["Market_PPSM"] = portfolio["Matched_Location"].map(area_mean_m2)
        portfolio["Change_%"] = (portfolio["Market_PPSM"] / portfolio["Your_PPSM"] - 1) * 100
        portfolio["Your_PPSF"] = portfolio["Your_PPSM"] / 10.7639
        portfolio["Market_PPSF"] = portfolio["Market_PPSM"] / 10.7639

        st.subheader("Your Portfolio (compared on AED / m² basis)")
        for i, row in portfolio.iterrows():
            c1, c2, c3, c4, c5, c6 = st.columns([2,2,2,2,2,1])
            c1.text(row["Location"])
            c2.text(f"AED {row['Price']:,.0f}")
            c3.text(f"{row['Area_ft2']:,.0f} ft²  ({row['Area_m2']:.1f} m²)")
            c4.text(f"Your {row['Your_PPSF']:,.0f} / ft²")
            c5.text(f"{row['Change_%']:+.2f}% vs market")
            if c6.button("🗑️", key=f"del_{i}"):
                portfolio = portfolio.drop(i).reset_index(drop=True)
                portfolio.to_csv(PORTFOLIO_FILE, index=False)
                st.experimental_rerun()

        avg = portfolio["Change_%"].mean()
        st.metric("Portfolio Avg Δ (AED / m²)", f"{avg:+.2f}%")
    else:
        st.info("Add a property above to see portfolio performance.")
else:
    st.warning("No Dubai Pulse file found in processed folder.")

st.caption("© 2025 MarketData | Sources: FRED · Yahoo · Cbonds (demo) · Dubai Pulse")