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
    agg["median_price_musd"] = agg["median_price"] / 1_000_000  # million JPY
    return agg.sort_values("median_ppm2", ascending=False)


def yoy_growth(df: pd.DataFrame, ward: str | None = None) -> float:
    """Year-over-year median price/m² growth (2024 vs 2023)."""
    d = df if ward is None else df[df["ward"] == ward]
    p23 = d[d["tx_year"] == 2023]["price_per_m2_jpy"].median()
    p24 = d[d["tx_year"] == 2024]["price_per_m2_jpy"].median()
    if pd.isna(p23) or pd.isna(p24) or p23 == 0:
        return 0.0
    return float((p24 - p23) / p23 * 100)


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
    g = g[g["n_transactions"] >= 5]  # filter thin samples
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


def estimate_price(
    df: pd.DataFrame,
    ward: str,
    area_m2: float,
    year_built: int,
    station_minutes: int,
    property_type: str = "Used Apartment",
) -> dict:
    """
    Lightweight price estimator: finds comparable transactions using
    a nearest-neighbor heuristic on (ward, property_type, age, distance)
    and returns p10 / p50 / p90 price estimates.

    Keeps it explainable (no opaque ML model needed for a demo).
    """
    if property_type == "Land Only":
        building_age = None
    else:
        building_age = 2024 - year_built

    # Filter to same ward + property type
    comps = df[(df["ward"] == ward) & (df["property_type"] == property_type)].copy()
    if len(comps) < 20:
        comps = df[df["property_type"] == property_type].copy()

    # Similarity score (lower is better)
    score = np.zeros(len(comps))
    # Area proximity
    score += np.abs(comps["area_m2"] - area_m2) / max(area_m2, 1)
    # Station distance proximity
    score += np.abs(comps["station_minutes"] - station_minutes) / 10
    # Age proximity (if applicable)
    if building_age is not None and "building_age" in comps.columns:
        age_diff = (comps["building_age"] - building_age).abs() / 10
        score += age_diff.fillna(1.0)

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


def format_jpy(value: float, short: bool = True) -> str:
    """Format JPY as human-readable string."""
    if pd.isna(value):
        return "—"
    if short:
        if value >= 100_000_000:  # 1億
            return f"¥{value/100_000_000:.2f}億"
        if value >= 10_000_000:
            return f"¥{value/10_000_000:.1f}千万"
        if value >= 10_000:
            return f"¥{value/10_000:.0f}万"
    return f"¥{value:,.0f}"


def format_ppm2(value: float) -> str:
    """Format price per square meter."""
    if pd.isna(value):
        return "—"
    return f"¥{value/10000:.0f}万/m²"
