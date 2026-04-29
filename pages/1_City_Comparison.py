"""
City Comparison — compare real estate trends across Japanese cities using MLIT API data.
"""
from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.data_loader import load_city_data, MAJOR_CITIES
from utils.analytics import price_trend, format_jpy, format_ppm2
from utils.styles import inject_css, kpi_card, plotly_defaults

st.set_page_config(page_title="City Comparison · Japan RE", page_icon="🏙️", layout="wide")
inject_css()

st.markdown("""
<div class="hero-banner">
    <div class="hero-title">🏙️ City Comparison</div>
    <div class="hero-sub">
        Compare real estate markets across Japan's major cities using official
        transaction data from the MLIT API. Select 2–5 cities to see price trends,
        market volume, and property type breakdowns side by side.
    </div>
    <span class="badge badge-live">● Live MLIT API</span>
    <span class="badge">Multi-city</span>
</div>
""", unsafe_allow_html=True)

api_key = os.environ.get("MLIT_API_KEY", "")

if not api_key:
    st.warning(
        "Live data requires the MLIT API key. Set the `MLIT_API_KEY` environment variable "
        "to enable real transaction data. Showing placeholder data below."
    )

city_names = list(MAJOR_CITIES.keys())
selected_cities = st.multiselect(
    "Select cities to compare (2–5)",
    options=city_names,
    default=["Tokyo", "Osaka", "Fukuoka"],
    max_selections=5,
)

if len(selected_cities) < 2:
    st.info("Select at least 2 cities to compare.")
    st.stop()


@st.cache_data(show_spinner=True, ttl=3600)
def _load_city(pref_code: str) -> pd.DataFrame:
    return load_city_data(pref_code, os.environ.get("MLIT_API_KEY", ""))


def _placeholder_df(city_name: str) -> pd.DataFrame:
    """Return a zero-filled placeholder when no API key is present."""
    from utils.prefecture_data import PREFECTURES
    code_to_ppm2 = {str(k): v["price_ppm2_2024"] for k, v in PREFECTURES.items()}
    pref_code = MAJOR_CITIES[city_name]["code"]
    base_ppm2 = code_to_ppm2.get(pref_code.lstrip("0") or pref_code, 300000)
    rows = []
    for yr in range(2020, 2025):
        for q in range(1, 5):
            rows.append({
                "prefecture_code": pref_code,
                "city": city_name,
                "property_type": "Used Apartment",
                "tx_year": yr,
                "tx_quarter": q,
                "tx_period": f"{yr}-Q{q}",
                "area_m2": 55.0,
                "layout": "2LDK",
                "year_built": 2010,
                "building_age": yr - 2010,
                "trade_price_jpy": int(base_ppm2 * 55),
                "price_per_m2_jpy": base_ppm2,
            })
    return pd.DataFrame(rows)


# Load data for each city
city_frames: dict[str, pd.DataFrame] = {}
CITY_COLORS = ["#177e89", "#f39c12", "#e74c3c", "#8e44ad", "#27ae60"]

for city in selected_cities:
    if not api_key:
        city_frames[city] = _placeholder_df(city)
    else:
        try:
            df_city = _load_city(MAJOR_CITIES[city]["code"])
            df_city["city_name"] = city
            city_frames[city] = df_city
        except Exception as exc:
            st.warning(f"Could not load data for {city}: {exc}")
            city_frames[city] = _placeholder_df(city)

if not city_frames:
    st.error("No city data available.")
    st.stop()


# ────────────────────────────────────────────────────────────────
# KPI comparison
# ────────────────────────────────────────────────────────────────
st.markdown("### Key metrics at a glance")
kpi_cols = st.columns(len(selected_cities))

city_medians: dict[str, int] = {}
for i, city in enumerate(selected_cities):
    df_c = city_frames[city]
    med_ppm2 = int(df_c["price_per_m2_jpy"].median())
    med_price = int(df_c["trade_price_jpy"].median())
    n_tx = len(df_c)

    latest_yr = df_c["tx_year"].max()
    prev_yr = latest_yr - 1
    p_lat = df_c[df_c["tx_year"] == latest_yr]["price_per_m2_jpy"].median()
    p_prev = df_c[df_c["tx_year"] == prev_yr]["price_per_m2_jpy"].median()
    yoy = ((p_lat - p_prev) / p_prev * 100) if (p_prev and p_prev > 0) else 0.0

    city_medians[city] = med_ppm2

    with kpi_cols[i]:
        kpi_card(city, format_ppm2(med_ppm2), f"Median price: {format_jpy(med_price)}")
        st.caption(f"{n_tx:,} transactions · YoY {yoy:+.1f}%")


# ────────────────────────────────────────────────────────────────
# Price trend comparison
# ────────────────────────────────────────────────────────────────
st.markdown("### Price trend comparison (median ¥/m²)")

