"""Step 1. The pits: every deep coal mine working in Great Britain at the start of 1984, when each closed, and where it was.

Reads (in place):
  data/nmrs_extract.csv            collieries closed in 1984 or later, from the Northern Mine Research Society's tables
                                   "NCB Collieries" for England, Wales and Scotland (nmrs.org.uk, read 28 October 2026;
                                   see README for how this extract was made and its caveats)
  _data12/wikipedia_batch12.json.gz  English Wikipedia (CC BY-SA 4.0): List of collieries in Yorkshire (1984 to 2015),
                                   List of collieries in Derbyshire, List of coal mines in the United Kingdom,
                                   List of collieries in the Rhondda Valleys, and colliery articles (for years and checks)
  _data12/wd_osm_bundle12.json.gz  OpenStreetMap features named as collieries (ODbL) and Wikidata mines (CC0)
  osnames_gb.tsv                   OS Open Names (OGL v3), to place a pit at its village when no mapped colliery is found

Writes:
  data/pits_1984.csv     one row per colliery unit: name, area, village, closure year (and the alternative year where
                         the sources differ), coordinates and how they were found
  data/_pit_stats.json   matching and agreement statistics

Rules
  Closure year: where an on-disk Wikipedia list gives a plain year for the pit, that year (Wikipedia is open and
  checkable); otherwise the NMRS year. Both are kept (closed_year, nmrs_year).
  Location: (1) an OpenStreetMap feature whose name is the pit's name followed by Colliery, Pit, Mine or Drift
  (railway branches, junctions, roads and institutes excluded) within 12 km of the pit's village; (2) a Wikidata
  mine item with a matching label within 12 km; (3) the village itself in OS Open Names.
"""
import csv
import gzip
import json
import math
import os
import re
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = "/home/claude/hist"
D = os.path.join(ROOT, "data")
KX, KY = 111.32 * math.cos(math.radians(54.0)), 110.57


def km(a, b):
    return math.hypot((a[0] - b[0]) * KX, (a[1] - b[1]) * KY)


WP = json.load(gzip.open(f"{H}/_data12/wikipedia_batch12.json.gz"))["articles"]


def cells(tbl):
    """Rows of a simple wikitable as lists of cell strings."""
    rows = []
    for chunk in re.split(r"\n\|-+", tbl)[1:]:
        cs = [c.strip() for c in re.split(r"\n\|", "\n" + chunk.strip()) if c.strip()]
        cs = [c.lstrip("|").strip() for c in cs]
        if cs and not cs[0].startswith("}"):
            rows.append(cs)
    return rows


