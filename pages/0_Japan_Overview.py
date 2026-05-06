"""
Japan Overview — prefecture price map, depopulation vs prices, and akiya vacancy crisis.
"""
from __future__ import annotations

import numpy as np
import requests
import pandas as pd
import plotly.express as px
import streamlit as st
from pathlib import Path

from utils.styles import (
    inject_css, page_header, section_title, callout, kpi_card,
    footer, plotly_base, nav_top, is_dark,
)
from utils.prefecture_data import get_all_as_df

st.set_page_config(
    page_title="Japan Overview · Japan RE",
    page_icon="🗾",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
nav_top("overview")

PARQUET_PATH = Path(__file__).resolve().parent.parent / "data" / "prefecture_aggregates.parquet"

page_header(
    eyebrow="Japan Real Estate Intelligence · National Overview",
    title="47 Prefectures. Where Is the Money Going?",
    desc=(
        "Real transaction data across all 47 prefectures — sourced directly from the MLIT "
        "Real Estate Information Library. Price geography, growth trends, and Japan's vacant home crisis."
    ),
    badges=["47 Prefectures", "2024–2025", "MLIT XIT001 API"],
)

callout(
    "✓ All price data on this page are <strong>real transaction medians</strong> from the "
    "MLIT XIT001 API — aggregated from hundreds of thousands of actual property deals across Japan. "
    "Akiya rates and population figures are from the Japan Housing &amp; Land Survey and Statistics Bureau census."
)

# ── Data ───────────────────────────────────────────────────────────────────────


@st.cache_data(show_spinner=False, ttl=86400)
def load_japan_geojson():
    url = "https://raw.githubusercontent.com/dataofjapan/land/master/japan.geojson"
    return requests.get(url, timeout=20).json()


@st.cache_data(show_spinner=False)
def load_pref_df():
    df = get_all_as_df()
    df["pref_code_str"] = df["code"].astype(int).astype(str).str.zfill(2)

    agg = pd.read_parquet(PARQUET_PATH)
    agg["prefecture_code"] = agg["prefecture_code"].astype(str).str.zfill(2)

    for year in agg["tx_year"].unique():
        slice_y = agg[agg["tx_year"] == year][["prefecture_code", "median_ppm2"]]
        slice_y = slice_y.rename(columns={"median_ppm2": f"price_ppm2_{year}"})
        df = df.merge(slice_y, left_on="pref_code_str", right_on="prefecture_code", how="left")
        df = df.drop(columns=["prefecture_code"])

    years_available = sorted(agg["tx_year"].unique())
    first_yr, last_yr = years_available[0], years_available[-1]
    df["price_change_pct"] = (
        (df[f"price_ppm2_{last_yr}"] - df[f"price_ppm2_{first_yr}"]) /
        df[f"price_ppm2_{first_yr}"] * 100
    ).fillna(0)
    df["rank_latest"] = df[f"price_ppm2_{last_yr}"].rank(ascending=False).astype(int)
    return df, years_available


df, YEARS_AVAILABLE = load_pref_df()
PRICE_COLS = {yr: f"price_ppm2_{yr}" for yr in YEARS_AVAILABLE}
LATEST_YEAR = YEARS_AVAILABLE[-1]
FIRST_YEAR  = YEARS_AVAILABLE[0]


# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_map, tab_demo, tab_akiya = st.tabs([
    "🗺️ Price Map", "📊 Demographics", "🏚️ Akiya Crisis",
])


