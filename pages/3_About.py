"""About â€” methodology, data sources, tech stack. Plain documentation, not marketing."""
from __future__ import annotations

import os
import streamlit as st
from utils.styles import inject_css, callout, footer, nav_top

st.set_page_config(page_title="About Â· Japan RE", page_icon="â„¹ï¸", layout="wide", initial_sidebar_state="collapsed")
inject_css()
nav_top("about")

st.markdown("# About & Methodology")
st.caption("Documentation of data sources, methods, and assumptions used across the app.")

api_key = os.environ.get("MLIT_API_KEY", "")
if api_key:
    callout("âœ“ <strong>Connected to MLIT API</strong> â€” Tokyo Deep Dive and City Comparison run on live transactions.", variant="pos")
else:
    callout("â„¹ï¸ MLIT API key not configured â€” Tokyo Deep Dive and City Comparison fall back to demo data.", variant="neg")

st.markdown("---")

st.markdown("## Data sources")
st.markdown("""
| Source | What it covers | Lag | Used in |
|---|---|---|---|
| MLIT XIT001 API | Transaction-level data, all 47 prefectures | ~2 quarters | City Comparison, Tokyo Deep Dive |
| Japan Housing & Land Survey | Prefecture akiya rates 2013 / 2018 / 2023 | 5-yr cycle | Akiya Crisis section |
| Statistics Bureau of Japan | Prefectural population 2010, 2020 | Census cycle | Demographics scatter |
| dataofjapan/land (GitHub) | Prefecture GeoJSON boundaries | static | All choropleths |
| MLIT aggregate reports / REINS | Prefecture price estimates 2015 / 2019 / 2024 | curated | Japan price map |

**MLIT data lag:** XIT001 publishes data approximately 2 quarters behind the current date. The app dynamically computes the latest available period to avoid empty requests.

**Curated estimates:** Prefecture-level prices and akiya rates on the Japan Overview page are not direct API outputs â€” they are curated estimates from MLIT aggregate reports and REINS publications. For transaction-level live MLIT data, use City Comparison or Tokyo Deep Dive.

**Secondary market only:** XIT001 publishes only secondary-market transactions (re-sales of existing properties). New construction sold directly by developers is not included. Verified empirically: across 78,000 Tokyo records spanning 2020-2024, the API never returned the categories "Newly Built Detached House" or "Pre-owned Detached House" â€” MLIT classifies all detached buildings under `Residential Land(Land and Building)` and uses the `Purpose` field (House / Office / Shop) to distinguish residential from commercial.

**Property type taxonomy used here:**

| Our category | MLIT raw type | + Purpose |
|---|---|---|
| Used Apartment | Pre-owned Condominiums, etc. | (any) |
| Used House | Residential Land(Land and Building) | House / empty |
| Used Commercial | Residential Land(Land and Building) | Office / Shop |
| Land Only | Residential Land(Land Only) | (any) |

Forest Land and Agricultural Land records (~0.1% of volume) are dropped.
""")

st.markdown("---")

st.markdown("## Methodology")

st.markdown("### Price estimator (k-NN)")
st.markdown("""
Finds the k most similar transactions using a composite distance score across floor area, building age, and station proximity. Returns P10/P50/P90 percentiles of comparable Â¥/mÂ² values, scaled to total price.

- Falls back to all ward data if fewer than 20 ward-specific matches exist.
- When MLIT API data is active, structure type, facing direction, and renovation status are added to the matching.
- Station walk-time is **not** included in MLIT API data; the input is used in synthetic mode only.

**Known limitation:** distance features are not standardised (z-scored) â€” the current heuristic is a portfolio simplification, not a calibrated model.
""")

st.markdown("### YoY growth")
st.markdown("""
Compares median Â¥/mÂ² in the most recent calendar year vs the prior year.

- Requires at least **30 transactions per ward per year** to publish a YoY figure (otherwise returned as 0).
- Below this sample size, the median is too noisy to be meaningful.
""")

st.markdown("### Investment Value Score")
st.markdown("""
Composite 0â€“100 score per ward, defined as:

```
value_score = 0.6 Ã— momentum_norm + 0.4 Ã— (1 âˆ’ price_relative_norm)
```

Where momentum is YoY price change and price_relative is median Â¥/mÂ² scaled against the city median. Both dimensions are min-max normalised across the 23 wards before weighting.

**Weighting rationale:** real estate cycles tend to persist 2â€“3 years, so momentum (60%) is weighted higher than relative affordability (40%). This is a heuristic, not a calibrated risk model.
""")

st.markdown("### Ward Ã— year heatmap")
st.markdown("""
Median Â¥/mÂ² per (ward, year) cell. Reveals which wards appreciated fastest and which plateaued. Color scale spans the full dataset range (not per-row).
""")

st.markdown("---")

st.markdown("## Tech stack")
st.markdown("""
| Layer | Tools |
|---|---|
| Language | Python 3.11 |
| App framework | Streamlit |
| Visualisation | Plotly Express, Plotly Graph Objects, Pydeck |
| Data wrangling | Pandas, NumPy |
| Geospatial | Plotly choropleth + dataofjapan/land GeoJSON |
| Maps | Pydeck (MapLibre) |
| API | MLIT Real Estate Information Library â€” XIT001 endpoint |
| Hosting | Streamlit Community Cloud |
| Source control | GitHub |
""")

st.markdown("---")

st.markdown("## Author")
st.markdown("""
**Santiago Martinez** â€” data scientist & BI analyst.

- [santimuru.github.io](https://santimuru.github.io)
- [github.com/santimuru](https://github.com/santimuru)
- [tokyo-real-estate-explorer source](https://github.com/santimuru/tokyo-real-estate-explorer)
""")

footer("About", "MLIT XIT001 API Â· Japan Housing and Land Survey Â· Statistics Bureau of Japan")
