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
    ward_summary, yoy_growth, price_trend, layout_distribution, estimate_price,
    neighborhood_summary, investment_signals, structure_premium,
    direction_premium, renovation_premium, format_jpy, format_ppm2,
)
from utils.styles import (
    inject_css, page_header, section_title, callout, kpi_card,
    footer, plotly_base, year_ticks, get_theme, nav_sidebar,
)

st.set_page_config(
    page_title="Tokyo Deep Dive · Japan RE",
    page_icon="🗼",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()
nav_sidebar()


# ── Data ───────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Fetching Tokyo transactions from MLIT API…", ttl=3600)
def _load() -> pd.DataFrame:
    return load_data()


df_all = _load()
_source = data_source_label()
is_live = "official" in _source.lower()
min_year, max_year = int(df_all["tx_year"].min()), int(df_all["tx_year"].max())


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🗼 Filters")

    years_available = sorted(df_all["tx_year"].unique())
    year_range = st.slider(
        "Transaction year",
        min_value=int(min(years_available)),
        max_value=int(max(years_available)),
        value=(int(min(years_available)), int(max(years_available))),
        format="%d",
    )
    available_types = sorted(df_all["property_type"].dropna().unique().tolist())
    st.markdown("**Property type**")
    select_all_types = st.checkbox("All types", value=True, key="cb_all_types")
    if select_all_types:
        ptype_filter = available_types
    else:
        ptype_filter = [t for t in available_types if st.checkbox(t, value=True, key=f"cb_{t}")]
        if not ptype_filter:
            ptype_filter = available_types
            st.caption("Showing all (none selected)")
    area_min, area_max = st.slider("Area (m²)", 0, 300, (0, 300), step=10)

    st.markdown("---")
    source_icon = "🟢" if is_live else "🟡"
    st.markdown(f"""
<div class="info-badge">
    <strong>{source_icon} Data Source</strong><br>
    {_source}
</div>
""", unsafe_allow_html=True)
    st.markdown("---")
    st.caption("Built by [Santiago Martinez](https://santimuru.github.io) · [GitHub](https://github.com/santimuru/tokyo-real-estate-explorer)")


# ── Page header ────────────────────────────────────────────────────────────────
page_header(
    eyebrow="Japan Real Estate Intelligence · Tokyo Deep Dive",
    title="Tokyo's 23 Wards — Deep Analytics",
    desc=(
        f"Ward-level breakdown of Tokyo's real estate market covering {min_year}–{max_year} "
        f"with {len(df_all):,} official transactions. "
        "Explore price geography, market trends, per-ward analysis, a data-driven price estimator, "
        "and investment signals — all powered by MLIT transaction records."
    ),
    badges=["● Live MLIT API" if is_live else "Demo Data", "23 Wards", f"{min_year}–{max_year}"],
)

# ── Filters ────────────────────────────────────────────────────────────────────
df = df_all[
    (df_all["tx_year"].between(*year_range))
    & (df_all["property_type"].isin(ptype_filter))
    & (df_all["area_m2"].between(area_min, area_max))
].copy()


if df.empty:
    st.warning("No transactions match the current filters. Try widening them.")
    st.stop()

# ── Global KPIs ────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Transactions",  f"{len(df):,}")
k2.metric("Median price",  format_jpy(df["trade_price_jpy"].median()))
k3.metric("Median ¥/m²",   format_ppm2(df["price_per_m2_jpy"].median()))
k4.metric("YoY growth",    f"{yoy_growth(df):+.1f}%")
k5.metric("Wards covered", str(df["ward"].nunique()))

st.markdown("<div style='margin-bottom:1.5rem'></div>", unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🗺️ Map & Rankings",
    "📈 Market Trends",
    "🏙️ Ward Analysis",
    "💴 Price Estimator",
    "🧠 Market Intelligence",
])


