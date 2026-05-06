"""
Japan Real Estate Intelligence — Landing / Intro page.
"""
from __future__ import annotations
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from utils.styles import inject_css, feature_cards, nav_sidebar, nav_top, footer
from utils.prefecture_data import get_all_as_df


st.set_page_config(
    page_title="Japan Real Estate Intelligence",
    page_icon="🗾",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()
nav_sidebar()
nav_top()



# ── Compute headline stats ─────────────────────────────────────────────────────
PARQUET = Path(__file__).resolve().parent / "data" / "prefecture_aggregates.parquet"


@st.cache_data(show_spinner=False)
def _headline_stats() -> list[tuple[str, str]]:
    df = get_all_as_df()
    high_akiya = int((df["akiya_rate_2023"] >= 20).sum())

    agg = pd.read_parquet(PARQUET)
    agg["prefecture_code"] = agg["prefecture_code"].astype(str).str.zfill(2)
    years = sorted(agg["tx_year"].unique())
    first_yr, last_yr = years[0], years[-1]
    a_first = agg[agg["tx_year"] == first_yr].set_index("prefecture_code")["median_ppm2"]
    a_last  = agg[agg["tx_year"] == last_yr].set_index("prefecture_code")["median_ppm2"]
    tokyo_growth   = (a_last["13"] - a_first["13"]) / a_first["13"] * 100
    joined         = pd.concat([a_first.rename("p0"), a_last.rename("p1")], axis=1).dropna()
    nat_growth_med = ((joined["p1"] - joined["p0"]) / joined["p0"] * 100).median()
    tokyo_premium  = a_last["13"] / a_last.median()
    window_label   = f"{first_yr}-{last_yr}"

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
html, body {{ width:100%; height:{height}px; overflow:hidden; background:#080808; font-family:system-ui,-apple-system,sans-serif; }}
canvas {{ position:absolute; inset:0; width:100%; height:{height}px; display:block; }}

#bar {{
  position:absolute; top:0; left:0; right:0; height:3px; z-index:10;
  background:linear-gradient(90deg,#3B82F6,#8B5CF6,#10B981);
}}

/* ── Main hero text ── */
#hero {{
  position:absolute; left:3.5%; top:9%; width:33%;
  z-index:6;
}}
.kicker {{
  font-size:9px; font-weight:700; text-transform:uppercase;
  letter-spacing:.20em; color:#3B82F6; margin-bottom:16px;
  display:flex; align-items:center; gap:10px;
}}
.kicker::before {{
  content:''; display:block; width:28px; height:1px;
  background:linear-gradient(90deg,#3B82F6,transparent);
  flex-shrink:0;
}}
.htitle-big {{
  font-size:clamp(47px,5.4vw,65px); font-weight:900; color:#fff;
  letter-spacing:-.04em; line-height:.88;
  text-shadow:0 2px 40px rgba(0,0,0,.95);
}}
.htitle-sub {{
  font-size:clamp(14px,1.6vw,19px); font-weight:300;
  color:rgba(160,200,255,.55); letter-spacing:.28em;
  margin-top:10px; margin-bottom:24px;
  text-transform:uppercase; font-style:italic;
}}
.hdesc {{
  font-size:11.5px; color:rgba(170,200,230,.55); line-height:1.82;
  border-left:2px solid rgba(59,130,246,.35); padding-left:14px;
}}
.hdesc p {{ margin:0 0 10px; }}
.hdesc p:last-child {{ margin-bottom:0; }}
.hdesc strong {{ color:rgba(200,225,255,.80); font-weight:600; }}

.sl {{
  font-size:8px; font-weight:600; text-transform:uppercase;
  letter-spacing:.10em; color:rgba(160,200,235,.40);
  margin-top:5px; line-height:1.5;
}}

/* ── Right floating stats ── */
#stats-right {{
  position:absolute; right:2.5%; top:6%;
  pointer-events:none; z-index:6;
  display:flex; flex-direction:column; gap:0;
  min-width:155px;
}}
.sr-block {{ padding:12px 0; border-bottom:1px solid rgba(255,255,255,.07); }}
.sr-block:last-child {{ border-bottom:none; }}
.sn {{ font-size:34px; font-weight:900; color:#3B82F6; line-height:1; }}

/* ── Bottom fade ── */
#fade {{
  position:absolute; bottom:0; left:0; right:0; height:100px; z-index:5;
  background:linear-gradient(to bottom,transparent,rgba(14,17,23,.90));
  pointer-events:none;
}}

