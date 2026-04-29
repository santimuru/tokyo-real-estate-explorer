"""
Japan Real Estate Intelligence — Landing / Intro page.
"""
from __future__ import annotations

import streamlit as st

from utils.styles import (
    inject_css, platform_hero, feature_cards,
    section_title, nav_sidebar, footer,
)
from utils.prefecture_data import get_all_as_df


st.set_page_config(
    page_title="Japan Real Estate Intelligence",
    page_icon="🗾",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
nav_sidebar()


# ── Compute headline insights from prefecture data ────────────────────────────
@st.cache_data(show_spinner=False)
def _headline_stats() -> list[tuple[str, str]]:
    df = get_all_as_df()
    df["price_change_pct"] = (
        (df["price_ppm2_2024"] - df["price_ppm2_2015"]) / df["price_ppm2_2015"] * 100
    )
    tokyo_growth   = df.loc[df["name_en"] == "Tokyo", "price_change_pct"].iloc[0]
    nat_avg_growth = df["price_change_pct"].mean()
    tokyo_2024     = df.loc[df["name_en"] == "Tokyo", "price_ppm2_2024"].iloc[0]
    nat_avg_2024   = df["price_ppm2_2024"].mean()
    tokyo_premium  = tokyo_2024 / nat_avg_2024
    high_akiya     = int((df["akiya_rate_2023"] >= 20).sum())
    return [
        (f"+{tokyo_growth:.0f}%",  f"Tokyo growth · vs +{nat_avg_growth:.0f}% national"),
        (f"{tokyo_premium:.1f}×",  "Tokyo premium · vs national avg"),
        ("9M+",                    "Vacant homes (akiya)"),
        (f"{high_akiya}",          "Prefectures > 20% vacancy"),
        ("47 / 23",                "Prefectures · Tokyo wards"),
    ]


platform_hero(stats=_headline_stats())
feature_cards()

st.markdown("---")

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
| Japan Housing & Land Survey | Prefecture akiya vacancy rates 2013 / 2018 / 2023 | Akiya Crisis section |
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
vs the Tokyo median (40%). A ward rising faster than average <em>and</em> still below
the city median scores highest.

<h4>YoY growth</h4>
Compares median ¥/m² in the most recent calendar year vs the prior year.
Requires at least one transaction per ward per year.

<h4>Ward × year heatmap</h4>
Median ¥/m² per ward × year cell — useful for spotting which wards appreciated
fastest and which plateaued.

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

footer("Home", "MLIT XIT001 API · Japan Housing and Land Survey · Statistics Bureau")
