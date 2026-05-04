"""
Japan Real Estate Intelligence — Landing / Intro page.
"""
from __future__ import annotations
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from utils.styles import inject_css, platform_hero, feature_cards, nav_sidebar, footer
from utils.prefecture_data import get_all_as_df


st.set_page_config(
    page_title="Japan Real Estate Intelligence",
    page_icon="🗾",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
nav_sidebar()


# ── Transparent backgrounds so the fixed canvas shows through ──────────────────
st.markdown("""
<style>
[data-testid="stApp"],
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.main, .main .block-container,
[data-testid="stVerticalBlock"] {
    background: transparent !important;
}
/* Hero: frosted glass over the particle canvas */
.platform-hero {
    background: rgba(14, 17, 23, 0.75) !important;
    backdrop-filter: blur(4px) !important;
    -webkit-backdrop-filter: blur(4px) !important;
}
</style>
""", unsafe_allow_html=True)


# ── Japan particle background (injected into parent document) ──────────────────
components.html("""<!DOCTYPE html>
<html><body style="margin:0;overflow:hidden;background:transparent;">
<script>
(function () {
  try {
    // Remove stale canvas from previous Streamlit reruns
    const old = parent.document.getElementById('japan-bg');
    if (old) old.remove();

    // Create canvas in the parent (Streamlit) document
    const canvas = parent.document.createElement('canvas');
    canvas.id = 'japan-bg';
    Object.assign(canvas.style, {
      position: 'fixed', top: '0', left: '0',
      width: '100%', height: '100%',
      zIndex: '0', pointerEvents: 'none',
    });
    parent.document.body.prepend(canvas);
    const ctx = canvas.getContext('2d');

    // Island polygons normalized to [0..1] — derived from lon/lat grid
    // x: 123-146°E → [0,1]   y: 46-24°N → [0,1] (north = 0)
    const ISLANDS = [
      // Hokkaido
      [[0.754,0.208],[0.766,0.129],[0.806,0.029],[0.960,0.067],[0.980,0.110],
       [0.914,0.181],[0.797,0.225],[0.749,0.215]],
      // Honshu — Pacific coast then Japan Sea coast back
      [[0.783,0.225],[0.806,0.294],[0.754,0.425],[0.709,0.463],[0.663,0.513],
       [0.557,0.519],[0.537,0.546],[0.534,0.571],[0.506,0.552],[0.466,0.531],
       [0.420,0.535],[0.377,0.544],[0.343,0.550],[0.349,0.546],[0.366,0.535],
       [0.411,0.500],[0.480,0.475],[0.520,0.475],[0.563,0.454],
       [0.623,0.381],[0.697,0.365],[0.737,0.283],[0.760,0.250]],
      // Shikoku
      [[0.423,0.546],[0.480,0.533],[0.537,0.546],[0.549,0.575],
       [0.500,0.590],[0.434,0.585],[0.400,0.571]],
      // Kyushu
      [[0.291,0.548],[0.357,0.538],[0.386,0.558],[0.391,0.600],
       [0.371,0.646],[0.329,0.671],[0.266,0.658],[0.200,0.629],
       [0.200,0.588],[0.243,0.563]],
    ];

    const B = { xMin:0.200, xMax:0.980, yMin:0.029, yMax:0.671 };

    let W, H, scale, offX, offY, maskData, particles = [];

    function proj(nx, ny) {
      return [nx * scale + offX, ny * scale + offY];
    }

    function setup() {
      W = canvas.width  = parent.innerWidth;
      H = canvas.height = parent.innerHeight;

      // Scale Japan to fill ~70 % of viewport height, centered
      scale = (H * 0.70) / (B.yMax - B.yMin);
      offX  = (W - (B.xMax - B.xMin) * scale) / 2 - B.xMin * scale;
      offY  = H * 0.10 - B.yMin * scale;

      // Rasterize mask in iframe-local canvas (no DOM append needed)
      const mc = document.createElement('canvas');
      mc.width = W; mc.height = H;
      const mctx = mc.getContext('2d');
      mctx.fillStyle = '#fff';
      ISLANDS.forEach(pts => {
        const [sx, sy] = proj(pts[0][0], pts[0][1]);
        mctx.beginPath(); mctx.moveTo(sx, sy);
        pts.slice(1).forEach(p => { const [px,py]=proj(p[0],p[1]); mctx.lineTo(px,py); });
        mctx.closePath(); mctx.fill();
      });
      maskData = mctx.getImageData(0, 0, W, H).data;
    }

    function inside(x, y) {
      const ix = Math.floor(x), iy = Math.floor(y);
      if (ix < 0 || ix >= W || iy < 0 || iy >= H) return false;
      return maskData[(iy * W + ix) * 4 + 3] > 0;
    }

    function seed() {
      const N = 230;
      particles = [];
      const [bx0, by0] = proj(B.xMin, B.yMin);
      const [bx1, by1] = proj(B.xMax, B.yMax);
      let tries = 0;
      while (particles.length < N && tries < 600000) {
        const x = bx0 + Math.random() * (bx1 - bx0);
        const y = by0 + Math.random() * (by1 - by0);
        if (inside(x, y)) {
          particles.push({ x, y, ox: x, oy: y,
            vx: (Math.random()-0.5)*0.4, vy: (Math.random()-0.5)*0.4,
            r: Math.random()*1.2+0.6 });
        }
        tries++;
      }
    }

    setup(); seed();

    parent.addEventListener('resize', () => { setup(); seed(); });

    let mx = -9999, my = -9999;
    parent.document.addEventListener('mousemove', e => { mx = e.clientX; my = e.clientY; });
    parent.document.addEventListener('mouseleave', () => { mx = -9999; my = -9999; });

    const LINK_D = 45, MOUSE_R = 95;

    function animate() {
      ctx.clearRect(0, 0, W, H);

      // Faint island outlines
      ISLANDS.forEach(pts => {
        const [sx, sy] = proj(pts[0][0], pts[0][1]);
        ctx.beginPath(); ctx.moveTo(sx, sy);
        pts.slice(1).forEach(p => { const [px,py]=proj(p[0],p[1]); ctx.lineTo(px,py); });
        ctx.closePath();
        ctx.strokeStyle = 'rgba(100,155,255,0.09)';
        ctx.lineWidth = 1; ctx.stroke();
      });

      // Physics — gentle ambient drift only, no mouse repulsion
      particles.forEach(p => {
        p.vx += (p.ox - p.x) * 0.003;
        p.vy += (p.oy - p.y) * 0.003;
        p.vx *= 0.95; p.vy *= 0.95;
        p.x += p.vx; p.y += p.vy;
      });

      // Links
      for (let i = 0; i < particles.length; i++) {
        for (let j = i+1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const d = Math.sqrt(dx*dx + dy*dy);
          if (d < LINK_D) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(140,195,255,${(1-d/LINK_D)*0.45})`;
            ctx.lineWidth = 0.6; ctx.stroke();
          }
        }
      }

      // Dots — glow on hover, subtle otherwise
      particles.forEach(p => {
        const dx = p.x - mx, dy = p.y - my;
        const d  = Math.sqrt(dx*dx + dy*dy);
        const bright = d < MOUSE_R ? Math.pow(1 - d/MOUSE_R, 1.4) : 0;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r * (1 + bright * 2.2), 0, Math.PI*2);

        if (bright > 0) {
          ctx.shadowColor = `rgba(130,215,255,${bright * 0.95})`;
          ctx.shadowBlur  = 6 + bright * 16;
          ctx.fillStyle   = `rgba(255,255,255,${0.55 + bright * 0.45})`;
        } else {
          ctx.shadowColor = 'transparent';
          ctx.shadowBlur  = 0;
          ctx.fillStyle   = 'rgba(175,215,255,0.60)';
        }
        ctx.fill();
      });
      ctx.shadowBlur = 0;

      requestAnimationFrame(animate);
    }

    animate();

  } catch (e) {
    console.warn('Japan particles: parent DOM access blocked', e);
  }
}());
</script>
</body></html>""", height=1, scrolling=False)


# ── Headline stats ─────────────────────────────────────────────────────────────
PARQUET = Path(__file__).resolve().parent / "data" / "prefecture_aggregates.parquet"


@st.cache_data(show_spinner=False)
def _headline_stats() -> list[tuple[str, str]]:
    df = get_all_as_df()
    high_akiya = int((df["akiya_rate_2023"] >= 20).sum())

    if PARQUET.exists():
        agg = pd.read_parquet(PARQUET)
        agg["prefecture_code"] = agg["prefecture_code"].astype(str).str.zfill(2)
        a20 = agg[agg["tx_year"] == 2020].set_index("prefecture_code")["median_ppm2"]
        a24 = agg[agg["tx_year"] == 2024].set_index("prefecture_code")["median_ppm2"]

        tokyo_growth   = (a24["13"] - a20["13"]) / a20["13"] * 100
        joined         = pd.concat([a20.rename("p20"), a24.rename("p24")], axis=1).dropna()
        nat_growth_med = ((joined["p24"] - joined["p20"]) / joined["p20"] * 100).median()
        tokyo_premium  = a24["13"] / a24.median()
        window_label   = "2020-2024"
    else:
        df["price_change_pct"] = (
            (df["price_ppm2_2024"] - df["price_ppm2_2015"]) / df["price_ppm2_2015"] * 100
        )
        tokyo_growth   = df.loc[df["name_en"] == "Tokyo", "price_change_pct"].iloc[0]
        nat_growth_med = df["price_change_pct"].median()
        tokyo_premium  = (
            df.loc[df["name_en"] == "Tokyo", "price_ppm2_2024"].iloc[0]
            / df["price_ppm2_2024"].median()
        )
        window_label   = "2015-2024"

    return [
        (f"+{tokyo_growth:.0f}%",  f"Tokyo growth {window_label} · vs +{nat_growth_med:.0f}% national median"),
        (f"{tokyo_premium:.0f}×",  "Tokyo premium · vs national median"),
        ("9M+",                    "Vacant homes (akiya)"),
        (f"{high_akiya}",          "Prefectures > 20% vacancy"),
        ("47 / 23",                "Prefectures · Tokyo wards"),
    ]


platform_hero(stats=_headline_stats())
feature_cards()

footer("Home", "MLIT XIT001 API · Japan Housing and Land Survey · Statistics Bureau")