def plain(s):
    s = re.sub(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>", "", s)
    s = re.sub(r"\[\[([^|\]]*\|)?([^\]]*)\]\]", r"\2", s)
    return re.sub(r"\s+", " ", s).strip()


def link(s):
    m = re.search(r"\[\[([^|\]]+)", s)
    return m.group(1) if m else ""


# ---------------------------------------------------------------- Wikipedia: Yorkshire 1984 to 2015 (complete for Yorkshire)
yt = WP["List of collieries in Yorkshire (1984–2015)"]["text"]
york = []
for r in cells(yt[yt.index("{|"):yt.index("|}")]):
    if len(r) >= 3 and re.match(r"\d{4}", plain(r[2])):
        york.append({"name": plain(r[0]), "district": plain(r[1]), "year": int(plain(r[2])[:4]),
                     "note": plain(r[3]) if len(r) > 3 else "", "article": link(r[0])})
print("Yorkshire list rows", len(york))  # the list intro says 56 collieries in 1984; the table has 58 rows
# Derbyshire: plain closure years (not "merged")
dt = WP["List of collieries in Derbyshire"]["text"]
derby = {}
for r in cells(dt[dt.index("{|"):dt.rindex("|}")]):
    if len(r) >= 4 and re.fullmatch(r"\d{4}", plain(r[3])):
        derby[plain(r[0])] = int(plain(r[3]))
# List of coal mines in the United Kingdom: earlier table, plain closure years
ut = WP["List of coal mines in the United Kingdom"]["text"]
ukl = {}
for line in ut.split("\n"):
    if line.startswith("|") and "||" in line:
        c = [plain(x) for x in line.lstrip("|").split("||")]
        if len(c) >= 4 and re.fullmatch(r"\d{4}", c[3].strip()):
            ukl[re.sub(r" Colliery$", "", c[0])] = int(c[3])
for nm, y in (("Daw Mill", 2013), ("Clipstone", 2003), ("Hatfield", 2015), ("Kellingley", 2015), ("Maltby Main", 2013), ("Thoresby", 2015)):
    assert nm in ut
    ukl[nm] = y  # 21st century table: "Closed <date> <year>" (checked against the text above)

# ---------------------------------------------------------------- NMRS extract and merge
nm_rows = list(csv.DictReader(open(os.path.join(D, "nmrs_extract.csv"), encoding="utf-8")))
YMAP = {"Cadeby & Denaby": "Cadeby", "Darfield": "Darfield Main", "Emley, West Yorkshire": "Emley Moor", "Ferrymoor/Riddings": "Ferrymoor Riddings",
        "Frickley/South Elmsall": "Frickley-South Elmsall", "Gascoigne Wood": "Gascoigne Wood Drift", "Goldthorpe": "Goldthorpe-Highgate",
        "Hickleton Main": "Hickleton", "Kinsley": "Kinsley Drift", "Manvers Main": "Manvers", "Sharlston": "Sharlston New"}
nmrs_by = {(r["country"], r["name"]): r for r in nm_rows}
pits = []
used = set()
# Yorkshire villages for the Wikipedia rows (from the list's notes or links; else the NMRS town)
YVILL = {"Ackton Hall": "Featherstone", "Barnsley Main": "Barnsley", "Bullcliffe Wood": "Netherton", "Caphouse": "Overton",
         "Denby Grange": "Netherton", "Ferrymoor/Riddings": "South Kirkby", "Hickleton Main": "Thurnscoe", "Highgate Colliery": "Highgate",
         "Houghton Main": "Little Houghton", "Ledston Luck": "Ledston", "Park Mill": "Clayton West", "Prince of Wales": "Pontefract",
         "Savile": "Methley", "Wheldale": "Castleford", "Yorkshire Main": "New Edlington", "Glasshoughton": "Castleford", "Fryston": "Airedale", "Nostell": "Crofton", "Cortonwood": "Brampton", "North Gawber": "Mapplewell"}
for y in york:
    key = YMAP.get(y["name"], y["name"])
    n = nmrs_by.get(("England", key))
    if n:
        used.add(("England", key))
    vill = YVILL.get(y["name"]) or (n["town"] if n else re.sub(r",.*", "", y["article"] or y["name"]))
    pits.append({"name": re.sub(r",.*", "", y["name"]).replace("/", " and ").replace(" Colliery", ""), "country": "England", "area": "Yorkshire",
                 "district": y["district"], "village": vill, "closed_year": y["year"], "nmrs_year": int(n["closed_year"]) if n else "",
                 "closed_month": n["closed_month"] if n else "", "year_source": "Wikipedia (Yorkshire list)",
                 "note": y["note"], "article": y["article"]})
for r in nm_rows:
    if (r["country"], r["name"]) in used:
        continue
    yr, src = int(r["closed_year"]), "NMRS"
    alt = None
    for cand in (r["name"], r["name"] + " Main"):
        if r["county"] == "Derbyshire" or r["name"] in ("Pleasley", "Shirebrook", "Cadley Hill"):
            alt = derby.get(cand, alt)
        alt = ukl.get(cand, alt)
    if r["name"] == "Silverdale":
        alt = ukl.get("Silverdale, Staffordshire|Silverdale Colliery") or 1998  # UK list row "Silverdale Colliery ... 1998"
        assert "Silverdale Colliery]] || Staffordshire || (?) || 1998" in ut
    if alt:
        yr, src = alt, "Wikipedia (Derbyshire or UK list)"
    pits.append({"name": r["name"], "country": r["country"], "area": "Yorkshire" if r["county"] == "Yorkshire" else r["county"],
                 "district": "", "village": r["town"], "closed_year": yr, "nmrs_year": int(r["closed_year"]), "closed_month": r["closed_month"],
                 "year_source": src, "note": r["note"], "article": ""})
# Golborne (Lancashire): in the UK list (closed 1989), not in the NMRS extract
assert "Golborne Colliery" in ut and "|| Lancashire || 1860s || 1989 ||" in ut
pits.append({"name": "Golborne", "country": "England", "area": "Lancashire", "district": "", "village": "Golborne", "closed_year": 1989,
             "nmrs_year": "", "closed_month": "", "year_source": "Wikipedia (UK list)", "note": "not in the NMRS extract", "article": "Golborne"})
# Highgate (Yorkshire list says merged with Goldthorpe in 1968, closed 1985): keep, it is in the 1984 list
print("pits:", len(pits))

# year agreement where both sources give a year
agree = Counter()
for p in pits:
    if p["nmrs_year"] != "" and p["year_source"] != "NMRS":
        d = abs(p["closed_year"] - p["nmrs_year"])
        agree["exact" if d == 0 else "1yr" if d == 1 else "more"] += 1
print("year agreement", agree)

# ---------------------------------------------------------------- places
osn = defaultdict(list)
with open(f"{H}/osnames_gb.tsv", encoding="utf-8") as f:
    rd = csv.reader(f, delimiter="\t")
    hdr = next(rd)
    for r in rd:
        if r[4] == "populatedPlace":
            for nm in (r[0], r[2]):
                if nm:
                    osn[nm.lower()].append((float(r[7]), float(r[6]), r[5], r[12]))
# rough anchors for each area, only to choose between places of the same name (not used as coordinates)
ANCH = {"Yorkshire": (-1.35, 53.55), "Nottinghamshire": (-1.15, 53.12), "Derbyshire": (-1.3, 53.2), "Durham": (-1.45, 54.78),
        "Northumberland": (-1.6, 55.15), "Kent": (1.25, 51.22), "Lancashire": (-2.55, 53.5), "Leicestershire": (-1.4, 52.73),
        "Staffordshire": (-2.0, 52.85), "Warwickshire": (-1.6, 52.5), "Cumberland": (-3.55, 54.55), "Carmarthenshire": (-4.05, 51.8),
        "Flintshire": (-3.2, 53.2), "Glamorgan": (-3.5, 51.65), "Monmouthshire": (-3.15, 51.7), "Ayrshire": (-4.4, 55.45),
        "Fife": (-3.4, 56.1), "Midlothian": (-3.1, 55.88), "Stirlingshire": (-3.9, 56.08), "West Lothian": (-3.65, 55.87)}
FIX = {}
RANK = {"City": 0, "Town": 1, "Village": 2, "Suburban Area": 3, "Hamlet": 4, "Other Settlement": 5}


def place(v, area):
    v = FIX.get(v, v)
    c = osn.get(v.lower()) or osn.get(v.lower().replace("-", " ")) or osn.get(v.lower().replace(" upon ", "-upon-"))
    if not c:
        return None
    a = ANCH[area]
    c = [x for x in c if km(x[:2], a) < 60] or c
    return min(c, key=lambda x: (km(x[:2], a) // 25, RANK.get(x[2], 9)))


# OSM colliery features (name = pit name + Colliery/Pit/Mine/Drift)
B = json.load(gzip.open(f"{H}/_data12/wd_osm_bundle12.json.gz"))["results"]
osm = []
BAD = re.compile(r"branch|junction|line|road|lane|street|institute|inn|arms|halt|station|farm|terrace|row|cottage|hotel|club|band|signal|sidings|tip|reservoir|pond|school|chapel|plantation|wood\b|close|avenue|drive|way\b|crescent|bridge|path|trail|incline|tramway|railway|f\.?c\.?|football|cricket|welfare|park\b|estate|houses|memorial|bus|dock|substation|cabinet", re.I)
for l in B["osm_collieries"]["tsv"].split("\n")[1:]:
    f = l.split("\t")
    if len(f) < 11 or not f[1]:
        continue
    nm = f[1].strip('"')
    if not re.search(r"(colliery|pit|mine|drift|main)(\s*\(.*\))?$", nm, re.I) or BAD.search(nm):
        continue
    pts = re.findall(r"(-?\d+\.\d+) (-?\d+\.\d+)", f[10])
    if not pts:
        continue
    lon = sum(float(p[0]) for p in pts) / len(pts)
    lat = sum(float(p[1]) for p in pts) / len(pts)
    osm.append((nm, lon, lat, f[0].strip("<>")))
wd = {}
for l in B["wd_mines"]["tsv"].split("\n")[1:]:
    f = l.split("\t")
    if len(f) >= 3 and f[2].startswith("POINT"):
        lon, lat = map(float, f[2][6:-1].split())
        if '"' in f[1]:
            wd[f[0]] = (f[1].split('"')[1], lon, lat)
print("OSM colliery-named features", len(osm), "Wikidata mines with coords", len(wd))


def keys(name):
    n = re.sub(r"\(.*\)", "", name)
    out = {n}
    for part in re.split(r"[-/]| and | & ", n):
        if len(part.strip()) > 3:
            out.add(part.strip())
    out |= {re.sub(r" (Main|Drift|New|Complex|3 and 4)$", "", k) for k in list(out)}
    return {k.strip().lower() for k in out if len(k.strip()) > 3}


geo = Counter()
for p in pits:
    pl = place(p["village"], p["area"])
    p["village_lat"], p["village_lon"] = (round(pl[1], 5), round(pl[0], 5)) if pl else ("", "")
    ks = keys(p["name"])
    best = None
    if pl:
        cand = []
        for nm, lon, lat, oid in osm:
            base = re.sub(r"^(former|site of( the)?|old|disused)\s+", "", nm.lower())
            base = re.sub(r"\s*\(.*\)$", "", base)
            base = re.sub(r"\s+(main\s+)?(colliery|pit|mine|drift)(\s+site)?$", "", base).strip()
            base = re.sub(r"\s+main$", "", base)
            if base in ks and km((lon, lat), pl[:2]) < 12:
                cand.append((km((lon, lat), pl[:2]), lon, lat, nm, oid))
        if cand:
            cand.sort()
            d0, lon, lat, nm, oid = cand[0]
            best = (lon, lat, "osm_colliery", f"{nm} ({oid})")
        else:
            for q, (nm, lon, lat) in wd.items():
                base = re.sub(r"\s+(main\s+)?(colliery|pit|mine|drift)$", "", nm.lower())
                if base in ks and km((lon, lat), pl[:2]) < 12:
                    best = (lon, lat, "wikidata", f"{nm} ({q})")
                    break
        if not best:
            best = (pl[0], pl[1], "village", f"OS Open Names: {p['village']} ({pl[2]}, {pl[3]})")
    if best:
        p["lon"], p["lat"], p["geo_method"], p["geo_source"] = round(best[0], 5), round(best[1], 5), best[2], best[3]
    else:
        p["lon"] = p["lat"] = ""
        p["geo_method"], p["geo_source"] = "unplaced", ""
    geo[p["geo_method"]] += 1
print("placing", geo)
for p in pits:
    if p["geo_method"] == "unplaced":
        print("  UNPLACED", p["name"], p["village"], p["area"])

for p in pits:
    p["wave"] = ("1984 to 1987" if p["closed_year"] <= 1987 else "1988 to 1994" if p["closed_year"] <= 1994 else "1995 to 2015")
    p["pre_strike"] = 1 if p["closed_year"] == 1984 and p["closed_month"] in ("January", "February") else 0
pits.sort(key=lambda p: (p["country"], p["area"], p["name"]))
cols = ["name", "country", "area", "district", "village", "closed_year", "closed_month", "nmrs_year", "year_source", "wave", "pre_strike",
        "lat", "lon", "geo_method", "geo_source", "village_lat", "village_lon", "note", "article"]
with open(os.path.join(D, "pits_1984.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(pits)
json.dump({"n_pits": len(pits), "n_york_wiki": len(york), "n_nmrs_rows": len(nm_rows), "year_agreement": agree, "placing": geo,
           "n_osm_named": len(osm), "n_wd_mines": len(wd)}, open(os.path.join(D, "_pit_stats.json"), "w"), indent=1)
