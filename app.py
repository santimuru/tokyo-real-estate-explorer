"""
Japan Real Estate Intelligence — Home
Japan-wide real estate market overview: price map, akiya crisis, depopulation.
"""
from __future__ import annotations

import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.styles import inject_css, kpi_card, plotly_defaults
from utils.prefecture_data import get_all_as_df, NATIONAL_AVG_PPM2

st.set_page_config(
    page_title="Japan Real Estate Intelligence",
    page_icon="🗾",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()


# ────────────────────────────────────────────────────────────────
# Sidebar
# ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding:0.3rem 0 1rem'>
        <span style='font-size:1.8rem'>🗾</span><br>
        <strong style='font-size:1rem; color:#177e89;'>Japan RE Intelligence</strong>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("### Navigate")
    section = st.radio("Section", ["Price Map", "Depopulation & Prices", "Akiya Crisis"], label_visibility="collapsed")
    st.markdown("---")
    st.markdown("""<div style='font-size:0.75rem; color:#999; text-align:center; line-height:2;'>
    Built by <a href='https://santimuru.github.io' style='color:#177e89;'>Santiago Martinez</a><br>
    <a href='https://github.com/santimuru/tokyo-real-estate-explorer' style='color:#177e89;'>GitHub</a>
    </div>""", unsafe_allow_html=True)


# ────────────────────────────────────────────────────────────────
# Hero banner
# ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-banner">
    <div class="hero-title">🗾 Japan Real Estate Intelligence</div>
    <div class="hero-sub">
        A data platform covering Japan's entire real estate market across all 47 prefectures —
        from Tokyo's historic price surge to the rural vacancy crisis eating away at the countryside.
        Three interconnected stories, one dataset.
    </div>
    <span class="badge badge-live">● Live MLIT API</span>
    <span class="badge">47 Prefectures</span>
    <span class="badge">国土交通省</span>
</div>
""", unsafe_allow_html=True)


# ────────────────────────────────────────────────────────────────
# Data loading
# ────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=86400)
def load_japan_geojson():
    url = "https://raw.githubusercontent.com/dataofjapan/land/master/japan.geojson"
    return requests.get(url, timeout=20).json()


@st.cache_data(show_spinner=False)
def load_pref_df():
    df = get_all_as_df()
    df["rank_2024"] = df["price_ppm2_2024"].rank(ascending=False).astype(int)
    df["price_change_pct"] = (df["price_ppm2_2024"] - df["price_ppm2_2015"]) / df["price_ppm2_2015"] * 100
    return df


df = load_pref_df()
PRICE_COLS = {2015: "price_ppm2_2015", 2019: "price_ppm2_2019", 2024: "price_ppm2_2024"}


# ════════════════════════════════════════════════════════════════
# SECTION: PRICE MAP
# ════════════════════════════════════════════════════════════════
if section == "Price Map":
    st.markdown("### Japan real estate prices by prefecture")

    year_sel = st.select_slider("Year", options=[2015, 2019, 2024], value=2024)
    price_col = PRICE_COLS[year_sel]

    # KPIs
    tokyo_price = df.loc[df["name_en"] == "Tokyo", price_col].iloc[0]
    nat_median = int(df[price_col].median())
    cheapest_row = df.loc[df[price_col].idxmin()]
    premium = tokyo_price / nat_median

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Tokyo ¥/m²", f"¥{tokyo_price/10000:.0f}万", f"#{df.loc[df['name_en']=='Tokyo','rank_2024'].iloc[0]} nationally")
    with c2:
        kpi_card("National median", f"¥{nat_median/10000:.0f}万", f"{year_sel} average")
    with c3:
        kpi_card("Tokyo premium", f"{premium:.1f}×", "vs national median")
    with c4:
        kpi_card("Most affordable", f"{cheapest_row['name_en']}", f"¥{cheapest_row[price_col]/10000:.0f}万/m²")

    st.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)

    try:
        geojson = load_japan_geojson()
        fig_map = px.choropleth(
            df,
            geojson=geojson,
            locations="name_geo",
            featureidkey="properties.nam",
            color=price_col,
            color_continuous_scale=["#e8f8fa", "#177e89", "#0d2b2e"],
            labels={price_col: "¥/m²"},
            hover_name="name_en",
            hover_data={"name_geo": False, price_col: ":,.0f", "rank_2024": True},
        )
        fig_map.update_geos(
            fitbounds="locations",
            visible=False,
            bgcolor="rgba(0,0,0,0)",
        )
        fig_map.update_layout(
            height=520,
            margin=dict(l=0, r=0, t=0, b=0),
            coloraxis_colorbar=dict(title="¥/m²", tickformat=",.0f"),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_map, use_container_width=True)
    except Exception as exc:
        st.warning(f"Could not load map: {exc}. Showing table instead.")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Top 10 most expensive prefectures**")
        top10 = df.nlargest(10, price_col)[["name_en", "name_ja", price_col, "rank_2024"]].copy()
        top10["¥/m²"] = top10[price_col].apply(lambda x: f"¥{x/10000:.0f}万")
        top10 = top10.rename(columns={"name_en": "Prefecture", "name_ja": "日本語", "rank_2024": "Rank"})
        st.dataframe(top10[["Prefecture", "日本語", "¥/m²", "Rank"]], use_container_width=True, hide_index=True)
    with col_b:
        st.markdown("**Bottom 10 most affordable prefectures**")
        bot10 = df.nsmallest(10, price_col)[["name_en", "name_ja", price_col]].copy()
        bot10["¥/m²"] = bot10[price_col].apply(lambda x: f"¥{x/10000:.0f}万")
        bot10 = bot10.rename(columns={"name_en": "Prefecture", "name_ja": "日本語"})
        st.dataframe(bot10[["Prefecture", "日本語", "¥/m²"]], use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════
# SECTION: DEPOPULATION & PRICES
# ════════════════════════════════════════════════════════════════
elif section == "Depopulation & Prices":
    st.markdown("### Population decline vs price appreciation (2010–2024)")

    st.markdown("""
    <div class="insight-box">
        Japan lost population in <strong>40 out of 47 prefectures</strong> between 2010 and 2020.
        Yet <strong>Tokyo prices rose 43%</strong> over the same period — a stark illustration
        of how urbanization concentration can override demographic headwinds.
    </div>
    """, unsafe_allow_html=True)

    # KPIs
    growing = (df["pop_change_pct"] > 0).sum()
    declining = (df["pop_change_pct"] <= 0).sum()
    avg_price_change = df["price_change_pct"].mean()
    tokyo_price_chg = df.loc[df["name_en"] == "Tokyo", "price_change_pct"].iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Prefectures declining", f"{declining}/47", "Population 2010→2020")
    with c2:
        kpi_card("Avg price growth", f"+{avg_price_change:.0f}%", "2015→2024 national avg")
    with c3:
        kpi_card("Tokyo price growth", f"+{tokyo_price_chg:.0f}%", "2015→2024")
    with c4:
        kpi_card("Prefectures growing", f"{growing}/47", "Population 2010→2020")

    st.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)

    # Scatter: pop change vs price change
    fig_scatter = px.scatter(
        df,
        x="pop_change_pct",
        y="price_change_pct",
        color="is_major_metro",
        text="name_en",
        size="price_ppm2_2024",
        size_max=30,
        color_discrete_map={True: "#177e89", False: "#aaa"},
        labels={
            "pop_change_pct": "Population change 2010–2020 (%)",
            "price_change_pct": "Price change 2015–2024 (%)",
            "is_major_metro": "Major metro",
        },
        hover_name="name_en",
        hover_data={"name_en": False, "pop_change_pct": ":.1f", "price_change_pct": ":.1f"},
    )
    _layout, _grid = plotly_defaults(480)
    fig_scatter.update_traces(textposition="top center", textfont_size=9)
    fig_scatter.update_layout(**_layout, margin=dict(l=10, r=10, t=20, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig_scatter.update_xaxes(gridcolor=_grid, zeroline=True, zerolinecolor=_grid, ticksuffix="%")
    fig_scatter.update_yaxes(gridcolor=_grid, zeroline=True, zerolinecolor=_grid, ticksuffix="%")
    fig_scatter.add_hline(y=0, line_dash="dot", line_color=_grid)
    fig_scatter.add_vline(x=0, line_dash="dot", line_color=_grid)
    st.plotly_chart(fig_scatter, use_container_width=True)

    # Top 10 price growth bar
    st.markdown("**Top 10 prefectures by price growth (2015–2024)**")
    top_growth = df.nlargest(10, "price_change_pct")[["name_en", "price_change_pct", "is_major_metro"]].copy()
    fig_bar = px.bar(
        top_growth.sort_values("price_change_pct"),
        x="price_change_pct",
        y="name_en",
        orientation="h",
        color="is_major_metro",
        color_discrete_map={True: "#177e89", False: "#84cdd4"},
        labels={"price_change_pct": "Price growth (%)", "name_en": "", "is_major_metro": "Major metro"},
    )
    _layout, _grid = plotly_defaults(350)
    fig_bar.update_layout(**_layout, showlegend=False)
    fig_bar.update_xaxes(gridcolor=_grid, ticksuffix="%")
    st.plotly_chart(fig_bar, use_container_width=True)


# ════════════════════════════════════════════════════════════════
# SECTION: AKIYA CRISIS
# ════════════════════════════════════════════════════════════════
elif section == "Akiya Crisis":
    st.markdown("### Japan's akiya (空き家) vacancy crisis")

    st.markdown("""
    <div class="insight-box">
        Japan has more vacant homes per capita than any developed country. At current trends,
        <strong>1 in 5 homes will be vacant by 2033</strong>. The <em>akiya</em> (空き家) problem
        is especially severe in rural prefectures losing population — yet even urban areas
        show rising vacancy as households shrink.
    </div>
    """, unsafe_allow_html=True)

    worst_row = df.loc[df["akiya_rate_2023"].idxmax()]
    nat_avg = df["akiya_rate_2023"].mean()
    total_vacant_m = 9.0  # Japan 2023 housing survey estimate (millions)
    avg_change = (df["akiya_rate_2023"] - df["akiya_rate_2013"]).mean()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Vacant homes (est.)", "9 million", "2023 Housing & Land Survey")
    with c2:
        kpi_card("National avg vacancy", f"{nat_avg:.1f}%", "2023")
    with c3:
        kpi_card("Worst prefecture", f"{worst_row['name_en']}", f"{worst_row['akiya_rate_2023']:.1f}% vacancy")
    with c4:
        kpi_card("10-yr trend", f"+{avg_change:.1f}pp", "2013→2023 avg change")

    st.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)

    col_map, col_bar = st.columns([3, 2])

    with col_map:
        try:
            geojson = load_japan_geojson()
            fig_akiya = px.choropleth(
                df,
                geojson=geojson,
                locations="name_geo",
                featureidkey="properties.nam",
                color="akiya_rate_2023",
                color_continuous_scale=["#fff9e6", "#f39c12", "#c0392b"],
                labels={"akiya_rate_2023": "Vacancy %"},
                hover_name="name_en",
                hover_data={"name_geo": False, "akiya_rate_2023": ":.1f", "akiya_rate_2013": ":.1f"},
            )
            fig_akiya.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
            fig_akiya.update_layout(
                height=460,
                margin=dict(l=0, r=0, t=0, b=0),
                coloraxis_colorbar=dict(title="Vacancy %", ticksuffix="%"),
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_akiya, use_container_width=True)
        except Exception as exc:
            st.warning(f"Could not load map: {exc}")

    with col_bar:
        st.markdown("**Top 15 prefectures by vacancy rate (2023)**")
        top15 = df.nlargest(15, "akiya_rate_2023")[["name_en", "akiya_rate_2023", "akiya_rate_2013"]].copy()
        fig_vac = px.bar(
            top15.sort_values("akiya_rate_2023"),
            x="akiya_rate_2023",
            y="name_en",
            orientation="h",
            color="akiya_rate_2023",
            color_continuous_scale=["#fde8b0", "#f39c12", "#c0392b"],
            labels={"akiya_rate_2023": "Vacancy rate (%)", "name_en": ""},
        )
        _layout, _grid = plotly_defaults(460)
        fig_vac.update_layout(**_layout, coloraxis_showscale=False)
        fig_vac.update_xaxes(gridcolor=_grid, ticksuffix="%")
        st.plotly_chart(fig_vac, use_container_width=True)

    # Regional vacancy trend
    st.markdown("**Vacancy rate trend by year (national sample)**")
    trend_data = []
    for _, row in df.iterrows():
        for yr, col in [(2013, "akiya_rate_2013"), (2018, "akiya_rate_2018"), (2023, "akiya_rate_2023")]:
            trend_data.append({"prefecture": row["name_en"], "region": row["region"], "year": yr, "akiya_rate": row[col]})
    trend_df = pd.DataFrame(trend_data)
    region_trend = trend_df.groupby(["region", "year"])["akiya_rate"].mean().reset_index()

    fig_trend = px.line(
        region_trend,
        x="year",
        y="akiya_rate",
        color="region",
        markers=True,
        labels={"year": "", "akiya_rate": "Avg vacancy rate (%)", "region": "Region"},
    )
    _layout, _grid = plotly_defaults(320)
    fig_trend.update_layout(**_layout,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig_trend.update_xaxes(showgrid=False, tickvals=[2013, 2018, 2023])
    fig_trend.update_yaxes(gridcolor=_grid, ticksuffix="%")
    st.plotly_chart(fig_trend, use_container_width=True)


# ────────────────────────────────────────────────────────────────
# Footer
# ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-footer">
    <strong>Japan Real Estate Intelligence</strong> · Built by
    <a href='https://santimuru.github.io' target='_blank'>Santiago Martinez</a> ·
    <a href='https://github.com/santimuru/tokyo-real-estate-explorer' target='_blank'>Source on GitHub</a><br/>
    Data: MLIT Real Estate Information Library · Prefecture data: Japan Housing and Land Survey
</div>
""", unsafe_allow_html=True)