# ══════════════════════════════════════════════════════════════════════
# TAB 1 — MAP & RANKINGS
# ══════════════════════════════════════════════════════════════════════
with tab1:
    section_title(
        "Price geography across Tokyo's 23 wards",
        "Each bubble is a ward. Size = transaction volume. Color intensity = median ¥/m². "
        "Hover for details. The geographic spread from central premium wards to outer affordable ones "
        "can be 3–4× in a single city.",
    )

    summary = ward_summary(df)
    summary["lat"]     = summary["ward"].map(lambda w: TOKYO_WARDS[w]["lat"])
    summary["lon"]     = summary["ward"].map(lambda w: TOKYO_WARDS[w]["lon"])
    summary["ward_ja"] = summary["ward"].map(lambda w: TOKYO_WARDS[w]["ja"])
    summary["ppm2_fmt"]  = summary["median_ppm2"].apply(lambda x: f"¥{x/10000:.0f}万/m²")
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
            return [int(59 + t * 29), int(130 - t * 100), int(246 - t * 180), 200]
        summary["color"] = summary["median_ppm2"].apply(_color)

        layer = pdk.Layer(
            "ScatterplotLayer", data=summary,
            get_position=["lon", "lat"], get_radius="radius",
            get_fill_color="color", pickable=True, opacity=0.85,
            stroked=True, get_line_color=[255, 255, 255, 120], line_width_min_pixels=1,
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
                    "backgroundColor": "#1E293B", "color": "white",
                    "fontSize": "12px", "padding": "10px", "borderRadius": "6px",
                },
            },
        )
        st.pydeck_chart(deck, use_container_width=True)

    with rank_col:
        section_title("All 23 wards ranked")
        rank = summary[["ward", "ward_ja", "median_ppm2", "median_price", "n_transactions"]].copy()
        rank["Ward"]         = rank.apply(lambda r: f"{r['ward']} ({r['ward_ja']})", axis=1)
        rank["¥/m²"]         = rank["median_ppm2"].apply(lambda x: f"¥{x/10000:.0f}万")
        rank["Median price"] = rank["median_price"].apply(
            lambda x: f"¥{x/1e8:.2f}億" if x >= 1e8 else f"¥{x/1e6:.0f}百万"
        )
        rank = rank[["Ward", "¥/m²", "Median price", "n_transactions"]].rename(columns={"n_transactions": "Txs"})
        rank.index = range(1, len(rank) + 1)
        st.dataframe(rank, use_container_width=True, height=500)

    top_w, bot_w = summary.iloc[0], summary.iloc[-1]
    callout(
        f"📍 <strong>{top_w['ward']} ({top_w['ward_ja']})</strong> is the most expensive ward "
        f"at <strong>{top_w['ppm2_fmt']}</strong>. "
        f"<strong>{bot_w['ward']} ({bot_w['ward_ja']})</strong> sits at <strong>{bot_w['ppm2_fmt']}</strong> — "
        f"a <strong>{top_w['median_ppm2']/bot_w['median_ppm2']:.1f}× price gap</strong> within the same city."
    )


