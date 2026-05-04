"""
Japan Real Estate Intelligence — Landing / Intro page.
"""
from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from utils.styles import (
    inject_css, platform_hero, feature_cards,
    nav_sidebar, footer,
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


# ── Japan particles hero ───────────────────────────────────────────────────────
def _japan_particles() -> None:
    """Interactive particle canvas shaped like Japan. Dots repel on mouse hover."""
    components.html(
        """<!DOCTYPE html>
<html>
<head>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #0e1117; display: flex; justify-content: center; align-items: flex-start; }
#wrap { position: relative; width: 350px; height: 480px; }
canvas { display: block; }
#lbl {
  position: absolute; bottom: 10px; width: 100%; text-align: center;
  color: rgba(140,190,255,0.35); font: 11px/1 system-ui, sans-serif;
  letter-spacing: 3px; text-transform: uppercase; pointer-events: none;
}
</style>
</head>
<body>
<div id="wrap">
  <canvas id="c" width="350" height="480"></canvas>
  <div id="lbl">Japan &nbsp;·&nbsp; 日本</div>
</div>
<script>
const W = 350, H = 480;
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');

// Island polygons — canvas coords for W=350, H=480
// Lon 123-146°E mapped to x, Lat 46-24°N mapped to y
const ISLANDS = [
  // Hokkaido
  [[264,100],[268,62],[282,14],[336,32],[343,53],[320,87],[279,108],[262,103]],

  // Honshu — Pacific coast (NE→SW) then Japan Sea coast (SW→NE)
  [[274,108],[282,141],[264,204],[248,222],[232,246],[195,249],
   [188,262],[187,274],[177,265],[163,255],[147,257],[132,261],[120,264],
   [122,262],[128,257],[144,240],[168,228],[182,228],[197,218],
   [218,183],[244,175],[258,136],[266,120]],

  // Shikoku
  [[148,262],[168,256],[188,262],[192,276],[175,283],[152,281],[140,274]],

  // Kyushu
  [[102,263],[125,258],[135,268],[137,288],[130,310],[115,322],
   [93,316],[70,302],[70,282],[85,270]],
];

// Rasterize shape into a pixel mask
const mc = document.createElement('canvas');
mc.width = W; mc.height = H;
const mctx = mc.getContext('2d');
mctx.fillStyle = '#fff';
ISLANDS.forEach(pts => {
  mctx.beginPath();
  mctx.moveTo(pts[0][0], pts[0][1]);
  pts.slice(1).forEach(p => mctx.lineTo(p[0], p[1]));
  mctx.closePath();
  mctx.fill();
});
const mask = mctx.getImageData(0, 0, W, H).data;

function inside(x, y) {
  const ix = Math.floor(x), iy = Math.floor(y);
  if (ix < 0 || ix >= W || iy < 0 || iy >= H) return false;
  return mask[(iy * W + ix) * 4 + 3] > 0;
}

// Seed particles inside the mask
const N = 190;
const pts = [];
let tries = 0;
while (pts.length < N && tries < 300000) {
  const x = Math.random() * W, y = Math.random() * H;
  if (inside(x, y)) {
    pts.push({
      x, y, ox: x, oy: y,
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
      r: Math.random() * 1.3 + 0.6,
    });
  }
  tries++;
}

// Mouse tracking
let mx = -9999, my = -9999;
canvas.addEventListener('mousemove', e => {
  const r = canvas.getBoundingClientRect();
  mx = (e.clientX - r.left) * (W / r.width);
  my = (e.clientY - r.top)  * (H / r.height);
});
canvas.addEventListener('mouseleave', () => { mx = -9999; my = -9999; });

const LINK_D = 36, MOUSE_R = 80;

function animate() {
  ctx.clearRect(0, 0, W, H);

  // Faint island outlines
  ISLANDS.forEach(island => {
    ctx.beginPath();
    ctx.moveTo(island[0][0], island[0][1]);
    island.slice(1).forEach(p => ctx.lineTo(p[0], p[1]));
    ctx.closePath();
    ctx.strokeStyle = 'rgba(100,155,255,0.10)';
    ctx.lineWidth = 0.8;
    ctx.stroke();
  });

  // Physics
  pts.forEach(p => {
    p.vx += (p.ox - p.x) * 0.003;
    p.vy += (p.oy - p.y) * 0.003;
    p.vx *= 0.95;
    p.vy *= 0.95;
    const dx = p.x - mx, dy = p.y - my;
    const d = Math.sqrt(dx * dx + dy * dy);
    if (d < MOUSE_R && d > 0.1) {
      const f = (MOUSE_R - d) / MOUSE_R * 3;
      p.vx += (dx / d) * f;
      p.vy += (dy / d) * f;
    }
    p.x += p.vx;
    p.y += p.vy;
  });

  // Links between nearby particles
  for (let i = 0; i < pts.length; i++) {
    for (let j = i + 1; j < pts.length; j++) {
      const dx = pts[i].x - pts[j].x, dy = pts[i].y - pts[j].y;
      const d = Math.sqrt(dx * dx + dy * dy);
      if (d < LINK_D) {
        ctx.beginPath();
        ctx.moveTo(pts[i].x, pts[i].y);
        ctx.lineTo(pts[j].x, pts[j].y);
        ctx.strokeStyle = `rgba(140,195,255,${(1 - d / LINK_D) * 0.55})`;
        ctx.lineWidth = 0.6;
        ctx.stroke();
      }
    }
  }

  // Dots
  pts.forEach(p => {
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(185,220,255,0.92)';
    ctx.fill();
  });

  requestAnimationFrame(animate);
}

animate();
</script>
</body>
</html>""",
        height=495,
        scrolling=False,
    )


_japan_particles()


# ── Compute headline insights from prefecture data ────────────────────────────
from pathlib import Path
import pandas as pd

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
        df["price_change_pct"] = (df["price_ppm2_2024"] - df["price_ppm2_2015"]) / df["price_ppm2_2015"] * 100
        tokyo_growth   = df.loc[df["name_en"] == "Tokyo", "price_change_pct"].iloc[0]
        nat_growth_med = df["price_change_pct"].median()
        tokyo_premium  = (
            df.loc[df["name_en"] == "Tokyo", "price_ppm2_2024"].iloc[0] /
            df["price_ppm2_2024"].median()
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
