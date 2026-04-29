"""
Japan Real Estate Intelligence — Home
National overview: prefecture price map, depopulation vs prices, and the akiya vacancy crisis.
"""
from __future__ import annotations

import requests
import pandas as pd
import plotly.express as px
import streamlit as st

from utils.styles import inject_css, page_header, section_title, callout, kpi_card, footer, plotly_base, nav_sidebar
from utils.prefecture_data import get_all_as_df, NATIONAL_AVG_PPM2

st.set_page_config(
    page_title="Japan Real Estate Intelligence",
    page_icon="🗾",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
nav_sidebar()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    section = st.radio(
        "Section",
        ["Price Map", "Depopulation & Prices", "Akiya Crisis"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown("""
<div class="info-badge">
    <strong>Data:</strong> Prefecture-level price estimates from MLIT aggregate reports
    and REINS data (2015 / 2019 / 2024).<br><br>
    <strong>Note:</strong> These are curated estimates — use City Comparison for
    transaction-level MLIT API data.
</div>
""", unsafe_allow_html=True)


# ── Data ───────────────────────────────────────────────────────────────────────
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


# ══════════════════════════════════════════════════════════════════════
# SECTION: PRICE MAP
# ══════════════════════════════════════════════════════════════════════
if section == "Price Map":
    page_header(
        eyebrow="Japan Overview · Price Map",
        title="Real Estate Prices Across Japan",
        desc=(
            "Median transaction price per m² across all 47 prefectures. "
            "Tokyo's extreme premium vs the rest of Japan is one of the defining features "
            "of the country's real estate market — use the year selector to see how the gap evolved."
        ),
        badges=["47 Prefectures", "2015 – 2024"],
    )

    year_sel = st.radio("Select year", [2015, 2019, 2024], index=2, horizontal=True)
    price_col = PRICE_COLS[year_sel]

    tokyo_price = df.loc[df["name_en"] == "Tokyo", price_col].iloc[0]
    nat_median  = int(df[price_col].median())
    cheapest    = df.loc[df[price_col].idxmin()]
    premium     = tokyo_price / nat_median

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Tokyo ¥/m²",      f"¥{tokyo_price/10000:.0f}万",  f"#{df.loc[df['name_en']=='Tokyo','rank_2024'].iloc[0]} nationally", accent=True)
    with c2: kpi_card("National median", f"¥{nat_median/10000:.0f}万",   f"{year_sel}")
    with c3: kpi_card("Tokyo premium",   f"{premium:.1f}×",              "vs national median", accent=True)
    with c4: kpi_card("Most affordable", cheapest["name_en"],            f"¥{cheapest[price_col]/10000:.0f}万/m²")

    try:
        geojson = load_japan_geojson()
        base, grid, _ = plotly_base(540)
        fig_map = px.choropleth(
            df,
            geojson=geojson,
            locations="name_geo",
            featureidkey="properties.nam",
            color=price_col,
            color_continuous_scale=["#DBEAFE", "#3B82F6", "#1D4ED8"],
            labels={price_col: "¥/m²"},
            hover_name="name_en",
            hover_data={"name_geo": False, price_col: ":,.0f", "rank_2024": True},
        )
        fig_map.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
        fig_map.update_layout(**base, coloraxis_colorbar=dict(title="¥/m²", tickformat=",.0f"))
        st.plotly_chart(fig_map, use_container_width=True)
    except Exception as exc:
        st.warning(f"Map unavailable: {exc}")

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
# SECTION: DEPOPULATION & PRICES
# ══════════════════════════════════════════════════════════════════════
elif section == "Depopulation & Prices":
    page_header(
        eyebrow="Japan Overview · Demographics",
        title="Population Decline vs Price Appreciation",
        desc=(
            "Japan lost population in 40 out of 47 prefectures between 2010 and 2020. "
            "Yet Tokyo prices rose over 40% in the same period. "
            "This page explores whether demographic decline predicts real estate performance — "
            "and why the answer is more nuanced than it appears."
        ),
        badges=["2010–2024", "47 Prefectures"],
    )

    growing = (df["pop_change_pct"] > 0).sum()
    declining = (df["pop_change_pct"] <= 0).sum()
    avg_price_change = df["price_change_pct"].mean()
    tokyo_price_chg  = df.loc[df["name_en"] == "Tokyo", "price_change_pct"].iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Prefectures declining", f"{declining}/47",           "Population 2010→2020")
    with c2: kpi_card("Avg price growth",      f"+{avg_price_change:.0f}%", "2015→2024 national avg", accent=True)
    with c3: kpi_card("Tokyo price growth",    f"+{tokyo_price_chg:.0f}%",  "2015→2024", accent=True)
    with c4: kpi_card("Prefectures growing",   f"{growing}/47",             "Population 2010→2020")

    callout(
        "Japan's real estate story isn't about population — it's about <strong>urbanisation concentration</strong>. "
        "Tokyo, Osaka, and Fukuoka absorbed most domestic migration, compressing demand into a handful of metros "
        "while rural prefectures simultaneously lost people <em>and</em> saw prices stagnate. "
        "The scatter below makes this divide visible."
    )

    base, grid, zero = plotly_base(500)
    fig_scatter = px.scatter(
        df, x="pop_change_pct", y="price_change_pct",
        color="is_major_metro", size="price_ppm2_2024", size_max=28,
        color_discrete_map={True: "#3B82F6", False: "#94A3B8"},
        labels={
            "pop_change_pct": "Population change 2010–2020 (%)",
            "price_change_pct": "Price appreciation 2015–2024 (%)",
            "is_major_metro": "Major metro",
        },
        hover_name="name_en",
        hover_data={"pop_change_pct": ":.1f", "price_change_pct": ":.1f"},
    )
    # Label only the most notable prefectures to avoid overlap
    label_mask = df["is_major_metro"] | (df["price_change_pct"] == df["price_change_pct"].max()) | (df["price_change_pct"] == df["price_change_pct"].min())
    for _, row in df[label_mask].iterrows():
        fig_scatter.add_annotation(
            x=row["pop_change_pct"], y=row["price_change_pct"],
            text=row["name_en"], showarrow=False,
            yshift=12, font=dict(size=10),
        )
    fig_scatter.update_layout(
        **base,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig_scatter.update_xaxes(gridcolor=grid, zeroline=True, zerolinecolor=zero, ticksuffix="%")
    fig_scatter.update_yaxes(gridcolor=grid, zeroline=True, zerolinecolor=zero, ticksuffix="%")
    fig_scatter.add_hline(y=0, line_dash="dot", line_color=zero)
    fig_scatter.add_vline(x=0, line_dash="dot", line_color=zero)
    st.plotly_chart(fig_scatter, use_container_width=True)

    # Insight derived from data
    most_surprising = df[~df["is_major_metro"]].nlargest(3, "price_change_pct")[["name_en", "price_change_pct"]]
    callout(
        f"<strong>Key insight:</strong> All 47 prefectures saw positive price growth (2015–2024) "
        f"regardless of population change — Japan's near-zero interest rates and aggressive QE "
        f"lifted prices everywhere. The <strong>biggest surprise performers outside the major metros</strong>: "
        + ", ".join(f"{r['name_en']} (+{r['price_change_pct']:.0f}%)" for _, r in most_surprising.iterrows())
        + ". Hover over any point for details."
    )

    section_title("Top 10 prefectures by price growth (2015–2024)")
    top_growth = df.nlargest(10, "price_change_pct")[["name_en", "price_change_pct", "is_major_metro"]].copy()
    base2, grid2, _ = plotly_base(320)
    fig_bar = px.bar(
        top_growth.sort_values("price_change_pct"),
        x="price_change_pct", y="name_en", orientation="h",
        color="is_major_metro",
        color_discrete_map={True: "#3B82F6", False: "#93C5FD"},
        labels={"price_change_pct": "Price growth (%)", "name_en": "", "is_major_metro": "Major metro"},
    )
    fig_bar.update_layout(**base2, showlegend=False)
    fig_bar.update_xaxes(gridcolor=grid2, ticksuffix="%")
    st.plotly_chart(fig_bar, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════
# SECTION: AKIYA CRISIS
# ══════════════════════════════════════════════════════════════════════
elif section == "Akiya Crisis":
    page_header(
        eyebrow="Japan Overview · Vacancy Crisis",
        title="Japan's Akiya (空き家) Problem",
        desc=(
            "Japan has more vacant homes per capita than any developed nation. "
            "The term akiya (空き家 — empty house) has become synonymous with Japan's demographic crisis: "
            "rural areas emptying out faster than buildings can be demolished, "
            "leaving an estimated 9 million vacant units as of 2023. "
            "At current trends, 1 in 5 homes will be vacant by 2033."
        ),
        badges=["空き家", "2013–2023", "47 Prefectures"],
    )

    worst_row   = df.loc[df["akiya_rate_2023"].idxmax()]
    nat_avg     = df["akiya_rate_2023"].mean()
    avg_change  = (df["akiya_rate_2023"] - df["akiya_rate_2013"]).mean()

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Vacant homes (est.)",  "9 million",                    "2023 Housing & Land Survey", accent=True)
    with c2: kpi_card("National avg vacancy", f"{nat_avg:.1f}%",              "2023")
    with c3: kpi_card("Worst prefecture",     worst_row["name_en"],           f"{worst_row['akiya_rate_2023']:.1f}% vacancy", accent=True)
    with c4: kpi_card("10-yr trend",          f"+{avg_change:.1f}pp",         "2013→2023 avg increase")

    callout(
        "The akiya crisis is <strong>not uniform</strong>. Coastal and mountain prefectures like "
        "Wakayama, Tokushima, and Kochi face 20%+ vacancy rates — one in five homes sitting empty. "
        "Urban prefectures have lower rates but their absolute numbers of vacant units are growing "
        "as households shrink and population ages. The maps below show both the geographic pattern "
        "and the decade-long trajectory.",
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
            st.plotly_chart(fig_akiya, use_container_width=True)
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
        st.plotly_chart(fig_vac, use_container_width=True)

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
    st.plotly_chart(fig_trend, use_container_width=True)


footer("Japan Overview", "MLIT XIT001 API · Japan Housing and Land Survey · Statistics Bureau")
