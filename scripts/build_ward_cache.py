"""Fetch real MLIT XIT001 transactions for Tokyo's 23 special wards.

Run offline (~10-20 min depending on data volume). Saves:
  data/ward_transactions.parquet

The app's load_data() checks for this file first; if present it uses real data
instead of the synthetic generator.

Usage:
  set MLIT_API_KEY=<your_key>
  python scripts/build_ward_cache.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.data_loader import (
    _classify_property_type,
    _parse_year_built,
    _parse_period,
    _STRUCTURE_MAP,
    _last_available_period,
)
from utils.ward_data import TOKYO_WARDS

API_URL = "https://www.reinfolib.mlit.go.jp/ex-api/external/XIT001"
START_YEAR = 2020
OUTPUT = Path(__file__).resolve().parent.parent / "data" / "ward_transactions.parquet"

MUNICIPALITY_CODES = {
    "13101": "Chiyoda",   "13102": "Chuo",      "13103": "Minato",
    "13104": "Shinjuku",  "13105": "Bunkyo",    "13106": "Taito",
    "13107": "Sumida",    "13108": "Koto",       "13109": "Shinagawa",
    "13110": "Meguro",    "13111": "Ota",        "13112": "Setagaya",
    "13113": "Shibuya",   "13114": "Nakano",     "13115": "Suginami",
    "13116": "Toshima",   "13117": "Kita",       "13118": "Arakawa",
    "13119": "Itabashi",  "13120": "Nerima",     "13121": "Adachi",
    "13122": "Katsushika","13123": "Edogawa",
}


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


def _num(v):
    try:
        return float(v) if v not in (None, "", "-") else None
    except (TypeError, ValueError):
        return None


def main() -> None:
    api_key = os.environ.get("MLIT_API_KEY", "")
    if not api_key:
        sys.exit("MLIT_API_KEY env var not set. Run: set MLIT_API_KEY=<your_key>")

    last_year, last_quarter = _last_available_period()
    quarters: list[tuple[int, int]] = [
        (y, q)
        for y in range(START_YEAR, last_year + 1)
        for q in range(1, 5)
        if not (y == last_year and q > last_quarter)
    ]
    print(f"Fetching Tokyo prefecture (area=13) for {len(quarters)} quarters...\n")

    rows: list[dict] = []
    ward_counts: dict[str, int] = {w: 0 for w in TOKYO_WARDS}

    for year, quarter in quarters:
        print(f"  {year}-Q{quarter}...", end=" ", flush=True)
        records = fetch_quarter(api_key, year, quarter, area="13")
        added = 0
        for rec in records:
            mcode = str(rec.get("MunicipalityCode", ""))
            ward = MUNICIPALITY_CODES.get(mcode)
            if ward is None:
                continue

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
                ppm2 = float(rec.get("UnitPrice") or 0)
            except (TypeError, ValueError):
                ppm2 = 0.0
            if ppm2 <= 0:
                ppm2 = trade_price / area_m2

            tx_year, tx_quarter = _parse_period(rec.get("Period"), year, quarter)
            year_built = _parse_year_built(rec.get("BuildingYear"))
            raw_struct = str(rec.get("Structure") or "").strip()

            winfo = TOKYO_WARDS[ward]
            rows.append({
                "ward":             ward,
                "ward_ja":          winfo["ja"],
                "property_type":    ptype,
                "purpose":          str(rec.get("Purpose") or "").strip() or None,
                "region":           str(rec.get("Region") or "").strip() or None,
                "tx_year":          tx_year,
                "tx_quarter":       tx_quarter,
                "tx_period":        f"{tx_year}-Q{tx_quarter}",
                "area_m2":          round(area_m2, 1),
                "layout":           rec.get("FloorPlan") or "-",
                "year_built":       year_built,
                "building_age":     (tx_year - year_built) if year_built else None,
                "nearest_station":  None,
                "station_minutes":  None,
                "trade_price_jpy":  int(trade_price),
                "price_per_m2_jpy": int(ppm2),
                "lat":              winfo["lat"],
                "lon":              winfo["lon"],
                "district":         str(rec.get("DistrictName") or "").strip() or None,
                "district_code":    str(rec.get("DistrictCode") or "").strip() or None,
                "structure":        _STRUCTURE_MAP.get(raw_struct) if raw_struct else None,
                "direction":        str(rec.get("Direction") or "").strip() or None,
                "renovation":       str(rec.get("Renovation") or "").strip() or None,
                "city_planning":    str(rec.get("CityPlanning") or "").strip() or None,
                "coverage_ratio":   _num(rec.get("CoverageRatio")),
                "floor_area_ratio": _num(rec.get("FloorAreaRatio")),
                "frontage_m":       _num(rec.get("Frontage")),
                "breadth_m":        _num(rec.get("Breadth")),
            })
            ward_counts[ward] += 1
            added += 1

        print(f"{added} records", flush=True)
        time.sleep(0.4)

    if not rows:
        sys.exit("No records fetched. Check your API key and connection.")

    df = pd.DataFrame(rows)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT, index=False)

    print(f"\nTotal records: {len(df):,}")
    print(f"Saved to: {OUTPUT}\n")
    print("Records per ward:")
    for ward, count in sorted(ward_counts.items(), key=lambda x: -x[1]):
        print(f"  {ward:<15} {count:>6,}")


if __name__ == "__main__":
    main()
