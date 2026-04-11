"""
Tokyo 23 Special Wards — reference data.

Contains:
- Ward metadata (name in English + Japanese, centroid lat/lon, population)
- Base price/m² by ward (modeled after MLIT public statistics 2023-2024
  for used apartments / 中古マンション)
- Activity weights (transaction volume distribution)

Sources (for the modeling, not live API):
- MLIT Real Estate Information Library public aggregates
- Tokyo Metropolitan Government Statistical Yearbook
- REINS Tokyo market reports (公益社団法人 東日本不動産流通機構)
"""

# Ward metadata: english name, japanese name, centroid (lat, lon), population (thousands)
# Base price/m² is in JPY (for used apartments, 2023 baseline)
# Activity weight is the relative share of transactions (sums to 1.0)

TOKYO_WARDS = {
    "Chiyoda":    {"ja": "千代田区", "lat": 35.6940, "lon": 139.7535, "pop": 67,   "base_price": 1420000, "activity": 0.018},
    "Chuo":       {"ja": "中央区",   "lat": 35.6706, "lon": 139.7720, "pop": 172,  "base_price": 1320000, "activity": 0.045},
    "Minato":     {"ja": "港区",     "lat": 35.6581, "lon": 139.7514, "pop": 260,  "base_price": 1610000, "activity": 0.062},
    "Shinjuku":   {"ja": "新宿区",   "lat": 35.6939, "lon": 139.7037, "pop": 346,  "base_price": 1080000, "activity": 0.061},
    "Bunkyo":     {"ja": "文京区",   "lat": 35.7081, "lon": 139.7524, "pop": 240,  "base_price": 1180000, "activity": 0.035},
    "Taito":      {"ja": "台東区",   "lat": 35.7127, "lon": 139.7799, "pop": 212,  "base_price": 950000,  "activity": 0.028},
    "Sumida":     {"ja": "墨田区",   "lat": 35.7107, "lon": 139.8015, "pop": 279,  "base_price": 810000,  "activity": 0.034},
    "Koto":       {"ja": "江東区",   "lat": 35.6731, "lon": 139.8170, "pop": 524,  "base_price": 900000,  "activity": 0.058},
    "Shinagawa":  {"ja": "品川区",   "lat": 35.6092, "lon": 139.7303, "pop": 417,  "base_price": 1090000, "activity": 0.049},
    "Meguro":     {"ja": "目黒区",   "lat": 35.6338, "lon": 139.7152, "pop": 283,  "base_price": 1290000, "activity": 0.038},
    "Ota":        {"ja": "大田区",   "lat": 35.5613, "lon": 139.7161, "pop": 741,  "base_price": 760000,  "activity": 0.071},
    "Setagaya":   {"ja": "世田谷区", "lat": 35.6465, "lon": 139.6528, "pop": 940,  "base_price": 910000,  "activity": 0.092},
    "Shibuya":    {"ja": "渋谷区",   "lat": 35.6618, "lon": 139.7041, "pop": 230,  "base_price": 1420000, "activity": 0.042},
    "Nakano":     {"ja": "中野区",   "lat": 35.7074, "lon": 139.6636, "pop": 346,  "base_price": 820000,  "activity": 0.039},
    "Suginami":   {"ja": "杉並区",   "lat": 35.6994, "lon": 139.6364, "pop": 591,  "base_price": 810000,  "activity": 0.056},
    "Toshima":    {"ja": "豊島区",   "lat": 35.7264, "lon": 139.7161, "pop": 301,  "base_price": 920000,  "activity": 0.037},
    "Kita":       {"ja": "北区",     "lat": 35.7528, "lon": 139.7337, "pop": 356,  "base_price": 720000,  "activity": 0.032},
    "Arakawa":    {"ja": "荒川区",   "lat": 35.7362, "lon": 139.7834, "pop": 219,  "base_price": 760000,  "activity": 0.021},
    "Itabashi":   {"ja": "板橋区",   "lat": 35.7512, "lon": 139.7093, "pop": 584,  "base_price": 660000,  "activity": 0.048},
    "Nerima":     {"ja": "練馬区",   "lat": 35.7356, "lon": 139.6518, "pop": 752,  "base_price": 660000,  "activity": 0.057},
    "Adachi":     {"ja": "足立区",   "lat": 35.7749, "lon": 139.8044, "pop": 694,  "base_price": 510000,  "activity": 0.049},
    "Katsushika": {"ja": "葛飾区",   "lat": 35.7436, "lon": 139.8472, "pop": 466,  "base_price": 550000,  "activity": 0.033},
    "Edogawa":    {"ja": "江戸川区", "lat": 35.7066, "lon": 139.8683, "pop": 697,  "base_price": 600000,  "activity": 0.045},
}

