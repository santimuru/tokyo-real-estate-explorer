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


# ── Japan city-map panel ───────────────────────────────────────────────────────
_MAP_HTML = """<!DOCTYPE html>
<html>
<head>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { width: 100%; height: 100%; overflow: hidden; }
body {
  background: var(--bg, #0e1117);
  border-radius: 16px;
  border: 1px solid rgba(255,255,255,0.08);
  position: relative;
}
canvas { display: block; width: 100%; height: 100%; }
#bar {
  position: absolute; top: 0; left: 0; right: 0; height: 3px; border-radius: 16px 16px 0 0;
  background: linear-gradient(90deg, #3B82F6, #8B5CF6, #10B981);
}
#tip {
  position: absolute; display: none; pointer-events: none; z-index: 10;
  background: rgba(10,14,22,0.96); color: rgba(195,225,255,0.95);
  padding: 8px 12px; border-radius: 8px;
  font-family: system-ui,-apple-system,sans-serif;
  border: 1px solid rgba(100,155,255,0.4);
  min-width: 140px; max-width: 220px;
}
.t-head { font-size: 13px; font-weight: 700; display: flex; align-items: baseline; gap: 6px; }
.t-ja   { font-size: 12px; font-weight: 400; color: rgba(150,200,255,0.7); }
.t-pref { font-size: 10px; color: rgba(140,190,255,0.55); text-transform: uppercase; letter-spacing: .08em; margin-top: 2px; }
.t-data { font-size: 11px; color: rgba(175,215,255,0.75); margin-top: 4px; line-height: 1.5; }
</style>
</head>
<body>
<div id="bar"></div>
<canvas id="c"></canvas>
<div id="tip">
  <div class="t-head"><span id="t-en"></span><span class="t-ja" id="t-ja"></span></div>
  <div class="t-pref" id="t-pf"></div>
  <div class="t-data" id="t-dt"></div>
</div>
<script>
const canvas = document.getElementById('c');
const ctx    = canvas.getContext('2d');
const tip    = document.getElementById('tip');

// Island outlines: x=(lon-123)/23, y=(46-lat)/22  (normalized)
const ISLANDS = [
  [[.754,.208],[.766,.129],[.806,.029],[.960,.067],[.980,.110],[.914,.181],[.797,.225],[.749,.215]],
  [[.783,.225],[.806,.294],[.754,.425],[.709,.463],[.663,.513],[.557,.519],[.537,.546],[.534,.571],
   [.506,.552],[.466,.531],[.420,.535],[.377,.544],[.343,.550],[.349,.546],[.366,.535],
   [.411,.500],[.480,.475],[.520,.475],[.563,.454],[.623,.381],[.697,.365],[.737,.283],[.760,.250]],
  [[.423,.546],[.480,.533],[.537,.546],[.549,.575],[.500,.590],[.434,.585],[.400,.571]],
  [[.291,.548],[.357,.538],[.386,.558],[.391,.600],[.371,.646],[.329,.671],
   [.266,.658],[.200,.629],[.200,.588],[.243,.563]],
];

// [name_en, name_ja, prefecture, lat, lon, size(1-3), pop, price_ppm2]
const CITIES = [
  // Hokkaido
  ['Sapporo','札幌','Hokkaido',43.065,141.354,3,'1.9M','¥131K/m²'],
  ['Asahikawa','旭川','Hokkaido',43.771,142.364,1.5,'',''],
  ['Hakodate','函館','Hokkaido',41.774,140.729,1.5,'',''],
  ['Kushiro','釧路','Hokkaido',42.985,144.381,1.5,'',''],
  ['Obihiro','帯広','Hokkaido',42.924,143.196,1.2,'',''],
  ['Tomakomai','苫小牧','Hokkaido',42.636,141.604,1.2,'',''],
  ['Otaru','小樽','Hokkaido',43.189,140.994,1.2,'',''],
  ['Kitami','北見','Hokkaido',43.803,143.900,1.2,'',''],
  ['Muroran','室蘭','Hokkaido',42.315,140.974,1.0,'',''],
  // Tohoku
  ['Aomori','青森','Aomori',40.824,140.740,2,'0.28M','¥48K/m²'],
  ['Hachinohe','八戸','Aomori',40.512,141.488,1.5,'',''],
  ['Hirosaki','弘前','Aomori',40.603,140.464,1.5,'',''],
  ['Morioka','盛岡','Iwate',39.703,141.154,2,'0.29M','¥55K/m²'],
  ['Sendai','仙台','Miyagi',38.268,140.869,2.5,'1.1M','¥150K/m²'],
  ['Ishinomaki','石巻','Miyagi',38.431,141.302,1.2,'',''],
  ['Akita','秋田','Akita',39.720,140.103,2,'0.30M','¥35K/m²'],
  ['Noshiro','能代','Akita',40.209,140.027,1.0,'',''],
  ['Yamagata','山形','Yamagata',38.240,140.363,2,'0.25M','¥55K/m²'],
  ['Tsuruoka','鶴岡','Yamagata',38.728,139.826,1.2,'',''],
  ['Fukushima','福島','Fukushima',37.750,140.467,2,'0.28M','¥65K/m²'],
  ['Koriyama','郡山','Fukushima',37.399,140.386,1.5,'',''],
  ['Iwaki','いわき','Fukushima',37.050,140.887,1.5,'',''],
  ['Aizuwakamatsu','会津若松','Fukushima',37.491,139.930,1.2,'',''],
  // Kanto
  ['Mito','水戸','Ibaraki',36.341,140.447,2,'0.27M','¥90K/m²'],
  ['Tsukuba','つくば','Ibaraki',36.083,140.076,1.5,'',''],
  ['Hitachi','日立','Ibaraki',36.601,140.651,1.5,'',''],
  ['Utsunomiya','宇都宮','Tochigi',36.555,139.883,2,'0.52M','¥100K/m²'],
  ['Oyama','小山','Tochigi',36.314,139.800,1.2,'',''],
  ['Ashikaga','足利','Tochigi',36.340,139.449,1.2,'',''],
  ['Maebashi','前橋','Gunma',36.389,139.062,2,'0.34M','¥85K/m²'],
  ['Takasaki','高崎','Gunma',36.323,139.011,1.5,'',''],
  ['Ota','太田','Gunma',36.292,139.375,1.5,'',''],
  ['Saitama','さいたま','Saitama',35.861,139.645,2,'1.35M','¥210K/m²'],
  ['Kawaguchi','川口','Saitama',35.807,139.724,1.5,'',''],
  ['Chiba','千葉','Chiba',35.605,140.123,2,'0.98M','¥195K/m²'],
  ['Funabashi','船橋','Chiba',35.694,139.983,1.5,'',''],
  ['Matsudo','松戸','Chiba',35.788,139.901,1.5,'',''],
  ['Kashiwa','柏','Chiba',35.868,139.975,1.5,'',''],
  ['Ichikawa','市川','Chiba',35.723,139.932,1.5,'',''],
  ['Tokyo','東京','Tokyo',35.690,139.692,3,'14M','¥863K/m²'],
  ['Hachioji','八王子','Tokyo',35.666,139.316,2,'',''],
  ['Tachikawa','立川','Tokyo',35.694,139.413,1.5,'',''],
  ['Machida','町田','Tokyo',35.549,139.446,1.5,'',''],
  ['Yokohama','横浜','Kanagawa',35.443,139.638,2.5,'3.8M','¥320K/m²'],
  ['Kawasaki','川崎','Kanagawa',35.520,139.702,2,'1.5M','¥350K/m²'],
  ['Sagamihara','相模原','Kanagawa',35.571,139.372,1.5,'',''],
  ['Yokosuka','横須賀','Kanagawa',35.281,139.669,2,'',''],
  ['Fujisawa','藤沢','Kanagawa',35.337,139.491,1.5,'',''],
  ['Odawara','小田原','Kanagawa',35.265,139.153,1.5,'',''],
  ['Hiratsuka','平塚','Kanagawa',35.328,139.342,1.5,'',''],
  ['Atsugi','厚木','Kanagawa',35.443,139.363,1.5,'',''],
  ['Chigasaki','茅ヶ崎','Kanagawa',35.333,139.404,1.2,'',''],
  // Chubu
  ['Niigata','新潟','Niigata',37.916,139.036,2,'0.78M','¥72K/m²'],
  ['Nagaoka','長岡','Niigata',37.447,138.851,1.5,'',''],
  ['Joetsu','上越','Niigata',37.147,138.236,1.2,'',''],
  ['Toyama','富山','Toyama',36.695,137.213,2,'0.41M','¥82K/m²'],
  ['Kanazawa','金沢','Ishikawa',36.561,136.656,2,'0.46M','¥118K/m²'],
  ['Fukui','福井','Fukui',36.065,136.222,2,'0.26M','¥90K/m²'],
  ['Kofu','甲府','Yamanashi',35.663,138.568,2,'0.19M','¥108K/m²'],
  ['Nagano','長野','Nagano',36.652,138.181,2,'0.37M','¥98K/m²'],
  ['Matsumoto','松本','Nagano',36.238,137.972,1.5,'',''],
  ['Gifu','岐阜','Gifu',35.423,136.760,2,'0.40M','¥110K/m²'],
  ['Shizuoka','静岡','Shizuoka',34.977,138.383,2,'0.69M','¥120K/m²'],
  ['Hamamatsu','浜松','Shizuoka',34.711,137.726,2,'0.80M','¥115K/m²'],
  ['Numazu','沼津','Shizuoka',35.097,138.863,1.5,'',''],
  ['Fuji','富士','Shizuoka',35.162,138.677,1.5,'',''],
  ['Nagoya','名古屋','Aichi',35.181,136.907,3,'2.3M','¥215K/m²'],
  ['Toyota','豊田','Aichi',35.083,137.156,1.5,'',''],
  ['Okazaki','岡崎','Aichi',34.956,137.161,1.5,'',''],
  ['Toyohashi','豊橋','Aichi',34.769,137.393,2,'0.38M',''],
  ['Kasugai','春日井','Aichi',35.248,136.972,1.5,'',''],
  ['Ichinomiya','一宮','Aichi',35.304,136.800,1.5,'',''],
  // Kinki
  ['Tsu','津','Mie',34.730,136.509,1.5,'0.28M','¥95K/m²'],
  ['Otsu','大津','Shiga',35.005,135.869,2,'0.35M','¥130K/m²'],
  ['Kyoto','京都','Kyoto',35.012,135.768,2.5,'1.4M','¥250K/m²'],
  ['Osaka','大阪','Osaka',34.693,135.502,3,'2.7M','¥289K/m²'],
  ['Sakai','堺','Osaka',34.573,135.483,1.5,'0.80M',''],
  ['Higashiosaka','東大阪','Osaka',34.679,135.601,1.5,'',''],
  ['Takatsuki','高槻','Osaka',34.849,135.617,1.5,'',''],
  ['Toyonaka','豊中','Osaka',34.782,135.469,1.5,'',''],
  ['Suita','吹田','Osaka',34.758,135.516,1.5,'',''],
  ['Kobe','神戸','Hyogo',34.690,135.196,2.5,'1.5M','¥175K/m²'],
  ['Himeji','姫路','Hyogo',34.816,134.686,2,'0.53M',''],
  ['Akashi','明石','Hyogo',34.650,134.989,1.5,'',''],
  ['Nishinomiya','西宮','Hyogo',34.737,135.343,1.5,'',''],
  ['Amagasaki','尼崎','Hyogo',34.723,135.414,1.5,'',''],
  ['Nara','奈良','Nara',34.685,135.805,2,'0.35M','¥125K/m²'],
  ['Wakayama','和歌山','Wakayama',34.226,135.168,2,'0.36M','¥82K/m²'],
  // Chugoku
  ['Tottori','鳥取','Tottori',35.501,134.238,2,'0.19M','¥60K/m²'],
  ['Yonago','米子','Tottori',35.432,133.330,1.5,'',''],
  ['Matsue','松江','Shimane',35.468,133.050,2,'0.20M','¥55K/m²'],
  ['Izumo','出雲','Shimane',35.367,132.755,1.5,'',''],
  ['Okayama','岡山','Okayama',34.655,133.919,2,'0.72M','¥120K/m²'],
  ['Kurashiki','倉敷','Okayama',34.585,133.772,1.5,'',''],
  ['Tsuyama','津山','Okayama',35.067,133.996,1.2,'',''],
  ['Hiroshima','広島','Hiroshima',34.385,132.455,2.5,'1.2M','¥183K/m²'],
  ['Fukuyama','福山','Hiroshima',34.486,133.362,2,'',''],
  ['Kure','呉','Hiroshima',34.249,132.566,1.5,'',''],
  ['Yamaguchi','山口','Yamaguchi',34.186,131.473,2,'0.19M','¥70K/m²'],
  // Shikoku
  ['Tokushima','徳島','Tokushima',34.066,134.559,2,'0.26M','¥65K/m²'],
  ['Takamatsu','高松','Kagawa',34.340,134.047,2,'0.42M','¥100K/m²'],
  ['Matsuyama','松山','Ehime',33.839,132.765,2,'0.50M','¥85K/m²'],
  ['Niihama','新居浜','Ehime',33.960,133.283,1.5,'',''],
  ['Imabari','今治','Ehime',34.066,132.998,1.5,'',''],
  ['Kochi','高知','Kochi',33.559,133.531,2,'0.32M','¥72K/m²'],
  // Kyushu
  ['Kitakyushu','北九州','Fukuoka',33.883,130.879,2,'0.94M','¥130K/m²'],
  ['Fukuoka','福岡','Fukuoka',33.590,130.401,3,'1.6M','¥193K/m²'],
  ['Kurume','久留米','Fukuoka',33.319,130.516,1.5,'',''],
  ['Tosu','鳥栖','Saga',33.379,130.509,1.2,'',''],
  ['Saga','佐賀','Saga',33.249,130.299,2,'0.23M','¥72K/m²'],
  ['Nagasaki','長崎','Nagasaki',32.751,129.877,2,'0.41M','¥78K/m²'],
  ['Sasebo','佐世保','Nagasaki',33.180,129.715,1.5,'',''],
  ['Isahaya','諫早','Nagasaki',32.843,130.055,1.2,'',''],
  ['Kumamoto','熊本','Kumamoto',32.803,130.742,2.5,'0.73M','¥135K/m²'],
  ['Yatsushiro','八代','Kumamoto',32.506,130.601,1.2,'',''],
  ['Oita','大分','Oita',33.238,131.612,2,'0.48M','¥88K/m²'],
  ['Beppu','別府','Oita',33.280,131.499,1.5,'',''],
  ['Nakatsu','中津','Oita',33.598,131.188,1.2,'',''],
  ['Miyazaki','宮崎','Miyazaki',31.911,131.424,2,'0.40M','¥75K/m²'],
  ['Nobeoka','延岡','Miyazaki',32.582,131.664,1.2,'',''],
  ['Miyakonojo','都城','Miyazaki',31.724,131.065,1.2,'',''],
  ['Kagoshima','鹿児島','Kagoshima',31.560,130.558,2,'0.60M','¥85K/m²'],
  // Okinawa
  ['Naha','那覇','Okinawa',26.212,127.681,2,'0.32M','¥158K/m²'],
  ['Okinawa City','沖縄市','Okinawa',26.334,127.802,1.5,'',''],
];

const B = { xMin:.200, xMax:.980, yMin:.029, yMax:.671 };
let W, H, scale, offX, offY, LINK_D, MOUSE_R, particles = [];

function proj(nx, ny) { return [nx*scale+offX, ny*scale+offY]; }
function ll(lat, lon)  { return proj((lon-123)/23, (46-lat)/22); }

function setup() {
  W = canvas.width  = window.innerWidth;
  H = canvas.height = window.innerHeight;
  scale  = (H * 0.86) / (B.yMax - B.yMin);
  offX   = (W - (B.xMax-B.xMin)*scale) / 2 - B.xMin*scale;
  offY   = H * 0.055 - B.yMin*scale;
  LINK_D = scale * 0.115;
  MOUSE_R = scale * 0.10;

  particles = CITIES.map(([en,ja,pref,lat,lon,s,pop,price]) => {
    const [x,y] = ll(lat, lon);
    return { x, y, ox:x, oy:y, vx:(Math.random()-.5)*.25, vy:(Math.random()-.5)*.25,
             r: s*0.82, en, ja, pref, pop, price };
  });
}
setup();
window.addEventListener('resize', setup);

let mx = -9999, my = -9999;
document.addEventListener('mousemove', e => {
  const r = canvas.getBoundingClientRect();
  mx = e.clientX - r.left;
  my = e.clientY - r.top;

  // Nearest city (30px threshold)
  let best = null, bestD = 30;
  particles.forEach(p => {
    const d = Math.hypot(p.x-mx, p.y-my);
    if (d < bestD) { bestD = d; best = p; }
  });

  if (best) {
    document.getElementById('t-en').textContent = best.en;
    document.getElementById('t-ja').textContent = best.ja;
    document.getElementById('t-pf').textContent = best.pref;
    const lines = [];
    if (best.pop)   lines.push('Pop: ' + best.pop);
    if (best.price) lines.push('Median: ' + best.price);
    document.getElementById('t-dt').textContent = lines.join('  ·  ');
    tip.style.display = 'block';
    const tx = mx + 14 + 230 > W ? mx - 240 : mx + 14;
    const ty = my - 70 < 0 ? my + 8 : my - 70;
    tip.style.left = tx + 'px';
    tip.style.top  = ty + 'px';
  } else {
    tip.style.display = 'none';
  }
});
document.addEventListener('mouseleave', () => { mx=-9999; my=-9999; tip.style.display='none'; });

function animate() {
  ctx.clearRect(0, 0, W, H);

  ISLANDS.forEach(pts => {
    const [sx,sy] = proj(pts[0][0], pts[0][1]);
    ctx.beginPath(); ctx.moveTo(sx, sy);
    pts.slice(1).forEach(([nx,ny]) => { const [px,py]=proj(nx,ny); ctx.lineTo(px,py); });
    ctx.closePath();
    ctx.strokeStyle = 'rgba(100,155,255,0.10)'; ctx.lineWidth = 0.8; ctx.stroke();
  });

  // Drift physics
  particles.forEach(p => {
    p.vx += (p.ox-p.x)*.003; p.vy += (p.oy-p.y)*.003;
    p.vx *= .95; p.vy *= .95;
    p.x += p.vx; p.y += p.vy;
  });

  // Links
  for (let i = 0; i < particles.length; i++) {
    for (let j = i+1; j < particles.length; j++) {
      const d = Math.hypot(particles[i].x-particles[j].x, particles[i].y-particles[j].y);
      if (d < LINK_D) {
        ctx.beginPath(); ctx.moveTo(particles[i].x, particles[i].y);
        ctx.lineTo(particles[j].x, particles[j].y);
        ctx.strokeStyle = `rgba(140,195,255,${(1-d/LINK_D)*.38})`; ctx.lineWidth=.5; ctx.stroke();
      }
    }
  }

  // Dots
  particles.forEach(p => {
    const d = Math.hypot(p.x-mx, p.y-my);
    const bright = d < MOUSE_R ? Math.pow(1-d/MOUSE_R, 1.4) : 0;
    ctx.beginPath(); ctx.arc(p.x, p.y, p.r*(1+bright*2.5), 0, Math.PI*2);
    if (bright > 0) {
      ctx.shadowColor=`rgba(130,215,255,${bright*.95})`; ctx.shadowBlur=8+bright*18;
      ctx.fillStyle=`rgba(255,255,255,${.5+bright*.5})`;
    } else {
      ctx.shadowColor='transparent'; ctx.shadowBlur=0;
      ctx.fillStyle='rgba(175,215,255,.68)';
    }
    ctx.fill();
  });
  ctx.shadowBlur = 0;
  requestAnimationFrame(animate);
}
animate();
</script>
</body>
</html>"""


def _japan_map_panel(height: int = 440) -> None:
    components.html(_MAP_HTML, height=height, scrolling=False)


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


# ── Layout: hero text left, Japan map right ────────────────────────────────────
col_text, col_map = st.columns([1.1, 1], gap="medium")

with col_text:
    platform_hero(stats=_headline_stats())

with col_map:
    _japan_map_panel(height=440)

feature_cards()
footer("Home", "MLIT XIT001 API · Japan Housing and Land Survey · Statistics Bureau")
