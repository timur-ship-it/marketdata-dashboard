#!/usr/bin/env python3
import requests
import json
import os

# === Cbonds JSON API configuration ===
API_BASE = "https://ws.cbonds.info/services/json/"
AUTH = {"login": "Test", "password": "Test"}

# === Endpoints (as described by Maria) ===
ENDPOINTS = {
    "emissions": "get_emissions",
    "defaults": "get_emission_default",
    "guarantors": "get_emission_guarantors",
    "flows": "get_flow_new",
    "offers": "get_offert",
    "tradings": "get_tradings_new"
}

# === ISIN list ===
ISINS = [
    "XS3065329446",
    "XS2633136234",
    "XS2914525154",
    "XS2841181972",
    "XS3068594129",
    "XS2777443768"
]

def fetch_cbonds(endpoint_key, isin):
    """Fetch data from Cbonds JSON API for a given endpoint and ISIN."""
    url = API_BASE + ENDPOINTS[endpoint_key]
    payload = {
        "auth": AUTH,
        "filters": [{"field": "isin", "operator": "eq", "value": isin}],
        "quantity": {"limit": 20, "offset": 0}
    }
    print(f"🔎 Fetching {endpoint_key} for {isin} ...")
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    try:
        return r.json()
    except json.JSONDecodeError:
        print(f"⚠️ Failed to decode JSON for {isin} ({endpoint_key}) — raw text:")
        print(r.text[:200])
        return {}

def main():
    out_dir = "/Users/Timur/Documents/PythonProjects/MarketData/data/processed/cbonds"
    os.makedirs(out_dir, exist_ok=True)

    for isin in ISINS:
        all_data = {}
        for key in ["emissions", "flows", "offers", "tradings"]:
            try:
                data = fetch_cbonds(key, isin)
                all_data[key] = data
            except Exception as e:
                print(f"⚠️ {key} failed for {isin}: {e}")
        out_path = os.path.join(out_dir, f"{isin}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved {isin} → {out_path}")

    print("\n✅ All ISINs processed successfully.")

if __name__ == "__main__":
    main()
