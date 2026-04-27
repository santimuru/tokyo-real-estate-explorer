from __future__ import annotations

import streamlit as st


def inject_css() -> None:
    st.markdown("""
<style>
    .main .block-container {
        padding-top: 0;
        padding-bottom: 3rem;
        max-width: 1400px;
    }

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
        color: white;
    }
    .hero-sub {
        font-size: 1.05rem;
        opacity: 0.88;
        max-width: 720px;
        line-height: 1.65;
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
        color: white;
    }
    .badge-live {
        background: rgba(39,174,96,0.35);
        border-color: rgba(39,174,96,0.7);
    }

    .stMetric {
        background: #f7f9fa;
        border-left: 3px solid #177e89;
        padding: 0.8rem 1rem;
        border-radius: 4px;
    }
    .stMetric label {
        font-size: 0.73rem !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #666 !important;
    }
    .stMetric [data-testid="stMetricValue"] {
        font-size: 1.45rem !important;
        color: #177e89;
        font-weight: 700;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
        border-bottom: 1px solid #e0e0e0;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 0.95rem;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        color: #177e89;
    }

    .insight-box {
        background: #f0f9fa;
        border-left: 4px solid #177e89;
        border-radius: 0 8px 8px 0;
        padding: 0.9rem 1.2rem;
        margin: 1rem 0;
        font-size: 0.88rem;
        line-height: 1.65;
        color: #2c2c2c;
    }
    .insight-box strong {
        color: #0d2b2e;
    }

    .app-footer {
        margin-top: 3rem;
        padding-top: 1.5rem;
        border-top: 1px solid #e0e0e0;
        color: #999;
        font-size: 0.78rem;
        text-align: center;
        line-height: 2;
    }
    .app-footer a {
        color: #177e89;
        text-decoration: none;
    }

    .kpi-card {
        background: #F8FAFC;
        border-left: 4px solid #177e89;
        padding: 1rem 1.2rem;
        border-radius: 6px;
        margin-bottom: 0.5rem;
    }
    .kpi-label {
        font-size: 0.78rem;
        color: #64748B;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .kpi-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #0F172A;
        line-height: 1.2;
    }
    .kpi-sub {
        font-size: 0.82rem;
        color: #94A3B8;
        margin-top: 2px;
    }

    div[data-testid="stSidebarNav"] {
        display: none;
    }
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