# ══════════════════════════════════════════════════════════════════════
# TAB 1 — PRICE MAP
# ══════════════════════════════════════════════════════════════════════
with tab_map:
    section_title("Real Estate Prices Across Japan", "Median ¥/m² — use the selector to compare years")

    year_sel  = st.radio("Select year", YEARS_AVAILABLE, index=len(YEARS_AVAILABLE)-1, horizontal=True)
    price_col = PRICE_COLS[year_sel]

    tokyo_price = df.loc[df["name_en"] == "Tokyo", price_col].iloc[0]
    nat_median  = int(df[price_col].median())
    cheapest    = df.loc[df[price_col].idxmin()]
    premium     = tokyo_price / nat_median

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Tokyo ¥/m²",      f"¥{tokyo_price/10000:.0f}万",  f"#{df.loc[df['name_en']=='Tokyo','rank_latest'].iloc[0]} nationally", accent=True)
    with c2: kpi_card("National median", f"¥{nat_median/10000:.0f}万",   f"{year_sel}")
    with c3: kpi_card("Tokyo premium",   f"{premium:.1f}×",              "vs national median", accent=True)
    with c4: kpi_card("Most affordable", cheapest["name_en"],            f"¥{cheapest[price_col]/10000:.0f}万/m²")

    try:
        geojson = load_japan_geojson()
        base, grid, _ = plotly_base(540)
        fig_map = px.choropleth(
            df, geojson=geojson, locations="name_geo",
            featureidkey="properties.nam", color=price_col,
            color_continuous_scale=["#DBEAFE", "#3B82F6", "#1D4ED8"],
            labels={price_col: "¥/m²"},
            hover_name="name_en",
            hover_data={"name_geo": False, price_col: ":,.0f", "rank_2024": True},
        )
        fig_map.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
        fig_map.update_layout(**base, coloraxis_colorbar=dict(title="¥/m²", tickformat=",.0f"))
        st.plotly_chart(fig_map, use_container_width=True, config={"scrollZoom": False, "doubleClick": False, "displayModeBar": False})
    except Exception as exc:
        st.warning(f"Map unavailable: {exc}")

    gap_first  = df.loc[df["name_en"] == "Tokyo", f"price_ppm2_{FIRST_YEAR}"].iloc[0] / df[f"price_ppm2_{FIRST_YEAR}"].min()
    gap_latest = df.loc[df["name_en"] == "Tokyo", f"price_ppm2_{LATEST_YEAR}"].iloc[0] / df[f"price_ppm2_{LATEST_YEAR}"].min()
    callout(
        f"<strong>The concentration is stark.</strong> In {FIRST_YEAR}, Tokyo traded at "
        f"<strong>{gap_first:.1f}×</strong> the cheapest prefecture. In {LATEST_YEAR} that multiple is "
        f"<strong>{gap_latest:.1f}×</strong> — evidence that Japan's real estate market remains highly concentrated "
        f"in a handful of metros while rural prefectures lag."
    )

    col_a, col_b = st.columns(2)
    with col_a:
        section_title("Top 10 most expensive", f"Ranked by median ¥/m² in {year_sel}")
        top10 = df.nlargest(10, price_col)[["name_en", "name_ja", price_col]].copy()
        top10["¥/m²"] = top10[price_col].apply(lambda x: f"¥{x/10000:.0f}万")
        top10 = top10.rename(columns={"name_en": "Prefecture", "name_ja": "日本語"})
        top10.index = range(1, len(top10) + 1)
        st.dataframe(top10[["Prefecture", "日本語", "¥/m²"]], use_container_width=True)
    with col_b:
        section_title("Top 10 most affordable", f"Lowest median ¥/m² in {year_sel}")
        bot10 = df.nsmallest(10, price_col)[["name_en", "name_ja", price_col]].copy()
        bot10["¥/m²"] = bot10[price_col].apply(lambda x: f"¥{x/10000:.0f}万")
        bot10 = bot10.rename(columns={"name_en": "Prefecture", "name_ja": "日本語"})
        bot10.index = range(1, len(bot10) + 1)
        st.dataframe(bot10[["Prefecture", "日本語", "¥/m²"]], use_container_width=True)



