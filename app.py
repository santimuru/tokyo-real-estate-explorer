"""
Japan Real Estate Intelligence — Landing / Intro page.
"""
from __future__ import annotations
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from utils.styles import inject_css, feature_cards, nav_sidebar, footer
from utils.prefecture_data import get_all_as_df


st.set_page_config(
    page_title="Japan Real Estate Intelligence",
    page_icon="🗾",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
nav_sidebar()


# ── Compute headline stats ─────────────────────────────────────────────────────
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
        (f"+{tokyo_growth:.0f}%",
         f"Tokyo growth {window_label} · vs +{nat_growth_med:.0f}% national median"),
        (f"{tokyo_premium:.0f}×",  "Tokyo premium · vs national median"),
        ("9M+",                    "Vacant homes (akiya)"),
        (f"{high_akiya}",          "Prefectures > 20% vacancy"),
        ("47 / 23",                "Prefectures · Tokyo wards"),
    ]


def _build_hero(stats: list[tuple[str, str]], height: int = 820) -> str:
    s0v, s0l = stats[0]
    s1v, s1l = stats[1]
    s2v, s2l = stats[2]
    s3v, s3l = stats[3]
    s4v, s4l = stats[4]

    return f"""<!DOCTYPE html>
<html>
<head>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width:100%; height:100%; overflow:hidden; background:#0e1117; font-family:system-ui,-apple-system,sans-serif; }}
canvas {{ position:absolute; inset:0; display:block; }}

#bar {{
  position:absolute; top:0; left:0; right:0; height:3px; z-index:10;
  background:linear-gradient(90deg,#3B82F6,#8B5CF6,#10B981);
}}

/* ── Main hero text ── */
#hero {{
  position:absolute; left:3.5%; top:9%; width:40%;
  pointer-events:none; z-index:6;
}}
.kicker {{
  font-size:10px; font-weight:700; text-transform:uppercase;
  letter-spacing:.20em; color:#60A5FA; margin-bottom:18px;
  display:flex; align-items:center; gap:10px;
}}
.kicker::before {{
  content:''; display:block; width:28px; height:1px;
  background:linear-gradient(90deg,#3B82F6,transparent);
  flex-shrink:0;
}}
.htitle-big {{
  font-size:clamp(52px,6vw,72px); font-weight:900; color:#fff;
  letter-spacing:-.04em; line-height:.88;
  text-shadow:0 2px 40px rgba(0,0,0,.95);
}}
.htitle-sub {{
  font-size:clamp(18px,2.2vw,26px); font-weight:400;
  color:rgba(160,200,255,.70); letter-spacing:.06em;
  margin-top:10px; margin-bottom:24px;
  text-transform:uppercase;
}}
.hdesc {{
  font-size:12.5px; color:rgba(170,200,230,.50); line-height:1.80;
  border-left:2px solid rgba(59,130,246,.40); padding-left:14px;
  max-width:360px;
}}

/* ── Stats row — bottom left ── */
#stats-row {{
  position:absolute; left:3.5%; bottom:8%;
  display:flex; gap:0; align-items:flex-start;
  pointer-events:none; z-index:6;
}}
.sc {{
  padding:0 32px 0 0; margin-right:32px;
  border-right:1px solid rgba(255,255,255,.08);
}}
.sc:last-child {{ border-right:none; margin-right:0; }}
.sn {{ font-size:36px; font-weight:800; color:#3B82F6; line-height:1; }}
.sl {{
  font-size:8px; font-weight:600; text-transform:uppercase;
  letter-spacing:.10em; color:rgba(160,200,235,.40);
  margin-top:6px; line-height:1.5;
}}

/* ── Right floating stats ── */
#stats-right {{
  position:absolute; right:2.5%; top:26%;
  pointer-events:none; z-index:6;
  display:flex; flex-direction:column; gap:0;
}}
.sr-block {{ padding:16px 0; border-bottom:1px solid rgba(255,255,255,.07); }}
.sr-block:last-child {{ border-bottom:none; }}
.sn-big {{ font-size:44px; font-weight:900; color:#3B82F6; line-height:1; }}

/* ── Bottom fade ── */
#fade {{
  position:absolute; bottom:0; left:0; right:0; height:100px; z-index:5;
  background:linear-gradient(to bottom,transparent,rgba(14,17,23,.90));
  pointer-events:none;
}}

/* ── City tooltip ── */
#tip {{
  position:absolute; display:none; pointer-events:none; z-index:20;
  background:rgba(10,14,22,0.96); color:rgba(195,225,255,.95);
  padding:8px 12px; border-radius:8px;
  border:1px solid rgba(100,155,255,.4);
  min-width:140px; max-width:210px;
}}
.t-head {{ font-size:13px; font-weight:700; display:flex; align-items:baseline; gap:6px; }}
.t-ja   {{ font-size:12px; font-weight:400; color:rgba(150,200,255,.7); }}
.t-pref {{ font-size:9.5px; color:rgba(140,190,255,.55); text-transform:uppercase; letter-spacing:.08em; margin-top:2px; }}
.t-data {{ font-size:10.5px; color:rgba(175,215,255,.72); margin-top:4px; line-height:1.5; }}
</style>
</head>
<body>
<div id="bar"></div>
<canvas id="c"></canvas>
<div id="fade"></div>

<!-- Main title block -->
<div id="hero">
  <div class="kicker">MLIT &nbsp;·&nbsp; 2010–2025 &nbsp;·&nbsp; 2.8M+ Transactions</div>
  <div class="htitle-big">JAPAN</div>
  <div class="htitle-sub">Real Estate Intelligence</div>
  <div class="hdesc">
    Transaction-level data from Japan's Ministry of Land, Infrastructure,
    Transport and Tourism — every prefecture, every one of Tokyo's 23 special wards.
    Price maps, vacancy trends, demographic shifts, deep ward analytics.
  </div>
</div>

<!-- Bottom stats row -->
<div id="stats-row">
  <div class="sc">
    <div class="sn">{s0v}</div>
    <div class="sl">{s0l}</div>
  </div>
  <div class="sc">
    <div class="sn">{s3v}</div>
    <div class="sl">{s3l}</div>
  </div>
  <div class="sc">
    <div class="sn">{s4v}</div>
    <div class="sl">{s4l}</div>
  </div>
</div>

<!-- Right-side floating stats -->
<div id="stats-right">
  <div class="sr-block">
    <div class="sn-big">{s1v}</div>
    <div class="sl">{s1l}</div>
  </div>
  <div class="sr-block">
    <div class="sn-big">{s2v}</div>
    <div class="sl">{s2l}</div>
  </div>
</div>

<!-- City tooltip -->
<div id="tip">
  <div class="t-head"><span id="t-en"></span><span class="t-ja" id="t-ja"></span></div>
  <div class="t-pref" id="t-pf"></div>
  <div class="t-data" id="t-dt"></div>
</div>

<script>
const canvas = document.getElementById('c');
const ctx    = canvas.getContext('2d');
const tip    = document.getElementById('tip');

const ISLANDS = [
  [[.754,.208],[.766,.129],[.806,.029],[.960,.067],[.980,.110],[.914,.181],[.797,.225],[.749,.215]],
  [[.783,.225],[.806,.294],[.754,.425],[.709,.463],[.663,.513],[.557,.519],[.537,.546],[.534,.571],
   [.506,.552],[.466,.531],[.420,.535],[.377,.544],[.343,.550],[.349,.546],[.366,.535],
   [.411,.500],[.480,.475],[.520,.475],[.563,.454],[.623,.381],[.697,.365],[.737,.283],[.760,.250]],
  [[.423,.546],[.480,.533],[.537,.546],[.549,.575],[.500,.590],[.434,.585],[.400,.571]],
  [[.291,.548],[.357,.538],[.386,.558],[.391,.600],[.371,.646],[.329,.671],
   [.266,.658],[.200,.629],[.200,.588],[.243,.563]],
];

// 52 cities: [en, ja, prefecture, lat, lon, size, pop, price]
const CITIES = [
  ['Sapporo','札幌','Hokkaido',43.065,141.354,3,'1.9M','¥131K/m²'],
  ['Asahikawa','旭川','Hokkaido',43.771,142.364,1.5,'',''],
  ['Hakodate','函館','Hokkaido',41.774,140.729,1.5,'',''],
  ['Aomori','青森','Aomori',40.824,140.740,2,'0.28M','¥48K/m²'],
  ['Morioka','盛岡','Iwate',39.703,141.154,2,'0.29M','¥55K/m²'],
  ['Sendai','仙台','Miyagi',38.268,140.869,2.5,'1.1M','¥150K/m²'],
  ['Akita','秋田','Akita',39.720,140.103,2,'0.30M','¥35K/m²'],
  ['Yamagata','山形','Yamagata',38.240,140.363,2,'0.25M','¥55K/m²'],
  ['Fukushima','福島','Fukushima',37.750,140.467,2,'0.28M','¥65K/m²'],
  ['Mito','水戸','Ibaraki',36.341,140.447,2,'0.27M','¥90K/m²'],
  ['Utsunomiya','宇都宮','Tochigi',36.555,139.883,2,'0.52M','¥100K/m²'],
  ['Maebashi','前橋','Gunma',36.389,139.062,2,'0.34M','¥85K/m²'],
  ['Saitama','さいたま','Saitama',35.861,139.645,2,'1.35M','¥210K/m²'],
  ['Chiba','千葉','Chiba',35.605,140.123,2,'0.98M','¥195K/m²'],
  ['Tokyo','東京','Tokyo',35.690,139.692,3,'14M','¥863K/m²'],
  ['Yokohama','横浜','Kanagawa',35.443,139.638,2.5,'3.8M','¥320K/m²'],
  ['Kawasaki','川崎','Kanagawa',35.520,139.702,2,'1.5M','¥350K/m²'],
  ['Niigata','新潟','Niigata',37.916,139.036,2,'0.78M','¥72K/m²'],
  ['Toyama','富山','Toyama',36.695,137.213,2,'0.41M','¥82K/m²'],
  ['Kanazawa','金沢','Ishikawa',36.561,136.656,2,'0.46M','¥118K/m²'],
  ['Fukui','福井','Fukui',36.065,136.222,2,'0.26M','¥90K/m²'],
  ['Kofu','甲府','Yamanashi',35.663,138.568,2,'0.19M','¥108K/m²'],
  ['Nagano','長野','Nagano',36.652,138.181,2,'0.37M','¥98K/m²'],
  ['Gifu','岐阜','Gifu',35.423,136.760,2,'0.40M','¥110K/m²'],
  ['Shizuoka','静岡','Shizuoka',34.977,138.383,2,'0.69M','¥120K/m²'],
  ['Hamamatsu','浜松','Shizuoka',34.711,137.726,2,'0.80M','¥115K/m²'],
  ['Nagoya','名古屋','Aichi',35.181,136.907,3,'2.3M','¥215K/m²'],
  ['Tsu','津','Mie',34.730,136.509,1.5,'0.28M','¥95K/m²'],
  ['Otsu','大津','Shiga',35.005,135.869,2,'0.35M','¥130K/m²'],
  ['Kyoto','京都','Kyoto',35.012,135.768,2.5,'1.4M','¥250K/m²'],
  ['Osaka','大阪','Osaka',34.693,135.502,3,'2.7M','¥289K/m²'],
  ['Kobe','神戸','Hyogo',34.690,135.196,2.5,'1.5M','¥175K/m²'],
  ['Nara','奈良','Nara',34.685,135.805,2,'0.35M','¥125K/m²'],
  ['Wakayama','和歌山','Wakayama',34.226,135.168,2,'0.36M','¥82K/m²'],
  ['Tottori','鳥取','Tottori',35.501,134.238,2,'0.19M','¥60K/m²'],
  ['Matsue','松江','Shimane',35.468,133.050,2,'0.20M','¥55K/m²'],
  ['Okayama','岡山','Okayama',34.655,133.919,2,'0.72M','¥120K/m²'],
  ['Hiroshima','広島','Hiroshima',34.385,132.455,2.5,'1.2M','¥183K/m²'],
  ['Yamaguchi','山口','Yamaguchi',34.186,131.473,2,'0.19M','¥70K/m²'],
  ['Tokushima','徳島','Tokushima',34.066,134.559,2,'0.26M','¥65K/m²'],
  ['Takamatsu','高松','Kagawa',34.340,134.047,2,'0.42M','¥100K/m²'],
  ['Matsuyama','松山','Ehime',33.839,132.765,2,'0.50M','¥85K/m²'],
  ['Kochi','高知','Kochi',33.559,133.531,2,'0.32M','¥72K/m²'],
  ['Kitakyushu','北九州','Fukuoka',33.883,130.879,2,'0.94M','¥130K/m²'],
  ['Fukuoka','福岡','Fukuoka',33.590,130.401,3,'1.6M','¥193K/m²'],
  ['Saga','佐賀','Saga',33.249,130.299,2,'0.23M','¥72K/m²'],
  ['Nagasaki','長崎','Nagasaki',32.751,129.877,2,'0.41M','¥78K/m²'],
  ['Kumamoto','熊本','Kumamoto',32.803,130.742,2.5,'0.73M','¥135K/m²'],
  ['Oita','大分','Oita',33.238,131.612,2,'0.48M','¥88K/m²'],
  ['Miyazaki','宮崎','Miyazaki',31.911,131.424,2,'0.40M','¥75K/m²'],
  ['Kagoshima','鹿児島','Kagoshima',31.560,130.558,2,'0.60M','¥85K/m²'],
  ['Naha','那覇','Okinawa',26.212,127.681,2,'0.32M','¥158K/m²'],
];

const B = {{ xMin:.200, xMax:.980, yMin:.029, yMax:.671 }};
let W, H, scale, offX, offY, LINK_D, MOUSE_R, particles = [];

function proj(nx, ny) {{ return [nx*scale+offX, ny*scale+offY]; }}
function ll(lat, lon)  {{ return proj((lon-123)/23, (46-lat)/22); }}

function setup() {{
  W = canvas.width  = window.innerWidth;
  H = canvas.height = window.innerHeight;
  // Fit Japan to fill the canvas — constrained by whichever axis runs out first
  const scaleH = (H * 0.88) / (B.yMax - B.yMin);
  const scaleW = (W * 0.68) / (B.xMax - B.xMin);
  scale = Math.min(scaleH, scaleW);
  // Center horizontally, nudge 2% right so left has room for text boxes
  offX   = (W - (B.xMax-B.xMin)*scale) / 2 - B.xMin*scale + W*0.02;
  // 6% top margin
  offY   = H * 0.06 - B.yMin*scale;
  LINK_D  = scale * 0.14;
  MOUSE_R = scale * 0.09;

  particles = CITIES.map(([en,ja,pref,lat,lon,s,pop,price]) => {{
    const [x,y] = ll(lat,lon);
    return {{ x,y,ox:x,oy:y, vx:(Math.random()-.5)*.25, vy:(Math.random()-.5)*.25,
             r:s*0.88, en,ja,pref,pop,price }};
  }});
}}
setup();
window.addEventListener('resize', setup);

let mx=-9999, my=-9999;
document.addEventListener('mousemove', e => {{
  const r = canvas.getBoundingClientRect();
  mx = e.clientX-r.left; my = e.clientY-r.top;
  let best=null, bestD=32;
  particles.forEach(p => {{
    const d=Math.hypot(p.x-mx,p.y-my);
    if(d<bestD){{bestD=d;best=p;}}
  }});
  if(best){{
    document.getElementById('t-en').textContent=best.en;
    document.getElementById('t-ja').textContent=best.ja;
    document.getElementById('t-pf').textContent=best.pref;
    const lines=[];
    if(best.pop)   lines.push('Pop: '+best.pop);
    if(best.price) lines.push('Median: '+best.price);
    document.getElementById('t-dt').textContent=lines.join('  ·  ');
    tip.style.display='block';
    const tx=mx+14+220>W?mx-228:mx+14;
    const ty=my-72<0?my+8:my-72;
    tip.style.left=tx+'px'; tip.style.top=ty+'px';
  }}else{{
    tip.style.display='none';
  }}
}});
document.addEventListener('mouseleave',()=>{{mx=-9999;my=-9999;tip.style.display='none';}});

function animate(){{
  ctx.clearRect(0,0,W,H);

  ISLANDS.forEach(pts=>{{
    const[sx,sy]=proj(pts[0][0],pts[0][1]);
    ctx.beginPath();ctx.moveTo(sx,sy);
    pts.slice(1).forEach(([nx,ny])=>{{const[px,py]=proj(nx,ny);ctx.lineTo(px,py);}});
    ctx.closePath();
    ctx.strokeStyle='rgba(100,155,255,.09)';ctx.lineWidth=.8;ctx.stroke();
  }});

  particles.forEach(p=>{{
    p.vx+=(p.ox-p.x)*.003; p.vy+=(p.oy-p.y)*.003;
    p.vx*=.95; p.vy*=.95; p.x+=p.vx; p.y+=p.vy;
  }});

  for(let i=0;i<particles.length;i++)for(let j=i+1;j<particles.length;j++){{
    const d=Math.hypot(particles[i].x-particles[j].x,particles[i].y-particles[j].y);
    if(d<LINK_D){{
      ctx.beginPath();ctx.moveTo(particles[i].x,particles[i].y);
      ctx.lineTo(particles[j].x,particles[j].y);
      ctx.strokeStyle=`rgba(140,195,255,${{(1-d/LINK_D)*.42}})`;
      ctx.lineWidth=.55;ctx.stroke();
    }}
  }}

  particles.forEach(p=>{{
    const d=Math.hypot(p.x-mx,p.y-my);
    const bright=d<MOUSE_R?Math.pow(1-d/MOUSE_R,1.4):0;
    ctx.beginPath();ctx.arc(p.x,p.y,p.r*(1+bright*2.5),0,Math.PI*2);
    if(bright>0){{
      ctx.shadowColor=`rgba(130,215,255,${{bright*.95}})`;
      ctx.shadowBlur=8+bright*18;
      ctx.fillStyle=`rgba(255,255,255,${{.5+bright*.5}})`;
    }}else{{
      ctx.shadowColor='transparent';ctx.shadowBlur=0;
      ctx.fillStyle='rgba(175,215,255,.70)';
    }}
    ctx.fill();
  }});
  ctx.shadowBlur=0;
  requestAnimationFrame(animate);
}}
animate();
</script>
</body>
</html>"""


# ── Render hero ────────────────────────────────────────────────────────────────
stats = _headline_stats()
components.html(_build_hero(stats), height=820, scrolling=False)

feature_cards()
footer("Home", "MLIT XIT001 API · Japan Housing and Land Survey · Statistics Bureau")
