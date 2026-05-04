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
.platform-hero {
    background: rgba(14, 17, 23, 0.75) !important;
    backdrop-filter: blur(4px) !important;
    -webkit-backdrop-filter: blur(4px) !important;
}
</style>
""", unsafe_allow_html=True)


# ── Japan city-particle background ────────────────────────────────────────────
components.html("""<!DOCTYPE html>
<html><body style="margin:0;overflow:hidden;background:transparent;">
<script>
(function () {
  try {
    // Clean up previous renders
    ['japan-bg','japan-tip'].forEach(id => {
      const el = parent.document.getElementById(id);
      if (el) el.remove();
    });

    // ── Canvas ──────────────────────────────────────────────────────────────
    const canvas = parent.document.createElement('canvas');
    canvas.id = 'japan-bg';
    Object.assign(canvas.style, {
      position:'fixed', top:'0', left:'0',
      width:'100%', height:'100%',
      zIndex:'0', pointerEvents:'none',
    });
    parent.document.body.prepend(canvas);
    const ctx = canvas.getContext('2d');

    // ── Tooltip ─────────────────────────────────────────────────────────────
    const tip = parent.document.createElement('div');
    tip.id = 'japan-tip';
    Object.assign(tip.style, {
      position:'fixed', zIndex:'10', display:'none',
      background:'rgba(10,14,20,0.92)', color:'rgba(185,220,255,0.95)',
      padding:'5px 12px', borderRadius:'7px',
      fontSize:'12px', fontFamily:'system-ui,-apple-system,sans-serif',
      border:'1px solid rgba(100,155,255,0.35)',
      letterSpacing:'0.04em', whiteSpace:'nowrap', pointerEvents:'none',
    });
    parent.document.body.appendChild(tip);

    // ── Island outlines (normalized: x=(lon-123)/23, y=(46-lat)/22) ─────────
    const ISLANDS = [
      [[0.754,0.208],[0.766,0.129],[0.806,0.029],[0.960,0.067],[0.980,0.110],
       [0.914,0.181],[0.797,0.225],[0.749,0.215]],
      [[0.783,0.225],[0.806,0.294],[0.754,0.425],[0.709,0.463],[0.663,0.513],
       [0.557,0.519],[0.537,0.546],[0.534,0.571],[0.506,0.552],[0.466,0.531],
       [0.420,0.535],[0.377,0.544],[0.343,0.550],[0.349,0.546],[0.366,0.535],
       [0.411,0.500],[0.480,0.475],[0.520,0.475],[0.563,0.454],
       [0.623,0.381],[0.697,0.365],[0.737,0.283],[0.760,0.250]],
      [[0.423,0.546],[0.480,0.533],[0.537,0.546],[0.549,0.575],
       [0.500,0.590],[0.434,0.585],[0.400,0.571]],
      [[0.291,0.548],[0.357,0.538],[0.386,0.558],[0.391,0.600],
       [0.371,0.646],[0.329,0.671],[0.266,0.658],[0.200,0.629],
       [0.200,0.588],[0.243,0.563]],
    ];

    // ── Cities: [name_en, name_ja, lat, lon, size(1-3)] ─────────────────────
    // size 3 = metropolis, 2.5 = major, 2 = prefectural capital, 1.5 = large city
    const CITIES = [
      // Hokkaido
      ['Sapporo','札幌',43.065,141.354,3],
      ['Asahikawa','旭川',43.771,142.364,1.5],
      ['Hakodate','函館',41.774,140.729,1.5],
      ['Kushiro','釧路',42.985,144.381,1.5],
      ['Obihiro','帯広',42.924,143.196,1.2],
      // Tohoku
      ['Aomori','青森',40.824,140.740,2],
      ['Hachinohe','八戸',40.512,141.488,1.5],
      ['Morioka','盛岡',39.703,141.154,2],
      ['Sendai','仙台',38.268,140.869,2.5],
      ['Akita','秋田',39.720,140.103,2],
      ['Yamagata','山形',38.240,140.363,2],
      ['Fukushima','福島',37.750,140.467,2],
      ['Koriyama','郡山',37.399,140.386,1.5],
      // Kanto
      ['Mito','水戸',36.341,140.447,2],
      ['Utsunomiya','宇都宮',36.555,139.883,2],
      ['Maebashi','前橋',36.389,139.062,2],
      ['Saitama','さいたま',35.861,139.645,2],
      ['Kawaguchi','川口',35.807,139.724,1.5],
      ['Chiba','千葉',35.605,140.123,2],
      ['Tokyo','東京',35.690,139.692,3],
      ['Yokohama','横浜',35.443,139.638,2.5],
      ['Kawasaki','川崎',35.520,139.702,2],
      ['Sagamihara','相模原',35.571,139.372,1.5],
      // Chubu
      ['Niigata','新潟',37.916,139.036,2],
      ['Toyama','富山',36.695,137.213,2],
      ['Kanazawa','金沢',36.561,136.656,2],
      ['Fukui','福井',36.065,136.222,2],
      ['Kofu','甲府',35.663,138.568,2],
      ['Nagano','長野',36.652,138.181,2],
      ['Matsumoto','松本',36.238,137.972,1.5],
      ['Gifu','岐阜',35.423,136.760,2],
      ['Shizuoka','静岡',34.977,138.383,2],
      ['Hamamatsu','浜松',34.711,137.726,2],
      ['Nagoya','名古屋',35.181,136.907,3],
      ['Toyota','豊田',35.083,137.156,1.5],
      // Kinki
      ['Tsu','津',34.730,136.509,1.5],
      ['Otsu','大津',35.005,135.869,2],
      ['Kyoto','京都',35.012,135.768,2.5],
      ['Osaka','大阪',34.693,135.502,3],
      ['Sakai','堺',34.573,135.483,1.5],
      ['Kobe','神戸',34.690,135.196,2.5],
      ['Himeji','姫路',34.816,134.686,2],
      ['Nara','奈良',34.685,135.805,2],
      ['Wakayama','和歌山',34.226,135.168,2],
      // Chugoku
      ['Tottori','鳥取',35.501,134.238,2],
      ['Matsue','松江',35.468,133.050,2],
      ['Okayama','岡山',34.655,133.919,2],
      ['Kurashiki','倉敷',34.585,133.772,1.5],
      ['Hiroshima','広島',34.385,132.455,2.5],
      ['Yamaguchi','山口',34.186,131.473,2],
      // Shikoku
      ['Tokushima','徳島',34.066,134.559,2],
      ['Takamatsu','高松',34.340,134.047,2],
      ['Matsuyama','松山',33.839,132.765,2],
      ['Kochi','高知',33.559,133.531,2],
      // Kyushu
      ['Kitakyushu','北九州',33.883,130.879,2],
      ['Fukuoka','福岡',33.590,130.401,3],
      ['Saga','佐賀',33.249,130.299,2],
      ['Nagasaki','長崎',32.751,129.877,2],
      ['Sasebo','佐世保',33.180,129.715,1.5],
      ['Kumamoto','熊本',32.803,130.742,2.5],
      ['Oita','大分',33.238,131.612,2],
      ['Miyazaki','宮崎',31.911,131.424,2],
      ['Kagoshima','鹿児島',31.560,130.558,2],
      // Okinawa
      ['Naha','那覇',26.212,127.681,2],
    ];

    const B = { xMin:0.200, xMax:0.980, yMin:0.029, yMax:0.671 };
    let W, H, scale, offX, offY, LINK_D, MOUSE_R, particles = [];

    function proj(nx, ny) { return [nx * scale + offX, ny * scale + offY]; }

    function latlon(lat, lon) {
      return proj((lon - 123) / 23, (46 - lat) / 22);
    }

    function setup() {
      W = canvas.width  = parent.innerWidth;
      H = canvas.height = parent.innerHeight;
      scale  = (H * 0.70) / (B.yMax - B.yMin);
      offX   = (W - (B.xMax - B.xMin) * scale) / 2 - B.xMin * scale;
      offY   = H * 0.10 - B.yMin * scale;
      LINK_D = scale * 0.115;   // ~geographic neighbors
      MOUSE_R = scale * 0.095;

      particles = CITIES.map(([en, ja, lat, lon, s]) => {
        const [x, y] = latlon(lat, lon);
        return { x, y, ox: x, oy: y,
                 vx: (Math.random()-0.5)*0.3, vy: (Math.random()-0.5)*0.3,
                 r: s * 0.85, en, ja };
      });
    }

    setup();
    parent.addEventListener('resize', setup);

    let mx = -9999, my = -9999;
    parent.document.addEventListener('mousemove', e => {
      mx = e.clientX; my = e.clientY;
      // Nearest city tooltip
      let best = null, bestD = 28;
      particles.forEach(p => {
        const d = Math.hypot(p.x - mx, p.y - my);
        if (d < bestD) { bestD = d; best = p; }
      });
      if (best) {
        tip.textContent = best.en + '  ' + best.ja;
        const tx = mx + 14 + 160 > W ? mx - 168 : mx + 14;
        const ty = my - 32 < 0 ? my + 8 : my - 32;
        tip.style.left = tx + 'px';
        tip.style.top  = ty + 'px';
        tip.style.display = 'block';
      } else {
        tip.style.display = 'none';
      }
    });
    parent.document.addEventListener('mouseleave', () => {
      mx = -9999; my = -9999; tip.style.display = 'none';
    });

    function animate() {
      ctx.clearRect(0, 0, W, H);

      // Faint island outlines
      ISLANDS.forEach(pts => {
        const [sx, sy] = proj(pts[0][0], pts[0][1]);
        ctx.beginPath(); ctx.moveTo(sx, sy);
        pts.slice(1).forEach(([nx,ny]) => { const [px,py]=proj(nx,ny); ctx.lineTo(px,py); });
        ctx.closePath();
        ctx.strokeStyle = 'rgba(100,155,255,0.09)';
        ctx.lineWidth = 1; ctx.stroke();
      });

      // Gentle drift physics
      particles.forEach(p => {
        p.vx += (p.ox - p.x) * 0.003;
        p.vy += (p.oy - p.y) * 0.003;
        p.vx *= 0.95; p.vy *= 0.95;
        p.x += p.vx; p.y += p.vy;
      });

      // Links between geographic neighbors
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const d = Math.hypot(particles[i].x - particles[j].x, particles[i].y - particles[j].y);
          if (d < LINK_D) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(140,195,255,${(1 - d/LINK_D) * 0.40})`;
            ctx.lineWidth = 0.5; ctx.stroke();
          }
        }
      }

      // City dots — glow on hover
      particles.forEach(p => {
        const d = Math.hypot(p.x - mx, p.y - my);
        const bright = d < MOUSE_R ? Math.pow(1 - d / MOUSE_R, 1.4) : 0;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r * (1 + bright * 2.5), 0, Math.PI * 2);
        if (bright > 0) {
          ctx.shadowColor = `rgba(130,215,255,${bright * 0.95})`;
          ctx.shadowBlur  = 8 + bright * 18;
          ctx.fillStyle   = `rgba(255,255,255,${0.5 + bright * 0.5})`;
        } else {
          ctx.shadowColor = 'transparent';
          ctx.shadowBlur  = 0;
          ctx.fillStyle   = 'rgba(175,215,255,0.65)';
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