/* ── Transaction ticker ── */
#ticker {{
  position:absolute; bottom:22px; right:0; z-index:7;
  width:470px; pointer-events:none;
}}
.tk-header {{
  font-size:7.5px; font-weight:700; text-transform:uppercase;
  letter-spacing:.15em; color:rgba(140,180,255,.70);
  border-bottom:1px solid rgba(90,145,255,.25);
  padding-bottom:5px; margin-bottom:4px;
  display:grid; grid-template-columns:48px 76px 105px 44px 46px 50px 55px 38px;
}}
#ticker-rows {{
  height:105px; overflow:hidden;
}}
.tk-row {{
  display:grid; grid-template-columns:48px 76px 105px 44px 46px 50px 55px 38px;
  height:21px; align-items:center;
  border-bottom:1px solid rgba(255,255,255,.035);
  opacity:0; animation:tk-in .35s ease forwards;
}}
@keyframes tk-in {{
  0%   {{ opacity:0; background:rgba(80,180,255,0.18); }}
  25%  {{ opacity:1; background:rgba(80,180,255,0.12); }}
  70%  {{ opacity:1; background:rgba(80,180,255,0.04); }}
  100% {{ opacity:1; background:transparent; }}
}}
.tk-cell {{
  font-size:9px; font-weight:400; color:rgba(180,210,240,.55);
  letter-spacing:.02em; white-space:nowrap; overflow:hidden;
}}

