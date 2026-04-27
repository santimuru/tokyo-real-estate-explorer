from __future__ import annotations

import streamlit as st


def inject_css() -> None:
    st.markdown("""
<style>
    /* ── Layout ── */
    .main .block-container {
        padding-top: 0;
        padding-bottom: 3rem;
        max-width: 1400px;
    }

    /* ── CSS variables — light mode defaults ── */
    :root {
        --accent:       #177e89;
        --accent-dark:  #0d2b2e;
        --surface:      #f7f9fa;
        --surface-2:    #f0f9fa;
        --border:       #e0e0e0;
        --text-primary: #1a1a1a;
        --text-muted:   #666;
        --text-sub:     #94A3B8;
    }

    /* ── Dark mode overrides ── */
    @media (prefers-color-scheme: dark) {
        :root {
            --surface:      rgba(255,255,255,0.05);
            --surface-2:    rgba(23,126,137,0.15);
            --border:       rgba(255,255,255,0.12);
            --text-primary: #f0f0f0;
            --text-muted:   #aaa;
            --text-sub:     #888;
        }
    }

    /* ── Hero banner (always dark — works in both modes) ── */
    .hero-banner {
        background: linear-gradient(135deg, #0d2b2e 0%, #177e89 65%, #1a9aaa 100%);
        border-radius: 12px;
        padding: 2.8rem 3rem;
        color: white;
        margin-bottom: 1.8rem;
    }
    .hero-title {
        font-size: 2.6rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: white !important;
    }
    .hero-sub {
        font-size: 1.05rem;
        opacity: 0.88;
        max-width: 720px;
        line-height: 1.65;
        color: white !important;
    }
    .badge {
        display: inline-block;
        background: rgba(255,255,255,0.15);
        border: 1px solid rgba(255,255,255,0.35);
        border-radius: 20px;
        padding: 0.22rem 0.75rem;
        font-size: 0.73rem;
        font-weight: 600;
        text-transform: uppercase;
        margin-right: 0.4rem;
        color: white !important;
    }
    .badge-live {
        background: rgba(39,174,96,0.35);
        border-color: rgba(39,174,96,0.7);
    }

    /* ── Metrics ── */
    .stMetric {
        background: var(--surface);
        border-left: 3px solid var(--accent);
        padding: 0.8rem 1rem;
        border-radius: 4px;
    }
    .stMetric label {
        font-size: 0.73rem !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--text-muted) !important;
    }
    .stMetric [data-testid="stMetricValue"] {
        font-size: 1.45rem !important;
        color: var(--accent) !important;
        font-weight: 700;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
        border-bottom: 1px solid var(--border);
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 0.95rem;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        color: var(--accent) !important;
    }

    /* ── Insight box ── */
    .insight-box {
        background: var(--surface-2);
        border-left: 4px solid var(--accent);
        border-radius: 0 8px 8px 0;
        padding: 0.9rem 1.2rem;
        margin: 1rem 0;
        font-size: 0.88rem;
        line-height: 1.65;
        color: var(--text-primary);
    }
    .insight-box strong {
        color: var(--accent);
    }

    /* ── KPI card ── */
    .kpi-card {
        background: var(--surface);
        border-left: 4px solid var(--accent);
        padding: 1rem 1.2rem;
        border-radius: 6px;
        margin-bottom: 0.5rem;
    }
    .kpi-label {
        font-size: 0.78rem;
        color: var(--text-muted);
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .kpi-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: var(--text-primary);
        line-height: 1.2;
    }
    .kpi-sub {
        font-size: 0.82rem;
        color: var(--text-sub);
        margin-top: 2px;
    }

    /* ── Footer ── */
    .app-footer {
        margin-top: 3rem;
        padding-top: 1.5rem;
        border-top: 1px solid var(--border);
        color: var(--text-muted);
        font-size: 0.78rem;
        text-align: center;
        line-height: 2;
    }
    .app-footer a { color: var(--accent); text-decoration: none; }
</style>
""", unsafe_allow_html=True)


def kpi_card(label: str, value: str, sub: str = "") -> None:
    """Render an HTML KPI card."""
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>{sub_html}</div>',
        unsafe_allow_html=True,
    )
