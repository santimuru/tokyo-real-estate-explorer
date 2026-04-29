from __future__ import annotations

import streamlit as st


# ── Theme detection ────────────────────────────────────────────────────────────

def get_theme() -> str:
    try:
        return st.get_option("theme.base") or "light"
    except Exception:
        return "light"


def is_dark() -> bool:
    return get_theme() == "dark"


# ── Plotly helpers ─────────────────────────────────────────────────────────────

def plotly_base(height: int = 420, margin: dict | None = None) -> tuple[dict, str, str]:
    """Return (layout_dict, grid_color, zero_color) for a transparent Plotly chart.
    Pass margin= to override the default; avoids duplicate-keyword errors when spreading **base.
    """
    dark = is_dark()
    font_color = "#F1F5F9" if dark else "#0F172A"
    grid  = "#2D3748" if dark else "#E2E8F0"
    zero  = "#4A5568" if dark else "#CBD5E0"
    m = margin if margin is not None else dict(l=8, r=8, t=24, b=8)
    return (
        dict(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=height,
            font=dict(color=font_color, family="Inter, sans-serif", size=12),
            margin=m,
        ),
        grid,
        zero,
    )


def year_ticks(periods: list[str]) -> tuple[list[str], list[str]]:
    """From a list of 'YYYY-Qn' strings, return tickvals/ticktext showing only years."""
    vals, texts = [], []
    seen: set[str] = set()
    for p in sorted(set(periods)):
        yr = p.split("-")[0]
        if yr not in seen:
            seen.add(yr)
            vals.append(p)
            texts.append(yr)
    return vals, texts


# ── CSS injection ──────────────────────────────────────────────────────────────

def inject_css() -> None:
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ── Reset & base ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}
/* Collapse Streamlit's default top toolbar height */
[data-testid="stHeader"] { height: 0 !important; min-height: 0 !important; }
.main .block-container {
    padding-top: 0.5rem !important;
    padding-bottom: 3rem;
    max-width: 1440px;
}
/* Hide Streamlit's auto-generated sidebar nav (shows raw filenames) */
[data-testid="stSidebarNav"] { display: none !important; }

/* ── Design tokens — light ── */
:root {
    --accent:        #3B82F6;
    --accent-dark:   #1D4ED8;
    --accent-faint:  rgba(59,130,246,0.10);
    --pos:           #10B981;
    --neg:           #EF4444;
    --surface:       #FFFFFF;
    --surface-2:     #F8FAFC;
    --surface-3:     #F1F5F9;
    --border:        #E2E8F0;
    --text-h:        #0F172A;
    --text-body:     #334155;
    --text-muted:    #64748B;
    --text-faint:    #94A3B8;
    --shadow:        0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.05);
    --shadow-md:     0 4px 12px rgba(0,0,0,.08);
}

/* ── Dark mode — OS ── */
@media (prefers-color-scheme: dark) {
    :root {
        --accent-faint:  rgba(59,130,246,0.15);
        --surface:       #1E293B;
        --surface-2:     #0F172A;
        --surface-3:     #273548;
        --border:        #334155;
        --text-h:        #F1F5F9;
        --text-body:     #CBD5E0;
        --text-muted:    #94A3B8;
        --text-faint:    #64748B;
        --shadow:        0 1px 3px rgba(0,0,0,.3);
        --shadow-md:     0 4px 12px rgba(0,0,0,.4);
    }
}

/* ── Dark mode — Streamlit toggle ── */
[data-theme="dark"] {
    --accent-faint:  rgba(59,130,246,0.15);
    --surface:       #1E293B;
    --surface-2:     #0F172A;
    --surface-3:     #273548;
    --border:        #334155;
    --text-h:        #F1F5F9;
    --text-body:     #CBD5E0;
    --text-muted:    #94A3B8;
    --text-faint:    #64748B;
    --shadow:        0 1px 3px rgba(0,0,0,.3);
    --shadow-md:     0 4px 12px rgba(0,0,0,.4);
}

/* ── Page header ── */
.page-header {
    padding: 2rem 0 1.5rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 2rem;
}
.page-header-eyebrow {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    color: var(--accent);
    margin-bottom: 0.4rem;
}
.page-header-title {
    font-size: 2.2rem;
    font-weight: 800;
    color: var(--text-h);
    letter-spacing: -0.02em;
    line-height: 1.15;
    margin-bottom: 0.6rem;
}
.page-header-desc {
    font-size: 1rem;
    color: var(--text-muted);
    max-width: 680px;
    line-height: 1.7;
}