/* ── City tooltip ── */
#tip {{
  position:absolute; display:none; pointer-events:none; z-index:20;
  background:rgba(8,12,20,0.97);
  border:1px solid rgba(70,130,255,.30);
  border-radius:11px; min-width:210px; max-width:250px;
  box-shadow:0 12px 40px rgba(0,0,0,.65), 0 0 0 1px rgba(100,160,255,.06);
  overflow:hidden; font-family:system-ui,-apple-system,sans-serif;
}}
.t-header {{
  padding:12px 14px 10px;
  border-bottom:1px solid rgba(255,255,255,.055);
  background:rgba(255,255,255,.025);
}}
.t-name-row {{ display:flex; align-items:baseline; gap:8px; }}
.t-city-en {{
  font-size:17px; font-weight:800; color:#fff; letter-spacing:-.02em; line-height:1;
}}
.t-city-ja {{
  font-size:13px; font-weight:400; color:rgba(130,180,255,.60);
}}
.t-meta {{
  font-size:8.5px; font-weight:700; text-transform:uppercase;
  letter-spacing:.13em; color:rgba(90,145,255,.50); margin-top:6px;
  display:flex; align-items:center; gap:6px;
}}
.t-meta-dot {{ width:3px; height:3px; border-radius:50%; background:rgba(90,145,255,.35); flex-shrink:0; }}
.t-body {{
  padding:11px 14px 13px;
  display:grid; grid-template-columns:1fr 1fr; gap:10px 16px;
}}
.t-stat-lbl {{
  font-size:7.5px; font-weight:700; text-transform:uppercase;
  letter-spacing:.11em; color:rgba(120,170,230,.38); margin-bottom:4px;
}}
.t-stat-num {{ font-size:20px; font-weight:800; color:#3B82F6; line-height:1; }}
.t-stat-unit {{ font-size:9px; color:rgba(140,190,255,.50); margin-left:2px; }}
.t-tier {{ display:flex; gap:3px; margin-top:5px; align-items:center; }}
.td {{ width:5px; height:5px; border-radius:50%; }}
.td.on  {{ background:#3B82F6; }}
.td.off {{ background:rgba(255,255,255,.10); }}
</style>
</head>
<body>
<div id="bar"></div>
<canvas id="c"></canvas>
<div id="fade"></div>

<!-- Main title block -->
<div id="hero">
  <div class="htitle-big">JAPAN</div>
  <div class="htitle-sub">Real Estate</div>
  <div class="hdesc">
    <p>Moving to Japan means navigating one of the world's most opaque property markets.
    Regional price dynamics, vacancy crises, ward-level micro-markets, and decades of
    depreciation norms make it genuinely hard to know what anything is worth or where to look.</p>
    <p>This project started as a personal question and became a data engineering exercise:
    pull every recorded transaction from Japan's government registry, clean it, model it,
    and make it explorable. Raw <strong>MLIT data</strong> covering
    <strong>47 prefectures</strong>, Tokyo's <strong>23 wards</strong>, and
    <strong>15 years</strong> of deals. No estimates. No aggregated indices. The actual receipts.</p>
    <p>Use it to understand price geography, spot regional growth stories the headlines miss,
    or pressure-test a neighborhood before committing to it.</p>
  </div>
</div>

<!-- All stats stacked on the right -->
<div id="stats-right">
  <div class="sr-block">
    <div class="sn">{s1v}</div>
    <div class="sl">{s1l}</div>
  </div>
  <div class="sr-block">
    <div class="sn">{s2v}</div>
    <div class="sl">{s2l}</div>
  </div>
  <div class="sr-block">
    <div class="sn">{s3v}</div>
    <div class="sl">{s3l}</div>
  </div>
  <div class="sr-block">
    <div class="sn">{s4v}</div>
    <div class="sl">{s4l}</div>
  </div>
</div>

<!-- Transaction ticker -->
<div id="ticker">
  <div class="tk-header">
    <span>ID</span>
    <span>CITY</span>
    <span>TYPE</span>
    <span>LAYOUT</span>
    <span>AREA</span>
    <span>¥/M²</span>
    <span>PRICE</span>
    <span>YEAR</span>
  </div>
  <div id="ticker-rows"></div>
</div>

<!-- City tooltip -->
<div id="tip">
  <div class="t-header">
    <div class="t-name-row">
      <span class="t-city-en" id="t-en"></span>
      <span class="t-city-ja" id="t-ja"></span>
    </div>
    <div class="t-meta">
      <span id="t-pf"></span>
      <span class="t-meta-dot"></span>
      <span id="t-tier-lbl"></span>
    </div>
  </div>
  <div class="t-body">
    <div>
      <div class="t-stat-lbl">Population</div>
      <div id="t-pop"></div>
    </div>
    <div>
      <div class="t-stat-lbl">Median Price</div>
      <div id="t-price"></div>
      <div class="t-tier" id="t-dots"></div>
    </div>
  </div>
</div>

<script>
const canvas = document.getElementById('c');
const ctx    = canvas.getContext('2d');
const tip    = document.getElementById('tip');

const ISLANDS = [
  // Hokkaido
  [[.754,.208],[.762,.175],[.766,.129],[.778,.085],[.806,.029],[.860,.038],[.920,.055],
   [.960,.067],[.980,.110],[.970,.140],[.950,.158],[.930,.172],[.914,.181],[.880,.200],
   [.850,.215],[.820,.222],[.797,.225],[.770,.220],[.749,.215]],
  // Honshu
  [[.783,.225],[.790,.250],[.800,.270],[.806,.294],[.800,.320],[.785,.348],[.770,.375],
   [.754,.425],[.735,.445],[.718,.455],[.709,.463],[.690,.480],[.675,.495],[.663,.513],
   [.645,.516],[.620,.518],[.600,.519],[.580,.520],[.557,.519],[.545,.530],[.537,.546],
   [.534,.571],[.520,.565],[.506,.552],[.490,.542],[.466,.531],[.445,.532],[.420,.535],
   [.400,.538],[.377,.544],[.360,.547],[.343,.550],[.340,.543],[.349,.536],[.349,.546],
   [.360,.540],[.366,.535],[.385,.528],[.411,.500],[.440,.488],[.460,.480],[.480,.475],
   [.500,.472],[.520,.475],[.542,.465],[.563,.454],[.585,.440],[.600,.425],[.623,.381],
   [.645,.372],[.668,.366],[.697,.365],[.715,.340],[.728,.315],[.737,.283],[.748,.268],[.760,.250]],
  // Shikoku
  [[.423,.546],[.445,.538],[.465,.534],[.480,.533],[.510,.537],[.537,.546],[.545,.558],
   [.549,.575],[.538,.585],[.518,.590],[.500,.590],[.475,.590],[.450,.587],[.434,.585],[.415,.578],[.400,.571]],
  // Kyushu
  [[.291,.548],[.315,.542],[.335,.538],[.357,.538],[.372,.548],[.386,.558],[.390,.575],
   [.391,.600],[.385,.620],[.375,.638],[.371,.646],[.355,.660],[.340,.668],[.329,.671],
   [.310,.668],[.290,.662],[.266,.658],[.240,.648],[.220,.638],[.200,.629],[.196,.610],
   [.200,.588],[.215,.572],[.230,.560],[.243,.563],[.265,.554]],
  // Okinawa (main)
  [[.105,.671],[.120,.665],[.138,.660],[.148,.665],[.145,.675],[.130,.680],[.112,.678]],
];

// 83 cities: [en, ja, prefecture, lat, lon, size(1-3), pop, price]
const CITIES = [
  // Hokkaido
  ['Wakkanai','稚内','Hokkaido',45.415,141.673,1,'',''],
  ['Sapporo','札幌','Hokkaido',43.065,141.354,3,'1.9M','¥131K/m²'],
  ['Asahikawa','旭川','Hokkaido',43.771,142.364,2,'0.33M','¥78K/m²'],
  ['Kushiro','釧路','Hokkaido',43.794,144.375,1.5,'0.17M','¥55K/m²'],
  ['Obihiro','帯広','Hokkaido',42.917,143.196,1.5,'0.17M','¥52K/m²'],
  ['Hakodate','函館','Hokkaido',41.774,140.729,2,'0.26M','¥75K/m²'],
  ['Tomakomai','苫小牧','Hokkaido',42.636,141.605,1.5,'0.17M','¥65K/m²'],
  // Tohoku
  ['Aomori','青森','Aomori',40.824,140.740,2,'0.28M','¥48K/m²'],
  ['Hachinohe','八戸','Aomori',40.512,141.488,2,'0.22M','¥52K/m²'],
  ['Morioka','盛岡','Iwate',39.703,141.154,2,'0.29M','¥55K/m²'],
  ['Sendai','仙台','Miyagi',38.268,140.869,2.5,'1.1M','¥150K/m²'],
  ['Akita','秋田','Akita',39.720,140.103,2,'0.30M','¥35K/m²'],
  ['Yamagata','山形','Yamagata',38.240,140.363,2,'0.25M','¥55K/m²'],
  ['Fukushima','福島','Fukushima',37.750,140.467,2,'0.28M','¥65K/m²'],
  ['Koriyama','郡山','Fukushima',37.399,140.387,2,'0.33M','¥78K/m²'],
  ['Iwaki','いわき','Fukushima',37.052,140.887,1.5,'0.34M','¥68K/m²'],
  // Kanto
  ['Mito','水戸','Ibaraki',36.341,140.447,2,'0.27M','¥90K/m²'],
  ['Tsukuba','つくば','Ibaraki',36.082,140.078,1.5,'0.25M','¥130K/m²'],
  ['Utsunomiya','宇都宮','Tochigi',36.555,139.883,2,'0.52M','¥100K/m²'],
  ['Maebashi','前橋','Gunma',36.389,139.062,2,'0.34M','¥85K/m²'],
  ['Takasaki','高崎','Gunma',36.323,139.004,2,'0.37M','¥92K/m²'],
  ['Saitama','さいたま','Saitama',35.861,139.645,2.5,'1.35M','¥210K/m²'],
  ['Kawagoe','川越','Saitama',35.925,139.486,1.5,'0.35M','¥185K/m²'],
  ['Chiba','千葉','Chiba',35.605,140.123,2.5,'0.98M','¥195K/m²'],
  ['Funabashi','船橋','Chiba',35.694,139.983,2,'0.63M','¥200K/m²'],
  ['Tokyo','東京','Tokyo',35.690,139.692,3,'14M','¥863K/m²'],
  ['Kawasaki','川崎','Kanagawa',35.520,139.702,2.5,'1.5M','¥350K/m²'],
  ['Yokohama','横浜','Kanagawa',35.443,139.638,3,'3.8M','¥320K/m²'],
  ['Sagamihara','相模原','Kanagawa',35.571,139.372,2,'0.73M','¥230K/m²'],
  ['Yokosuka','横須賀','Kanagawa',35.282,139.672,2,'0.40M','¥180K/m²'],
  // Chubu
  ['Niigata','新潟','Niigata',37.916,139.036,2,'0.78M','¥72K/m²'],
  ['Toyama','富山','Toyama',36.695,137.213,2,'0.41M','¥82K/m²'],
  ['Kanazawa','金沢','Ishikawa',36.561,136.656,2,'0.46M','¥118K/m²'],
  ['Fukui','福井','Fukui',36.065,136.222,2,'0.26M','¥90K/m²'],
  ['Kofu','甲府','Yamanashi',35.663,138.568,1.5,'0.19M','¥108K/m²'],
  ['Nagano','長野','Nagano',36.652,138.181,2,'0.37M','¥98K/m²'],
  ['Matsumoto','松本','Nagano',36.238,137.972,1.5,'0.24M','¥105K/m²'],
  ['Gifu','岐阜','Gifu',35.423,136.760,2,'0.40M','¥110K/m²'],
  ['Numazu','沼津','Shizuoka',35.096,138.863,1.5,'0.19M','¥115K/m²'],
  ['Shizuoka','静岡','Shizuoka',34.977,138.383,2,'0.69M','¥120K/m²'],
  ['Hamamatsu','浜松','Shizuoka',34.711,137.726,2,'0.80M','¥115K/m²'],
  ['Nagoya','名古屋','Aichi',35.181,136.907,3,'2.3M','¥215K/m²'],
  ['Toyota','豊田','Aichi',35.083,137.157,2,'0.43M','¥115K/m²'],
  ['Okazaki','岡崎','Aichi',34.948,137.163,2,'0.39M','¥120K/m²'],
  ['Toyohashi','豊橋','Aichi',34.769,137.392,2,'0.38M','¥110K/m²'],
  ['Tsu','津','Mie',34.730,136.509,1.5,'0.28M','¥95K/m²'],
  // Kansai
  ['Otsu','大津','Shiga',35.005,135.869,2,'0.35M','¥130K/m²'],
  ['Kyoto','京都','Kyoto',35.012,135.768,2.5,'1.4M','¥250K/m²'],
  ['Osaka','大阪','Osaka',34.693,135.502,3,'2.7M','¥289K/m²'],
  ['Sakai','堺','Osaka',34.573,135.483,2,'0.83M','¥175K/m²'],
  ['Higashiosaka','東大阪','Osaka',34.679,135.601,2,'0.49M','¥210K/m²'],
  ['Kobe','神戸','Hyogo',34.690,135.196,2.5,'1.5M','¥175K/m²'],
  ['Himeji','姫路','Hyogo',34.816,134.686,2,'0.53M','¥110K/m²'],
  ['Amagasaki','尼崎','Hyogo',34.735,135.413,2,'0.45M','¥200K/m²'],
  ['Nara','奈良','Nara',34.685,135.805,2,'0.35M','¥125K/m²'],
  ['Wakayama','和歌山','Wakayama',34.226,135.168,2,'0.36M','¥82K/m²'],
  // Chugoku
  ['Tottori','鳥取','Tottori',35.501,134.238,1.5,'0.19M','¥60K/m²'],
  ['Matsue','松江','Shimane',35.468,133.050,1.5,'0.20M','¥55K/m²'],
  ['Okayama','岡山','Okayama',34.655,133.919,2,'0.72M','¥120K/m²'],
  ['Kurashiki','倉敷','Okayama',34.585,133.772,2,'0.48M','¥100K/m²'],
  ['Hiroshima','広島','Hiroshima',34.385,132.455,2.5,'1.2M','¥183K/m²'],
  ['Fukuyama','福山','Hiroshima',34.486,133.363,2,'0.46M','¥90K/m²'],
  ['Yamaguchi','山口','Yamaguchi',34.186,131.473,1.5,'0.19M','¥70K/m²'],
  // Shikoku
  ['Tokushima','徳島','Tokushima',34.066,134.559,2,'0.26M','¥65K/m²'],
  ['Takamatsu','高松','Kagawa',34.340,134.047,2,'0.42M','¥100K/m²'],
  ['Matsuyama','松山','Ehime',33.839,132.765,2,'0.50M','¥85K/m²'],
  ['Kochi','高知','Kochi',33.559,133.531,2,'0.32M','¥72K/m²'],
  // Kyushu
  ['Kitakyushu','北九州','Fukuoka',33.883,130.879,2.5,'0.94M','¥130K/m²'],
  ['Fukuoka','福岡','Fukuoka',33.590,130.401,3,'1.6M','¥193K/m²'],
  ['Kurume','久留米','Fukuoka',33.319,130.508,1.5,'0.31M','¥115K/m²'],
  ['Saga','佐賀','Saga',33.249,130.299,1.5,'0.23M','¥72K/m²'],
  ['Sasebo','佐世保','Nagasaki',33.181,129.715,1.5,'0.25M','¥65K/m²'],
  ['Nagasaki','長崎','Nagasaki',32.751,129.877,2,'0.41M','¥78K/m²'],
  ['Kumamoto','熊本','Kumamoto',32.803,130.742,2.5,'0.73M','¥135K/m²'],
  ['Oita','大分','Oita',33.238,131.612,2,'0.48M','¥88K/m²'],
  ['Miyazaki','宮崎','Miyazaki',31.911,131.424,2,'0.40M','¥75K/m²'],
  ['Kagoshima','鹿児島','Kagoshima',31.560,130.558,2,'0.60M','¥85K/m²'],
  // Extra coastal/detail cities
  ['Nemuro','根室','Hokkaido',43.330,145.583,1,'',''],
  ['Abashiri','網走','Hokkaido',44.021,144.274,1,'0.04M','¥40K/m²'],
  ['Rumoi','留萌','Hokkaido',43.935,141.636,1,'',''],
  ['Otaru','小樽','Hokkaido',43.190,140.994,1.5,'0.11M','¥85K/m²'],
  ['Muroran','室蘭','Hokkaido',42.315,140.974,1.5,'0.08M','¥55K/m²'],
  ['Aomori-N','むつ','Aomori',41.293,141.182,1,'',''],
  ['Miyako','宮古','Iwate',39.641,141.956,1,'',''],
  ['Kesennuma','気仙沼','Miyagi',38.907,141.571,1,'',''],
  ['Ishinomaki','石巻','Miyagi',38.432,141.303,1.5,'0.14M','¥62K/m²'],
  ['Wajima','輪島','Ishikawa',37.390,136.900,1,'',''],
  ['Toyooka','豊岡','Hyogo',35.544,134.818,1,'',''],
  ['Tottori-W','米子','Tottori',35.428,133.330,1.5,'0.15M','¥72K/m²'],
  ['Hamada','浜田','Shimane',34.899,132.079,1,'',''],
  ['Iwakuni','岩国','Yamaguchi',34.166,132.219,1,'',''],
  ['Tokuyama','周南','Yamaguchi',34.054,131.865,1,'',''],
  ['Ube','宇部','Yamaguchi',33.952,131.246,1.5,'0.17M','¥65K/m²'],
  ['Imabari','今治','Ehime',34.066,132.998,1.5,'0.16M','¥75K/m²'],
  ['Uwajima','宇和島','Ehime',33.223,132.560,1,'',''],
  ['Nobeoka','延岡','Miyazaki',32.583,131.667,1,'0.12M','¥62K/m²'],
  ['Minamata','水俣','Kumamoto',32.213,130.409,1,'',''],
  ['Nagasaki-N','佐世保N','Nagasaki',33.745,129.869,1,'',''],
  ['Goto','五島','Nagasaki',32.700,128.836,1,'',''],
];

const B = {{ xMin:.200, xMax:.980, yMin:.029, yMax:.671 }};
let W, H, scale, offX, offY, LINK_D, particles = [], nearest = null;
const flashes = [];

function proj(nx, ny) {{ return [nx*scale+offX, ny*scale+offY]; }}
function ll(lat, lon)  {{ return proj((lon-123)/23, (46-lat)/22); }}

function setup() {{
  W = canvas.width  = window.innerWidth;
  H = canvas.height = {height};
  // Fit Japan to fill the canvas — constrained by whichever axis runs out first
  const scaleH = (H * 0.78) / (B.yMax - B.yMin);
  const scaleW = (W * 0.50) / (B.xMax - B.xMin);
  scale = Math.min(scaleH, scaleW);
  offX   = (W - (B.xMax-B.xMin)*scale) / 2 - B.xMin*scale - W*0.01;
  offY   = H * 0.08 - B.yMin*scale;
  LINK_D = scale * 0.13;

  particles = CITIES.map(([en,ja,pref,lat,lon,s,pop,price]) => {{
    const [x,y] = ll(lat,lon);
    // radius proportional to city size (s=1 small town, s=3 major city)
    const r = 1.0 + (s - 1) * 1.4;
    // transaction weight = population in millions (proxy for deal volume)
    const txw = pop ? parseFloat(pop) : 0.08;
    return {{ x,y,ox:x,oy:y, vx:(Math.random()-.5)*.25, vy:(Math.random()-.5)*.25,
             r, txw, en,ja,pref,pop,price }};
  }});
}}
setup();
window.addEventListener('resize', setup);

// ── Transaction ticker ────────────────────────────────────────────────────────
const PROP_TYPES  = ['Used Apartment','Residential Land','Pre-owned Condo','Used House','Land Only'];
const APT_LAYOUTS = ['1K','1DK','1LDK','2DK','2LDK','2LDK','3LDK'];
const HSE_LAYOUTS = ['3LDK','3LDK','4LDK','4SLDK'];
const LAND_TYPES  = new Set(['Residential Land','Land Only']);
const MAX_ROWS   = 5;
const tickerRows = document.getElementById('ticker-rows');

function addTickerRow(p) {{
  // Parse price per m² from city data (e.g. "¥863K/m²" → 863000)
  const rawPrice = p.price || '¥100K/m²';
  const match = rawPrice.match(/([\d.]+)K/);
  const ppm2 = match ? parseFloat(match[1]) * 1000 : 100000;

  // Generate realistic area based on city tier
  const isLarge = p.r > 2;
  const area = isLarge
    ? Math.round(30 + Math.random() * 70)   // 30-100 m² apartments
    : Math.round(60 + Math.random() * 140);  // 60-200 m² land/house

  const totalM = (ppm2 * area / 1e6);
  const priceStr = totalM >= 100
    ? `¥${{Math.round(totalM/10)*10}}M`
    : `¥${{totalM.toFixed(1)}}M`;

  const type   = PROP_TYPES[Math.floor(Math.random() * PROP_TYPES.length)];
  const txId   = '#' + String(Math.floor(10000 + Math.random() * 90000));
  const isLand = LAND_TYPES.has(type);
  const isHouse= type === 'Used House';
  const layout = isLand ? '' : isHouse
    ? HSE_LAYOUTS[Math.floor(Math.random() * HSE_LAYOUTS.length)]
    : APT_LAYOUTS[Math.floor(Math.random() * APT_LAYOUTS.length)];
  const ppm2k  = Math.round(ppm2 / 1000);
  const ppm2Str= `¥${{ppm2k}}k`;
  const yearBuilt = isLand ? '' : String(Math.floor(
    isHouse ? 1968 + Math.random() * 45 : 1975 + Math.random() * 45
  ));

  const row = document.createElement('div');
  row.className = 'tk-row';
  row.innerHTML = `
    <span class="tk-cell" style="color:rgba(120,160,220,.40);font-size:8px">${{txId}}</span>
    <span class="tk-cell">${{p.en}}</span>
    <span class="tk-cell">${{type}}</span>
    <span class="tk-cell">${{layout}}</span>
    <span class="tk-cell">${{area}} m²</span>
    <span class="tk-cell">${{ppm2Str}}</span>
    <span class="tk-cell">${{priceStr}}</span>
    <span class="tk-cell">${{yearBuilt}}</span>
  `;

  // Remove oldest if at limit (before insert to keep height stable)
  if(tickerRows.children.length >= MAX_ROWS) {{
    tickerRows.removeChild(tickerRows.lastChild);
  }}
  tickerRows.insertBefore(row, tickerRows.firstChild);
}}

// ── Transaction flash simulation ──────────────────────────────────────────────
function triggerFlash() {{
  if(!particles.length) return;
  // Weight flash probability by population (proxy for transaction volume)
  const w = particles.map(p => p.txw);
  const total = w.reduce((a,b)=>a+b, 0);
  let rnd = Math.random() * total;
  let idx = 0;
  for(let i=0; i<w.length; i++) {{ rnd -= w[i]; if(rnd<=0){{idx=i;break;}} }}
  flashes.push({{idx, a:0, dir:1, age:0}});
  addTickerRow(particles[idx]);
}}
// Random interval 150-700ms — feels organic, never metronomic
function scheduleFlash() {{
  triggerFlash();
  setTimeout(scheduleFlash, 200 + Math.random() * 800);
}}
setTimeout(scheduleFlash, 300);

let mx=-9999, my=-9999;
document.addEventListener('mousemove', e => {{
  const r = canvas.getBoundingClientRect();
  mx = e.clientX-r.left; my = e.clientY-r.top;
  let best=null, bestD=60;
  particles.forEach(p => {{
    const d=Math.hypot(p.x-mx,p.y-my);
    if(d<bestD){{bestD=d;best=p;}}
  }});
  nearest = best;
  if(best){{
    document.getElementById('t-en').textContent = best.en;
    document.getElementById('t-ja').textContent = best.ja;
    document.getElementById('t-pf').textContent = best.pref + ' Prefecture';

    // City tier label from radius
    const tierLbl = best.r >= 3.8 ? 'Major City'
                  : best.r >= 3.1 ? 'Large City'
                  : best.r >= 2.4 ? 'City'
                  : best.r >= 1.7 ? 'Town'
                  : 'Small Town';
    document.getElementById('t-tier-lbl').textContent = tierLbl;

    // Population
    const popEl = document.getElementById('t-pop');
    if(best.pop) {{
      const parts = best.pop.split('M');
      popEl.innerHTML = `<span class="t-stat-num">${{best.pop}}</span>`;
    }} else {{
      popEl.innerHTML = '<span class="t-stat-num" style="color:rgba(150,200,255,.25)">n/a</span>';
    }}

    // Price + tier dots
    const priceEl = document.getElementById('t-price');
    const dotsEl  = document.getElementById('t-dots');
    if(best.price) {{
      const raw = parseFloat(best.price.replace('¥','').replace('K/m²',''));
      const tier = raw > 400 ? 5 : raw > 180 ? 4 : raw > 100 ? 3 : raw > 60 ? 2 : 1;
      const clean = best.price.replace('/m²','');
      priceEl.innerHTML = `<span class="t-stat-num">${{clean}}</span><span class="t-stat-unit">/m²</span>`;
      dotsEl.innerHTML  = [1,2,3,4,5].map(i=>`<div class="td ${{i<=tier?'on':'off'}}"></div>`).join('');
    }} else {{
      priceEl.innerHTML = '<span class="t-stat-num" style="color:rgba(150,200,255,.25)">n/a</span>';
      dotsEl.innerHTML  = '';
    }}

    tip.style.display='block';
    const tx = mx+16+260>W ? mx-266 : mx+16;
    const ty = my-110<0    ? my+10  : my-110;
    tip.style.left=tx+'px'; tip.style.top=ty+'px';
  }}else{{
    tip.style.display='none';
  }}
}});
document.addEventListener('mouseleave',()=>{{mx=-9999;my=-9999;nearest=null;tip.style.display='none';}});

function animate(){{
  ctx.clearRect(0,0,W,H);


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

  // ── Base dots ────────────────────────────────────────────────────────────────
  particles.forEach(p=>{{
    const hot = (p === nearest);
    if(hot){{
      ctx.beginPath();ctx.arc(p.x,p.y,p.r+8,0,Math.PI*2);
      ctx.strokeStyle='rgba(100,200,255,0.90)';
      ctx.lineWidth=1.5;
      ctx.shadowColor='rgba(80,180,255,0.55)';
      ctx.shadowBlur=14;
      ctx.stroke();
      ctx.beginPath();ctx.arc(p.x,p.y,p.r+3,0,Math.PI*2);
      ctx.fillStyle='rgba(100,200,255,0.12)';
      ctx.fill();
      ctx.shadowBlur=0;
    }}
    ctx.beginPath();ctx.arc(p.x,p.y,hot?p.r*1.6:p.r,0,Math.PI*2);
    if(hot){{
      ctx.shadowColor='rgba(160,220,255,0.95)';ctx.shadowBlur=22;
      ctx.fillStyle='rgba(255,255,255,0.95)';
    }}else{{
      ctx.shadowColor='transparent';ctx.shadowBlur=0;
      ctx.fillStyle='rgba(175,215,255,.72)';
    }}
    ctx.fill();
  }});
  ctx.shadowBlur=0;

  // ── Transaction flashes ───────────────────────────────────────────────────────
  for(let i=flashes.length-1; i>=0; i--){{
    const f=flashes[i];
    f.age += 1;
    if(f.dir===1){{ f.a+=0.04; if(f.a>=1){{f.a=1;f.dir=-1;}} }}
    else          {{ f.a-=0.012; }}
    if(f.a<=0){{ flashes.splice(i,1); continue; }}
    const p=particles[f.idx];
    // Ring always expands outward using age
    const ring = p.r + f.age * 0.28;
    ctx.beginPath();ctx.arc(p.x,p.y,ring,0,Math.PI*2);
    ctx.strokeStyle=`rgba(120,230,255,${{f.a*0.70}})`;
    ctx.lineWidth=1.5;
    ctx.shadowColor=`rgba(80,200,255,${{f.a*0.45}})`;
    ctx.shadowBlur=14;
    ctx.stroke();
    // Bright dot flash
    ctx.beginPath();ctx.arc(p.x,p.y,p.r*(1+f.a*0.40),0,Math.PI*2);
    ctx.fillStyle=`rgba(220,245,255,${{f.a*0.75}})`;
    ctx.shadowColor=`rgba(160,230,255,${{f.a*0.85}})`;
    ctx.shadowBlur=14+f.a*8;
    ctx.fill();
    ctx.shadowBlur=0;
  }}
  requestAnimationFrame(animate);
}}
animate();

</script>
</body>
</html>"""


# ── Render hero ────────────────────────────────────────────────────────────────
stats = _headline_stats()
components.html(_build_hero(stats, height=580), height=580, scrolling=False)

footer("Home", "MLIT XIT001 API · Japan Housing and Land Survey · Statistics Bureau")
