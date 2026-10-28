"""Step 2. Towns: built-up areas (BUA22), their pits, and their Census 2021 profile.

Reads (in place):
  data/pits_1984.csv                 from step 1
  _data12/wd_osm_bundle12.json.gz    OpenStreetMap features named as collieries (ODbL), Wikidata mines (CC0): older pits
  _data8/ons_geo.json                BUA22 centroids and areas, MSOA21 to BUA22 lookup (OGL v3)
  _data8/lsoa21_bua22_lookup.json    LSOA21 to BUA22 best-fit lookup (OGL v3)
  _data8/census/census2021-ts001-lsoa.csv, _data11/census/census2021-{ts007a,ts045,ts062,ts066}-lsoa.csv  (OGL v3)
  _data8/ons_msoa_income_fye2023.xlsx  ONS small area income estimates FYE2023 (OGL v3)

Writes:
  data/towns.csv          every built-up area in Great Britain: its 1984 pits and their closure years, its group, and for
                          England and Wales its 2021 residents, age, car, work, inactivity, sickness, class and income
  data/old_collieries.csv colliery sites named in OpenStreetMap or Wikidata that are not in the 1984 list (older pits)

Pit group (main rule: a pit counts for a town if it lies within 3 km of the area's centre, or within 2 km beyond the
edge of a circle with the same area as the town if that reaches further; checks use 2 km or 1 km beyond the edge, and
5 km or 3 km beyond the edge):
  pit      at least one deep mine that was working at the start of 1984 within reach
  near     no 1984 pit within reach, but one within 10 km beyond the edge (coalfield neighbours; left out of the main
           comparison because they may share the pits' labour market)
  older    none of the above, but a colliery named in OpenStreetMap or Wikidata within reach (pits that closed before
           1984, or small mines): a separate group
  none     none of these: the comparison towns
"""
import csv
import gzip
import json
import math
import os
import re
from collections import Counter, defaultdict

import numpy as np
import openpyxl
from scipy.spatial import cKDTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = "/home/claude/hist"
OUT = os.path.join(ROOT, "data")
KX, KY = 111.32 * math.cos(math.radians(54.0)), 110.57

pits = [r for r in csv.DictReader(open(os.path.join(OUT, "pits_1984.csv"), encoding="utf-8")) if r["lat"]]
for r in pits:
    r["y"] = int(r["closed_year"])
ptree = cKDTree(np.array([(float(r["lon"]) * KX, float(r["lat"]) * KY) for r in pits]))

# ---------------------------------------------------------------- older collieries (OSM names, Wikidata labels)
B = json.load(gzip.open(f"{H}/_data12/wd_osm_bundle12.json.gz"))["results"]
BAD = re.compile(r"branch|junction|line|road|lane|street|institute|inn|arms|halt|station|farm|terrace|row|cottage|hotel|club|band|signal|sidings|tip|reservoir|pond|school|chapel|plantation|wood\b|close|avenue|drive|way\b|crescent|bridge|path|trail|incline|tramway|railway|f\.?c\.?|football|cricket|welfare|park\b|estate|houses|memorial|bus|dock|substation|cabinet|lead|tin|copper|iron|slate|gold|silver|barytes|fluor|ochre|salt|gypsum|jet|stone|quarry", re.I)
old = []
for l in B["osm_collieries"]["tsv"].split("\n")[1:]:
    f = l.split("\t")
    if len(f) < 11 or not f[1]:
        continue
    nm = f[1].strip('"')
    if not re.search(r"(colliery|coal pit|coal mine|pit)(\s*\(.*\))?$", nm, re.I) or BAD.search(nm):
        continue
    pts = re.findall(r"(-?\d+\.\d+) (-?\d+\.\d+)", f[10])
    if pts:
        old.append({"name": nm, "lon": round(sum(float(p[0]) for p in pts) / len(pts), 5), "lat": round(sum(float(p[1]) for p in pts) / len(pts), 5),
                    "source": f[0].strip("<>")})
seen = set()
for l in B["wd_mines"]["tsv"].split("\n")[1:]:
    f = l.split("\t")
    if len(f) >= 3 and f[2].startswith("POINT") and '"' in f[1] and f[0] not in seen:
        nm = f[1].split('"')[1]
        if re.search(r"colliery|coal|pit\b", nm, re.I) and not BAD.search(nm):
            seen.add(f[0])
            lon, lat = map(float, f[2][6:-1].split())
            old.append({"name": nm, "lon": round(lon, 5), "lat": round(lat, 5), "source": f[0].strip("<>")})
