"""
City Comparison â€” compare real estate trends across Japanese cities using MLIT API data.
"""
from __future__ import annotations

import os
import pandas as pd
import plotly.express as px
import streamlit as st

from utils.data_loader import load_city_data, MAJOR_CITIES
from utils.analytics import format_jpy, format_ppm2
from utils.styles import inject_css, page_header, section_title, callout, kpi_card, footer, plotly_base, year_ticks, nav_top
from utils.prefecture_data import NATIONAL_AVG_PPM2

st.set_page_config(page_title="City Comparison Â· Japan RE", page_icon="ðŸ™ï¸", layout="wide", initial_sidebar_state="collapsed")
inject_css()
nav_top("city")

api_key = os.environ.get("MLIT_API_KEY", "")

page_header(
    eyebrow="Japan Real Estate Intelligence Â· City Comparison",
    title="Compare Cities Side by Side",
    desc=(
        "Select 2 to 5 Japanese cities and compare their real estate markets using transaction-level "
        "data from the Ministry of Land, Infrastructure, Transport and Tourism (MLIT). "
        "Each data point is an actual property transaction registered with the government â€” "
        "not an index or estimate."
    ),
    badges=["â— Live MLIT API" if api_key else "Demo Data", "Up to 5 cities"],
)

if not api_key:
    callout(
        "Live MLIT API key not configured â€” showing <strong>estimated placeholder data</strong> for illustration. "
        "Set the <code>MLIT_API_KEY</code> secret in Streamlit Cloud to enable real transaction data.",
        variant="neg",
    )

city_names = list(MAJOR_CITIES.keys())
selected_cities = st.multiselect(
    "Select cities to compare (2â€“5)",
    options=city_names,
    default=["Tokyo", "Osaka", "Fukuoka"],
    max_selections=5,
)

if len(selected_cities) < 2:
    st.info("Select at least 2 cities to compare.")
    st.stop()


@st.cache_data(ttl=7200)
def _load_city(pref_code: str, city_name: str) -> pd.DataFrame:
    return load_city_data(pref_code, os.environ.get("MLIT_API_KEY", ""), start_year=2022)


def _placeholder_df(city_name: str) -> pd.DataFrame:
    from utils.prefecture_data import PREFECTURES
    code_to_ppm2 = {str(k): v["price_ppm2_2024"] for k, v in PREFECTURES.items()}
    pref_code = MAJOR_CITIES[city_name]["code"]
    base_ppm2 = code_to_ppm2.get(pref_code.lstrip("0") or pref_code, 300000)
    rows = []
    for yr in range(2022, 2025):
        for q in range(1, 5):
            rows.append({
                "prefecture_code": pref_code, "city": city_name,
                "property_type": "Used Apartment", "tx_year": yr, "tx_quarter": q,
                "tx_period": f"{yr}-Q{q}", "area_m2": 55.0, "layout": "2LDK",
                "year_built": 2010, "building_age": yr - 2010,
                "trade_price_jpy": int(base_ppm2 * 55), "price_per_m2_jpy": base_ppm2,
            })
    return pd.DataFrame(rows)


CITY_COLORS = ["#3B82F6", "#F59E0B", "#EF4444", "#8B5CF6", "#10B981"]

city_frames: dict[str, pd.DataFrame] = {}
cities_to_load = [c for c in selected_cities if api_key]
if cities_to_load:
    load_bar = st.progress(0, text="Loading city data from MLIT APIâ€¦")
for idx, city in enumerate(selected_cities):
    if not api_key:
        city_frames[city] = _placeholder_df(city)
    else:
        load_bar.progress((idx) / len(selected_cities), text=f"Loading {city} from MLIT APIâ€¦ ({idx+1}/{len(selected_cities)})")
        try:
            df_city = _load_city(MAJOR_CITIES[city]["code"], city)
            df_city["city_name"] = city
            city_frames[city] = df_city
        except Exception as exc:
            st.warning(f"Could not load {city}: {exc} â€” showing estimate instead.")
            city_frames[city] = _placeholder_df(city)
if cities_to_load:
    load_bar.empty()

if not city_frames:
    st.error("No city data available.")
    st.stop()


# â”€â”€ KPI comparison â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
section_title("Key metrics at a glance", "Latest available year vs prior year")
kpi_cols = st.columns(len(selected_cities))
city_medians: dict[str, int] = {}

for i, city in enumerate(selected_cities):
    df_c = city_frames[city]
    med_ppm2  = int(df_c["price_per_m2_jpy"].median())
    med_price = int(df_c["trade_price_jpy"].median())
    n_tx      = len(df_c)
    latest_yr = df_c["tx_year"].max()
    prev_yr   = latest_yr - 1
    p_lat  = df_c[df_c["tx_year"] == latest_yr]["price_per_m2_jpy"].median()
    p_prev = df_c[df_c["tx_year"] == prev_yr]["price_per_m2_jpy"].median()
    yoy    = ((p_lat - p_prev) / p_prev * 100) if (p_prev and p_prev > 0) else 0.0
    city_medians[city] = med_ppm2
    with kpi_cols[i]:
        kpi_card(city, format_ppm2(med_ppm2), f"Median {format_jpy(med_price)} Â· YoY {yoy:+.1f}%", accent=(i == 0))
        st.caption(f"{n_tx:,} transactions")