# Major train lines / representative stations per ward (for richer analytics)
WARD_MAIN_STATIONS = {
    "Chiyoda":    ["Tokyo", "Otemachi", "Kasumigaseki"],
    "Chuo":       ["Ginza", "Nihonbashi", "Tsukiji"],
    "Minato":     ["Roppongi", "Azabu-Juban", "Shinagawa"],
    "Shinjuku":   ["Shinjuku", "Shinjuku-Sanchome", "Takadanobaba"],
    "Bunkyo":     ["Korakuen", "Hongo-Sanchome", "Myogadani"],
    "Taito":      ["Ueno", "Asakusa", "Okachimachi"],
    "Sumida":     ["Kinshicho", "Oshiage", "Ryogoku"],
    "Koto":       ["Toyosu", "Monzen-Nakacho", "Kiba"],
    "Shinagawa":  ["Osaki", "Gotanda", "Oimachi"],
    "Meguro":     ["Nakameguro", "Jiyugaoka", "Meguro"],
    "Ota":        ["Kamata", "Omori", "Heiwajima"],
    "Setagaya":   ["Shimokitazawa", "Sangenjaya", "Futako-Tamagawa"],
    "Shibuya":    ["Shibuya", "Ebisu", "Harajuku"],
    "Nakano":     ["Nakano", "Higashi-Nakano", "Araiyakushi-mae"],
    "Suginami":   ["Ogikubo", "Koenji", "Asagaya"],
    "Toshima":    ["Ikebukuro", "Mejiro", "Otsuka"],
    "Kita":       ["Akabane", "Oji", "Tabata"],
    "Arakawa":    ["Nippori", "Machiya", "Minowa"],
    "Itabashi":   ["Itabashi", "Narimasu", "Tokiwadai"],
    "Nerima":     ["Nerima", "Hikarigaoka", "Oizumi-Gakuen"],
    "Adachi":     ["Kita-Senju", "Ayase", "Takenotsuka"],
    "Katsushika": ["Kameari", "Aoto", "Kanamachi"],
    "Edogawa":    ["Nishi-Kasai", "Koiwa", "Kasai"],
}

PROPERTY_TYPES = [
    "Used Apartment",   # 中古マンション
    "Used House",       # 中古戸建
    "New House",        # 新築戸建
    "Land Only",        # 宅地(土地)
]

# Share of each property type in Tokyo market (2023 approximation)
PROPERTY_TYPE_WEIGHTS = {
    "Used Apartment": 0.58,
    "Used House":     0.18,
    "New House":      0.10,
    "Land Only":      0.14,
}

LAYOUTS = ["1R", "1K", "1DK", "1LDK", "2DK", "2LDK", "3DK", "3LDK", "4LDK"]

# Layout distribution (shifts by property type downstream)
LAYOUT_WEIGHTS_APARTMENT = [0.08, 0.12, 0.06, 0.22, 0.05, 0.24, 0.03, 0.17, 0.03]

def get_ward_list():
    """Return list of ward names (English)."""
    return list(TOKYO_WARDS.keys())

def get_ward_info(name):
    return TOKYO_WARDS[name]
