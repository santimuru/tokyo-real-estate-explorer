"""
Japan Real Estate Intelligence — Home
National overview: prefecture price map, depopulation vs prices, and the akiya vacancy crisis.
"""
from __future__ import annotations

import numpy as np
import requests
import pandas as pd
import plotly.express as px
import streamlit as st

from utils.styles import (
    inject_css, platform_hero, feature_cards, page_header,
    section_title, callout, kpi_card, footer, plotly_base,
    nav_sidebar, is_dark,
)
from utils.prefecture_data import get_all_as_df, NATIONAL_AVG_PPM2

st.set_page_config(
    page_title="Japan Real Estate Intelligence",
    page_icon="🗾",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
nav_sidebar()

# ── Sidebar — info note only ───────────────────────────────────────────────────
with st.sidebar:
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


# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_intro, tab_map, tab_demo, tab_akiya, tab_about = st.tabs([
    "🏠 Introduction", "🗺️ Price Map", "📊 Demographics", "🏚️ Akiya Crisis", "ℹ️ About",
])


# ══════════════════════════════════════════════════════════════════════
# TAB 1 — INTRODUCTION
# ══════════════════════════════════════════════════════════════════════
with tab_intro:
    platform_hero()
    feature_cards()


# ══════════════════════════════════════════════════════════════════════
# TAB 2 — PRICE MAP
# ══════════════════════════════════════════════════════════════════════
with tab_map:
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
        st.plotly_chart(fig_map, use_container_width=True, config={"scrollZoom": False})
    except Exception as exc:
        st.warning(f"Map unavailable: {exc}")

    # Analytical insight derived from data
    tokyo_2015  = df.loc[df["name_en"] == "Tokyo", "price_ppm2_2015"].iloc[0]
    gap_2015    = tokyo_2015 / df["price_ppm2_2015"].min()
    gap_2024    = df.loc[df["name_en"] == "Tokyo", "price_ppm2_2024"].iloc[0] / df["price_ppm2_2024"].min()
    callout(
        f"<strong>The gap is widening.</strong> In 2015, Tokyo traded at "
        f"<strong>{gap_2015:.1f}×</strong> the cheapest prefecture. By 2024 that multiple "
        f"had grown to <strong>{gap_2024:.1f}×</strong> — evidence that Japan's real estate boom "
        f"is highly concentrated rather than broadly distributed. "
        f"Rural prefectures appreciated in absolute terms (near-zero rates lifted all markets) "
        f"but fell further behind Tokyo in relative terms. The year selector above makes this divergence visible."
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
    page_header(
        eyebrow="Japan Overview · Demographics",
        title="Population Decline vs Price Appreciation",
        desc=(
            "Japan lost population in 40 out of 47 prefectures between 2010 and 2020. "
            "Yet Tokyo prices rose over 40% in the same period. "
            "This section explores whether demographic decline predicts real estate performance — "
            "and why the answer is more nuanced than it appears."
        ),
        badges=["2010–2024", "47 Prefectures"],
    )

    growing          = (df["pop_change_pct"] > 0).sum()
    declining        = (df["pop_change_pct"] <= 0).sum()
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
        "while rural prefectures simultaneously lost people <em>and</em> saw prices stagnate or grow slowly. "
        "The scatter below makes this divide visible — each bubble is a prefecture, sized by its 2024 median ¥/m²."
    )

    # Regression for analytical context
    m_coef, b_coef = np.polyfit(df["pop_change_pct"], df["price_change_pct"], 1)
    corr   = df["pop_change_pct"].corr(df["price_change_pct"])
    r_sq   = corr ** 2

    dark       = is_dark()
    ann_bg     = "rgba(15,23,42,0.88)"   if dark else "rgba(255,255,255,0.92)"
    ann_border = "#475569"               if dark else "#CBD5E0"
    ann_font   = "#F1F5F9"               if dark else "#0F172A"

    base, grid, zero = plotly_base(500)
    fig_scatter = px.scatter(
        df, x="pop_change_pct", y="price_change_pct",
        color="is_major_metro", size="price_ppm2_2024", size_max=28,
        color_discrete_map={True: "#3B82F6", False: "#94A3B8"},
        labels={
            "pop_change_pct":   "Population change 2010–2020 (%)",
            "price_change_pct": "Price appreciation 2015–2024 (%)",
            "is_major_metro":   "Major metro",
        },
        hover_name="name_en",
        hover_data={"pop_change_pct": ":.1f", "price_change_pct": ":.1f"},
    )

    # Regression line
    x_range = [df["pop_change_pct"].min() - 0.5, df["pop_change_pct"].max() + 0.5]
    fig_scatter.add_scatter(
        x=x_range, y=[m_coef * x + b_coef for x in x_range],
        mode="lines", line=dict(color="#94A3B8", dash="dot", width=1.5),
        showlegend=False,
    )

    # Labels only on major metros + extremes — opaque background so they're always readable
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
    st.plotly_chart(fig_scatter, use_container_width=True, config={"scrollZoom": False})

    # Data-driven analytical callout
    most_surprising = df[~df["is_major_metro"]].nlargest(3, "price_change_pct")[["name_en", "price_change_pct"]]
    callout(
        f"<strong>Correlation is weak (R² = {r_sq:.2f}):</strong> Population change explains only "
        f"{r_sq*100:.0f}% of the variation in price appreciation across prefectures. "
        f"The dotted regression line is nearly flat — confirming that demographics alone "
        f"do not drive real estate prices in Japan. Near-zero interest rates and aggressive "
        f"BoJ QE lifted prices everywhere (all 47 prefectures saw positive appreciation 2015–2024). "
        f"<strong>Biggest non-metro surprises:</strong> "
        + ", ".join(f"{r['name_en']} (+{r['price_change_pct']:.0f}%)" for _, r in most_surprising.iterrows())
        + ". Hover over any point for the full details."
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
    st.plotly_chart(fig_bar, use_container_width=True, config={"scrollZoom": False})


# ══════════════════════════════════════════════════════════════════════
# TAB 3 — AKIYA CRISIS
# ══════════════════════════════════════════════════════════════════════
with tab_akiya:
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

    worst_row    = df.loc[df["akiya_rate_2023"].idxmax()]
    nat_avg      = df["akiya_rate_2023"].mean()
    avg_change   = (df["akiya_rate_2023"] - df["akiya_rate_2013"]).mean()
    high_vacancy = int((df["akiya_rate_2023"] >= 20).sum())

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Vacant homes (est.)",  "9 million",                    "2023 Housing & Land Survey", accent=True)
    with c2: kpi_card("National avg vacancy", f"{nat_avg:.1f}%",              "2023")
    with c3: kpi_card("Worst prefecture",     worst_row["name_en"],           f"{worst_row['akiya_rate_2023']:.1f}% vacancy", accent=True)
    with c4: kpi_card("10-yr trend",          f"+{avg_change:.1f}pp",         "2013→2023 avg increase")

    callout(
        "The akiya crisis is <strong>not uniform</strong>. Coastal and mountain prefectures like "
        "Wakayama, Tokushima, and Kochi face 20%+ vacancy rates — one in five homes sitting empty. "
        "Urban prefectures have lower rates but their absolute vacant unit counts are still rising "
        "as households shrink and the population ages. The maps below show both the geographic "
        "pattern and the decade-long trajectory across regions.",
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
            st.plotly_chart(fig_akiya, use_container_width=True, config={"scrollZoom": False})
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
        st.plotly_chart(fig_vac, use_container_width=True, config={"scrollZoom": False})

    callout(
        f"<strong>{high_vacancy} prefectures</strong> already exceed 20% vacancy as of 2023. "
        f"The hardest-hit regions — Shikoku, Chugoku, and the Kinki coast — face compounding pressures: "
        f"an aging population that can no longer maintain properties, and younger generations "
        f"who have already migrated to major cities. Some municipal governments now <em>pay buyers</em> "
        f"to take ownership of akiya — with renovation subsidies reaching ¥1M+ in select towns.",
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
    st.plotly_chart(fig_trend, use_container_width=True, config={"scrollZoom": False})

    callout(
        f"<strong>Projection:</strong> If the +{avg_change:.1f}pp per-decade increase continues, "
        f"Japan's national vacancy rate will surpass <strong>20%</strong> by the early 2030s. "
        f"Every region accelerated after 2018 — suggesting structural factors "
        f"(inheritance laws making it legally complex to demolish inherited homes, high demolition costs, "
        f"and cultural reluctance to sell family properties) are reinforcing the cycle "
        f"beyond what demographic decline alone would predict.",
        variant="neg",
    )


# ══════════════════════════════════════════════════════════════════════
# TAB 4 — ABOUT
# ══════════════════════════════════════════════════════════════════════
with tab_about:
    page_header(
        eyebrow="Japan Real Estate Intelligence · About",
        title="How This Was Built",
        desc=(
            "A portfolio project combining official Japanese government transaction data "
            "with interactive analytics — from national prefecture trends to individual ward price estimators. "
            "Built end-to-end in Python: data pipeline, API integration, and interactive visualisation."
        ),
        badges=["Open Source", "Portfolio Project", "Python · Streamlit · Plotly"],
    )

    col_left, col_right = st.columns([3, 2])

    with col_left:
        section_title("Tech stack")
        st.markdown("""
| Layer | Tools |
|---|---|
| Language | Python 3.11 |
| App framework | Streamlit |
| Visualisation | Plotly Express, Plotly Graph Objects, Pydeck |
| Data wrangling | Pandas, NumPy |
| Geospatial | Plotly choropleth + dataofjapan/land GeoJSON |
| Maps | Pydeck (MapLibre) |
| API | MLIT Real Estate Information Library — XIT001 endpoint |
| Hosting | Streamlit Community Cloud |
| Source control | GitHub |
""")

        section_title("Data sources")
        st.markdown("""
| Source | What it covers | How it's used |
|---|---|---|
| MLIT XIT001 API | Transaction-level data, all 47 prefectures | City Comparison + Tokyo Deep Dive |
| Japan Housing & Land Survey | Prefecture akiya vacancy rates 2013 / 2018 / 2023 | Akiya Crisis tab |
| Statistics Bureau of Japan | Prefectural population 2010, 2020 | Demographics scatter |
| dataofjapan/land (GitHub) | Prefecture GeoJSON boundaries | All choropleth maps |
| MLIT aggregate reports / REINS | Prefecture price estimates 2015 / 2019 / 2024 | Japan price map |

**Note on MLIT data lag:** The XIT001 endpoint publishes data approximately 2 quarters behind the current date.
The app dynamically computes the latest available period to avoid requesting data that doesn't exist yet.
""")

    with col_right:
        section_title("Methodology")
        st.markdown("""
<div class="method-box">

<h4>Price estimator (k-NN)</h4>
Finds the <em>k</em> most similar transactions using a composite distance score across floor area,
building age, and station proximity. Returns P10/P50/P90 percentiles of comparable ¥/m² values,
scaled to total price. Falls back to all ward data if fewer than 20 matches exist.

<h4>Investment Value Score</h4>
Composite 0–100 score weighting YoY price momentum (60%) and relative affordability
vs the Tokyo median (40%). A ward that is rising faster than average <em>and</em> still
below the city median scores highest.

<h4>YoY growth</h4>
Compares median ¥/m² in the most recent calendar year in the dataset versus the prior year.
Requires at least one transaction per year per ward.

<h4>Ward × year heatmap</h4>
Median ¥/m² per ward × year cell. Useful for spotting which wards appreciated fastest
and which plateaued. Colour scale is relative to the full dataset range.

<h4>Station proximity in estimator</h4>
The MLIT XIT001 endpoint does not include station walk-time data. The station
proximity input in the estimator is used for within-dataset matching comparisons
but is not sourced from the API itself.

</div>
""", unsafe_allow_html=True)

        st.markdown("---")
        section_title("Author")
        st.markdown("""
**Santiago Martinez** — Data scientist and BI analyst.
Building data products that make complex markets legible.

- 🌐 [santimuru.github.io](https://santimuru.github.io)
- 💻 [github.com/santimuru](https://github.com/santimuru)
- 📁 [tokyo-real-estate-explorer repo](https://github.com/santimuru/tokyo-real-estate-explorer)
""")


footer("Japan Overview", "MLIT XIT001 API · Japan Housing and Land Survey · Statistics Bureau")