/* ── Section header ── */
.section-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text-h);
    margin: 1.8rem 0 0.4rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.section-title::before {
    content: '';
    display: inline-block;
    width: 3px;
    height: 1.1em;
    background: var(--accent);
    border-radius: 2px;
    flex-shrink: 0;
}
.section-sub {
    font-size: 0.85rem;
    color: var(--text-muted);
    margin-bottom: 1rem;
    line-height: 1.6;
}

/* ── Insight / callout box ── */
.callout {
    background: var(--accent-faint);
    border-left: 3px solid var(--accent);
    border-radius: 0 8px 8px 0;
    padding: 0.85rem 1.1rem;
    margin: 0.8rem 0 1.2rem;
    font-size: 0.875rem;
    color: var(--text-body);
    line-height: 1.65;
}
.callout strong { color: var(--accent); }
.callout-pos { border-left-color: var(--pos); background: rgba(16,185,129,.08); }
.callout-pos strong { color: var(--pos); }
.callout-neg { border-left-color: var(--neg); background: rgba(239,68,68,.08); }
.callout-neg strong { color: var(--neg); }

/* ── KPI cards ── */
.kpi-row { display: flex; gap: 0.75rem; margin: 1rem 0 1.5rem; flex-wrap: wrap; }
.kpi {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 0.9rem 1.1rem;
    flex: 1;
    min-width: 130px;
    box-shadow: var(--shadow);
}
.kpi-label {
    font-size: 0.70rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    margin-bottom: 0.3rem;
}
.kpi-value {
    font-size: 1.55rem;
    font-weight: 700;
    color: var(--text-h);
    line-height: 1.15;
}
.kpi-value-accent { color: var(--accent); }
.kpi-sub {
    font-size: 0.75rem;
    color: var(--text-faint);
    margin-top: 0.2rem;
}

/* ── Streamlit metric overrides ── */
.stMetric {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 0.85rem 1rem !important;
    box-shadow: var(--shadow);
}
.stMetric label {
    font-size: 0.70rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    color: var(--text-muted) !important;
}
.stMetric [data-testid="stMetricValue"] {
    font-size: 1.4rem !important;
    font-weight: 700 !important;
    color: var(--text-h) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 2px solid var(--border);
    background: transparent !important;
}
.stTabs [data-baseweb="tab"] {
    font-size: 0.88rem;
    font-weight: 600;
    padding: 0.6rem 1.2rem;
    color: var(--text-muted);
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
}
.stTabs [aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom-color: var(--accent) !important;
}

/* ── Info badge (sidebar) ── */
.info-badge {
    background: var(--surface-3);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.6rem 0.8rem;
    font-size: 0.75rem;
    color: var(--text-muted);
    line-height: 1.55;
}
.info-badge strong { color: var(--text-body); }

/* ── Methodology box ── */
.method-box {
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    font-size: 0.82rem;
    color: var(--text-muted);
    line-height: 1.7;
    margin-top: 0.5rem;
}
.method-box h4 {
    color: var(--text-body);
    font-size: 0.82rem;
    font-weight: 700;
    margin: 0.8rem 0 0.3rem;
}
.method-box h4:first-child { margin-top: 0; }

/* ── Platform hero ── */
.platform-hero {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 2.5rem 2.5rem 2rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
    box-shadow: var(--shadow-md);
}
.platform-hero::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #3B82F6, #8B5CF6, #10B981);
}
.ph-eyebrow {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--accent);
    margin-bottom: 0.5rem;
}
.ph-title {
    font-size: 2.6rem;
    font-weight: 800;
    color: var(--text-h);
    letter-spacing: -0.02em;
    line-height: 1.1;
    margin: 0 0 0.8rem;
}
.ph-desc {
    font-size: 1rem;
    color: var(--text-muted);
    max-width: 680px;
    line-height: 1.7;
    margin: 0 0 1.8rem;
}
.ph-stats {
    display: flex;
    gap: 2.5rem;
    flex-wrap: wrap;
    border-top: 1px solid var(--border);
    padding-top: 1.2rem;
}
.ph-stat-n {
    font-size: 1.75rem;
    font-weight: 800;
    color: var(--accent);
    line-height: 1;
}
.ph-stat-l {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    margin-top: 0.25rem;
}

/* ── Chart & data container borders ── */
[data-testid="stPlotlyChart"] {
    border: 1px solid var(--border);
    border-radius: 12px;
    background: var(--surface);
    padding: 4px;
    overflow: hidden;
}
[data-testid="stDeckGlJsonChart"],
[data-testid="stPydeckChart"] {
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
}
[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
}

