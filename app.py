"""
Japan Real Estate Intelligence — Landing / Intro page.
"""
from __future__ import annotations

import streamlit as st

from utils.styles import (
    inject_css, platform_hero, feature_cards,
    nav_sidebar, footer,
)
from utils.prefecture_data import get_all_as_df


st.set_page_config(
    page_title="Japan Real Estate Intelligence",
    page_icon="🗾",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
nav_sidebar()


# ── Compute headline insights from prefecture data ────────────────────────────
@st.cache_data(show_spinner=False)
def _headline_stats() -> list[tuple[str, str]]:
    df = get_all_as_df()
    df["price_change_pct"] = (
        (df["price_ppm2_2024"] - df["price_ppm2_2015"]) / df["price_ppm2_2015"] * 100
    )
    tokyo_growth   = df.loc[df["name_en"] == "Tokyo", "price_change_pct"].iloc[0]
    nat_avg_growth = df["price_change_pct"].mean()
    tokyo_2024     = df.loc[df["name_en"] == "Tokyo", "price_ppm2_2024"].iloc[0]
    nat_avg_2024   = df["price_ppm2_2024"].mean()
    tokyo_premium  = tokyo_2024 / nat_avg_2024
    high_akiya     = int((df["akiya_rate_2023"] >= 20).sum())
    return [
        (f"+{tokyo_growth:.0f}%",  f"Tokyo growth · vs +{nat_avg_growth:.0f}% national"),
        (f"{tokyo_premium:.1f}×",  "Tokyo premium · vs national avg"),
        ("9M+",                    "Vacant homes (akiya)"),
        (f"{high_akiya}",          "Prefectures > 20% vacancy"),
        ("47 / 23",                "Prefectures · Tokyo wards"),
    ]


platform_hero(stats=_headline_stats())
feature_cards()

footer("Home", "MLIT XIT001 API · Japan Housing and Land Survey · Statistics Bureau")
