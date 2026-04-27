"""
Tokyo Real Estate Explorer — Streamlit app

Real estate transaction analytics for Tokyo's 23 Special Wards.
Data sourced from the MLIT Real Estate Information Library API.
Built by Santiago Martinez · https://santimuru.github.io
"""
from __future__ import annotations

from datetime import datetime

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
    layout_distribution,
    estimate_price,
    format_jpy,
    format_ppm2,
)

# ────────────────────────────────────────────────────────────────
# Page config
# ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Tokyo Real Estate Explorer",
    page_icon="🗼",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main .block-container { padding-top: 0; padding-bottom: 3rem; max-width: 1400px; }
    h1, h2, h3 { font-family: 'Helvetica Neue', sans-serif; letter-spacing: -0.01em; }

    .hero-banner {
        background: linear-gradient(135deg, #0d2b2e 0%, #177e89 65%, #1a9aaa 100%);
        border-radius: 12px;
        padding: 2.8rem 3rem 2.2rem;
        margin-bottom: 1.8rem;
        color: white;
    }
    .hero-title {
        font-size: 2.6rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin: 0 0 0.5rem 0;
        color: white;
        line-height: 1.1;
    }
    .hero-sub {
        font-size: 1.05rem;
        opacity: 0.88;
        max-width: 720px;
        margin: 0 0 1.4rem 0;
        line-height: 1.65;
    }
    .badge {
        display: inline-block;
        background: rgba(255,255,255,0.15);
        border: 1px solid rgba(255,255,255,0.35);
        border-radius: 20px;
        padding: 0.22rem 0.75rem;
        font-size: 0.73rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-right: 0.4rem;
        margin-bottom: 0.3rem;
        color: white;
    }
    .badge-live {
        background: rgba(39, 174, 96, 0.35);
        border-color: rgba(39, 174, 96, 0.7);
    }

    .stMetric {
        background: #f7f9fa;
        border-left: 3px solid #177e89;
        padding: 0.8rem 1rem;
        border-radius: 4px;
    }
    .stMetric label {
        font-size: 0.73rem !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #666 !important;
    }
    .stMetric [data-testid="stMetricValue"] {
        font-size: 1.45rem !important;
        color: #177e89;
        font-weight: 700;
    }

    .stTabs [data-baseweb="tab-list"] { gap: 2rem; border-bottom: 1px solid #e0e0e0; }
    .stTabs [data-baseweb="tab"] { font-size: 0.95rem; font-weight: 600; }
    .stTabs [aria-selected="true"] { color: #177e89; }

    .insight-box {
        background: #f0f9fa;
        border-left: 4px solid #177e89;
        border-radius: 0 8px 8px 0;
        padding: 0.9rem 1.2rem;
        margin: 1rem 0;
        font-size: 0.88rem;
        line-height: 1.65;
        color: #2c2c2c;
    }
    .insight-box strong { color: #0d2b2e; }

    div[data-testid="stSidebarNav"] { display: none; }

    .app-footer {
        margin-top: 3rem;
        padding-top: 1.5rem;
        border-top: 1px solid #e0e0e0;
        color: #999;
        font-size: 0.78rem;
        text-align: center;
        line-height: 2;
    }
    .app-footer a { color: #177e89; text-decoration: none; }
</style>
""", unsafe_allow_html=True)


# ────────────────────────────────────────────────────────────────
# Data loading
# ────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Fetching Tokyo real estate transactions from MLIT API…", ttl=3600)
def _load() -> pd.DataFrame:
    return load_data()

df_all = _load()

_source_label = data_source_label()
is_live = "official" in _source_label.lower()
min_year = int(df_all["tx_year"].min())
max_year = int(df_all["tx_year"].max())


# ────────────────────────────────────────────────────────────────
# HERO BANNER
# ────────────────────────────────────────────────────────────────
live_badge = (
    '<span class="badge badge-live">● Live MLIT API</span>'
    if is_live else
    '<span class="badge">Demo Data</span>'
)
st.markdown(f"""
<div class="hero-banner">
    <div class="hero-title">🗼 Tokyo Real Estate Explorer</div>
    <div class="hero-sub">
        An interactive analytics platform for Tokyo's 23 Special Wards real estate market —
        transaction prices, market trends, ward-level intelligence, and a data-driven
        price estimator. Covering <strong>{min_year}–{max_year}</strong> with
        <strong>{len(df_all):,} official transactions</strong>.
    </div>
    {live_badge}
    <span class="badge">Tokyo 23 Wards</span>
    <span class="badge">Ministry of Land, Infrastructure & Transport</span>
    <span class="badge">国土交通省</span>
</div>
""", unsafe_allow_html=True)


# ────────────────────────────────────────────────────────────────
# Sidebar
# ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding:0.3rem 0 1rem'>
        <span style='font-size:1.8rem'>🗼</span><br>
        <strong style='font-size:1rem; color:#177e89;'>Tokyo RE Explorer</strong>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Filters")

    years_available = sorted(df_all["tx_year"].unique())
    year_range = st.slider(
        "Transaction year",
        min_value=int(min(years_available)),
        max_value=int(max(years_available)),
        value=(int(min(years_available)), int(max(years_available))),
    )

    ptype_filter = st.multiselect(
        "Property type",
        options=PROPERTY_TYPES,
        default=PROPERTY_TYPES,
    )

    area_min, area_max = st.slider(
        "Area (m²)", min_value=0, max_value=300, value=(0, 300), step=10,
    )

    st.markdown("---")
    source_icon = "🟢" if is_live else "🟡"
    st.markdown(f"""
    <div style='background:#f7f9fa; border-radius:8px; padding:0.75rem 1rem; font-size:0.78rem;'>
        <div style='font-weight:700; color:#1a1a1a; margin-bottom:0.3rem;'>{source_icon} Data Source</div>
        <div style='color:#555; line-height:1.5;'>{_source_label}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style='font-size:0.75rem; color:#999; text-align:center; line-height:2;'>
        Built by <a href='https://santimuru.github.io' style='color:#177e89;'>Santiago Martinez</a><br>
        <a href='https://github.com/santimuru/tokyo-real-estate-explorer' style='color:#177e89;'>View on GitHub</a>
    </div>
    """, unsafe_allow_html=True)


# ────────────────────────────────────────────────────────────────
# Apply filters
# ────────────────────────────────────────────────────────────────
df = df_all[
    (df_all["tx_year"].between(*year_range))
    & (df_all["property_type"].isin(ptype_filter))
    & (df_all["area_m2"].between(area_min, area_max))
].copy()

if df.empty:
    st.warning("No transactions match the current filters. Try widening them.")
    st.stop()


# ────────────────────────────────────────────────────────────────
# Global KPIs
# ────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Transactions", f"{len(df):,}")
k2.metric("Median price", format_jpy(df["trade_price_jpy"].median()))
k3.metric("Median ¥/m²", format_ppm2(df["price_per_m2_jpy"].median()))
k4.metric("YoY growth", f"{yoy_growth(df):+.1f}%")
k5.metric("Wards covered", str(df["ward"].nunique()))

st.markdown("<div style='margin-bottom:1.5rem'></div>", unsafe_allow_html=True)


# ────────────────────────────────────────────────────────────────
# Tabs
# ────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🗺️ Map & Rankings",
    "📈 Market Trends",
    "🏙️ Ward Analysis",
    "💴 Price Estimator",
    "ℹ️ About & Data",
])


# ═══════════════════════════════════════════════════════════════
# TAB 1 — MAP & RANKINGS
# ═══════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### Price per m² across Tokyo's 23 wards")
    st.caption("Bubble size = transaction volume · Color intensity = median price/m² · Hover for details")

    summary = ward_summary(df)
    summary["lat"] = summary["ward"].map(lambda w: TOKYO_WARDS[w]["lat"])
    summary["lon"] = summary["ward"].map(lambda w: TOKYO_WARDS[w]["lon"])
    summary["ward_ja"] = summary["ward"].map(lambda w: TOKYO_WARDS[w]["ja"])
    summary["ppm2_fmt"] = summary["median_ppm2"].apply(lambda x: f"¥{x/10000:.0f}万/m²")
    summary["price_fmt"] = summary["median_price"].apply(
        lambda x: f"¥{x/1e8:.2f}億" if x >= 1e8 else f"¥{x/1e6:.0f}百万"
    )

    map_col, rank_col = st.columns([2, 1])

    with map_col:
        max_n = summary["n_transactions"].max()
        summary["radius"] = 400 + (summary["n_transactions"] / max_n) * 1400

        min_p, max_p = summary["median_ppm2"].min(), summary["median_ppm2"].max()
        def _color(p):
            t = (p - min_p) / (max_p - min_p) if max_p > min_p else 0.5
            return [int(23 + t * 197), int(126 - t * 60), int(137 - t * 100), 190]
        summary["color"] = summary["median_ppm2"].apply(_color)

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=summary,
            get_position=["lon", "lat"],
            get_radius="radius",
            get_fill_color="color",
            pickable=True,
            opacity=0.78,
            stroked=True,
            get_line_color=[255, 255, 255, 200],
            line_width_min_pixels=1.5,
        )
        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=pdk.ViewState(latitude=35.685, longitude=139.75, zoom=10.2, pitch=0),
            map_style="light",
            tooltip={
                "html": (
                    "<b>{ward}</b> ({ward_ja})<br/>"
                    "Median ¥/m²: <b>{ppm2_fmt}</b><br/>"
                    "Median price: <b>{price_fmt}</b><br/>"
                    "Transactions: <b>{n_transactions}</b>"
                ),
                "style": {
                    "backgroundColor": "#0d2b2e",
                    "color": "white",
                    "fontSize": "12px",
                    "padding": "10px",
                    "borderRadius": "6px",
                },
            },
        )
        st.pydeck_chart(deck, use_container_width=True)

    with rank_col:
        st.markdown("**All 23 wards ranked by ¥/m²**")
        rank = summary[["ward", "ward_ja", "median_ppm2", "median_price", "n_transactions"]].copy()
        rank["Ward"] = rank.apply(lambda r: f"{r['ward']}  ({r['ward_ja']})", axis=1)
        rank["¥/m²"] = rank["median_ppm2"].apply(lambda x: f"¥{x/10000:.0f}万")
        rank["Median price"] = rank["median_price"].apply(
            lambda x: f"¥{x/1e8:.2f}億" if x >= 1e8 else f"¥{x/1e6:.0f}百万"
        )
        rank = rank[["Ward", "¥/m²", "Median price", "n_transactions"]].rename(
            columns={"n_transactions": "Txs"}
        )
        rank.index = range(1, len(rank) + 1)
        st.dataframe(rank, use_container_width=True, height=520)

    # Auto-generated insight
    top_w = summary.iloc[0]
    bot_w = summary.iloc[-1]
    gap = top_w["median_ppm2"] / bot_w["median_ppm2"]
    st.markdown(f"""
    <div class="insight-box">
        📍 <strong>{top_w['ward']} ({top_w['ward_ja']})</strong> is Tokyo's most expensive ward
        at <strong>{top_w['ppm2_fmt']}</strong>. At the other end,
        <strong>{bot_w['ward']} ({bot_w['ward_ja']})</strong> sits at
        <strong>{bot_w['ppm2_fmt']}</strong> — a <strong>{gap:.1f}× price gap</strong>
        across the 23 wards, illustrating Tokyo's extreme intra-city market segmentation.
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# TAB 2 — MARKET TRENDS
# ═══════════════════════════════════════════════════════════════
with tab2:
    st.markdown(f"### Tokyo real estate — market evolution {min_year}–{max_year}")

    trend_all = price_trend(df)
    first_val = trend_all["median_ppm2"].iloc[0]
    last_val = trend_all["median_ppm2"].iloc[-1]
    total_growth = (last_val - first_val) / first_val * 100

    st.markdown(f"""
    <div class="insight-box">
        📈 Tokyo's citywide median price per m² moved from
        <strong>¥{first_val/10000:.0f}万</strong> in {min_year}
        to <strong>¥{last_val/10000:.0f}万</strong> in {max_year} —
        a <strong>{total_growth:+.1f}% total appreciation</strong> over the period.
        Post-COVID demand recovery, a weak yen attracting foreign investors,
        and chronic housing undersupply in central wards have all contributed.
    </div>
    """, unsafe_allow_html=True)

    fig_area = px.area(
        trend_all, x="tx_period", y="median_ppm2",
        labels={"tx_period": "", "median_ppm2": "Median ¥/m²"},
    )
    fig_area.update_traces(
        line_color="#177e89", line_width=2.5,
        fillcolor="rgba(23, 126, 137, 0.1)",
    )
    fig_area.update_layout(
        plot_bgcolor="white", height=300,
        margin=dict(l=10, r=10, t=10, b=10),
    )
    fig_area.update_xaxes(showgrid=False, tickangle=-30)
    fig_area.update_yaxes(gridcolor="#eee", tickformat=",.0f")
    st.plotly_chart(fig_area, use_container_width=True)

    st.markdown("---")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**YoY price change by ward** (latest year vs prior year)")
        ward_yoy_rows = [
            {"ward": w, "yoy": yoy_growth(df, ward=w)}
            for w in df["ward"].unique()
        ]
        yoy_df = pd.DataFrame(ward_yoy_rows).sort_values("yoy", ascending=True)
        fig_yoy = px.bar(
            yoy_df, x="yoy", y="ward",
            orientation="h",
            color="yoy",
            color_continuous_scale=["#e74c3c", "#f5b7b1", "#d5f5e3", "#177e89"],
            color_continuous_midpoint=0,
            labels={"yoy": "YoY growth (%)", "ward": ""},
        )
        fig_yoy.update_layout(
            plot_bgcolor="white", height=520,
            margin=dict(l=10, r=10, t=10, b=10),
            coloraxis_showscale=False,
        )
        fig_yoy.update_xaxes(gridcolor="#eee", ticksuffix="%")
        fig_yoy.add_vline(x=0, line_dash="dot", line_color="#bbb", line_width=1)
        st.plotly_chart(fig_yoy, use_container_width=True)

    with c2:
        st.markdown("**Price trend by property type**")
        trend_pt = (
            df.groupby(["tx_period", "property_type"])["price_per_m2_jpy"]
            .median()
            .reset_index()
            .rename(columns={"price_per_m2_jpy": "median_ppm2"})
        )
        fig_pt = px.line(
            trend_pt, x="tx_period", y="median_ppm2",
            color="property_type",
            markers=True,
            labels={"tx_period": "", "median_ppm2": "¥/m²", "property_type": ""},
            color_discrete_sequence=["#177e89", "#f39c12", "#e74c3c", "#8e44ad"],
        )
        fig_pt.update_layout(
            plot_bgcolor="white", height=270,
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        fig_pt.update_xaxes(showgrid=False, tickangle=-30)
        fig_pt.update_yaxes(gridcolor="#eee", tickformat=",.0f")
        st.plotly_chart(fig_pt, use_container_width=True)

        st.markdown("**Ward × year price heatmap** (median ¥/m²)")
        heat_df = (
            df.groupby(["ward", "tx_year"])["price_per_m2_jpy"]
            .median()
            .reset_index()
        )
        heat_pivot = heat_df.pivot(index="ward", columns="tx_year", values="price_per_m2_jpy")
        fig_heat = px.imshow(
            heat_pivot,
            color_continuous_scale=["#e8f8fa", "#177e89", "#0d2b2e"],
            labels={"color": "¥/m²", "x": "", "y": ""},
            aspect="auto",
        )
        fig_heat.update_layout(
            height=520,
            margin=dict(l=10, r=10, t=10, b=10),
            coloraxis_colorbar=dict(title="¥/m²", tickformat=",.0f"),
        )
        fig_heat.update_xaxes(side="bottom")
        st.plotly_chart(fig_heat, use_container_width=True)


# ═══════════════════════════════════════════════════════════════
# TAB 3 — WARD ANALYSIS
# ═══════════════════════════════════════════════════════════════
with tab3:
    ward_list = sorted(df["ward"].unique())
    if not ward_list:
        st.warning("No wards available with the current filters.")
        st.stop()

    default_idx = ward_list.index("Minato") if "Minato" in ward_list else 0
    selected_ward = st.selectbox(
        "Select a ward to analyze",
        options=ward_list,
        format_func=lambda w: f"{w}  ·  {TOKYO_WARDS[w]['ja']}",
        index=default_idx,
    )

    ward_df = df[df["ward"] == selected_ward]
    ward_info = TOKYO_WARDS[selected_ward]
    ward_yoy = yoy_growth(df, ward=selected_ward)

    # KPI row
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Transactions", f"{len(ward_df):,}")
    c2.metric("Median price", format_jpy(ward_df["trade_price_jpy"].median()))
    c3.metric("Median ¥/m²", format_ppm2(ward_df["price_per_m2_jpy"].median()))
    c4.metric("YoY growth", f"{ward_yoy:+.1f}%")
    c5.metric("Population", f"{ward_info['pop']}k")

    ward_rank = (
        ward_summary(df)
        .reset_index(drop=True)
        .reset_index()
        .query("ward == @selected_ward")["index"]
        .values
    )
    rank_pos = int(ward_rank[0]) + 1 if len(ward_rank) else "—"
    st.markdown(f"""
    <div class="insight-box">
        🏙️ <strong>{selected_ward} ({TOKYO_WARDS[selected_ward]['ja']})</strong>
        ranks <strong>#{rank_pos}</strong> out of 23 wards by median price/m².
        YoY change: <strong>{ward_yoy:+.1f}%</strong>.
        The ward has a population of <strong>{ward_info['pop']}k</strong>.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    r1c1, r1c2 = st.columns(2)

    with r1c1:
        st.markdown(f"**Price distribution — {selected_ward}**")
        st.caption("Clipped at 97th percentile")
        clip97 = ward_df["trade_price_jpy"].quantile(0.97)
        clipped = ward_df[ward_df["trade_price_jpy"] <= clip97]
        fig = px.histogram(
            clipped, x="trade_price_jpy", nbins=40,
            color_discrete_sequence=["#177e89"],
            labels={"trade_price_jpy": "Trade price (JPY)", "count": ""},
        )
        fig.update_layout(
            plot_bgcolor="white", height=300,
            margin=dict(l=10, r=10, t=10, b=10),
            bargap=0.05,
        )
        fig.update_xaxes(tickformat=".2s")
        fig.update_yaxes(gridcolor="#eee")
        st.plotly_chart(fig, use_container_width=True)

    with r1c2:
        st.markdown(f"**Area vs price/m² — {selected_ward}**")
        scatter_df = ward_df.sample(min(1500, len(ward_df)), random_state=42)
        fig = px.scatter(
            scatter_df, x="area_m2", y="price_per_m2_jpy",
            color="property_type",
            opacity=0.45,
            color_discrete_sequence=["#177e89", "#f39c12", "#e74c3c", "#8e44ad"],
            labels={"area_m2": "Area (m²)", "price_per_m2_jpy": "¥/m²", "property_type": ""},
        )
        fig.update_layout(
            plot_bgcolor="white", height=300,
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        fig.update_yaxes(gridcolor="#eee", tickformat=",.0f")
        fig.update_xaxes(gridcolor="#eee")
        st.plotly_chart(fig, use_container_width=True)

    r2c1, r2c2 = st.columns(2)

    with r2c1:
        st.markdown(f"**Price trend — {selected_ward}**")
        trend_w = price_trend(df, ward=selected_ward)
        if not trend_w.empty:
            fig = px.line(
                trend_w, x="tx_period", y="median_ppm2",
                markers=True,
                labels={"tx_period": "", "median_ppm2": "¥/m²"},
            )
            fig.update_traces(line_color="#177e89", line_width=3, marker_size=8)
            fig.update_layout(
                plot_bgcolor="white", height=300,
                margin=dict(l=10, r=10, t=10, b=10),
            )
            fig.update_xaxes(showgrid=False, tickangle=-30)
            fig.update_yaxes(gridcolor="#eee", tickformat=",.0f")
            st.plotly_chart(fig, use_container_width=True)

    with r2c2:
        st.markdown(f"**Layout breakdown — {selected_ward}**")
        layout_df = layout_distribution(df, ward=selected_ward)
        layout_df = layout_df[layout_df["n"] > 0]
        if not layout_df.empty:
            fig = px.bar(
                layout_df.sort_values("n", ascending=True),
                x="n", y="layout",
                orientation="h",
                color="n",
                color_continuous_scale=["#b8e0e5", "#177e89", "#0d4d55"],
                labels={"n": "Transactions", "layout": ""},
            )
            fig.update_layout(
                plot_bgcolor="white", height=300,
                margin=dict(l=10, r=10, t=10, b=10),
                coloraxis_showscale=False,
            )
            fig.update_xaxes(gridcolor="#eee")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No layout data available for this ward with current filters.")


# ═══════════════════════════════════════════════════════════════
# TAB 4 — PRICE ESTIMATOR
# ═══════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### Property price estimator")
    st.markdown(f"""
    <div class="insight-box">
        Enter a property's characteristics to get a price estimate derived from real
        comparable transactions. The model uses <strong>k-nearest neighbors</strong>
        matching on ward, floor area, and building age to find the most similar deals in
        the dataset ({len(df_all):,} transactions) and returns <strong>P10 / P50 / P90</strong>
        price ranges.
    </div>
    """, unsafe_allow_html=True)

    ec1, ec2 = st.columns(2)
    with ec1:
        est_ward = st.selectbox(
            "Ward",
            options=sorted(TOKYO_WARDS.keys()),
            format_func=lambda w: f"{w}  ·  {TOKYO_WARDS[w]['ja']}",
            index=sorted(TOKYO_WARDS.keys()).index("Shibuya"),
        )
        est_type = st.selectbox("Property type", options=PROPERTY_TYPES, index=0)
        est_area = st.number_input("Floor area (m²)", min_value=15, max_value=300, value=55, step=5)
    with ec2:
        est_year = st.number_input(
            "Year built", min_value=1970, max_value=datetime.now().year, value=2010, step=1,
        )
        est_minutes = st.number_input(
            "Walk to nearest station (min)", min_value=1, max_value=30, value=8, step=1,
        )

    if st.button("Estimate →", type="primary"):
        result = estimate_price(
            df_all,
            ward=est_ward,
            area_m2=float(est_area),
            year_built=int(est_year),
            station_minutes=int(est_minutes),
            property_type=est_type,
        )

        st.markdown("---")
        age_label = datetime.now().year - int(est_year)
        st.markdown(
            f"#### {est_area:.0f} m² · {est_type} · {est_ward} ({TOKYO_WARDS[est_ward]['ja']}) "
            f"· {age_label} yr old"
        )

        rc1, rc2, rc3 = st.columns(3)
        rc1.metric("Conservative (P10)", format_jpy(result["total_p10"]), format_ppm2(result["ppm2_p10"]))
        rc2.metric("Most likely (P50)",  format_jpy(result["total_p50"]), format_ppm2(result["ppm2_p50"]))
        rc3.metric("Optimistic (P90)",   format_jpy(result["total_p90"]), format_ppm2(result["ppm2_p90"]))

        st.caption(f"Based on {result['n_comparables']:,} comparable transactions.")

        fig_range = go.Figure()
        fig_range.add_trace(go.Bar(
            x=[result["total_p90"] - result["total_p10"]],
            y=["Estimated range"],
            base=result["total_p10"],
            orientation="h",
            marker_color="rgba(23, 126, 137, 0.18)",
            marker_line=dict(color="#177e89", width=2),
            showlegend=False,
            hovertemplate="P10: ¥%{base:,.0f}<br>P90: ¥%{x:,.0f}<extra></extra>",
        ))
        fig_range.add_trace(go.Scatter(
            x=[result["total_p50"]],
            y=["Estimated range"],
            mode="markers+text",
            marker=dict(size=24, color="#177e89", symbol="diamond"),
            text=[format_jpy(result["total_p50"])],
            textposition="top center",
            showlegend=False,
            hovertemplate="Median: ¥%{x:,.0f}<extra></extra>",
        ))
        fig_range.update_layout(
            height=180,
            margin=dict(l=10, r=10, t=40, b=20),
            plot_bgcolor="white",
            xaxis_title="Price (JPY)",
            xaxis_tickformat=",.0f",
        )
        st.plotly_chart(fig_range, use_container_width=True)


# ═══════════════════════════════════════════════════════════════
# TAB 5 — ABOUT & DATA
# ═══════════════════════════════════════════════════════════════
with tab5:
    a1, a2 = st.columns([3, 2])

    with a1:
        st.markdown("### About this project")
        st.markdown(f"""
Tokyo's real estate market is one of the most data-rich and dynamic in the world.
Despite being one of the largest cities on earth, it combines extreme price
concentration in central wards with relatively affordable options in the periphery —
making it a fascinating case study in urban economics.

This dashboard brings together **{len(df_all):,} official transaction records**
spanning **{min_year}–{max_year}** to make that complexity navigable.

---

**What you can explore:**

🗺️ **Map & Rankings** — Visual comparison of all 23 wards by price per m² and
transaction volume. Hover any bubble for ward details.

📈 **Market Trends** — Full citywide price evolution, YoY growth by ward, property
type trajectories, and a ward × year price heatmap.

🏙️ **Ward Analysis** — Deep dive into any ward: price distribution, area vs price
scatter, quarterly trend, and layout breakdown.

💴 **Price Estimator** — Enter property characteristics to get a data-driven
P10/P50/P90 price range from real comparable transactions.

---

**Tech stack:** Python · Streamlit · Plotly · Pydeck · Pandas · MLIT REST API
        """)

        st.markdown("### Data source")
        st.markdown(f"""
Powered by the **MLIT Real Estate Information Library**
(国土交通省 不動産情報ライブラリ) — Japan's official real estate transaction
database maintained by the Ministry of Land, Infrastructure, Transport and Tourism.

| | |
|---|---|
| **API endpoint** | XIT001 — Transaction price information |
| **Coverage** | Tokyo prefecture (都道府県コード: 13) |
| **Ward scope** | All 23 Special Wards (特別区) |
| **Publication lag** | ~2 quarters behind current date |
| **Cache TTL** | 1 hour |
| **Current dataset** | {min_year} Q1 – {max_year} Q4 |

> Transaction types covered: used apartments (中古マンション等),
> used detached houses (中古戸建), newly built houses (新築戸建),
> and land-only deals (宅地/土地).
        """)

    with a2:
        if is_live:
            st.success("✓ Connected to MLIT API — data is official and refreshes hourly.")
        else:
            st.info("ℹ️ Demo mode — synthetic data modeled after MLIT public statistics.")

        st.markdown("### Methodology")
        st.markdown("""
**Price estimator**

Finds the k most similar transactions to a query property using a distance
score across floor area, building age, and station proximity. Returns
P10/P50/P90 percentiles of comparable ¥/m² values, scaled to total price.
Falls back to all ward data if fewer than 20 matches exist.

**YoY growth**

Compares median price/m² in the most recent calendar year in the dataset
versus the prior year. Requires at least one transaction per year.

**Ward heatmap**

Median price/m² per ward × year cell. Dark = expensive, light = affordable.
Useful for spotting which wards appreciated fastest over the period.

**Data note**

The MLIT XIT001 endpoint does not include station proximity data.
The station walk-time input in the estimator is used for comparisons
within the dataset but is not sourced from the API itself.
        """)

        st.markdown("### Author")
        st.markdown("""
**Santiago Martinez**

Data scientist and BI analyst. Building data products that make
complex markets legible.

🌐 [santimuru.github.io](https://santimuru.github.io)
💻 [GitHub](https://github.com/santimuru/tokyo-real-estate-explorer)
        """)


# ────────────────────────────────────────────────────────────────
# Footer
# ────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class='app-footer'>
        <strong>Tokyo Real Estate Explorer</strong> · Built by
        <a href='https://santimuru.github.io' target='_blank'>Santiago Martinez</a> ·
        <a href='https://github.com/santimuru/tokyo-real-estate-explorer' target='_blank'>Source on GitHub</a>
        <br/>
        Data: {_source_label} · Last loaded: {datetime.now().strftime("%Y-%m-%d %H:%M")} UTC
    </div>
    """,
    unsafe_allow_html=True,
)
