"""
Tokyo Real Estate Explorer — Streamlit app

A data visualization dashboard for Tokyo's 23 Special Wards real estate market.
Built by Santiago Martinez · https://santimuru.github.io
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

from utils.data_loader import load_data, data_source_label
from utils.ward_data import TOKYO_WARDS, PROPERTY_TYPES
from utils.analytics import (
    ward_summary,
    yoy_growth,
    price_trend,
    top_stations,
    layout_distribution,
    estimate_price,
    format_jpy,
    format_ppm2,
)

# ────────────────────────────────────────────────────────────────
# Page config & styling
# ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Tokyo Real Estate Explorer",
    page_icon="🗼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS — matches portfolio aesthetic (teal accents, clean typography)
st.markdown("""
<style>
    .main .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1400px; }
    h1, h2, h3 { font-family: 'Helvetica Neue', sans-serif; letter-spacing: -0.01em; }
    h1 { color: #1a1a1a; font-weight: 700; }
    .stMetric { background: #f7f9fa; border-left: 3px solid #177e89; padding: 0.8rem 1rem; border-radius: 4px; }
    .stMetric label { font-size: 0.75rem !important; text-transform: uppercase; letter-spacing: 0.05em; color: #666 !important; }
    .stMetric [data-testid="stMetricValue"] { font-size: 1.5rem !important; color: #177e89; font-weight: 700; }
    .stTabs [data-baseweb="tab-list"] { gap: 2rem; border-bottom: 1px solid #e0e0e0; }
    .stTabs [data-baseweb="tab"] { font-size: 0.95rem; font-weight: 600; }
    .stTabs [aria-selected="true"] { color: #177e89; }
    div[data-testid="stSidebarNav"] { display: none; }
    .app-footer { margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid #e0e0e0; color: #888; font-size: 0.8rem; text-align: center; }
    .app-footer a { color: #177e89; text-decoration: none; }
</style>
""", unsafe_allow_html=True)


# ────────────────────────────────────────────────────────────────
# Data loading (cached)
# ────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading Tokyo transactions…")
def _load() -> pd.DataFrame:
    return load_data()

df_all = _load()


# ────────────────────────────────────────────────────────────────
# Header
# ────────────────────────────────────────────────────────────────
col_title, col_meta = st.columns([3, 1])
with col_title:
    st.title("🗼 Tokyo Real Estate Explorer")
    st.markdown(
        "<p style='color:#666; font-size:1.0rem; margin-top:-0.8rem;'>"
        "Interactive analysis of Tokyo's 23 Special Wards real estate market "
        "(2020–2024)</p>",
        unsafe_allow_html=True,
    )
with col_meta:
    st.metric("Transactions analyzed", f"{len(df_all):,}")


# ────────────────────────────────────────────────────────────────
# Sidebar — global filters
# ────────────────────────────────────────────────────────────────
st.sidebar.header("Filters")

years = sorted(df_all["tx_year"].unique())
year_range = st.sidebar.slider(
    "Transaction year",
    min_value=int(min(years)),
    max_value=int(max(years)),
    value=(int(min(years)), int(max(years))),
)

ptype_filter = st.sidebar.multiselect(
    "Property type",
    options=PROPERTY_TYPES,
    default=PROPERTY_TYPES,
)

area_min, area_max = st.sidebar.slider(
    "Area (m²)",
    min_value=0,
    max_value=300,
    value=(0, 300),
    step=10,
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    f"<div style='font-size:0.78rem; color:#888;'>"
    f"<b>Data source:</b><br>{data_source_label()}"
    f"</div>",
    unsafe_allow_html=True,
)

# Apply filters
df = df_all[
    (df_all["tx_year"].between(*year_range))
    & (df_all["property_type"].isin(ptype_filter))
    & (df_all["area_m2"].between(area_min, area_max))
].copy()

if df.empty:
    st.warning("No transactions match the current filters. Try widening them.")
    st.stop()


# ────────────────────────────────────────────────────────────────
# Tabs
# ────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 Market Overview", "🏙️ Ward Deep Dive", "💴 Price Estimator"])


# ═══════════════════════════════════════════════════════════════
# TAB 1 — MARKET OVERVIEW
# ═══════════════════════════════════════════════════════════════
with tab1:
    # KPI row
    c1, c2, c3, c4 = st.columns(4)
    median_price = df["trade_price_jpy"].median()
    median_ppm2 = df["price_per_m2_jpy"].median()
    yoy = yoy_growth(df)
    n_tx = len(df)

    c1.metric("Median transaction price", format_jpy(median_price))
    c2.metric("Median price per m²", format_ppm2(median_ppm2))
    c3.metric("YoY growth (2024 vs 2023)", f"{yoy:+.1f}%")
    c4.metric("Transactions in view", f"{n_tx:,}")

    st.markdown("### Price per m² by ward")
    st.caption("Bubble size = transaction volume · Color = median price/m²")

    summary = ward_summary(df)
    # Merge centroids for map
    summary["lat"] = summary["ward"].map(lambda w: TOKYO_WARDS[w]["lat"])
    summary["lon"] = summary["ward"].map(lambda w: TOKYO_WARDS[w]["lon"])
    summary["ward_ja"] = summary["ward"].map(lambda w: TOKYO_WARDS[w]["ja"])

    # Pydeck map — one column for the 3D map, one for the leaderboard
    map_col, rank_col = st.columns([2, 1])

    with map_col:
        # Normalize for bubble radius (in meters)
        max_n = summary["n_transactions"].max()
        summary["radius"] = 400 + (summary["n_transactions"] / max_n) * 1400

        # Color: low price → teal, high price → red-ish
        min_p = summary["median_ppm2"].min()
        max_p = summary["median_ppm2"].max()
        def color_scale(p):
            t = (p - min_p) / (max_p - min_p) if max_p > min_p else 0.5
            r = int(23 + t * (220 - 23))
            g = int(126 - t * 60)
            b = int(137 - t * 100)
            return [r, g, b, 180]
        summary["color"] = summary["median_ppm2"].apply(color_scale)

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=summary,
            get_position=["lon", "lat"],
            get_radius="radius",
            get_fill_color="color",
            pickable=True,
            opacity=0.75,
            stroked=True,
            get_line_color=[255, 255, 255, 220],
            line_width_min_pixels=1.5,
        )
        view_state = pdk.ViewState(latitude=35.685, longitude=139.75, zoom=10.2, pitch=0)
        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            map_style="light",
            tooltip={
                "html": (
                    "<b>{ward}</b> ({ward_ja})<br/>"
                    "Median ¥/m²: <b>{median_ppm2}</b><br/>"
                    "Transactions: {n_transactions}"
                ),
                "style": {"backgroundColor": "#177e89", "color": "white", "fontSize": "12px"},
            },
        )
        st.pydeck_chart(deck, use_container_width=True)

    with rank_col:
        st.markdown("**Top 10 wards by price/m²**")
        rank = summary.head(10)[["ward", "median_ppm2", "n_transactions"]].copy()
        rank["median_ppm2"] = rank["median_ppm2"].apply(lambda x: f"¥{x/10000:.0f}万")
        rank.columns = ["Ward", "¥/m²", "N"]
        rank.index = range(1, len(rank) + 1)
        st.dataframe(rank, use_container_width=True, height=400)

    # Bottom row: price trend + property type split
    st.markdown("### Market trend & composition")
    tc1, tc2 = st.columns(2)

    with tc1:
        trend = price_trend(df)
        fig = px.line(
            trend, x="tx_period", y="median_ppm2",
            markers=True,
            title="Median price per m² over time",
            labels={"tx_period": "Period", "median_ppm2": "JPY / m²"},
        )
        fig.update_traces(line_color="#177e89", line_width=3, marker_size=8)
        fig.update_layout(
            plot_bgcolor="white",
            height=360,
            margin=dict(l=10, r=10, t=50, b=10),
            title_font_size=14,
        )
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(gridcolor="#eee", tickformat=",.0f")
        st.plotly_chart(fig, use_container_width=True)

    with tc2:
        ptype_agg = df.groupby("property_type").agg(
            n=("trade_price_jpy", "size"),
            median_price=("trade_price_jpy", "median"),
        ).reset_index()
        fig2 = px.bar(
            ptype_agg.sort_values("n"),
            x="n", y="property_type",
            orientation="h",
            color="median_price",
            color_continuous_scale=["#b8e0e5", "#177e89", "#0d4d55"],
            title="Transactions by property type",
            labels={"n": "Number of transactions", "property_type": "", "median_price": "Median price (JPY)"},
        )
        fig2.update_layout(
            plot_bgcolor="white",
            height=360,
            margin=dict(l=10, r=10, t=50, b=10),
            title_font_size=14,
            coloraxis_colorbar=dict(title="Median ¥"),
        )
        st.plotly_chart(fig2, use_container_width=True)


# ═══════════════════════════════════════════════════════════════
# TAB 2 — WARD DEEP DIVE
# ═══════════════════════════════════════════════════════════════
with tab2:
    ward_list = sorted(df["ward"].unique())
    if not ward_list:
        st.warning("No wards in the current filter selection.")
    else:
        default_idx = ward_list.index("Minato") if "Minato" in ward_list else 0
        selected_ward = st.selectbox(
            "Choose a ward",
            options=ward_list,
            format_func=lambda w: f"{w} ({TOKYO_WARDS[w]['ja']})",
            index=default_idx,
        )

        ward_df = df[df["ward"] == selected_ward]
        ward_info = TOKYO_WARDS[selected_ward]

        # KPI row
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Transactions", f"{len(ward_df):,}")
        c2.metric("Median price", format_jpy(ward_df["trade_price_jpy"].median()))
        c3.metric("Median ¥/m²", format_ppm2(ward_df["price_per_m2_jpy"].median()))
        c4.metric("Population", f"{ward_info['pop']}k")

        st.markdown("---")

        # Row 1: Histogram + Scatter
        r1c1, r1c2 = st.columns(2)

        with r1c1:
            st.markdown(f"**Price distribution in {selected_ward}**")
            # Clip long tail for display
            clipped = ward_df[ward_df["trade_price_jpy"] < ward_df["trade_price_jpy"].quantile(0.97)]
            fig = px.histogram(
                clipped, x="trade_price_jpy", nbins=40,
                color_discrete_sequence=["#177e89"],
            )
            fig.update_layout(
                plot_bgcolor="white",
                height=320,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title="Trade price (JPY)",
                yaxis_title="Count",
                bargap=0.05,
            )
            fig.update_xaxes(tickformat=".2s")
            fig.update_yaxes(gridcolor="#eee")
            st.plotly_chart(fig, use_container_width=True)

        with r1c2:
            st.markdown(f"**Area vs Price per m² — {selected_ward}**")
            scatter_df = ward_df[ward_df["layout"] != "-"].sample(min(1000, len(ward_df)), random_state=1)
            fig = px.scatter(
                scatter_df, x="area_m2", y="price_per_m2_jpy",
                color="property_type",
                opacity=0.55,
                color_discrete_sequence=["#177e89", "#f39c12", "#e74c3c", "#8e44ad"],
                labels={"area_m2": "Area (m²)", "price_per_m2_jpy": "JPY / m²", "property_type": "Type"},
            )
            fig.update_layout(
                plot_bgcolor="white",
                height=320,
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            fig.update_yaxes(gridcolor="#eee", tickformat=",.0f")
            fig.update_xaxes(gridcolor="#eee")
            st.plotly_chart(fig, use_container_width=True)

        # Row 2: Trend + Layout
        r2c1, r2c2 = st.columns(2)

        with r2c1:
            st.markdown(f"**Price trend — {selected_ward}**")
            trend = price_trend(df, ward=selected_ward)
            if not trend.empty:
                fig = px.line(
                    trend, x="tx_period", y="median_ppm2", markers=True,
                    labels={"tx_period": "Period", "median_ppm2": "JPY / m²"},
                )
                fig.update_traces(line_color="#177e89", line_width=3, marker_size=8)
                fig.update_layout(
                    plot_bgcolor="white",
                    height=320,
                    margin=dict(l=10, r=10, t=10, b=10),
                )
                fig.update_xaxes(showgrid=False)
                fig.update_yaxes(gridcolor="#eee", tickformat=",.0f")
                st.plotly_chart(fig, use_container_width=True)

        with r2c2:
            st.markdown(f"**Top stations in {selected_ward}**")
            stations = top_stations(df, ward=selected_ward, n=8)
            if not stations.empty:
                fig = px.bar(
                    stations.sort_values("median_ppm2"),
                    x="median_ppm2", y="nearest_station",
                    orientation="h",
                    color="median_ppm2",
                    color_continuous_scale=["#b8e0e5", "#177e89", "#0d4d55"],
                    labels={"median_ppm2": "Median ¥/m²", "nearest_station": ""},
                )
                fig.update_layout(
                    plot_bgcolor="white",
                    height=320,
                    margin=dict(l=10, r=10, t=10, b=10),
                    showlegend=False,
                    coloraxis_showscale=False,
                )
                fig.update_xaxes(gridcolor="#eee", tickformat=",.0f")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Not enough data for station analysis with current filters.")


# ═══════════════════════════════════════════════════════════════
# TAB 3 — PRICE ESTIMATOR
# ═══════════════════════════════════════════════════════════════
with tab3:
    st.markdown(
        "Enter property details below to estimate a price range based on "
        "comparable transactions (k-nearest neighbors on ward, area, age, "
        "and station distance)."
    )

    ec1, ec2 = st.columns(2)
    with ec1:
        est_ward = st.selectbox(
            "Ward", options=sorted(TOKYO_WARDS.keys()),
            format_func=lambda w: f"{w} ({TOKYO_WARDS[w]['ja']})",
            index=sorted(TOKYO_WARDS.keys()).index("Shibuya"),
        )
        est_type = st.selectbox("Property type", options=PROPERTY_TYPES, index=0)
        est_area = st.number_input("Area (m²)", min_value=15, max_value=300, value=55, step=5)
    with ec2:
        est_year = st.number_input("Year built", min_value=1970, max_value=2024, value=2010, step=1)
        est_minutes = st.number_input("Walk to station (minutes)", min_value=1, max_value=30, value=8, step=1)

    if st.button("Estimate price", type="primary"):
        result = estimate_price(
            df_all,
            ward=est_ward,
            area_m2=float(est_area),
            year_built=int(est_year),
            station_minutes=int(est_minutes),
            property_type=est_type,
        )

        st.markdown("---")
        st.markdown(f"### Estimated price for {est_area:.0f} m² {est_type} in {est_ward}")

        rc1, rc2, rc3 = st.columns(3)
        rc1.metric("Low (P10)",    format_jpy(result["total_p10"]), format_ppm2(result["ppm2_p10"]))
        rc2.metric("Median (P50)", format_jpy(result["total_p50"]), format_ppm2(result["ppm2_p50"]))
        rc3.metric("High (P90)",   format_jpy(result["total_p90"]), format_ppm2(result["ppm2_p90"]))

        st.caption(f"Based on {result['n_comparables']} comparable transactions.")

        # Range visualization
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[result["total_p90"] - result["total_p10"]],
            y=["Price range"],
            base=result["total_p10"],
            orientation="h",
            marker_color="#b8e0e5",
            showlegend=False,
            hovertemplate="Range: ¥%{base:,.0f} – ¥%{x:,.0f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=[result["total_p50"]],
            y=["Price range"],
            mode="markers",
            marker=dict(size=18, color="#177e89", symbol="diamond"),
            name="Median",
            hovertemplate="Median: ¥%{x:,.0f}<extra></extra>",
        ))
        fig.update_layout(
            height=160,
            margin=dict(l=10, r=10, t=10, b=40),
            plot_bgcolor="white",
            xaxis_title="Price (JPY)",
            xaxis_tickformat=",.0f",
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)


# ────────────────────────────────────────────────────────────────
# Footer
# ────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class='app-footer'>
        <b>Tokyo Real Estate Explorer</b> · Built by
        <a href='https://santimuru.github.io' target='_blank'>Santiago Martinez</a> ·
        <a href='https://github.com/santimuru/tokyo-real-estate-explorer' target='_blank'>Source on GitHub</a>
        <br/>
        Data source: {data_source_label()}
    </div>
    """,
    unsafe_allow_html=True,
)
