"""
Tokyo Deep Dive — ward-level analytics for Tokyo's 23 Special Wards.
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
    neighborhood_summary,
    investment_signals,
    structure_premium,
    direction_premium,
    renovation_premium,
    format_jpy,
    format_ppm2,
)
from utils.styles import inject_css, kpi_card, plotly_defaults, get_theme

st.set_page_config(
    page_title="Tokyo Deep Dive · Japan RE",
    page_icon="🗼",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()


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
# Hero banner
# ────────────────────────────────────────────────────────────────
live_badge = (
    '<span class="badge badge-live">● Live MLIT API</span>'
    if is_live else
    '<span class="badge">Demo Data</span>'
)
st.markdown(f"""
<div class="hero-banner">
    <div class="hero-title">🗼 Tokyo Deep Dive</div>
    <div class="hero-sub">
        Ward-level analytics for Tokyo's 23 Special Wards — prices, trends, and a
        data-driven price estimator powered by official MLIT transaction data.
        Covering <strong>{min_year}–{max_year}</strong> with
        <strong>{len(df_all):,} official transactions</strong>.
    </div>
    {live_badge}
    <span class="badge">Tokyo 23 Wards</span>
    <span class="badge">国土交通省</span>
</div>
""", unsafe_allow_html=True)


# ────────────────────────────────────────────────────────────────
# Sidebar filters
# ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding:0.3rem 0 1rem'>
        <span style='font-size:1.8rem'>🗼</span><br>
        <strong style='font-size:1rem; color:#177e89;'>Tokyo Deep Dive</strong>
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
    <div class="info-card">
        <div class="card-title">{source_icon} Data Source</div>
        <div class="card-body">{_source_label}</div>
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
    "🧠 Market Intelligence",
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
            map_style="dark" if get_theme() == "dark" else "light",
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
    _layout, _grid = plotly_defaults(300)
    fig_area.update_layout(**_layout)
    fig_area.update_xaxes(showgrid=False, tickangle=-30)
    fig_area.update_yaxes(gridcolor=_grid, tickformat=",.0f")
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
            color_continuous_scale=["#e74c3c", "#888888", "#177e89"],
            color_continuous_midpoint=0,
            labels={"yoy": "YoY growth (%)", "ward": ""},
        )
        _layout, _grid = plotly_defaults(520)
        fig_yoy.update_layout(**_layout, coloraxis_showscale=False)
        fig_yoy.update_xaxes(gridcolor=_grid, ticksuffix="%")
        fig_yoy.add_vline(x=0, line_dash="dot", line_color=_grid, line_width=1)
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
        _layout, _grid = plotly_defaults(270)
        fig_pt.update_layout(**_layout,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig_pt.update_xaxes(showgrid=False, tickangle=-30)
        fig_pt.update_yaxes(gridcolor=_grid, tickformat=",.0f")
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
        _layout, _ = plotly_defaults(520)
        fig_heat.update_layout(**_layout,
            coloraxis_colorbar=dict(title="¥/m²", tickformat=",.0f"))
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
        _layout, _grid = plotly_defaults(300)
        fig.update_layout(**_layout, bargap=0.05)
        fig.update_xaxes(tickformat=".2s")
        fig.update_yaxes(gridcolor=_grid)
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
        _layout, _grid = plotly_defaults(300)
        fig.update_layout(**_layout,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig.update_yaxes(gridcolor=_grid, tickformat=",.0f")
        fig.update_xaxes(gridcolor=_grid)
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
            _layout, _grid = plotly_defaults(300)
            fig.update_layout(**_layout)
            fig.update_xaxes(showgrid=False, tickangle=-30)
            fig.update_yaxes(gridcolor=_grid, tickformat=",.0f")
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
            _layout, _grid = plotly_defaults(300)
            fig.update_layout(**_layout, coloraxis_showscale=False)
            fig.update_xaxes(gridcolor=_grid)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No layout data available for this ward with current filters.")


# ═══════════════════════════════════════════════════════════════
# TAB 4 — PRICE ESTIMATOR
# ═══════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### Property price estimator")
    _has_extended = (
        "structure" in df_all.columns and df_all["structure"].notna().any()
    )
    st.markdown(f"""
    <div class="insight-box">
        Enter a property's characteristics to get a price estimate derived from
        comparable transactions using <strong>k-nearest neighbors</strong> matching on
        ward, floor area, building age{", structure, orientation, and renovation" if _has_extended else ""}.
        Returns <strong>P10 / P50 / P90</strong> price ranges from
        {result_n:,} comparable deals in the dataset.
    </div>
    """.replace("result_n", str(len(df_all))), unsafe_allow_html=True)

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

    _structure_opts = ["Any", "RC", "SRC", "Steel", "Light Steel", "Wood"]
    _direction_opts = ["Any", "South", "Southeast", "Southwest", "East", "West", "North", "Northeast", "Northwest"]
    with st.expander(
        "🔬 Advanced property features" + (" — improves estimate accuracy" if _has_extended else " — requires live MLIT data"),
        expanded=_has_extended,
    ):
        adv1, adv2, adv3 = st.columns(3)
        with adv1:
            est_structure = st.selectbox("Structure type", _structure_opts)
        with adv2:
            est_direction = st.selectbox("Facing direction", _direction_opts)
        with adv3:
            st.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
            est_renovated = st.checkbox("Recently renovated")

    if st.button("Estimate →", type="primary"):
        result = estimate_price(
            df_all,
            ward=est_ward,
            area_m2=float(est_area),
            year_built=int(est_year),
            station_minutes=int(est_minutes),
            property_type=est_type,
            structure=est_structure if est_structure != "Any" else None,
            direction=est_direction if est_direction != "Any" else None,
            renovated=est_renovated,
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
        _layout, _ = plotly_defaults(180)
        fig_range.update_layout(**_layout,
            margin=dict(l=10, r=10, t=40, b=20),
            xaxis_title="Price (JPY)",
            xaxis_tickformat=",.0f")
        st.plotly_chart(fig_range, use_container_width=True)


# ═══════════════════════════════════════════════════════════════
# TAB 5 — MARKET INTELLIGENCE
# ═══════════════════════════════════════════════════════════════
with tab5:

    # ── Investment Signal Dashboard ──────────────────────────────
    st.markdown("### Investment Signal Dashboard")
    st.markdown(f"""
    <div class="insight-box">
        Each ward is scored on two axes: <strong>price momentum</strong>
        ({sorted(df["tx_year"].dropna().unique())[-2] if len(df["tx_year"].dropna().unique()) >= 2 else "prior year"} → {int(df["tx_year"].max())} YoY ¥/m² change)
        and <strong>relative affordability</strong> vs the Tokyo median.
        The <strong>Value Score</strong> (0–100) weights momentum 60% and affordability 40%
        — a rising ward that is still below market average scores highest.
    </div>
    """, unsafe_allow_html=True)

    sig_df = investment_signals(df)

    if not sig_df.empty:
        sig_col, top_col = st.columns([3, 1])

        with sig_col:
            fig_sig = go.Figure()
            # Quadrant reference lines
            city_med_ppm2 = float(df["price_per_m2_jpy"].median())
            avg_momentum  = float(sig_df["momentum_pct"].mean())
            fig_sig.add_vline(x=city_med_ppm2,  line_dash="dot", line_color="rgba(150,150,150,0.4)", line_width=1)
            fig_sig.add_hline(y=avg_momentum,    line_dash="dot", line_color="rgba(150,150,150,0.4)", line_width=1)

            fig_sig.add_trace(go.Scatter(
                x=sig_df["median_ppm2"],
                y=sig_df["momentum_pct"],
                mode="markers+text",
                text=sig_df["ward"],
                textposition="top center",
                textfont=dict(size=9),
                marker=dict(
                    size=np.sqrt(sig_df["n_transactions"]).clip(8, 28),
                    color=sig_df["value_score"],
                    colorscale=[[0, "#e74c3c"], [0.4, "#f39c12"], [0.7, "#27ae60"], [1, "#177e89"]],
                    showscale=True,
                    colorbar=dict(title="Value Score", thickness=12, len=0.7),
                    line=dict(color="white", width=1),
                ),
                customdata=np.stack([sig_df["signal"], sig_df["value_score"], sig_df["volume_trend_pct"]], axis=1),
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Signal: %{customdata[0]}<br>"
                    "Value Score: %{customdata[1]:.0f}<br>"
                    "Momentum: %{y:+.1f}%<br>"
                    "Median ¥/m²: ¥%{x:,.0f}<br>"
                    "Volume change: %{customdata[2]:+.0f}%<extra></extra>"
                ),
            ))

            # Quadrant labels
            x_range = [sig_df["median_ppm2"].min() * 0.92, sig_df["median_ppm2"].max() * 1.05]
            y_range = [sig_df["momentum_pct"].min() - 1.5, sig_df["momentum_pct"].max() + 2.5]
            for label, x_frac, y_frac, color in [
                ("Rising Stars", 0.08, 0.92, "rgba(23,126,137,0.15)"),
                ("Hot Market",   0.85, 0.92, "rgba(243,156,18,0.12)"),
                ("Undervalued",  0.08, 0.08, "rgba(52,152,219,0.12)"),
                ("Cooling",      0.85, 0.08, "rgba(231,76,60,0.10)"),
            ]:
                fig_sig.add_annotation(
                    x=x_range[0] + (x_range[1]-x_range[0]) * x_frac,
                    y=y_range[0] + (y_range[1]-y_range[0]) * y_frac,
                    text=label, showarrow=False,
                    font=dict(size=10, color="rgba(100,100,100,0.6)"),
                )

            _layout, _grid = plotly_defaults(480)
            fig_sig.update_layout(**_layout,
                margin=dict(l=10, r=10, t=20, b=40),
                xaxis=dict(title="Median ¥/m²", gridcolor=_grid, tickformat=",.0f"),
                yaxis=dict(title="YoY Momentum (%)", gridcolor=_grid, ticksuffix="%"),
                showlegend=False)
            st.plotly_chart(fig_sig, use_container_width=True)

        with top_col:
            st.markdown("**Top value plays**")
            for _, row in sig_df.head(5).iterrows():
                kpi_card(
                    row["ward"],
                    row["signal"],
                    f"Score {row['value_score']:.0f} · {row['momentum_pct']:+.1f}% MoM",
                )
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            st.markdown("**Most bearish**")
            bearish = sig_df[sig_df["momentum_pct"] < 0].sort_values("momentum_pct").head(3)
            if not bearish.empty:
                for _, row in bearish.iterrows():
                    kpi_card(row["ward"], f"{row['momentum_pct']:+.1f}%", "YoY momentum")
    else:
        st.info("Investment signals require at least 2 years of data.")

    st.markdown("---")

    # ── Neighborhood Intelligence ────────────────────────────────
    st.markdown("### Neighborhood Intelligence")

    has_district = (
        "district" in df_all.columns
        and df_all["district"].notna().any()
        and (df_all["district"] != "").any()
    )

    if has_district:
        st.caption("District-level breakdown within each ward — powered by MLIT DistrictName field.")
        ni_ward = st.selectbox(
            "Select ward for neighborhood drill-down",
            options=sorted(df["ward"].unique()),
            format_func=lambda w: f"{w}  ·  {TOKYO_WARDS[w]['ja']}",
            key="ni_ward",
        )
        nb_df = neighborhood_summary(df, ward=ni_ward)
        if not nb_df.empty:
            nb_col1, nb_col2 = st.columns([3, 1])
            with nb_col1:
                top_nb = nb_df.head(20)
                fig_nb = px.bar(
                    top_nb.sort_values("median_ppm2"),
                    x="median_ppm2", y="district",
                    orientation="h",
                    color="median_ppm2",
                    color_continuous_scale=["#e8f8fa", "#177e89", "#0d2b2e"],
                    labels={"median_ppm2": "Median ¥/m²", "district": ""},
                    text=top_nb.sort_values("median_ppm2")["median_ppm2"].apply(
                        lambda x: f"¥{x/10000:.0f}万"
                    ),
                )
                fig_nb.update_traces(textposition="outside")
                _layout, _grid = plotly_defaults(max(350, len(top_nb) * 24))
                fig_nb.update_layout(**_layout, coloraxis_showscale=False)
                fig_nb.update_xaxes(gridcolor=_grid, tickformat=",.0f")
                st.plotly_chart(fig_nb, use_container_width=True)
            with nb_col2:
                if len(nb_df) >= 2:
                    top_d   = nb_df.iloc[0]
                    cheap_d = nb_df.iloc[-1]
                    gap = top_d["median_ppm2"] / cheap_d["median_ppm2"]
                    st.markdown(f"""
                    <div class="insight-box">
                        Within <strong>{ni_ward}</strong>, prices vary
                        <strong>{gap:.1f}×</strong> from district to district.<br><br>
                        🏆 Most expensive:<br>
                        <strong>{top_d['district']}</strong><br>
                        ¥{top_d['median_ppm2']/10000:.0f}万/m²<br><br>
                        💡 Best value:<br>
                        <strong>{cheap_d['district']}</strong><br>
                        ¥{cheap_d['median_ppm2']/10000:.0f}万/m²
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info(f"Not enough district-level data for {ni_ward} in the current filter range.")
    else:
        st.markdown("""
        <div class="insight-box">
            🔌 <strong>Connect to the live MLIT API</strong> to unlock neighborhood intelligence.<br>
            The <code>DistrictName</code> field reveals sub-ward price variation —
            e.g. Roppongi vs Azabu-Juban vs Shibaura within Minato Ward —
            up to <strong>3–5× price gaps</strong> within a single ward.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Property DNA ─────────────────────────────────────────────
    st.markdown("### Property DNA")
    st.caption("How structure type, orientation, and renovation history affect price per m².")

    has_dna = (
        "structure" in df_all.columns and df_all["structure"].notna().any()
    )

    if not has_dna:
        st.markdown("""
        <div class="insight-box">
            🔌 <strong>Connect to the live MLIT API</strong> to unlock Property DNA analysis.<br>
            The API provides building <strong>structure</strong> (RC / SRC / Steel / Wood),
            <strong>facing direction</strong> (south-facing apartments command a premium in Japan),
            and <strong>renovation status</strong> — enabling price decomposition by physical property traits.
        </div>
        """, unsafe_allow_html=True)
    else:
        # Structure premium
        struct_df = structure_premium(df)
        if not struct_df.empty:
            st.markdown("**Price premium by building structure**")
            fig_struct = px.bar(
                struct_df.sort_values("premium_pct"),
                x="premium_pct", y="structure",
                orientation="h",
                color="premium_pct",
                color_continuous_scale=["#e74c3c", "#888888", "#177e89"],
                color_continuous_midpoint=0,
                text=struct_df.sort_values("premium_pct")["premium_pct"].apply(
                    lambda x: f"{x:+.1f}%"
                ),
                labels={"premium_pct": "Premium vs city median (%)", "structure": ""},
                hover_data={"median_ppm2": True, "n_transactions": True, "median_age": True},
            )
            fig_struct.update_traces(textposition="outside")
            _layout, _grid = plotly_defaults(280)
            fig_struct.update_layout(**_layout, coloraxis_showscale=False)
            fig_struct.add_vline(x=0, line_dash="dot", line_color=_grid, line_width=1)
            fig_struct.update_xaxes(gridcolor=_grid, ticksuffix="%")
            st.plotly_chart(fig_struct, use_container_width=True)

        dna_c1, dna_c2 = st.columns(2)

        with dna_c1:
            dir_df = direction_premium(df)
            if not dir_df.empty:
                st.markdown("**Price premium by facing direction**")
                fig_dir = px.bar(
                    dir_df.sort_values("premium_pct"),
                    x="premium_pct", y="direction",
                    orientation="h",
                    color="premium_pct",
                    color_continuous_scale=["#e74c3c", "#888888", "#177e89"],
                    color_continuous_midpoint=0,
                    text=dir_df.sort_values("premium_pct")["premium_pct"].apply(
                        lambda x: f"{x:+.1f}%"
                    ),
                    labels={"premium_pct": "Premium (%)", "direction": ""},
                )
                fig_dir.update_traces(textposition="outside")
                _layout, _grid = plotly_defaults(320)
                fig_dir.update_layout(**_layout, coloraxis_showscale=False)
                fig_dir.add_vline(x=0, line_dash="dot", line_color=_grid, line_width=1)
                fig_dir.update_xaxes(gridcolor=_grid, ticksuffix="%")
                st.plotly_chart(fig_dir, use_container_width=True)
            else:
                st.info("Not enough direction data in current selection.")

        with dna_c2:
            renov = renovation_premium(df)
            if renov:
                st.markdown("**Renovation premium**")
                renov_vals = [renov["median_ppm2_not_renovated"], renov["median_ppm2_renovated"]]
                renov_labels = [
                    f"Not renovated\n({renov['n_not_renovated']:,} txs)",
                    f"Renovated\n({renov['n_renovated']:,} txs)",
                ]
                fig_renov = go.Figure(go.Bar(
                    x=renov_labels,
                    y=renov_vals,
                    marker_color=["#94A3B8", "#177e89"],
                    text=[f"¥{v/10000:.0f}万/m²" for v in renov_vals],
                    textposition="outside",
                ))
                _layout, _grid = plotly_defaults(320)
                fig_renov.update_layout(**_layout,
                    margin=dict(l=10, r=10, t=50, b=10),
                    yaxis=dict(gridcolor=_grid, tickformat=",.0f"),
                    title=dict(
                        text=f"Renovation adds <b>{renov['premium_pct']:+.1f}%</b> to price/m²",
                        font=dict(size=13), x=0.5,
                    ),
                    showlegend=False)
                st.plotly_chart(fig_renov, use_container_width=True)
            else:
                st.info("Not enough renovation data in current selection.")


# ────────────────────────────────────────────────────────────────
# Footer
# ────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class='app-footer'>
        <strong>Tokyo Deep Dive</strong> · Built by
        <a href='https://santimuru.github.io' target='_blank'>Santiago Martinez</a> ·
        <a href='https://github.com/santimuru/tokyo-real-estate-explorer' target='_blank'>Source on GitHub</a>
        <br/>
        Data: {_source_label} · Last loaded: {datetime.now().strftime("%Y-%m-%d %H:%M")} UTC
    </div>
    """,
    unsafe_allow_html=True,
)