# ══════════════════════════════════════════════════════════════════════
# TAB 2 — DEMOGRAPHICS
# ══════════════════════════════════════════════════════════════════════
with tab_demo:
    _growth_window = f"{FIRST_YEAR}–{LATEST_YEAR}"
    section_title("Population Decline vs Price Appreciation",
                  f"2010–2020 population change vs {_growth_window} price growth")

    growing          = (df["pop_change_pct"] > 0).sum()
    declining        = (df["pop_change_pct"] <= 0).sum()
    avg_price_change = df["price_change_pct"].mean()
    tokyo_price_chg  = df.loc[df["name_en"] == "Tokyo", "price_change_pct"].iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Prefectures declining", f"{declining}/47",           "Population 2010→2020")
    with c2: kpi_card("Avg price growth",      f"+{avg_price_change:.0f}%", f"{_growth_window} national avg", accent=True)
    with c3: kpi_card("Tokyo price growth",    f"+{tokyo_price_chg:.0f}%",  _growth_window, accent=True)
    with c4: kpi_card("Prefectures growing",   f"{growing}/47",             "Population 2010→2020")

    top3_growth = df.nlargest(3, "price_change_pct")[["name_en", "price_change_pct"]]
    top3_str = ", ".join(
        f"<strong>{r['name_en']}</strong> (+{r['price_change_pct']:.0f}%)"
        for _, r in top3_growth.iterrows()
    )
    callout(
        f"Strongest price growth {_growth_window}: {top3_str}. "
        f"Tokyo (+{tokyo_price_chg:.0f}%) vs national median (+{avg_price_change:.0f}%). "
        f"Each bubble is a prefecture, sized by {LATEST_YEAR} median ¥/m²."
    )

    m_coef, b_coef = np.polyfit(df["pop_change_pct"], df["price_change_pct"], 1)
    corr = df["pop_change_pct"].corr(df["price_change_pct"])
    r_sq = corr ** 2

    dark       = is_dark()
    ann_bg     = "rgba(15,23,42,0.88)" if dark else "rgba(255,255,255,0.92)"
    ann_border = "#475569"             if dark else "#CBD5E0"
    ann_font   = "#F1F5F9"             if dark else "#0F172A"

    base, grid, zero = plotly_base(500)
    fig_scatter = px.scatter(
        df, x="pop_change_pct", y="price_change_pct",
        color="is_major_metro", size=f"price_ppm2_{LATEST_YEAR}", size_max=28,
        color_discrete_map={True: "#3B82F6", False: "#94A3B8"},
        labels={
            "pop_change_pct":   "Population change 2010–2020 (%)",
            "price_change_pct": "Price appreciation 2015–2024 (%)",
            "is_major_metro":   "Major metro",
        },
        hover_name="name_en",
        hover_data={"pop_change_pct": ":.1f", "price_change_pct": ":.1f"},
    )
    x_range = [df["pop_change_pct"].min() - 0.5, df["pop_change_pct"].max() + 0.5]
    fig_scatter.add_scatter(
        x=x_range, y=[m_coef * x + b_coef for x in x_range],
        mode="lines", line=dict(color="#94A3B8", dash="dot", width=1.5),
        showlegend=False,
    )
    label_mask = (
        df["is_major_metro"] |
        (df["price_change_pct"] == df["price_change_pct"].max()) |
        (df["price_change_pct"] == df["price_change_pct"].min())
    )
    for _, row in df[label_mask].iterrows():
        fig_scatter.add_annotation(
            x=row["pop_change_pct"], y=row["price_change_pct"],
            text=row["name_en"],
            showarrow=True, arrowhead=0, arrowwidth=1,
            arrowcolor=ann_border, ax=0, ay=-26,
            font=dict(size=9, color=ann_font),
            bgcolor=ann_bg, bordercolor=ann_border,
            borderwidth=1, borderpad=3,
        )
    fig_scatter.update_layout(
        **base,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig_scatter.update_xaxes(gridcolor=grid, zeroline=True, zerolinecolor=zero, ticksuffix="%")
    fig_scatter.update_yaxes(gridcolor=grid, zeroline=True, zerolinecolor=zero, ticksuffix="%")
    fig_scatter.add_hline(y=0, line_dash="dot", line_color=zero)
    fig_scatter.add_vline(x=0, line_dash="dot", line_color=zero)
    fig_scatter.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>Population change: %{x:.1f}%<br>Price growth: %{y:.0f}%<extra></extra>"
    )
    st.plotly_chart(fig_scatter, use_container_width=True, config={"scrollZoom": False, "doubleClick": False, "displayModeBar": False})

    most_surprising = df[~df["is_major_metro"]].nlargest(3, "price_change_pct")[["name_en", "price_change_pct"]]
    callout(
        f"<strong>Correlation is weak (R² = {r_sq:.2f}):</strong> Population change explains only "
        f"{r_sq*100:.0f}% of price variation. Near-zero BoJ rates lifted all 47 prefectures — "
        f"demographics alone do not predict real estate performance in Japan. "
        f"<strong>Biggest non-metro surprises:</strong> "
        + ", ".join(f"{r['name_en']} (+{r['price_change_pct']:.0f}%)" for _, r in most_surprising.iterrows())
        + "."
    )

    section_title(f"Top 10 by price growth ({_growth_window})", "YoY appreciation — real MLIT transaction data")
    top_growth = df.nlargest(10, "price_change_pct")[["name_en", "price_change_pct", "is_major_metro"]].copy()
    top_growth_sorted = top_growth.sort_values("price_change_pct")
    base2, grid2, _ = plotly_base(320)
    fig_bar = px.bar(
        top_growth_sorted,
        x="price_change_pct", y="name_en", orientation="h",
        color="is_major_metro",
        color_discrete_map={True: "#3B82F6", False: "#93C5FD"},
        labels={"price_change_pct": "Price growth (%)", "name_en": "", "is_major_metro": "Major metro"},
        category_orders={"name_en": top_growth_sorted["name_en"].tolist()},
    )
    fig_bar.update_layout(**base2, showlegend=False)
    fig_bar.update_xaxes(gridcolor=grid2, ticksuffix="%")
    fig_bar.update_yaxes(categoryorder="array", categoryarray=top_growth_sorted["name_en"].tolist())
    fig_bar.update_traces(hovertemplate="%{y}<br>Price growth: %{x:.0f}%<extra></extra>")
    st.plotly_chart(fig_bar, use_container_width=True, config={"scrollZoom": False, "doubleClick": False, "displayModeBar": False})