# â”€â”€ Price trend â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
section_title(
    "Price trend comparison",
    "Median Â¥/mÂ² per quarter. Only year labels shown on the axis to keep it readable.",
)

all_trends = []
for city in selected_cities:
    trend = (
        city_frames[city]
        .groupby("tx_period")["price_per_m2_jpy"]
        .median().reset_index()
        .rename(columns={"price_per_m2_jpy": "median_ppm2"})
    )
    trend["city_name"] = city
    all_trends.append(trend)

combined_trend = pd.concat(all_trends, ignore_index=True).sort_values("tx_period")
all_periods = sorted(combined_trend["tx_period"].unique().tolist())
tick_vals, tick_texts = year_ticks(all_periods)

base, grid, _ = plotly_base(380)
fig_trend = px.line(
    combined_trend, x="tx_period", y="median_ppm2", color="city_name", markers=True,
    labels={"tx_period": "", "median_ppm2": "Median Â¥/mÂ²", "city_name": ""},
    color_discrete_sequence=CITY_COLORS,
)
fig_trend.update_layout(
    **base,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
fig_trend.update_xaxes(tickvals=tick_vals, ticktext=tick_texts, showgrid=False)
fig_trend.update_yaxes(gridcolor=grid, tickformat=",.0f")
fig_trend.update_traces(hovertemplate="%{fullData.name}<br>%{x}<br>Â¥/mÂ²: %{y:,.0f}<extra></extra>")
st.plotly_chart(fig_trend, use_container_width=True, config={"scrollZoom": False, "doubleClick": False, "displayModeBar": False})


# â”€â”€ Bar + property type â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
col_left, col_right = st.columns(2)

with col_left:
    section_title("Median Â¥/mÂ² by city", "Latest full year")
    bar_data = []
    for city in selected_cities:
        df_c = city_frames[city]
        latest_yr = df_c["tx_year"].max()
        med = int(df_c[df_c["tx_year"] == latest_yr]["price_per_m2_jpy"].median())
        bar_data.append({"city": city, "median_ppm2": med})
    bar_df = pd.DataFrame(bar_data).sort_values("median_ppm2", ascending=True)

    base2, grid2, _ = plotly_base(300)
    fig_bar = px.bar(
        bar_df, x="median_ppm2", y="city", orientation="h",
        color="median_ppm2",
        color_continuous_scale=["#BFDBFE", "#3B82F6", "#1D4ED8"],
        labels={"median_ppm2": "Â¥/mÂ²", "city": ""},
    )
    fig_bar.update_layout(**base2)
    fig_bar.update_coloraxes(showscale=False)
    fig_bar.update_xaxes(gridcolor=grid2, tickformat=",.0f")
    fig_bar.update_traces(hovertemplate="%{y}<br>Â¥/mÂ²: %{x:,.0f}<extra></extra>")
    st.plotly_chart(fig_bar, use_container_width=True, config={"scrollZoom": False, "doubleClick": False, "displayModeBar": False})

with col_right:
    section_title("Property type mix", "Share of total transactions")
    type_rows = []
    for city in selected_cities:
        counts = city_frames[city]["property_type"].value_counts(normalize=True).reset_index()
        counts.columns = ["property_type", "share"]
        counts["city"] = city
        type_rows.append(counts)
    type_df = pd.concat(type_rows, ignore_index=True)

    base3, grid3, _ = plotly_base(300)
    fig_type = px.bar(
        type_df, x="share", y="city", color="property_type",
        orientation="h", barmode="stack",
        labels={"share": "Share", "city": "", "property_type": ""},
        color_discrete_sequence=["#3B82F6", "#F59E0B", "#EF4444", "#8B5CF6"],
    )
    fig_type.update_layout(
        **base3,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig_type.update_xaxes(gridcolor=grid3, tickformat=".0%")
    fig_type.update_traces(hovertemplate="%{fullData.name}<br>%{y}<br>Share: %{x:.0%}<extra></extra>")
    st.plotly_chart(fig_type, use_container_width=True, config={"scrollZoom": False, "doubleClick": False, "displayModeBar": False})


# â”€â”€ Auto insight â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if "Tokyo" in city_medians:
    tokyo_ppm2    = city_medians["Tokyo"]
    cheapest_city = min(city_medians, key=city_medians.get)
    cheapest_ppm2 = city_medians[cheapest_city]
    nat_avg       = NATIONAL_AVG_PPM2[2024]
    callout(
        f"Tokyo's median Â¥/mÂ² (<strong>{format_ppm2(tokyo_ppm2)}</strong>) is "
        f"<strong>{tokyo_ppm2/nat_avg:.1f}Ã—</strong> the national average and "
        f"<strong>{tokyo_ppm2/cheapest_ppm2:.1f}Ã—</strong> that of the most affordable city in this comparison "
        f"(<strong>{cheapest_city}</strong> at {format_ppm2(cheapest_ppm2)})."
    )
elif city_medians:
    most_exp  = max(city_medians, key=city_medians.get)
    cheapest  = min(city_medians, key=city_medians.get)
    callout(
        f"<strong>{most_exp}</strong> leads this comparison at {format_ppm2(city_medians[most_exp])}, "
        f"which is <strong>{city_medians[most_exp]/city_medians[cheapest]:.1f}Ã—</strong> the median of "
        f"<strong>{cheapest}</strong> ({format_ppm2(city_medians[cheapest])})."
    )

footer("City Comparison")
