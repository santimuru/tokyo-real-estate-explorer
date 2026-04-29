"""About — Japan Real Estate Intelligence platform."""
from __future__ import annotations

import os
import streamlit as st
from utils.styles import inject_css, page_header, section_title, callout, footer, nav_sidebar

st.set_page_config(page_title="About · Japan RE", page_icon="ℹ️", layout="wide", initial_sidebar_state="collapsed")
inject_css()
nav_sidebar()

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

api_key = os.environ.get("MLIT_API_KEY", "")
if api_key:
    callout("✓ <strong>Connected to MLIT API</strong> — all data is live and refreshes hourly.", variant="pos")
else:
    callout("ℹ️ MLIT API key not configured — Tokyo Deep Dive and City Comparison show demo data.", variant="neg")

st.markdown("---")

col_left, col_right = st.columns([3, 2])

with col_left:
    section_title("What each page covers")
    st.markdown("""
**🗾 Japan Overview (home page)**

Three interconnected stories about Japan's real estate market at the national level:

- **Price Map** — choropleth of all 47 prefectures ranked by median ¥/m², with a 2015 / 2019 / 2024 year selector. Prefecture data comes from curated MLIT aggregate reports.
- **Depopulation & Prices** — scatter plot showing the relationship (and lack thereof) between population decline and price appreciation. Reveals the urbanisation concentration story.
- **Akiya Crisis** — Japan's 9-million vacant homes problem visualised with prefecture choropleth, ranking bars, and 10-year regional trend lines.

---

**🏙️ City Comparison**

Select 2–5 Japanese cities and compare their real estate markets using live transaction-level data from the MLIT XIT001 API. Each data point is a real government-registered property sale. Covers price trends, transaction volume, YoY changes, and property type mix.

---

**🗼 Tokyo Deep Dive**

Ward-level analytics for Tokyo's 23 Special Wards — the most granular view in the platform:

- **Map & Rankings** — geographic bubble map of ward prices + full ranking table
- **Market Trends** — city-wide area chart, YoY ward comparison, property type trends, and a ward × year price heatmap
- **Ward Analysis** — select any ward for a dedicated breakdown: price distribution, area vs price scatter, price trend, and layout breakdown
- **Price Estimator** — k-NN comparables model returning P10/P50/P90 price ranges for any property specification
- **Market Intelligence** — investment signal dashboard (momentum vs affordability quadrant), neighbourhood drill-down via DistrictName, and Property DNA (structure/direction/renovation premiums)
""")

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
| Source | What it covers | Publication lag | How it's used |
|---|---|---|---|
| MLIT XIT001 API | Transaction-level data, all 47 prefectures | ~2 quarters | City Comparison + Tokyo Deep Dive |
| Japan Housing & Land Survey | Prefecture akiya (vacancy) rates 2013 / 2018 / 2023 | 5-year cycle | Akiya Crisis page |
| Statistics Bureau of Japan | Prefectural population 2010, 2020 | Census cycle | Depopulation scatter |
| dataofjapan/land (GitHub) | Prefecture GeoJSON boundaries | N/A | All choropleths |
| MLIT aggregate reports / REINS | Prefecture price estimates 2015 / 2019 / 2024 | Curated | Japan price map |

**A note on MLIT data lag:** The XIT001 endpoint publishes data approximately 2 quarters behind the current date.
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
When live MLIT data is active, structure type, facing direction, and renovation status
are also included in the matching.

<h4>YoY growth</h4>
Compares median ¥/m² in the most recent calendar year in the dataset versus the prior year.
Requires at least one transaction per year per ward.

<h4>Investment Value Score</h4>
Composite 0–100 score weighting YoY price momentum (60%) and relative affordability
vs the Tokyo median (40%). A ward that is rising faster than average <em>and</em> still
below the city median scores highest.

<h4>Ward × year heatmap</h4>
Median ¥/m² per ward × year cell. Useful for spotting which wards appreciated fastest
and which plateaued. The color scale is relative to the full dataset range.

<h4>Prefecture price data note</h4>
Prefecture-level price statistics (2015/2019/2024) are curated estimates based on MLIT
aggregate reports and REINS data. They are <strong>not</strong> direct API outputs.
Use the City Comparison page for transaction-level analysis.

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

footer("About", "MLIT XIT001 API · Japan Housing and Land Survey · Statistics Bureau of Japan")
