"""
Analytics helpers — stats, aggregations, and the price estimator model.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def ward_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Per-ward aggregates for map and overview tables."""
    agg = df.groupby("ward").agg(
        n_transactions=("trade_price_jpy", "size"),
        median_price=("trade_price_jpy", "median"),
        median_ppm2=("price_per_m2_jpy", "median"),
        mean_ppm2=("price_per_m2_jpy", "mean"),
        median_area=("area_m2", "median"),
    ).reset_index()
    agg["median_price_musd"] = agg["median_price"] / 1_000_000
    return agg.sort_values("median_ppm2", ascending=False)


def yoy_growth(df: pd.DataFrame, ward: str | None = None) -> float:
    """Year-over-year median price/m² growth using the last 2 available years."""
    d = df if ward is None else df[df["ward"] == ward]
    available_years = sorted(d["tx_year"].dropna().unique())
    if len(available_years) < 2:
        return 0.0
    y_curr, y_prev = available_years[-1], available_years[-2]
    p_prev = d[d["tx_year"] == y_prev]["price_per_m2_jpy"].median()
    p_curr = d[d["tx_year"] == y_curr]["price_per_m2_jpy"].median()
    if pd.isna(p_prev) or pd.isna(p_curr) or p_prev == 0:
        return 0.0
    return float((p_curr - p_prev) / p_prev * 100)


def price_trend(df: pd.DataFrame, ward: str | None = None) -> pd.DataFrame:
    """Median price/m² trend by year-quarter."""
    d = df if ward is None else df[df["ward"] == ward]
    trend = d.groupby("tx_period").agg(
        median_ppm2=("price_per_m2_jpy", "median"),
        n=("trade_price_jpy", "size"),
    ).reset_index().sort_values("tx_period")
    return trend


def top_stations(df: pd.DataFrame, ward: str | None = None, n: int = 10) -> pd.DataFrame:
    """Top stations by median price/m² (within a ward if specified)."""
    d = df if ward is None else df[df["ward"] == ward]
    g = d.groupby("nearest_station").agg(
        median_ppm2=("price_per_m2_jpy", "median"),
        n_transactions=("trade_price_jpy", "size"),
    ).reset_index()
    g = g[g["n_transactions"] >= 5]
    return g.sort_values("median_ppm2", ascending=False).head(n)


def layout_distribution(df: pd.DataFrame, ward: str | None = None) -> pd.DataFrame:
    """Layout distribution (apartments + houses)."""
    d = df if ward is None else df[df["ward"] == ward]
    d = d[d["layout"] != "-"]
    return (
        d["layout"].value_counts()
        .reindex(["1R", "1K", "1DK", "1LDK", "2DK", "2LDK", "3DK", "3LDK", "4LDK"])
        .fillna(0)
        .astype(int)
        .reset_index()
        .rename(columns={"index": "layout", "count": "n"})
    )


# ──────────────────────────────────────────────────────────────────
# NEIGHBORHOOD INTELLIGENCE
# ──────────────────────────────────────────────────────────────────

def neighborhood_summary(df: pd.DataFrame, ward: str | None = None) -> pd.DataFrame:
    """
    Per-district aggregates within a ward (requires MLIT API live data).
    Returns empty DataFrame if no district data available.
    """
    d = df if ward is None else df[df["ward"] == ward]
    if "district" not in d.columns:
        return pd.DataFrame()
    d = d[d["district"].notna() & (d["district"] != "")]
    if d.empty:
        return pd.DataFrame()
    agg = d.groupby("district").agg(
        n_transactions=("trade_price_jpy", "size"),
        median_ppm2=("price_per_m2_jpy", "median"),
        median_price=("trade_price_jpy", "median"),
        median_area=("area_m2", "median"),
    ).reset_index()
    agg = agg[agg["n_transactions"] >= 3]
    city_median = d["price_per_m2_jpy"].median()
    agg["premium_pct"] = (agg["median_ppm2"] / city_median - 1) * 100
    return agg.sort_values("median_ppm2", ascending=False)


# ──────────────────────────────────────────────────────────────────
# INVESTMENT SIGNALS
# ──────────────────────────────────────────────────────────────────