# ══════════════════════════════════════════════════════════════════════
# TAB 2 — MARKET TRENDS
# ══════════════════════════════════════════════════════════════════════
with tab2:
    section_title(
        f"Tokyo market evolution {min_year}–{max_year}",
        "YoY breakdown by ward and property type below. Heatmap reveals which wards appreciated and which plateaued.",
    )

    trend_all = price_trend(df)
    first_val, last_val = trend_all["median_ppm2"].iloc[0], trend_all["median_ppm2"].iloc[-1]
    total_growth = (last_val - first_val) / first_val * 100

    callout(
        f"Tokyo's citywide median ¥/m² moved from <strong>¥{first_val/10000:.0f}万</strong> ({min_year}) "
        f"to <strong>¥{last_val/10000:.0f}万</strong> ({max_year}) — "
        f"a <strong>{total_growth:+.1f}% appreciation</strong> over the period. "
        "Post-COVID demand recovery, a weak yen attracting foreign capital, "
        "and chronic undersupply in central wards have all contributed.",
        variant="pos",
    )

    c1, c2 = st.columns(2)

    with c1:
        section_title("YoY price change by ward", "Latest year vs prior year — positive = appreciation")
        ward_yoy_rows = [{"ward": w, "yoy": yoy_growth(df, ward=w)} for w in df["ward"].unique()]
        yoy_df = pd.DataFrame(ward_yoy_rows).sort_values("yoy", ascending=True)
        base2, grid2, zero2 = plotly_base(520)
        fig_yoy = px.bar(
            yoy_df, x="yoy", y="ward", orientation="h",
            color="yoy",
            color_continuous_scale=["#EF4444", "#888888", "#3B82F6"],
            color_continuous_midpoint=0,
            labels={"yoy": "YoY (%)", "ward": ""},
        )
        fig_yoy.update_layout(**base2)
        fig_yoy.update_coloraxes(showscale=False)
        fig_yoy.update_xaxes(gridcolor=grid2, ticksuffix="%")
        fig_yoy.add_vline(x=0, line_dash="dot", line_color=zero2, line_width=1)
        fig_yoy.update_traces(hovertemplate="%{y}<br>YoY: %{x:+.1f}%<extra></extra>")
        st.plotly_chart(fig_yoy, use_container_width=True, config={"scrollZoom": False, "doubleClick": False, "displayModeBar": False})

    with c2:
        section_title(
            "Price trend by property type",
            "Quarterly median. Year labels only — hover to see individual quarters.",
        )
        trend_pt = (
            df.groupby(["tx_period", "property_type"])["price_per_m2_jpy"]
            .median().reset_index()
            .rename(columns={"price_per_m2_jpy": "median_ppm2"})
        )
        pt_periods = sorted(trend_pt["tx_period"].unique().tolist())
        tv, tt = year_ticks(pt_periods)

        base3, grid3, _ = plotly_base(520)
        fig_pt = px.line(
            trend_pt, x="tx_period", y="median_ppm2", color="property_type", markers=True,
            labels={"tx_period": "", "median_ppm2": "¥/m²", "property_type": ""},
            color_discrete_sequence=["#3B82F6", "#F59E0B", "#EF4444", "#8B5CF6"],
        )
        fig_pt.update_layout(
            **base3,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        fig_pt.update_xaxes(tickvals=tv, ticktext=tt, showgrid=False)
        fig_pt.update_yaxes(gridcolor=grid3, tickformat=",.0f")
        fig_pt.update_traces(hovertemplate="%{fullData.name}<br>%{x}<br>¥/m²: %{y:,.0f}<extra></extra>")
        st.plotly_chart(fig_pt, use_container_width=True, config={"scrollZoom": False, "doubleClick": False, "displayModeBar": False})

    section_title("Ward × year price heatmap", "Each cell = median ¥/m² — spot which wards appreciated fastest and which plateaued")
    heat_df = (
        df.groupby(["ward", "tx_year"])["price_per_m2_jpy"]
        .median().reset_index()
    )
    heat_pivot = heat_df.pivot(index="ward", columns="tx_year", values="price_per_m2_jpy")
    base4, _, _ = plotly_base(520)
    fig_heat = px.imshow(
        heat_pivot,
        color_continuous_scale=["#DBEAFE", "#3B82F6", "#1D4ED8"],
        labels={"color": "¥/m²", "x": "", "y": ""},
        aspect="auto",
    )
    fig_heat.update_layout(**base4, coloraxis_colorbar=dict(title="¥/m²", tickformat=",.0f"))
    fig_heat.update_xaxes(side="bottom", tickformat="d")
    st.plotly_chart(fig_heat, use_container_width=True, config={"scrollZoom": False, "doubleClick": False, "displayModeBar": False})


# ══════════════════════════════════════════════════════════════════════
# TAB 3 — WARD ANALYSIS
# ══════════════════════════════════════════════════════════════════════
with tab3:
    ward_list = sorted(df["ward"].unique())
    if not ward_list:
        st.warning("No wards available with the current filters.")
        st.stop()

    default_idx = ward_list.index("Minato") if "Minato" in ward_list else 0
    selected_ward = st.selectbox(
        "Select a ward",
        options=ward_list,
        format_func=lambda w: f"{w}  ·  {TOKYO_WARDS[w]['ja']}",
        index=default_idx,
    )

    ward_df   = df[df["ward"] == selected_ward]
    ward_info = TOKYO_WARDS[selected_ward]
    ward_yoy  = yoy_growth(df, ward=selected_ward)

    ward_rank = (
        ward_summary(df).reset_index(drop=True).reset_index()
        .query("ward == @selected_ward")["index"].values
    )
    rank_pos = int(ward_rank[0]) + 1 if len(ward_rank) else "—"

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Transactions", f"{len(ward_df):,}")
    c2.metric("Median price",  format_jpy(ward_df["trade_price_jpy"].median()))
    c3.metric("Median ¥/m²",   format_ppm2(ward_df["price_per_m2_jpy"].median()))
    c4.metric("YoY growth",    f"{ward_yoy:+.1f}%")
    c5.metric("Population",    f"{ward_info['pop']}k")

    callout(
        f"🏙️ <strong>{selected_ward} ({ward_info['ja']})</strong> ranks "
        f"<strong>#{rank_pos}</strong>/23 by median ¥/m² · "
        f"YoY change: <strong>{ward_yoy:+.1f}%</strong> · "
        f"Population: <strong>{ward_info['pop']}k</strong>."
    )

    r1c1, r1c2 = st.columns(2)

    with r1c1:
        section_title("Price distribution", "Clipped at 97th percentile to remove outliers")
        clip97  = ward_df["trade_price_jpy"].quantile(0.97)
        clipped = ward_df[ward_df["trade_price_jpy"] <= clip97]
        base, grid, _ = plotly_base(300)
        fig = px.histogram(
            clipped, x="trade_price_jpy", nbins=40,
            color_discrete_sequence=["#3B82F6"],
            labels={"trade_price_jpy": "Trade price (JPY)", "count": ""},
        )
        fig.update_layout(**base, bargap=0.05)
        fig.update_xaxes(tickformat=".2s")
        fig.update_yaxes(gridcolor=grid)
        fig.update_traces(hovertemplate="Price: ¥%{x:,.0f}<extra></extra>")
        st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": False, "doubleClick": False, "displayModeBar": False})

    with r1c2:
        section_title("Area vs ¥/m²", "Sample of up to 1,500 transactions · color by property type")
        scatter_df = ward_df.sample(min(1500, len(ward_df)), random_state=42)
        base2, grid2, _ = plotly_base(300)
        fig = px.scatter(
            scatter_df, x="area_m2", y="price_per_m2_jpy", color="property_type",
            opacity=0.45,
            color_discrete_sequence=["#3B82F6", "#F59E0B", "#EF4444", "#8B5CF6"],
            labels={"area_m2": "Area (m²)", "price_per_m2_jpy": "¥/m²", "property_type": ""},
        )
        fig.update_layout(
            **base2,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        fig.update_yaxes(gridcolor=grid2, tickformat=",.0f")
        fig.update_xaxes(gridcolor=grid2)
        fig.update_traces(hovertemplate="%{fullData.name}<br>Area: %{x:.0f} m²<br>¥/m²: %{y:,.0f}<extra></extra>")
        st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": False, "doubleClick": False, "displayModeBar": False})

    r2c1, r2c2 = st.columns(2)

    with r2c1:
        section_title("Price trend", "Quarterly median ¥/m²")
        trend_w = price_trend(df, ward=selected_ward)
        if not trend_w.empty:
            w_periods = trend_w["tx_period"].tolist()
            tv, tt = year_ticks(w_periods)
            base3, grid3, _ = plotly_base(300)
            fig = px.line(trend_w, x="tx_period", y="median_ppm2", markers=True,
                          labels={"tx_period": "", "median_ppm2": "¥/m²"})
            fig.update_traces(line_color="#3B82F6", line_width=3, marker_size=7,
                              hovertemplate="%{x}<br>¥/m²: %{y:,.0f}<extra></extra>")
            fig.update_layout(**base3)
            fig.update_xaxes(tickvals=tv, ticktext=tt, showgrid=False)
            fig.update_yaxes(gridcolor=grid3, tickformat=",.0f")
            st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": False, "doubleClick": False, "displayModeBar": False})

    with r2c2:
        section_title("Layout breakdown", "Transaction count by apartment layout type")
        layout_df = layout_distribution(df, ward=selected_ward)
        layout_df = layout_df[layout_df["n"] > 0]
        if not layout_df.empty:
            base4, grid4, _ = plotly_base(300)
            fig = px.bar(
                layout_df.sort_values("n", ascending=True),
                x="n", y="layout", orientation="h",
                color="n",
                color_continuous_scale=["#BFDBFE", "#3B82F6", "#1D4ED8"],
                labels={"n": "Transactions", "layout": ""},
            )
            fig.update_layout(**base4)
            fig.update_coloraxes(showscale=False)
            fig.update_xaxes(gridcolor=grid4)
            fig.update_traces(hovertemplate="%{y}<br>Transactions: %{x:,}<extra></extra>")
            st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": False, "doubleClick": False, "displayModeBar": False})
        else:
            st.info("No layout data available for this ward with current filters.")


# ══════════════════════════════════════════════════════════════════════
# TAB 4 — PRICE ESTIMATOR
# ══════════════════════════════════════════════════════════════════════
with tab4:
    section_title(
        "Property price estimator",
        "Enter a property's characteristics to get a price range derived from comparable transactions.",
    )
    _has_extended = "structure" in df_all.columns and df_all["structure"].notna().any()

    callout(
        "This estimator uses <strong>k-nearest neighbors</strong> matching — it finds the most similar "
        "transactions to your query property based on ward, floor area, building age, and station proximity, "
        f"then returns <strong>P10 / P50 / P90 percentiles</strong> from {len(df_all):,} comparable deals. "
        + ("Extended attributes (structure, orientation, renovation) are available from the live MLIT data." if _has_extended
           else "Connect to the live MLIT API to unlock structure, orientation, and renovation attributes.")
    )

    ec1, ec2 = st.columns(2)
    with ec1:
        est_ward    = st.selectbox("Ward", options=sorted(TOKYO_WARDS.keys()),
                                   format_func=lambda w: f"{w}  ·  {TOKYO_WARDS[w]['ja']}",
                                   index=sorted(TOKYO_WARDS.keys()).index("Shibuya"))
        est_type    = st.selectbox("Property type", options=PROPERTY_TYPES, index=0)
        est_area    = st.number_input("Floor area (m²)", min_value=15, max_value=300, value=55, step=5)
    with ec2:
        est_year    = st.number_input("Year built", min_value=1970, max_value=datetime.now().year, value=2010, step=1)
        if is_live:
            est_minutes = 8  # MLIT API doesn't include station walk-time; not used in live matching
            st.caption("ℹ️ Station proximity unavailable from MLIT API — not used in matching.")
        else:
            est_minutes = st.number_input("Walk to nearest station (min)", min_value=1, max_value=30, value=8, step=1)

    _structure_opts  = ["Any", "RC", "SRC", "Steel", "Light Steel", "Wood"]
    _direction_opts  = ["Any", "South", "Southeast", "Southwest", "East", "West", "North", "Northeast", "Northwest"]
    with st.expander(
        "🔬 Advanced features" + (" — improves accuracy with live data" if _has_extended else " — requires live MLIT data"),
        expanded=_has_extended,
    ):
        adv1, adv2, adv3 = st.columns(3)
        with adv1: est_structure = st.selectbox("Structure type", _structure_opts)
        with adv2: est_direction = st.selectbox("Facing direction", _direction_opts)
        with adv3:
            st.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
            est_renovated = st.checkbox("Recently renovated")

    if st.button("Estimate →", type="primary"):
        result = estimate_price(
            df_all, ward=est_ward, area_m2=float(est_area), year_built=int(est_year),
            station_minutes=int(est_minutes), property_type=est_type,
            structure=est_structure if est_structure != "Any" else None,
            direction=est_direction if est_direction != "Any" else None,
            renovated=est_renovated,
        )

        st.markdown("---")
        age_label = datetime.now().year - int(est_year)
        st.markdown(f"#### {est_area:.0f} m² · {est_type} · {est_ward} ({TOKYO_WARDS[est_ward]['ja']}) · {age_label} yr old")

        rc1, rc2, rc3 = st.columns(3)
        rc1.metric("Conservative (P10)", format_jpy(result["total_p10"]), format_ppm2(result["ppm2_p10"]))
        rc2.metric("Most likely (P50)",  format_jpy(result["total_p50"]), format_ppm2(result["ppm2_p50"]))
        rc3.metric("Optimistic (P90)",   format_jpy(result["total_p90"]), format_ppm2(result["ppm2_p90"]))
        st.caption(f"Based on {result['n_comparables']:,} comparable transactions.")

        base, _, _ = plotly_base(160)
        fig_range = go.Figure()
        fig_range.add_trace(go.Bar(
            x=[result["total_p90"] - result["total_p10"]], y=["Estimated range"],
            base=result["total_p10"], orientation="h",
            marker_color="rgba(59,130,246,0.18)",
            marker_line=dict(color="#3B82F6", width=2),
            showlegend=False,
            hovertemplate="P10: ¥%{base:,.0f}<br>P90: ¥%{x:,.0f}<extra></extra>",
        ))
        fig_range.add_trace(go.Scatter(
            x=[result["total_p50"]], y=["Estimated range"],
            mode="markers+text",
            marker=dict(size=22, color="#3B82F6", symbol="diamond"),
            text=[format_jpy(result["total_p50"])], textposition="top center",
            showlegend=False,
            hovertemplate="Median: ¥%{x:,.0f}<extra></extra>",
        ))
        fig_range.update_layout(**base, margin=dict(l=8, r=8, t=40, b=8), xaxis_tickformat=",.0f")
        st.plotly_chart(fig_range, use_container_width=True, config={"scrollZoom": False, "doubleClick": False, "displayModeBar": False})


# ══════════════════════════════════════════════════════════════════════
# TAB 5 — MARKET INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════
with tab5:

    # Investment signal dashboard
    section_title(
        "Investment Signal Dashboard",
        "Each ward scored on price momentum (YoY ¥/m² change) vs affordability vs the Tokyo median. "
        "Value Score (0–100) weights momentum 60% + affordability 40%. "
        "Rising wards still below market average score highest.",
    )

    sig_df = investment_signals(df)

    if not sig_df.empty:
        sig_col, top_col = st.columns([3, 1])

        with sig_col:
            base, grid, zero = plotly_base(480, margin=dict(l=8, r=8, t=20, b=40))
            city_med_ppm2 = float(df["price_per_m2_jpy"].median())
            avg_momentum  = float(sig_df["momentum_pct"].mean())

            fig_sig = go.Figure()
            fig_sig.add_vline(x=city_med_ppm2, line_dash="dot", line_color=zero, line_width=1)
            fig_sig.add_hline(y=avg_momentum,  line_dash="dot", line_color=zero, line_width=1)

            fig_sig.add_trace(go.Scatter(
                x=sig_df["median_ppm2"], y=sig_df["momentum_pct"],
                mode="markers+text", text=sig_df["ward"],
                textposition="top center", textfont=dict(size=9),
                marker=dict(
                    size=np.sqrt(sig_df["n_transactions"]).clip(8, 28),
                    color=sig_df["value_score"],
                    colorscale=[[0, "#EF4444"], [0.4, "#F59E0B"], [0.7, "#10B981"], [1, "#3B82F6"]],
                    showscale=True,
                    colorbar=dict(title="Value Score", thickness=12, len=0.7),
                    line=dict(color="white", width=1),
                ),
                customdata=np.stack([sig_df["signal"], sig_df["value_score"], sig_df["volume_trend_pct"]], axis=1),
                hovertemplate=(
                    "<b>%{text}</b><br>Signal: %{customdata[0]}<br>"
                    "Value Score: %{customdata[1]:.0f}<br>"
                    "Momentum: %{y:+.1f}%<br>Median ¥/m²: ¥%{x:,.0f}<br>"
                    "Volume change: %{customdata[2]:+.0f}%<extra></extra>"
                ),
            ))

            x_range = [sig_df["median_ppm2"].min() * 0.92, sig_df["median_ppm2"].max() * 1.05]
            y_range = [sig_df["momentum_pct"].min() - 1.5,  sig_df["momentum_pct"].max() + 2.5]
            for label, x_frac, y_frac in [
                ("Rising Stars", 0.08, 0.92), ("Hot Market", 0.85, 0.92),
                ("Undervalued",  0.08, 0.08), ("Cooling",    0.85, 0.08),
            ]:
                fig_sig.add_annotation(
                    x=x_range[0] + (x_range[1] - x_range[0]) * x_frac,
                    y=y_range[0] + (y_range[1] - y_range[0]) * y_frac,
                    text=label, showarrow=False,
                    font=dict(size=10, color=zero),
                )

            fig_sig.update_layout(
                **base, showlegend=False,
                xaxis=dict(title="Median ¥/m²", gridcolor=grid, tickformat=",.0f"),
                yaxis=dict(title="YoY Momentum (%)", gridcolor=grid, ticksuffix="%"),
            )
            st.plotly_chart(fig_sig, use_container_width=True, config={"scrollZoom": False, "doubleClick": False, "displayModeBar": False})

        with top_col:
            section_title("Top value plays")
            for _, row in sig_df.head(5).iterrows():
                kpi_card(row["ward"], row["signal"], f"Score {row['value_score']:.0f} · {row['momentum_pct']:+.1f}%")
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            section_title("Most bearish")
            for _, row in sig_df[sig_df["momentum_pct"] < 0].sort_values("momentum_pct").head(3).iterrows():
                kpi_card(row["ward"], f"{row['momentum_pct']:+.1f}%", "YoY momentum")
    else:
        st.info("Investment signals require at least 2 years of data.")

    st.markdown("---")

    # Neighborhood Intelligence
    section_title(
        "Neighborhood Intelligence",
        "District-level price breakdown within each ward — powered by the MLIT DistrictName field. "
        "This reveals sub-ward variation that ward-level averages hide: "
        "Roppongi vs Azabu-Juban vs Shibaura within Minato, for example.",
    )

    has_district = (
        "district" in df_all.columns
        and df_all["district"].notna().any()
        and (df_all["district"] != "").any()
    )

    if has_district:
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
                base, grid, _ = plotly_base(max(350, len(top_nb) * 26))
                fig_nb = px.bar(
                    top_nb.sort_values("median_ppm2"),
                    x="median_ppm2", y="district", orientation="h",
                    color="median_ppm2",
                    color_continuous_scale=["#DBEAFE", "#3B82F6", "#1D4ED8"],
                    labels={"median_ppm2": "Median ¥/m²", "district": ""},
                    text=top_nb.sort_values("median_ppm2")["median_ppm2"].apply(lambda x: f"¥{x/10000:.0f}万"),
                )
                fig_nb.update_traces(textposition="outside",
                                    hovertemplate="%{y}<br>¥/m²: %{x:,.0f}<extra></extra>")
                fig_nb.update_layout(**base)
                fig_nb.update_coloraxes(showscale=False)
                fig_nb.update_xaxes(gridcolor=grid, tickformat=",.0f")
                st.plotly_chart(fig_nb, use_container_width=True, config={"scrollZoom": False, "doubleClick": False, "displayModeBar": False})
            with nb_col2:
                if len(nb_df) >= 2:
                    top_d, cheap_d = nb_df.iloc[0], nb_df.iloc[-1]
                    callout(
                        f"Within <strong>{ni_ward}</strong>, prices vary "
                        f"<strong>{top_d['median_ppm2']/cheap_d['median_ppm2']:.1f}×</strong> "
                        f"from district to district.<br><br>"
                        f"🏆 <strong>{top_d['district']}</strong><br>"
                        f"¥{top_d['median_ppm2']/10000:.0f}万/m²<br><br>"
                        f"💡 <strong>{cheap_d['district']}</strong><br>"
                        f"¥{cheap_d['median_ppm2']/10000:.0f}万/m²"
                    )
        else:
            st.info(f"Not enough district data for {ni_ward} in the current filter range.")
    else:
        callout(
            "🔌 <strong>Connect to the live MLIT API</strong> to unlock neighborhood intelligence. "
            "The <code>DistrictName</code> field reveals sub-ward price variation — "
            "up to <strong>3–5× price gaps</strong> within a single ward.",
            variant="neg",
        )

    st.markdown("---")

    # Property DNA
    section_title(
        "Property DNA",
        "How building structure, facing orientation, and renovation history affect ¥/m². "
        "These physical attributes are sourced directly from the MLIT transaction records.",
    )

    has_dna = "structure" in df_all.columns and df_all["structure"].notna().any()

    if not has_dna:
        callout(
            "🔌 <strong>Connect to the live MLIT API</strong> to unlock Property DNA. "
            "The API provides <strong>structure</strong> (RC / SRC / Steel / Wood), "
            "<strong>facing direction</strong> (south-facing commands a premium in Japan), "
            "and <strong>renovation status</strong> — enabling price decomposition by physical traits.",
            variant="neg",
        )
    else:
        struct_df = structure_premium(df)
        if not struct_df.empty:
            section_title("Price premium by building structure", "Relative to the Tokyo city median")
            base, grid, zero = plotly_base(280)
            fig_struct = px.bar(
                struct_df.sort_values("premium_pct"),
                x="premium_pct", y="structure", orientation="h",
                color="premium_pct",
                color_continuous_scale=["#EF4444", "#888888", "#3B82F6"],
                color_continuous_midpoint=0,
                text=struct_df.sort_values("premium_pct")["premium_pct"].apply(lambda x: f"{x:+.1f}%"),
                labels={"premium_pct": "Premium vs city median (%)", "structure": ""},
            )
            fig_struct.update_traces(textposition="outside",
                                    hovertemplate="%{y}<br>Premium: %{x:+.1f}%<extra></extra>")
            fig_struct.update_layout(**base)
            fig_struct.update_coloraxes(showscale=False)
            fig_struct.add_vline(x=0, line_dash="dot", line_color=zero, line_width=1)
            fig_struct.update_xaxes(gridcolor=grid, ticksuffix="%")
            st.plotly_chart(fig_struct, use_container_width=True, config={"scrollZoom": False, "doubleClick": False, "displayModeBar": False})

        dna_c1, dna_c2 = st.columns(2)

        with dna_c1:
            dir_df = direction_premium(df)
            if not dir_df.empty:
                section_title("Price premium by facing direction")
                base2, grid2, zero2 = plotly_base(320)
                fig_dir = px.bar(
                    dir_df.sort_values("premium_pct"),
                    x="premium_pct", y="direction", orientation="h",
                    color="premium_pct",
                    color_continuous_scale=["#EF4444", "#888888", "#3B82F6"],
                    color_continuous_midpoint=0,
                    text=dir_df.sort_values("premium_pct")["premium_pct"].apply(lambda x: f"{x:+.1f}%"),
                    labels={"premium_pct": "Premium (%)", "direction": ""},
                )
                fig_dir.update_traces(textposition="outside",
                                     hovertemplate="%{y}<br>Premium: %{x:+.1f}%<extra></extra>")
                fig_dir.update_layout(**base2)
                fig_dir.update_coloraxes(showscale=False)
                fig_dir.add_vline(x=0, line_dash="dot", line_color=zero2, line_width=1)
                fig_dir.update_xaxes(gridcolor=grid2, ticksuffix="%")
                st.plotly_chart(fig_dir, use_container_width=True, config={"scrollZoom": False, "doubleClick": False, "displayModeBar": False})

        with dna_c2:
            renov = renovation_premium(df)
            if renov:
                section_title("Renovation premium")
                renov_vals   = [renov["median_ppm2_not_renovated"], renov["median_ppm2_renovated"]]
                renov_labels = [
                    f"Not renovated\n({renov['n_not_renovated']:,} txs)",
                    f"Renovated\n({renov['n_renovated']:,} txs)",
                ]
                base3, grid3, _ = plotly_base(320)
                fig_renov = go.Figure(go.Bar(
                    x=renov_labels, y=renov_vals,
                    marker_color=["#94A3B8", "#3B82F6"],
                    text=[f"¥{v/10000:.0f}万/m²" for v in renov_vals],
                    textposition="outside",
                ))
                fig_renov.update_layout(
                    **base3, margin=dict(l=8, r=8, t=50, b=8),
                    yaxis=dict(gridcolor=grid3, tickformat=",.0f"),
                    title=dict(
                        text=f"Renovation adds <b>{renov['premium_pct']:+.1f}%</b> to ¥/m²",
                        font=dict(size=13), x=0.5,
                    ),
                    showlegend=False,
                )
                st.plotly_chart(fig_renov, use_container_width=True, config={"scrollZoom": False, "doubleClick": False, "displayModeBar": False})


footer("Tokyo Deep Dive", f"{_source} · Last loaded: {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC")
