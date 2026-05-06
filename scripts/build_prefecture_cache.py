"""Build national price aggregates from MLIT API across all 47 prefectures.

Run offline (~15 min). Saves data/prefecture_aggregates.parquet which is read
by Japan Overview at app startup, replacing the hand-curated price estimates
that used to live in utils/prefecture_data.py.

Usage:
  set MLIT_API_KEY=...
  python scripts/build_prefecture_cache.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests

# Make sibling 'utils' importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.data_loader import _classify_property_type, _last_available_period  # noqa: E402

API_URL = "https://www.reinfolib.mlit.go.jp/ex-api/external/XIT001"
START_YEAR = 2024
PREF_CODES = [f"{i:02d}" for i in range(1, 48)]  # "01" .. "47"
OUTPUT = Path(__file__).resolve().parent.parent / "data" / "prefecture_aggregates.parquet"


def fetch_quarter(api_key: str, year: int, quarter: int, area: str) -> list[dict]:
    try:
        r = requests.get(
            API_URL,
            headers={"Ocp-Apim-Subscription-Key": api_key},
            params={"year": str(year), "quarter": str(quarter), "area": area, "language": "en"},
            timeout=30,
        )
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception as exc:
        print(f"   ! {area} {year}-Q{quarter}: {exc}", flush=True)
        return []


def main() -> None:
    api_key = os.environ.get("MLIT_API_KEY", "")
    if not api_key:
        sys.exit("MLIT_API_KEY env var not set")

    last_year, last_quarter = _last_available_period()
    quarters_to_fetch: list[tuple[int, int]] = [
        (y, q)
        for y in range(START_YEAR, last_year + 1)
        for q in range(1, 5)
        if not (y == last_year and q > last_quarter)
    ]
    print(f"Fetching {len(PREF_CODES)} prefectures × {len(quarters_to_fetch)} quarters "
          f"= {len(PREF_CODES) * len(quarters_to_fetch)} API calls\n")

    rows: list[dict] = []
    for i, pref in enumerate(PREF_CODES, 1):
        pref_total = 0
        for year, quarter in quarters_to_fetch:
            data = fetch_quarter(api_key, year, quarter, pref)
            for rec in data:
                ptype = _classify_property_type(rec)
                if ptype is None:
                    continue
                try:
                    area_m2 = float(rec.get("Area") or rec.get("TotalFloorArea") or 0)
                    trade_price = float(rec.get("TradePrice") or 0)
                except (TypeError, ValueError):
                    continue
                if area_m2 <= 0 or trade_price <= 0:
                    continue
                try:
                    unit_price = float(rec.get("UnitPrice") or 0)
                except (TypeError, ValueError):
                    unit_price = 0.0
                ppm2 = unit_price if unit_price > 0 else (trade_price / area_m2)

                rows.append({
                    "prefecture_code": pref,
                    "tx_year":         year,
                    "tx_quarter":      quarter,
                    "property_type":   ptype,
                    "price_per_m2_jpy": int(ppm2),
                    "trade_price_jpy":  int(trade_price),
                    "area_m2":          round(area_m2, 1),
                })
                pref_total += 1
            time.sleep(0.1)
        print(f"[{i:2d}/47] pref {pref}: {pref_total:>6} records", flush=True)

    df = pd.DataFrame(rows)
    print(f"\nRaw records: {len(df):,}")

    # ── Aggregations the Japan Overview page consumes ──────────────────────────
    yearly = (
        df.groupby(["prefecture_code", "tx_year"])
        .agg(
            median_ppm2    = ("price_per_m2_jpy", "median"),
            mean_ppm2      = ("price_per_m2_jpy", "mean"),
            n_transactions = ("price_per_m2_jpy", "size"),
        )
        .reset_index()
    )

    by_type = (
        df.groupby(["prefecture_code", "tx_year", "property_type"])
        .agg(
            median_ppm2    = ("price_per_m2_jpy", "median"),
            n_transactions = ("price_per_m2_jpy", "size"),
        )
        .reset_index()
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    yearly.to_parquet(OUTPUT, index=False)
    OUTPUT_BY_TYPE = OUTPUT.with_name("prefecture_aggregates_by_type.parquet")
    by_type.to_parquet(OUTPUT_BY_TYPE, index=False)

    print(f"\nWrote {OUTPUT.name}: {len(yearly)} rows")
    print(f"Wrote {OUTPUT_BY_TYPE.name}: {len(by_type)} rows")


if __name__ == "__main__":
    main()