all_trends = []
for city in selected_cities:
    df_c = city_frames[city]
    trend = (
        df_c.groupby("tx_period")["price_per_m2_jpy"]
        .median()
        .reset_index()
        .rename(columns={"price_per_m2_jpy": "median_ppm2"})
    )
    trend["city_name"] = city
    all_trends.append(trend)

combined_trend = pd.concat(all_trends, ignore_index=True).sort_values("tx_period")

fig_trend = px.line(
    combined_trend,
    x="tx_period",
    y="median_ppm2",
    color="city_name",
    markers=True,
    labels={"tx_period": "", "median_ppm2": "Median ¥/m²", "city_name": "City"},
    color_discrete_sequence=CITY_COLORS,
)
_layout, _grid = plotly_defaults(360)
fig_trend.update_layout(**_layout,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
fig_trend.update_xaxes(showgrid=False, tickangle=-30)
fig_trend.update_yaxes(gridcolor=_grid, tickformat=",.0f")
st.plotly_chart(fig_trend, use_container_width=True)


# ────────────────────────────────────────────────────────────────
# Bar comparison + property type breakdown
# ────────────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("**Median ¥/m² by city (latest year)**")
    bar_data = []
    for city in selected_cities:
        df_c = city_frames[city]
        latest_yr = df_c["tx_year"].max()
        med = int(df_c[df_c["tx_year"] == latest_yr]["price_per_m2_jpy"].median())
        bar_data.append({"city": city, "median_ppm2": med})
    bar_df = pd.DataFrame(bar_data).sort_values("median_ppm2", ascending=True)

    fig_bar = px.bar(
        bar_df,
        x="median_ppm2",
        y="city",
        orientation="h",
        color="median_ppm2",
        color_continuous_scale=["#84cdd4", "#177e89", "#0d2b2e"],
        labels={"median_ppm2": "¥/m²", "city": ""},
    )
    _layout, _grid = plotly_defaults(300)
    fig_bar.update_layout(**_layout, coloraxis_showscale=False)
    fig_bar.update_xaxes(gridcolor=_grid, tickformat=",.0f")
    st.plotly_chart(fig_bar, use_container_width=True)

with col_right:
    st.markdown("**Property type mix by city (% of transactions)**")
    type_rows = []
    for city in selected_cities:
        df_c = city_frames[city]
        counts = df_c["property_type"].value_counts(normalize=True).reset_index()
        counts.columns = ["property_type", "share"]
        counts["city"] = city
        type_rows.append(counts)
    type_df = pd.concat(type_rows, ignore_index=True)

    fig_type = px.bar(
        type_df,
        x="share",
        y="city",
        color="property_type",
        orientation="h",
        barmode="stack",
        labels={"share": "Share", "city": "", "property_type": ""},
        color_discrete_sequence=["#177e89", "#f39c12", "#e74c3c", "#8e44ad"],
    )
    _layout, _grid = plotly_defaults(300)
    fig_type.update_layout(**_layout,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig_type.update_xaxes(gridcolor=_grid, tickformat=".0%")
    st.plotly_chart(fig_type, use_container_width=True)


# ────────────────────────────────────────────────────────────────
# Auto insight
# ────────────────────────────────────────────────────────────────
if "Tokyo" in city_medians:
    tokyo_ppm2 = city_medians["Tokyo"]
    cheapest_city = min(city_medians, key=city_medians.get)
    cheapest_ppm2 = city_medians[cheapest_city]
    from utils.prefecture_data import NATIONAL_AVG_PPM2
    nat_avg = NATIONAL_AVG_PPM2[2024]
    ratio_national = tokyo_ppm2 / nat_avg
    ratio_cheapest = tokyo_ppm2 / cheapest_ppm2 if cheapest_city != "Tokyo" else 1.0
    st.markdown(f"""
    <div class="insight-box">
        Tokyo's median ¥/m² (<strong>{format_ppm2(tokyo_ppm2)}</strong>) is
        <strong>{ratio_national:.1f}×</strong> the national average and
        <strong>{ratio_cheapest:.1f}×</strong> that of the most affordable city in this
        comparison (<strong>{cheapest_city}</strong> at {format_ppm2(cheapest_ppm2)}).
    </div>
    """, unsafe_allow_html=True)
elif city_medians:
    most_expensive = max(city_medians, key=city_medians.get)
    cheapest_city = min(city_medians, key=city_medians.get)
    ratio = city_medians[most_expensive] / city_medians[cheapest_city]
    st.markdown(f"""
    <div class="insight-box">
        <strong>{most_expensive}</strong> leads this comparison at
        {format_ppm2(city_medians[most_expensive])}, which is
        <strong>{ratio:.1f}×</strong> the median of <strong>{cheapest_city}</strong>
        ({format_ppm2(city_medians[cheapest_city])}).
    </div>
    """, unsafe_allow_html=True)