/* ── Footer ── */
.app-footer {
    margin-top: 4rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--border);
    font-size: 0.75rem;
    color: var(--text-faint);
    text-align: center;
    line-height: 2;
}
.app-footer a { color: var(--accent); text-decoration: none; }
.app-footer a:hover { text-decoration: underline; }
</style>
""", unsafe_allow_html=True)


# ── Python component helpers ───────────────────────────────────────────────────

def page_header(eyebrow: str, title: str, desc: str, badges: list[str] | None = None) -> None:
    badge_html = ""
    if badges:
        for b in badges:
            badge_html += f'<span style="display:inline-block;background:var(--accent-faint);color:var(--accent);border:1px solid var(--accent);border-radius:20px;padding:0.15rem 0.65rem;font-size:0.70rem;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;margin-right:0.4rem;">{b}</span>'
    st.markdown(f"""
<div class="page-header">
    <div class="page-header-eyebrow">{eyebrow}</div>
    <div class="page-header-title">{title}</div>
    <div class="page-header-desc">{desc}</div>
    {'<div style="margin-top:0.8rem;">' + badge_html + '</div>' if badge_html else ''}
</div>
""", unsafe_allow_html=True)


def section_title(text: str, sub: str = "") -> None:
    sub_html = f'<div class="section-sub">{sub}</div>' if sub else ""
    st.markdown(f'<div class="section-title">{text}</div>{sub_html}', unsafe_allow_html=True)


def callout(text: str, variant: str = "") -> None:
    cls = f"callout callout-{variant}" if variant else "callout"
    st.markdown(f'<div class="{cls}">{text}</div>', unsafe_allow_html=True)


def kpi_card(label: str, value: str, sub: str = "", accent: bool = False) -> None:
    val_cls = "kpi-value kpi-value-accent" if accent else "kpi-value"
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    st.markdown(
        f'<div class="kpi"><div class="kpi-label">{label}</div>'
        f'<div class="{val_cls}">{value}</div>{sub_html}</div>',
        unsafe_allow_html=True,
    )


def platform_hero() -> None:
    """Full-width hero shown on the home page above all sections."""
    st.markdown("""
<div class="platform-hero">
    <div class="ph-eyebrow">Portfolio Project &nbsp;·&nbsp; Python · Streamlit · Plotly · MLIT API</div>
    <div class="ph-title">Japan Real Estate Intelligence</div>
    <div class="ph-desc">
        Transaction-level property data from Japan's Ministry of Land, Infrastructure, Transport and Tourism (MLIT)
        — covering every prefecture in the country and every one of Tokyo's 23 special wards.
        Explore national price maps, demographic trends, the akiya vacancy crisis,
        and deep ward-level analytics including a k-NN price estimator and investment signal dashboard.
    </div>
    <div class="ph-stats">
        <div>
            <div class="ph-stat-n">47</div>
            <div class="ph-stat-l">Prefectures</div>
        </div>
        <div>
            <div class="ph-stat-n">23</div>
            <div class="ph-stat-l">Tokyo Wards</div>
        </div>
        <div>
            <div class="ph-stat-n">9M+</div>
            <div class="ph-stat-l">Vacant Homes</div>
        </div>
        <div>
            <div class="ph-stat-n">2015–24</div>
            <div class="ph-stat-l">Data Range</div>
        </div>
        <div>
            <div class="ph-stat-n">¥/m²</div>
            <div class="ph-stat-l">Transaction Level</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


def nav_sidebar() -> None:
    """Custom sidebar navigation — replaces Streamlit's filename-based nav."""
    with st.sidebar:
        st.markdown("""
<div style="padding: 1rem 0 0.5rem; display:flex; align-items:center; gap:0.6rem;">
    <span style="font-size:1.4rem;">🗾</span>
    <span style="font-weight:700; font-size:0.95rem; color:var(--text-h);">Japan RE Intelligence</span>
</div>
""", unsafe_allow_html=True)
        st.page_link("app.py",                          label="Japan Overview",  icon="🗾")
        st.page_link("pages/1_City_Comparison.py",      label="City Comparison", icon="🏙️")
        st.page_link("pages/2_Tokyo_Deep_Dive.py",      label="Tokyo Deep Dive", icon="🗼")
        st.page_link("pages/3_About.py",                label="About",           icon="ℹ️")
        st.markdown("<hr style='margin:0.75rem 0; border-color:var(--border);'>", unsafe_allow_html=True)


def footer(page_name: str, source: str = "MLIT Real Estate Information Library") -> None:
    st.markdown(f"""
<div class="app-footer">
    <strong>Japan Real Estate Intelligence</strong> · {page_name} ·
    Built by <a href="https://santimuru.github.io" target="_blank">Santiago Martinez</a> ·
    <a href="https://github.com/santimuru/tokyo-real-estate-explorer" target="_blank">GitHub</a><br/>
    Data: {source}
</div>
""", unsafe_allow_html=True)
