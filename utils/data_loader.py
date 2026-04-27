"""
Data loader — abstract interface with two backends:

1. synthetic (DEFAULT):
   Generates a deterministic, statistically realistic dataset of Tokyo
   real estate transactions modeled after MLIT public aggregates.
   Used while waiting for MLIT API key approval.

2. mlit_api (FUTURE):
   Calls the MLIT Real Estate Information Library API (XIT001) with the
   user's subscription key. Stub provided; activate by setting
   MLIT_API_KEY env variable and DATA_SOURCE='mlit_api'.

Swapping backends is a one-line change in app.py.
"""
from __future__ import annotations

import gzip
import json
import os
import re
import time
from datetime import datetime

import numpy as np
import pandas as pd
import requests

from .ward_data import (
    TOKYO_WARDS,
    WARD_MAIN_STATIONS,
    PROPERTY_TYPES,
    PROPERTY_TYPE_WEIGHTS,
    LAYOUTS,
    LAYOUT_WEIGHTS_APARTMENT,
)

RANDOM_SEED = 42
N_TRANSACTIONS = 50_000
START_YEAR = 2020
END_YEAR = 2024  # synthetic backend fixed range


def _last_available_period() -> tuple[int, int]:
    """Last quarter published by MLIT (~2 quarter lag from today)."""
    now = datetime.now()
    current_q = (now.month - 1) // 3 + 1
    year, quarter = now.year, current_q - 2
    if quarter <= 0:
        quarter += 4
        year -= 1
    return year, quarter


# ──────────────────────────────────────────────────────────────────
# SYNTHETIC BACKEND
# ──────────────────────────────────────────────────────────────────

def _yearly_market_factor(year: int) -> float:
    """
    Tokyo market price trend factor relative to 2020 baseline.
    Based on public REINS / MLIT index reports:
      2020 → 1.00 (post-COVID dip baseline)
      2021 → 1.04
      2022 → 1.10
      2023 → 1.15
      2024 → 1.19  (continued appreciation, weak yen driving foreign demand)
    """
    factors = {2020: 1.00, 2021: 1.04, 2022: 1.10, 2023: 1.15, 2024: 1.19}
    return factors.get(year, 1.0)


def _year_built_discount(year_built: int, tx_year: int) -> float:
    """
    Used apartments/houses lose value with age.
    Rough Japanese market curve:
      0-5 years:    ~1.00
      5-10 years:   ~0.88
      10-20 years:  ~0.75
      20-30 years:  ~0.60
      30-40 years:  ~0.48
      40+ years:    ~0.35
    """
    age = max(0, tx_year - year_built)
    if age <= 5:
        return 1.00
    if age <= 10:
        return 0.88
    if age <= 20:
        return 0.75
    if age <= 30:
        return 0.60
    if age <= 40:
        return 0.48
    return 0.35


def _station_distance_factor(minutes: int) -> float:
    """
    Distance to nearest station impacts price significantly in Tokyo.
      0-5 min:   1.10
      5-10 min:  1.00
      10-15 min: 0.92
      15-20 min: 0.85
      20+ min:   0.78
    """
    if minutes <= 5:
        return 1.10
    if minutes <= 10:
        return 1.00
    if minutes <= 15:
        return 0.92
    if minutes <= 20:
        return 0.85
    return 0.78


def _property_type_factor(ptype: str) -> float:
    """
    Used apartment is the baseline (1.00).
    """
    return {
        "Used Apartment": 1.00,
        "Used House":     0.85,  # typically cheaper per m² (land dominates)
        "New House":      1.15,
        "Land Only":      0.70,  # land-only has different pricing logic
    }[ptype]


def _sample_area(ptype: str, rng: np.random.Generator) -> float:
    """Return square meters based on property type."""
    if ptype == "Used Apartment":
        # Most apartments in Tokyo are 20-100 m², mode ~50
        return float(np.clip(rng.gamma(shape=4.5, scale=11), 18, 180))
    if ptype == "Used House":
        return float(np.clip(rng.gamma(shape=5, scale=18), 50, 280))
    if ptype == "New House":
        return float(np.clip(rng.gamma(shape=5.5, scale=17), 55, 260))
    # Land Only
    return float(np.clip(rng.gamma(shape=5, scale=22), 40, 350))


def _sample_layout(ptype: str, area_m2: float, rng: np.random.Generator) -> str:
    """Pick a plausible layout given area and property type."""
    if ptype == "Land Only":
        return "-"
    # Bias layout by size
    if area_m2 < 25:
        choices = ["1R", "1K"]
    elif area_m2 < 35:
        choices = ["1K", "1DK", "1LDK"]
    elif area_m2 < 50:
        choices = ["1LDK", "2DK", "2LDK"]
    elif area_m2 < 70:
        choices = ["2LDK", "3DK", "3LDK"]
    elif area_m2 < 100:
        choices = ["3LDK", "4LDK"]
    else:
        choices = ["4LDK"]
    return rng.choice(choices)


