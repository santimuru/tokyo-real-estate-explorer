"""About — Japan Real Estate Intelligence platform."""
import streamlit as st

from utils.styles import inject_css

st.set_page_config(page_title="About · Japan RE", page_icon="ℹ️", layout="wide")
inject_css()

st.markdown("""
<div class="hero-banner">
    <div class="hero-title">ℹ️ About this Platform</div>
    <div class="hero-sub">
        Japan Real Estate Intelligence — a portfolio project combining official government
        transaction data with interactive analytics across 47 prefectures and Tokyo's
        23 Special Wards.
    </div>
    <span class="badge">Open Source</span>
    <span class="badge">Portfolio Project</span>
</div>
""", unsafe_allow_html=True)

import os
api_key = os.environ.get("MLIT_API_KEY", "")
if api_key:
    st.success("✓ Connected to MLIT API — data is official and refreshes hourly.")
else:
    st.info("ℹ️ MLIT_API_KEY not set — Tokyo Deep Dive and City Comparison will use demo data.")

col_left, col_right = st.columns([3, 2])

with col_left:
    st.markdown("### Project overview")
    st.markdown("""
This platform brings together two datasets and four analytical lenses on Japan's real estate market:

**What each page covers:**

🗾 **Japan Overview** (this app's home) — Three interconnected stories at the national level:
- *Price Map*: choropleth of all 47 prefectures ranked by median ¥/m², with year slider (2015/2019/2024)
- *Depopulation & Prices*: scatter showing how population decline and price appreciation relate — or don't
- *Akiya Crisis*: Japan's 9-million vacant homes problem visualized with trend lines and regional breakdowns

🏙️ **City Comparison** — Select 2–5 major cities and compare price trends, transaction volume,
and property type mix using live MLIT API data.

🗼 **Tokyo Deep Dive** — Ward-level analytics for Tokyo's 23 Special Wards: price map, market trends,
per-ward deep dives, and a data-driven P10/P50/P90 price estimator.

---

**Tech stack**

| Layer | Tools |
|---|---|
| Language | Python 3.11 |
| App framework | Streamlit |
| Visualization | Plotly, Pydeck |
| Data wrangling | Pandas, NumPy |
| Geospatial | Plotly choropleth + dataofjapan/land GeoJSON |
| API | MLIT Real Estate Information Library (XIT001) |
| Hosting | Streamlit Cloud |

---

**Data sources**

| Source | Coverage | Lag | Cache TTL |
|---|---|---|---|
| MLIT XIT001 API | All 47 prefectures, transaction-level | ~2 quarters | 1 hour |
| Japan Housing & Land Survey | Prefecture akiya rates 2013/2018/2023 | 5 years | Static |
| Census / Statistics Bureau | Population 2010, 2020 | 5 years | Static |
| dataofjapan/land | Prefecture GeoJSON | N/A | 24 hours |
    """)

with col_right:
    st.markdown("### Methodology")
    st.markdown("""
**Price estimator (Tokyo Deep Dive)**

Finds the *k* most similar transactions to a query property using a distance score
across floor area, building age, and station proximity. Returns P10/P50/P90 percentiles
of comparable ¥/m² values, scaled to total price. Falls back to all ward data if
fewer than 20 matches exist.

**YoY growth**

Compares median price/m² in the most recent calendar year in the dataset versus the
prior year. Requires at least one transaction per year.

**Ward heatmap**

Median price/m² per ward × year cell. Dark = expensive, light = affordable.
Useful for spotting which wards appreciated fastest over the period.

**Data note**

The MLIT XIT001 endpoint does not include station proximity data. The station
walk-time input in the estimator is used for comparisons within the dataset but
is not sourced from the API itself.

**Prefecture price data**

Prefecture-level price statistics (2015/2019/2024) are curated estimates based on
publicly available MLIT aggregate reports and REINS data. They are not direct API
outputs — use the City Comparison page for transaction-level analysis.
    """)

    st.markdown("---")
    st.markdown("### Author")
    st.markdown("""
**Santiago Martinez**

Data scientist and BI analyst. Building data products that make complex markets legible.

- [santimuru.github.io](https://santimuru.github.io)
- [GitHub: santimuru/tokyo-real-estate-explorer](https://github.com/santimuru/tokyo-real-estate-explorer)
    """)

st.caption(
    "Japan Real Estate Intelligence · Built by Santiago Martinez · "
    "github.com/santimuru/tokyo-real-estate-explorer"
)