# drop those within 1.5 km of a 1984 pit (the same site)
old = [o for o in old if ptree.query((o["lon"] * KX, o["lat"] * KY))[0] > 1.5]
# one point per name per 1 km
ded, otree_pts = [], []
for o in sorted(old, key=lambda o: o["name"]):
    if any(d["name"] == o["name"] and math.hypot((d["lon"] - o["lon"]) * KX, (d["lat"] - o["lat"]) * KY) < 1 for d in ded[-20:]):
        continue
    ded.append(o)
old = ded
with open(os.path.join(OUT, "old_collieries.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["name", "lat", "lon", "source"])
    w.writeheader()
    w.writerows(old)
otree = cKDTree(np.array([(o["lon"] * KX, o["lat"] * KY) for o in old]))
print("older colliery points", len(old))

# ---------------------------------------------------------------- census by LSOA, summed to BUA22 (as in beeching-cuts)
geo = json.load(open(f"{H}/_data8/ons_geo.json", encoding="utf-8"))
lad_rgn = {r["LAD22CD"]: (r["RGN22NM"] or "Wales") for r in geo["msoa21_bua22_lookup"]}
look = json.load(open(f"{H}/_data8/lsoa21_bua22_lookup.json", encoding="utf-8"))
lsoa_bua = {r["LSOA21CD"]: r["BUA22CD"] for r in look if r["BUA22CD"]}
lsoa_lad = {r["LSOA21CD"]: r["LAD22CD"] for r in look}


def read(path, cols):
    out = {}
    with open(path, encoding="utf-8") as f:
        rd = csv.reader(f)
        hdr = next(rd)
        idx = [hdr.index(c) for c in cols]
        for r in rd:
            out[r[2]] = [int(r[i]) for i in idx]
    return out


C = f"{H}/_data11/census"
pop = read(f"{H}/_data8/census/census2021-ts001-lsoa.csv", ["Residence type: Total; measures: Value"])
age_hdr = next(csv.reader(open(f"{C}/census2021-ts007a-lsoa.csv", encoding="utf-8")))
age = read(f"{C}/census2021-ts007a-lsoa.csv", ["Age: Total"] + [h for h in age_hdr if any(k in h for k in ("65 to 69", "70 to 74", "75 to 79", "80 to 84", "85 years"))])
car = read(f"{C}/census2021-ts045-lsoa.csv", ["Number of cars or vans: Total: All households", "Number of cars or vans: No cars or vans in household"])
P = "National Statistics Socio-economic Classification (NS-SEC): "
sec = read(f"{C}/census2021-ts062-lsoa.csv", [P + "Total: All usual residents aged 16 years and over",
                                               P + "L1, L2 and L3 Higher managerial, administrative and professional occupations",
                                               P + "L4, L5 and L6 Lower managerial, administrative and professional occupations",
                                               P + "L12 Semi-routine occupations", P + "L13 Routine occupations", P + "L15 Full-time students"])
E = "Economic activity status: "
eco = read(f"{C}/census2021-ts066-lsoa.csv", [E + "Total: All usual residents aged 16 years and over",
                                               E + "Economically active (excluding full-time students):In employment",
                                               E + "Economically active and a full-time student:In employment",
                                               E + "Economically inactive", E + "Economically inactive: Retired",
                                               E + "Economically inactive: Student",
                                               E + "Economically inactive: Long-term sick or disabled"])
rgn_pop = defaultdict(Counter)
for l, b in lsoa_bua.items():
    if l in pop:
        rgn_pop[b][lad_rgn.get(lsoa_lad[l], "Wales" if l.startswith("W") else "")] += pop[l][0]
NV = 2 + 1 + 2 + 6 + 7
agg = defaultdict(lambda: np.zeros(NV))
for l, b in lsoa_bua.items():
    if l not in pop:
        continue
    a = age[l]
    agg[b] += np.array([pop[l][0], a[0], sum(a[1:]), car[l][0], car[l][1], *sec[l], *eco[l]], dtype=float)

msoa_pop = {}
with open(f"{H}/_data8/census/census2021-ts001-msoa.csv", encoding="utf-8") as f:
    for r in csv.reader(f):
        if r[0] == "2021":
            msoa_pop[r[2]] = int(r[3])
inc = {}
ws = openpyxl.load_workbook(f"{H}/_data8/ons_msoa_income_fye2023.xlsx", read_only=True)["Total annual income"]
for i, r in enumerate(ws.iter_rows(values_only=True)):
    if i >= 4 and r[0] and isinstance(r[6], (int, float)):
        inc[r[0]] = r[6]
iw, ip = defaultdict(float), defaultdict(float)
for r in geo["msoa21_bua22_lookup"]:
    b = r["BUA22CD"]
    if b and r["MSOA21CD"] in inc:
        p = msoa_pop.get(r["MSOA21CD"], 0)
        iw[b] += inc[r["MSOA21CD"]] * p
        ip[b] += p

# ---------------------------------------------------------------- pits near each BUA
bua = [b for b in geo["bua22_gb"] if b["BUA22CD"][0] in "EWS"]
big = np.array([(b["LONG"] * KX, b["LAT"] * KY) for b in bua if agg[b["BUA22CD"]][0] >= 100000])
btree = cKDTree(big)


def classify(b, rad, req):
    p = (b["LONG"] * KX, b["LAT"] * KY)
    pl = [pits[j] for j in ptree.query_ball_point(p, rad)]
    if pl:
        return "pit", pl
    if ptree.query_ball_point(p, req + 10):
        return "near", []
    if otree.query_ball_point(p, rad):
        return "older", []
    return "none", []


rows = []
for b in bua:
    code = b["BUA22CD"]
    req = math.sqrt(b["Shape__Area"] / math.pi) / 1000
    a = agg.get(code)
    r = {"bua22cd": code, "bua22": b["BUA22NM"], "lat": round(b["LAT"], 5), "lon": round(b["LONG"], 5),
         "country": {"E": "England", "W": "Wales", "S": "Scotland"}[code[0]], "radius_km": round(req, 3)}
    if code[0] == "S":
        r["region"] = "Scotland"
    elif a is not None and a[0] > 0:
        r["region"] = rgn_pop[code].most_common(1)[0][0]
        (pop_, at, a65, hh, nocar, st, l13, l46, l12, l13r, l15, et, emp, emps, inact, ret, stud, sick) = a
        ns = st - l15
        r.update(pop2021=int(pop_), pct_65plus=round(a65 / at, 4), pct_no_car=round(nocar / hh, 4) if hh else "",
                 pct_managerial=round((l13 + l46) / ns, 4) if ns else "", pct_routine=round((l12 + l13r) / ns, 4) if ns else "",
                 pct_in_work=round((emp + emps) / et, 4) if et else "", pct_sick=round(sick / et, 4) if et else "",
                 pct_inactive=round(inact / et, 4) if et else "",
                 pct_inactive_working_age=round((inact - ret - stud) / et, 4) if et else "",
                 income_fye2023=round(iw[code] / ip[code]) if ip[code] else "")
    xy = (b["LONG"] * KX, b["LAT"] * KY)
    r["km_to_city100k"] = round(float(btree.query(xy)[0]), 2)
    d, j = ptree.query(xy)
    r["km_to_pit"] = round(float(d), 2)
    r["nearest_pit"] = pits[j]["name"]
    r["nearest_pit_closed"] = pits[j]["y"]
    for tag, base, edge in (("", 3.0, 2.0), ("_tight", 2.0, 1.0), ("_wide", 5.0, 3.0)):
        rad = max(base, req + edge)
        g, pl = classify(b, rad, req)
        r["group" + tag] = g
        if tag == "":
            r["n_pits"] = len(pl)
            r["pits"] = "; ".join(f'{x["name"]} ({x["y"]})' for x in sorted(pl, key=lambda x: x["y"]))
            r["first_closure"] = min([x["y"] for x in pl], default="")
            r["last_closure"] = max([x["y"] for x in pl], default="")
            r["coalfield"] = Counter(x["area"] for x in pl).most_common(1)[0][0] if pl else ""
        else:
            r["last_closure" + tag] = max([x["y"] for x in pl], default="")
    rows.append(r)

print(Counter(r["group"] for r in rows))
cols = ["bua22cd", "bua22", "country", "region", "lat", "lon", "radius_km", "pop2021", "group", "group_tight", "group_wide",
        "n_pits", "pits", "coalfield", "first_closure", "last_closure", "last_closure_tight", "last_closure_wide", "km_to_pit", "nearest_pit", "nearest_pit_closed",
        "pct_65plus", "pct_no_car", "pct_in_work", "pct_inactive", "pct_inactive_working_age", "pct_sick", "pct_managerial", "pct_routine",
        "income_fye2023", "km_to_city100k"]
rows.sort(key=lambda r: -(r.get("pop2021") or 0))
with open(os.path.join(OUT, "towns.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