# ══════════════════════════════════════════════════════════════════════
# TAB 3 — AKIYA CRISIS
# ══════════════════════════════════════════════════════════════════════
with tab_akiya:
    section_title("Japan's Akiya (空き家) Problem", "9 million vacant homes — and growing")

    worst_row    = df.loc[df["akiya_rate_2023"].idxmax()]
    nat_avg      = df["akiya_rate_2023"].mean()
    avg_change   = (df["akiya_rate_2023"] - df["akiya_rate_2013"]).mean()
    high_vacancy = int((df["akiya_rate_2023"] >= 20).sum())

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Vacant homes (est.)",  "9 million",                    "2023 Housing & Land Survey", accent=True)
    with c2: kpi_card("National avg vacancy", f"{nat_avg:.1f}%",              "2023")
    with c3: kpi_card("Worst prefecture",     worst_row["name_en"],           f"{worst_row['akiya_rate_2023']:.1f}% vacancy", accent=True)
    with c4: kpi_card("10-yr trend",          f"+{avg_change:.1f}pp",         "2013→2023 avg increase")

    top3_akiya = df.nlargest(3, "akiya_rate_2023")[["name_en", "akiya_rate_2023"]]
    top3_str = ", ".join(
        f"<strong>{r['name_en']}</strong> ({r['akiya_rate_2023']:.1f}%)"
        for _, r in top3_akiya.iterrows()
    )
    callout(
        f"The akiya crisis is <strong>not uniform</strong>. The hardest-hit prefectures — "
        f"{top3_str} — sit above 20% vacancy. Urban prefectures have lower rates but growing "
        f"absolute numbers as households shrink and inheritances pile up.",
        variant="neg",
    )

    col_map, col_bar = st.columns([3, 2])
    try:
        geojson = load_japan_geojson()
        with col_map:
            base, _, _ = plotly_base(480)
            fig_akiya = px.choropleth(
                df, geojson=geojson, locations="name_geo",
                featureidkey="properties.nam", color="akiya_rate_2023",
                color_continuous_scale=["#FEF9C3", "#F59E0B", "#DC2626"],
                labels={"akiya_rate_2023": "Vacancy %"},
                hover_name="name_en",
                hover_data={"name_geo": False, "akiya_rate_2023": ":.1f", "akiya_rate_2013": ":.1f"},
            )
            fig_akiya.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
            fig_akiya.update_layout(**base, coloraxis_colorbar=dict(title="Vacancy %", ticksuffix="%"))
            st.plotly_chart(fig_akiya, use_container_width=True, config={"scrollZoom": False, "doubleClick": False, "displayModeBar": False})
    except Exception as exc:
        st.warning(f"Map unavailable: {exc}")

    with col_bar:
        section_title("Top 15 by vacancy rate")
        top15 = df.nlargest(15, "akiya_rate_2023")[["name_en", "akiya_rate_2023"]].copy()
        base3, grid3, _ = plotly_base(480)
        fig_vac = px.bar(
            top15.sort_values("akiya_rate_2023"),
            x="akiya_rate_2023", y="name_en", orientation="h",
            color="akiya_rate_2023",
            color_continuous_scale=["#FDE68A", "#F59E0B", "#DC2626"],
            labels={"akiya_rate_2023": "Vacancy rate (%)", "name_en": ""},
        )
        fig_vac.update_layout(**base3)
        fig_vac.update_coloraxes(showscale=False)
        fig_vac.update_xaxes(gridcolor=grid3, ticksuffix="%")
        fig_vac.update_traces(hovertemplate="%{y}<br>Vacancy rate: %{x:.1f}%<extra></extra>")
        st.plotly_chart(fig_vac, use_container_width=True, config={"scrollZoom": False, "doubleClick": False, "displayModeBar": False})

    callout(
        f"<strong>{high_vacancy} prefectures</strong> already exceed 20% vacancy. "
        f"The hardest-hit regions face compounding pressures: an aging population that can no longer "
        f"maintain properties, and younger generations already migrated to major cities. "
        f"Some municipalities now <em>pay buyers</em> to take akiya, with subsidies reaching ¥1M+ in select towns.",
        variant="neg",
    )

    section_title("Vacancy rate by region (2013 → 2018 → 2023)")
    trend_data = []
    for _, row in df.iterrows():
        for yr, col in [(2013, "akiya_rate_2013"), (2018, "akiya_rate_2018"), (2023, "akiya_rate_2023")]:
            trend_data.append({"region": row["region"], "year": yr, "akiya_rate": row[col]})
    region_trend = pd.DataFrame(trend_data).groupby(["region", "year"])["akiya_rate"].mean().reset_index()

    base4, grid4, _ = plotly_base(300)
    fig_trend = px.line(
        region_trend, x="year", y="akiya_rate", color="region", markers=True,
        labels={"year": "", "akiya_rate": "Avg vacancy rate (%)", "region": ""},
    )
    fig_trend.update_layout(
        **base4,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig_trend.update_xaxes(showgrid=False, tickvals=[2013, 2018, 2023])
    fig_trend.update_yaxes(gridcolor=grid4, ticksuffix="%")
    fig_trend.update_traces(hovertemplate="%{fullData.name}<br>%{x}<br>Avg vacancy: %{y:.1f}%<extra></extra>")
    st.plotly_chart(fig_trend, use_container_width=True, config={"scrollZoom": False, "doubleClick": False, "displayModeBar": False})

    callout(
        f"<strong>Projection:</strong> If the +{avg_change:.1f}pp per-decade increase continues, "
        f"Japan's national vacancy rate will surpass <strong>20%</strong> by the early 2030s. "
        f"Every region accelerated after 2018 — structural factors (inheritance laws, high demolition costs, "
        f"cultural reluctance to sell family homes) are reinforcing the cycle.",
        variant="neg",
    )


footer("Japan Overview", "MLIT XIT001 API · Japan Housing and Land Survey · Statistics Bureau")