def investment_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Per-ward investment signal combining price momentum, volume trend, and
    relative affordability into a 0–100 value score.

    Columns returned: ward, momentum_pct, volume_trend_pct, n_transactions,
                      median_ppm2, price_relative, value_score, signal
    """
    available_years = sorted(df["tx_year"].dropna().unique())
    if len(available_years) < 2:
        return pd.DataFrame()

    y_curr, y_prev = available_years[-1], available_years[-2]
    city_median = df["price_per_m2_jpy"].median()

    results = []
    for ward in df["ward"].unique():
        ward_df = df[df["ward"] == ward]

        p_prev = ward_df[ward_df["tx_year"] == y_prev]["price_per_m2_jpy"].median()
        p_curr = ward_df[ward_df["tx_year"] == y_curr]["price_per_m2_jpy"].median()
        if pd.isna(p_prev) or pd.isna(p_curr) or p_prev == 0:
            momentum = 0.0
        else:
            momentum = float((p_curr - p_prev) / p_prev * 100)

        n_prev = len(ward_df[ward_df["tx_year"] == y_prev])
        n_curr = len(ward_df[ward_df["tx_year"] == y_curr])
        vol_trend = float((n_curr - n_prev) / n_prev * 100) if n_prev > 0 else 0.0

        median_ppm2 = float(ward_df["price_per_m2_jpy"].median())
        results.append({
            "ward":              ward,
            "momentum_pct":      momentum,
            "volume_trend_pct":  vol_trend,
            "n_transactions":    len(ward_df),
            "median_ppm2":       median_ppm2,
            "price_relative":    median_ppm2 / city_median if city_median > 0 else 1.0,
        })

    if not results:
        return pd.DataFrame()

    sig_df = pd.DataFrame(results)

    # Normalise both dimensions to [0, 1]
    m_min, m_max = sig_df["momentum_pct"].min(), sig_df["momentum_pct"].max()
    p_min, p_max = sig_df["price_relative"].min(), sig_df["price_relative"].max()
    momentum_norm  = (sig_df["momentum_pct"] - m_min)   / (m_max - m_min   + 1e-9)
    price_inv_norm = 1 - (sig_df["price_relative"] - p_min) / (p_max - p_min + 1e-9)

    sig_df["value_score"] = (momentum_norm * 0.6 + price_inv_norm * 0.4) * 100

    def _signal(row: pd.Series) -> str:
        if row["momentum_pct"] >= 5 and row["value_score"] >= 60:
            return "🚀 Strong Buy"
        if row["momentum_pct"] >= 2 and row["value_score"] >= 45:
            return "📈 Bullish"
        if row["momentum_pct"] <= -3:
            return "📉 Bearish"
        if row["value_score"] >= 55:
            return "💎 Value Play"
        return "➡️ Neutral"

    sig_df["signal"] = sig_df.apply(_signal, axis=1)
    return sig_df.sort_values("value_score", ascending=False).reset_index(drop=True)


# ──────────────────────────────────────────────────────────────────
# PROPERTY DNA
# ──────────────────────────────────────────────────────────────────

def structure_premium(df: pd.DataFrame) -> pd.DataFrame:
    """
    Median price/m² and relative premium by building structure type.
    Returns empty DataFrame when structure data isn't available (synthetic mode).
    """
    if "structure" not in df.columns or df["structure"].isna().all():
        return pd.DataFrame()
    d = df[df["structure"].notna()]
    agg = d.groupby("structure").agg(
        n_transactions=("trade_price_jpy", "size"),
        median_ppm2=("price_per_m2_jpy", "median"),
        median_age=("building_age", "median"),
    ).reset_index()
    agg = agg[agg["n_transactions"] >= 10]
    city_median = d["price_per_m2_jpy"].median()
    agg["premium_pct"] = (agg["median_ppm2"] / city_median - 1) * 100
    return agg.sort_values("median_ppm2", ascending=False)


def direction_premium(df: pd.DataFrame) -> pd.DataFrame:
    """
    Median price/m² premium by compass direction the property faces.
    Returns empty DataFrame when direction data isn't available.
    """
    if "direction" not in df.columns or df["direction"].isna().all():
        return pd.DataFrame()
    d = df[df["direction"].notna() & (df["direction"] != "")]
    if d.empty:
        return pd.DataFrame()
    agg = d.groupby("direction").agg(
        n_transactions=("trade_price_jpy", "size"),
        median_ppm2=("price_per_m2_jpy", "median"),
    ).reset_index()
    agg = agg[agg["n_transactions"] >= 10]
    if agg.empty:
        return pd.DataFrame()
    city_median = d["price_per_m2_jpy"].median()
    agg["premium_pct"] = (agg["median_ppm2"] / city_median - 1) * 100
    return agg.sort_values("median_ppm2", ascending=False)


def renovation_premium(df: pd.DataFrame) -> dict:
    """
    Price premium for renovated vs non-renovated properties.
    Returns empty dict when renovation data isn't available.
    """
    if "renovation" not in df.columns or df["renovation"].isna().all():
        return {}
    d = df[df["renovation"].notna() & (df["renovation"] != "")]
    if d.empty:
        return {}

    _RENOV_PATTERN = r"(?i)renovation|done|有|改装|リノベ"
    renovated     = d[d["renovation"].str.contains(_RENOV_PATTERN, na=False)]
    not_renovated = d[~d["renovation"].str.contains(_RENOV_PATTERN, na=False)]

    if len(renovated) < 5 or len(not_renovated) < 5:
        return {}

    med_r  = float(renovated["price_per_m2_jpy"].median())
    med_nr = float(not_renovated["price_per_m2_jpy"].median())
    premium = (med_r / med_nr - 1) * 100 if med_nr > 0 else 0.0

    return {
        "n_renovated":             len(renovated),
        "n_not_renovated":         len(not_renovated),
        "median_ppm2_renovated":   med_r,
        "median_ppm2_not_renovated": med_nr,
        "premium_pct":             premium,
    }


# ──────────────────────────────────────────────────────────────────
# PRICE ESTIMATOR
# ──────────────────────────────────────────────────────────────────

def estimate_price(
    df: pd.DataFrame,
    ward: str,
    area_m2: float,
    year_built: int,
    station_minutes: int,
    property_type: str = "Used Apartment",
    structure: str | None = None,
    direction: str | None = None,
    renovated: bool = False,
) -> dict:
    """
    Lightweight k-NN price estimator. Finds comparable transactions via a
    weighted distance score on (area, age, station, structure, direction,
    renovation) and returns P10/P50/P90 estimates.
    """
    building_age = None if property_type == "Land Only" else (2024 - year_built)

    comps = df[(df["ward"] == ward) & (df["property_type"] == property_type)].copy()
    if len(comps) < 20:
        comps = df[df["property_type"] == property_type].copy()

    score = np.zeros(len(comps))

    # Core features
    score += np.abs(comps["area_m2"] - area_m2) / max(area_m2, 1)
    if comps["station_minutes"].notna().any():
        score += (comps["station_minutes"].fillna(station_minutes) - station_minutes).abs() / 10
    if building_age is not None and "building_age" in comps.columns:
        score += (comps["building_age"] - building_age).abs().fillna(1.0) / 10

    # Extended features (only applied when MLIT API data is present)
    if structure and "structure" in comps.columns and comps["structure"].notna().any():
        score += (comps["structure"] != structure).astype(float) * 0.5
    if direction and "direction" in comps.columns and comps["direction"].notna().any():
        score += (comps["direction"] != direction).astype(float) * 0.2
    if renovated and "renovation" in comps.columns and comps["renovation"].notna().any():
        _RENOV = r"(?i)renovation|done|有|改装|リノベ"
        is_renov = comps["renovation"].str.contains(_RENOV, na=False)
        score += (~is_renov).astype(float) * 0.3

    comps = comps.assign(_score=score).sort_values("_score")
    nearest = comps.head(max(50, int(len(comps) * 0.05)))

    ppm2_p10 = float(nearest["price_per_m2_jpy"].quantile(0.10))
    ppm2_p50 = float(nearest["price_per_m2_jpy"].quantile(0.50))
    ppm2_p90 = float(nearest["price_per_m2_jpy"].quantile(0.90))

    return {
        "ppm2_p10": ppm2_p10,
        "ppm2_p50": ppm2_p50,
        "ppm2_p90": ppm2_p90,
        "total_p10": ppm2_p10 * area_m2,
        "total_p50": ppm2_p50 * area_m2,
        "total_p90": ppm2_p90 * area_m2,
        "n_comparables": len(nearest),
    }


# ──────────────────────────────────────────────────────────────────
# FORMATTERS
# ──────────────────────────────────────────────────────────────────

def format_jpy(value: float, short: bool = True) -> str:
    if pd.isna(value):
        return "—"
    if short:
        if value >= 100_000_000:
            return f"¥{value/100_000_000:.2f}億"
        if value >= 10_000_000:
            return f"¥{value/10_000_000:.1f}千万"
        if value >= 10_000:
            return f"¥{value/10_000:.0f}万"
    return f"¥{value:,.0f}"


def format_ppm2(value: float) -> str:
    if pd.isna(value):
        return "—"
    return f"¥{value/10000:.0f}万/m²"