def generate_synthetic_data(n: int = N_TRANSACTIONS, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """
    Generate a deterministic synthetic transaction dataset modeled after
    real Tokyo market statistics. Reproducible with fixed seed.
    """
    rng = np.random.default_rng(seed)
    ward_names = list(TOKYO_WARDS.keys())
    ward_weights = np.array([TOKYO_WARDS[w]["activity"] for w in ward_names], dtype=float)
    ward_weights /= ward_weights.sum()

    ptypes = list(PROPERTY_TYPE_WEIGHTS.keys())
    ptype_probs = np.array([PROPERTY_TYPE_WEIGHTS[p] for p in ptypes], dtype=float)

    rows = []
    years = np.arange(START_YEAR, END_YEAR + 1)
    for i in range(n):
        ward = rng.choice(ward_names, p=ward_weights)
        winfo = TOKYO_WARDS[ward]
        ptype = rng.choice(ptypes, p=ptype_probs)

        # Transaction year (slight recent skew — more data in recent years)
        year_weights = np.array([0.17, 0.18, 0.20, 0.22, 0.23])
        tx_year = int(rng.choice(years, p=year_weights))
        tx_quarter = int(rng.integers(1, 5))

        # Year built: apartments 1980-2023, new house always 2023-2024
        if ptype == "New House":
            year_built = int(rng.integers(tx_year - 1, tx_year + 1))
        elif ptype == "Land Only":
            year_built = None
        else:
            # Log-skewed around ~1995-2015
            year_built = int(np.clip(round(rng.normal(2005, 12)), 1975, tx_year))

        area_m2 = _sample_area(ptype, rng)
        layout = _sample_layout(ptype, area_m2, rng)

        # Station distance (minutes walk) — weighted, most properties 5-15 min
        station_min = int(np.clip(rng.gamma(shape=2.8, scale=3.5), 1, 30))
        station = rng.choice(WARD_MAIN_STATIONS[ward])

        # Price computation: base × factors × area × noise
        base = winfo["base_price"]
        price_per_m2 = (
            base
            * _yearly_market_factor(tx_year)
            * _property_type_factor(ptype)
            * _station_distance_factor(station_min)
        )
        if year_built is not None:
            price_per_m2 *= _year_built_discount(year_built, tx_year)

        # Multiplicative noise (log-normal) for realistic spread
        price_per_m2 *= float(rng.lognormal(mean=0, sigma=0.18))

        trade_price = price_per_m2 * area_m2

        # Round to plausible values
        trade_price = round(trade_price / 10000) * 10000  # round to 10k JPY
        price_per_m2 = round(price_per_m2 / 1000) * 1000  # round to 1k JPY

        rows.append({
            "ward": ward,
            "ward_ja": winfo["ja"],
            "property_type": ptype,
            "tx_year": tx_year,
            "tx_quarter": tx_quarter,
            "tx_period": f"{tx_year}-Q{tx_quarter}",
            "area_m2": round(area_m2, 1),
            "layout": layout,
            "year_built": year_built,
            "building_age": (tx_year - year_built) if year_built else None,
            "nearest_station": station,
            "station_minutes": station_min,
            "trade_price_jpy": int(trade_price),
            "price_per_m2_jpy": int(price_per_m2),
            "lat": winfo["lat"],
            "lon": winfo["lon"],
        })

    df = pd.DataFrame(rows)
    return df


# ──────────────────────────────────────────────────────────────────
# MLIT API BACKEND
# ──────────────────────────────────────────────────────────────────

_MLIT_URL = "https://www.reinfolib.mlit.go.jp/ex-api/external/XIT001"
_TOKYO_AREA = "13"

# Tokyo 23-ward JIS municipality codes → English ward name
_MUNICIPALITY_TO_WARD: dict[str, str] = {
    "13101": "Chiyoda",  "13102": "Chuo",      "13103": "Minato",
    "13104": "Shinjuku", "13105": "Bunkyo",    "13106": "Taito",
    "13107": "Sumida",   "13108": "Koto",      "13109": "Shinagawa",
    "13110": "Meguro",   "13111": "Ota",       "13112": "Setagaya",
    "13113": "Shibuya",  "13114": "Nakano",    "13115": "Suginami",
    "13116": "Toshima",  "13117": "Kita",      "13118": "Arakawa",
    "13119": "Itabashi", "13120": "Nerima",    "13121": "Adachi",
    "13122": "Katsushika", "13123": "Edogawa",
}

# MLIT "Type" field (English, language=en) → our property_type
_TYPE_MAP: dict[str, str] = {
    "Pre-owned Condominiums, etc.":       "Used Apartment",
    "Pre-owned Detached House":           "Used House",
    "Newly Built Detached House":         "New House",
    "Residential Land(Land)":             "Land Only",
    "Residential Land(Land and Building)": "Used House",
    # Japanese fallbacks (if language param is ignored)
    "中古マンション等": "Used Apartment",
    "中古戸建":         "Used House",
    "新築戸建":         "New House",
    "宅地(土地)":      "Land Only",
    "宅地(土地と建物)": "Used House",
}

# Japanese era base years for BuildingYear parsing
_ERA_BASE = {"明治": 1868, "大正": 1912, "昭和": 1926, "平成": 1989, "令和": 2019}

MAJOR_CITIES: dict[str, dict] = {
    "Tokyo":    {"code": "13", "name_ja": "東京都",  "lat": 35.69, "lon": 139.69},
    "Osaka":    {"code": "27", "name_ja": "大阪府",  "lat": 34.69, "lon": 135.50},
    "Yokohama": {"code": "14", "name_ja": "神奈川県", "lat": 35.45, "lon": 139.64},
    "Nagoya":   {"code": "23", "name_ja": "愛知県",  "lat": 35.18, "lon": 136.91},
    "Sapporo":  {"code": "01", "name_ja": "北海道",  "lat": 43.06, "lon": 141.35},
    "Fukuoka":  {"code": "40", "name_ja": "福岡県",  "lat": 33.61, "lon": 130.42},
    "Kyoto":    {"code": "26", "name_ja": "京都府",  "lat": 35.02, "lon": 135.76},
    "Kobe":     {"code": "28", "name_ja": "兵庫県",  "lat": 34.69, "lon": 135.18},
}


def _parse_year_built(raw: str | None) -> int | None:
    if not raw or raw in ("-", "戦前", "Pre-War"):
        return None
    m = re.match(r"(\d{4})年?", raw)
    if m:
        return int(m.group(1))
    for era, base in _ERA_BASE.items():
        m = re.match(rf"{era}(\d+)年?", raw)
        if m:
            return base + int(m.group(1)) - 1
    return None


def _parse_period(raw: str | None, fallback_year: int, fallback_q: int) -> tuple[int, int]:
    if raw:
        m = re.match(r"(\d{4})年第(\d)四半期", raw)
        if m:
            return int(m.group(1)), int(m.group(2))
        m = re.match(r"(\d{4})-Q(\d)", raw)
        if m:
            return int(m.group(1)), int(m.group(2))
    return fallback_year, fallback_q


def _fetch_quarter(api_key: str, year: int, quarter: int, pref_code: str = _TOKYO_AREA) -> list[dict]:
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    params = {"year": str(year), "quarter": str(quarter), "area": pref_code, "language": "en"}
    resp = requests.get(_MLIT_URL, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    try:
        data = resp.json()
    except Exception:
        data = json.loads(gzip.decompress(resp.content))
    return data.get("data", [])


def load_from_mlit_api(api_key: str) -> pd.DataFrame:
    """
    Fetch real transaction data from MLIT Real Estate Information Library (XIT001).
    Covers START_YEAR up to the last published MLIT quarter (~2 quarter lag).
    Returns a DataFrame matching the schema of generate_synthetic_data().
    """
    rows: list[dict] = []
    last_year, last_quarter = _last_available_period()

    for year in range(START_YEAR, last_year + 1):
        for quarter in range(1, 5):
            if year == last_year and quarter > last_quarter:
                continue
            try:
                records = _fetch_quarter(api_key, year, quarter)
            except Exception as exc:
                print(f"[MLIT] Warning: {year}-Q{quarter} failed — {exc}")
                records = []

            for rec in records:
                ward = _MUNICIPALITY_TO_WARD.get(str(rec.get("MunicipalityCode", "")))
                if ward is None:
                    continue

                ptype = _TYPE_MAP.get(rec.get("Type", ""))
                if ptype is None:
                    continue

                try:
                    area_m2 = float(rec.get("Area") or rec.get("TotalFloorArea") or 0)
                except (TypeError, ValueError):
                    area_m2 = 0.0
                if area_m2 <= 0:
                    continue

                try:
                    trade_price = float(rec.get("TradePrice") or 0)
                except (TypeError, ValueError):
                    trade_price = 0.0
                if trade_price <= 0:
                    continue

                try:
                    price_per_m2 = float(rec.get("UnitPrice") or 0)
                except (TypeError, ValueError):
                    price_per_m2 = 0.0
                if price_per_m2 <= 0:
                    price_per_m2 = trade_price / area_m2

                tx_year, tx_quarter = _parse_period(rec.get("Period"), year, quarter)
                year_built = _parse_year_built(rec.get("BuildingYear"))
                layout = rec.get("FloorPlan") or "-"

                winfo = TOKYO_WARDS[ward]
                rows.append({
                    "ward":             ward,
                    "ward_ja":          winfo["ja"],
                    "property_type":    ptype,
                    "tx_year":          tx_year,
                    "tx_quarter":       tx_quarter,
                    "tx_period":        f"{tx_year}-Q{tx_quarter}",
                    "area_m2":          round(area_m2, 1),
                    "layout":           layout,
                    "year_built":       year_built,
                    "building_age":     (tx_year - year_built) if year_built else None,
                    "nearest_station":  None,
                    "station_minutes":  None,
                    "trade_price_jpy":  int(trade_price),
                    "price_per_m2_jpy": int(price_per_m2),
                    "lat":              winfo["lat"],
                    "lon":              winfo["lon"],
                })

            time.sleep(0.4)  # respect MLIT rate limits

    if not rows:
        raise RuntimeError("MLIT API returned no usable records for Tokyo 23 wards (2020-2024).")

    return pd.DataFrame(rows)


def load_city_data(pref_code: str, api_key: str) -> pd.DataFrame:
    """
    Fetch transaction data for any Japanese prefecture from MLIT XIT001.
    Returns a city (municipality) level DataFrame — not ward-level.
    Schema: prefecture_code, city, property_type, tx_year, tx_quarter, tx_period,
            area_m2, layout, year_built, building_age, trade_price_jpy, price_per_m2_jpy
    """
    rows: list[dict] = []
    last_year, last_quarter = _last_available_period()

    for year in range(START_YEAR, last_year + 1):
        for quarter in range(1, 5):
            if year == last_year and quarter > last_quarter:
                continue
            try:
                records = _fetch_quarter(api_key, year, quarter, pref_code=pref_code)
            except Exception as exc:
                print(f"[MLIT] Warning: {pref_code} {year}-Q{quarter} failed — {exc}")
                records = []

            for rec in records:
                ptype = _TYPE_MAP.get(rec.get("Type", ""))
                if ptype is None:
                    continue
                try:
                    area_m2 = float(rec.get("Area") or rec.get("TotalFloorArea") or 0)
                except (TypeError, ValueError):
                    area_m2 = 0.0
                if area_m2 <= 0:
                    continue
                try:
                    trade_price = float(rec.get("TradePrice") or 0)
                except (TypeError, ValueError):
                    trade_price = 0.0
                if trade_price <= 0:
                    continue
                try:
                    price_per_m2 = float(rec.get("UnitPrice") or 0)
                except (TypeError, ValueError):
                    price_per_m2 = 0.0
                if price_per_m2 <= 0:
                    price_per_m2 = trade_price / area_m2

                tx_year, tx_quarter_val = _parse_period(rec.get("Period"), year, quarter)
                year_built = _parse_year_built(rec.get("BuildingYear"))

                rows.append({
                    "prefecture_code": pref_code,
                    "city":            str(rec.get("Municipality") or rec.get("MunicipalityCode") or ""),
                    "property_type":   ptype,
                    "tx_year":         tx_year,
                    "tx_quarter":      tx_quarter_val,
                    "tx_period":       f"{tx_year}-Q{tx_quarter_val}",
                    "area_m2":         round(area_m2, 1),
                    "layout":          rec.get("FloorPlan") or "-",
                    "year_built":      year_built,
                    "building_age":    (tx_year - year_built) if year_built else None,
                    "trade_price_jpy": int(trade_price),
                    "price_per_m2_jpy": int(price_per_m2),
                })
            time.sleep(0.4)

    if not rows:
        raise RuntimeError(f"MLIT API returned no data for prefecture {pref_code}.")
    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# ──────────────────────────────────────────────────────────────────

def load_data() -> pd.DataFrame:
    """
    Load transaction data from the configured source.
    Controlled by env var DATA_SOURCE ('synthetic' | 'mlit_api').
    Defaults to 'synthetic'.
    """
    source = os.environ.get("DATA_SOURCE", "synthetic").lower()
    if source == "mlit_api":
        key = os.environ.get("MLIT_API_KEY", "")
        if not key:
            raise RuntimeError("DATA_SOURCE=mlit_api but MLIT_API_KEY is not set.")
        return load_from_mlit_api(key)
    return generate_synthetic_data()


def data_source_label() -> str:
    """Human-readable label for the current data source (shown in UI footer)."""
    source = os.environ.get("DATA_SOURCE", "synthetic").lower()
    if source == "mlit_api":
        return "Official MLIT Real Estate Information Library API"
    return "Demo data modeled after MLIT public statistics (2020–2024)"
