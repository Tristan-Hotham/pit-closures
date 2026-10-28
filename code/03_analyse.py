"""Step 3. Analysis: when the pits closed, which towns were pit towns, and how those towns compare today.

Reads data/pits_1984.csv, data/towns.csv, data/_pit_stats.json (steps 1 and 2) and _data12/wikipedia_batch12.json.gz
(the miners' strike and Kellingley articles, for a few facts quoted with their source).
Writes data/results.json (every number used on the page, in the paper, the blog post and the collage) and
_site_data.json (compact map and chart data for the page; a temporary build file).

Comparisons use built-up areas in England and Wales with 2,000 to 100,000 residents in 2021 (Census outcomes exist only
for England and Wales). Pit towns are compared with "none" towns (no 1984 pit within reach, none within 10 km beyond
the edge, and no older colliery named in OpenStreetMap or Wikidata within reach). Regressions add log population and its
square and region; checks add the distance to the nearest city of 100,000 or more, the share aged 65 or over, and other
definitions. Each pit town is also matched with replacement to the comparison town in the same region with the nearest
2021 population. All of this is association: the coalfields differed from other places long before 1984.
"""
import gzip
import json
import math
import os
import re

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = "/home/claude/hist"
D = os.path.join(ROOT, "data")
rng = np.random.default_rng(1984)

P = pd.read_csv(os.path.join(D, "pits_1984.csv"))
tw = pd.read_csv(os.path.join(D, "towns.csv"))
st = json.load(open(os.path.join(D, "_pit_stats.json")))
R = {}

# ---------------------------------------------------------------- 1. pits
by_year = P.closed_year.value_counts().sort_index()
R["pits"] = {
    "n": int(len(P)), "by_country": {k: int(v) for k, v in P.country.value_counts().items()},
    "by_area": {k: int(v) for k, v in P.area.value_counts().items()},
    "by_year": {int(k): int(v) for k, v in by_year.items()},
    "peak_year": int(by_year.idxmax()), "peak_n": int(by_year.max()),
    "n_1984_87": int((P.closed_year <= 1987).sum()), "n_1988_94": int(((P.closed_year >= 1988) & (P.closed_year <= 1994)).sum()),
    "n_1995_2015": int((P.closed_year >= 1995).sum()), "n_by_1994": int((P.closed_year <= 1994).sum()),
    "n_1992_94": int(((P.closed_year >= 1992) & (P.closed_year <= 1994)).sum()),
    "n_1985_86": int(((P.closed_year >= 1985) & (P.closed_year <= 1986)).sum()),
    "n_pre_strike": int(P.pre_strike.sum()), "n_2000s": int((P.closed_year >= 2000).sum()),
    "share_by_1994": float((P.closed_year <= 1994).mean()), "share_by_1987": float((P.closed_year <= 1987).mean()),
    "placing": {k: int(v) for k, v in P.geo_method.value_counts().items()},
    "year_source": {k: int(v) for k, v in P.year_source.value_counts().items()},
    "year_agreement": st["year_agreement"], "n_york_wiki": st["n_york_wiki"], "n_nmrs_rows": st["n_nmrs_rows"],
}
ya = st["year_agreement"]
R["pits"]["n_year_checked"] = int(sum(ya.values()))
R["pits"]["share_year_exact"] = ya.get("exact", 0) / sum(ya.values())
R["pits"]["share_year_within1"] = (ya.get("exact", 0) + ya.get("1yr", 0)) / sum(ya.values())
last = P.sort_values("closed_year", ascending=False).head(12)
R["pits"]["last"] = [{"name": r.name, "village": r.village, "area": r.area, "year": int(r.closed_year)} for r in last.itertuples()]
med_year = {}
for a, g in P.groupby("area"):
    med_year[a] = {"n": int(len(g)), "median_year": float(g.closed_year.median()), "last": int(g.closed_year.max()),
                   "share_by_1987": float((g.closed_year <= 1987).mean())}
R["pits"]["by_area_detail"] = med_year
cty = {}
for c, g in P.groupby("country"):
    cty[c] = {"n": int(len(g)), "median_year": float(g.closed_year.median()), "last": int(g.closed_year.max()),
              "share_by_1987": float((g.closed_year <= 1987).mean()), "share_by_1994": float((g.closed_year <= 1994).mean())}
R["pits"]["by_country_detail"] = cty

# facts quoted from Wikipedia (asserted against the text on disk)
W = json.load(gzip.open(f"{H}/_data12/wikipedia_batch12.json.gz"))["articles"]
ms = W["1984–1985 United Kingdom miners' strike"]["text"]
for s in ("by 1984 only 173 were still operating", "started on 6 March 1984 with a walkout at [[Cortonwood Colliery]]",
          "The national strike ended on 3 March 1985", "closed for the last time on 18 December 2015"):
    assert s in ms, s
cm = W["Coal mining in the United Kingdom"]["text"]
assert "Thatcher (Conservative) closed 115 between 1979 and 1990" in cm
yl = W["List of collieries in Yorkshire (1984–2015)"]["text"]
assert "In 1984, the Yorkshire area had a total of 56" in yl
R["context"] = {"pits_1984_wiki": 173, "strike_start": "6 March 1984", "strike_end": "3 March 1985", "kellingley_close": "18 December 2015",
                "york_1984_wiki": 56, "source": "Wikipedia, 1984 to 1985 United Kingdom miners' strike; List of collieries in Yorkshire (1984 to 2015) (CC BY-SA 4.0), retrieved 28 October 2026"}

# ---------------------------------------------------------------- 2. towns
tw["logpop"] = np.log(tw.pop2021)
ew = tw[tw.pop2021.notna()].copy()
S = ew[(ew.pop2021 >= 2000) & (ew.pop2021 <= 100000)].copy()
GROUPS = ["pit", "near", "older", "none"]
R["towns"] = {"n_bua_gb": int(len(tw)), "n_bua_ew": int(len(ew)), "n_sample": int(len(S)),
              "groups_sample": {g: int((S.group == g).sum()) for g in GROUPS},
              "groups_gb": {g: int((tw.group == g).sum()) for g in GROUPS},
              "groups_scotland": {g: int(((tw.country == "Scotland") & (tw.group == g)).sum()) for g in GROUPS}}
PT = ew[ew.group == "pit"]
R["towns"]["n_pit_ew"] = int(len(PT))
R["towns"]["pop_pit_ew"] = int(PT.pop2021.sum())
R["towns"]["pop_pit_sample"] = int(S[S.group == "pit"].pop2021.sum())
R["towns"]["n_pit_scotland"] = int(((tw.country == "Scotland") & (tw.group == "pit")).sum())
med = {}
for g in GROUPS:
    x = S[S.group == g]
    med[g] = {"n": int(len(x)), "median_pop": float(x.pop2021.median()), "median_km_city": float(x.km_to_city100k.median())}
R["towns"]["medians"] = med
reg = []
for rg, h in S.groupby("region"):
    reg.append({"region": rg, "n": int(len(h)), "pit": int((h.group == "pit").sum()), "share_pit": float((h.group == "pit").mean())})
R["towns"]["by_region"] = sorted(reg, key=lambda r: -r["share_pit"])
cf = []
for a, h in S[S.group == "pit"].groupby("coalfield"):
    cf.append({"area": a, "n": int(len(h)), "median_last": float(h.last_closure.median())})
R["towns"]["by_coalfield"] = sorted(cf, key=lambda r: -r["n"])
# pit towns by year of last closure
lc = S[S.group == "pit"].last_closure.astype(int)
R["towns"]["pit_last_wave"] = {"1984 to 1987": int((lc <= 1987).sum()), "1988 to 1994": int(((lc >= 1988) & (lc <= 1994)).sum()),
                               "1995 to 2015": int((lc >= 1995).sum())}


def short(r):
    return {"name": r.bua22, "pop": int(r.pop2021), "region": r.region, "pits": r.pits, "last": int(r.last_closure),
            "sick": float(r.pct_sick), "inact": float(r.pct_inactive_working_age), "inc": int(r.income_fye2023) if pd.notna(r.income_fye2023) else None}


big = S[S.group == "pit"].sort_values("pop2021", ascending=False)
R["towns"]["top_pit"] = [short(r) for r in big.head(25).itertuples()]
sk = S[(S.group == "pit")].sort_values("pct_sick", ascending=False)
R["towns"]["top_sick"] = [short(r) for r in sk[sk.pop2021 >= 5000].head(12).itertuples()]
R["towns"]["n_pits_placed_in_sample_towns"] = int(len({p.strip() for s in S[S.group == "pit"].pits for p in s.split(";")}))

# ---------------------------------------------------------------- 3. outcomes
OUT = {"pct_sick": "Adults long-term sick or disabled", "pct_inactive_working_age": "Adults inactive (not retired or students)",
       "pct_in_work": "Adults (16+) in work", "pct_routine": "Adults in routine or semi-routine jobs",
       "pct_managerial": "Adults in managerial or professional jobs", "pct_65plus": "Aged 65 or over",
       "pct_no_car": "Households without a car or van", "income_fye2023": "Mean household income (MSOA, FYE2023)"}
R["outcomes"] = {"labels": OUT}
S["income_k"] = S.income_fye2023 / 1000
S["logkm"] = np.log1p(S.km_to_city100k)

desc = {}
for g in GROUPS:
    x = S[S.group == g]
    desc[g] = {"n": int(len(x))}
    for o in OUT:
        desc[g][o] = float(x[o].median()) if x[o].notna().any() else None
        desc[g][o + "_n"] = int(x[o].notna().sum())
R["outcomes"]["median"] = desc


def matched(treat, ctrl, outcome, tol=math.log(1.25)):
    diffs = []
    for rg, t in treat.groupby("region"):
        c = ctrl[(ctrl.region == rg) & ctrl[outcome].notna()]
        if c.empty:
            continue
        cl, cv = c.logpop.values, c[outcome].values
        for r in t.itertuples():
            v = getattr(r, outcome)
            if pd.isna(v):
                continue
            j = np.argmin(np.abs(cl - r.logpop))
            if abs(cl[j] - r.logpop) <= tol:
                diffs.append(v - cv[j])
    d = np.array(diffs)
    if len(d) < 5:
        return None
    boots = [rng.choice(d, len(d)).mean() for _ in range(2000)]
    return {"n": int(len(d)), "diff": float(d.mean()), "lo": float(np.percentile(boots, 2.5)), "hi": float(np.percentile(boots, 97.5)),
            "share_higher": float((d > 0).mean())}


def models(df, groups=("pit", "older", "near"), extra=""):
    out = {}
    df = df[df.group.isin(("none",) + tuple(groups))].copy()
    for o in OUT:
        y = "income_k" if o == "income_fye2023" else o
        dd = df[df[y].notna()]
        res = {}
        specs = (("size_region", f"{y} ~ C(group, Treatment('none')) + logpop + I(logpop**2) + C(region){extra}"),
                 ("plus_remote", f"{y} ~ C(group, Treatment('none')) + logpop + I(logpop**2) + C(region) + logkm{extra}"))
        for name, f in specs:
            m = smf.ols(f, data=dd).fit(cov_type="HC1")
            for g in groups:
                k = f"C(group, Treatment('none'))[T.{g}]"
                if k in m.params:
                    sc = 1000 if o == "income_fye2023" else 1
                    res[f"{name}_{g}"] = {"b": float(m.params[k] * sc), "lo": float(m.conf_int().loc[k, 0] * sc),
                                          "hi": float(m.conf_int().loc[k, 1] * sc), "p": float(m.pvalues[k])}
            res[f"{name}_n"] = int(m.nobs)
        out[o] = res
    return out


pit, none, older, near = (S[S.group == g] for g in GROUPS)
R["outcomes"]["matched_pit"] = {o: matched(pit, none, o) for o in OUT}
R["outcomes"]["matched_older"] = {o: matched(older, none, o) for o in OUT}
R["outcomes"]["models"] = models(S)

# checks
chk = {}
for tag in ("tight", "wide"):
    s2 = S.copy()
    s2["group"] = s2["group_" + tag]
    chk[tag] = {"n_pit": int((s2.group == "pit").sum()), "n_none": int((s2.group == "none").sum()), "models": models(s2, groups=("pit",))}
chk["age_control"] = {"models": models(S, groups=("pit",), extra=" + pct_65plus")}
s4 = S[S.pop2021 >= 5000]
chk["over5k"] = {"n_pit": int((s4.group == "pit").sum()), "models": models(s4, groups=("pit",))}
s5 = S[S.country == "England"]
chk["england"] = {"n_pit": int((s5.group == "pit").sum()), "models": models(s5, groups=("pit",))}
s6 = S[S.country == "Wales"]
chk["wales"] = {"n_pit": int((s6.group == "pit").sum()), "n_none": int((s6.group == "none").sum()), "models": models(s6, groups=("pit",))}
s7 = S[S.km_to_city100k >= 15]
chk["away_from_cities"] = {"n_pit": int((s7.group == "pit").sum()), "models": models(s7, groups=("pit",))}
# comparison towns drawn only from the coalfield regions (regions with at least 10 pit towns)
creg = [r["region"] for r in R["towns"]["by_region"] if r["pit"] >= 10]
s8 = S[S.region.isin(creg)]
chk["coal_regions"] = {"regions": creg, "n_pit": int((s8.group == "pit").sum()), "n_none": int((s8.group == "none").sum()), "models": models(s8, groups=("pit",))}
R["checks"] = chk

# ---------------------------------------------------------------- 4. timing: does a later closure go with better outcomes?
T = S[S.group == "pit"].copy()
T["wave"] = pd.cut(T.last_closure, [1983, 1987, 1994, 2016], labels=["early", "mid", "late"]).astype(str)
tm = {}
for o in OUT:
    y = "income_k" if o == "income_fye2023" else o
    dd = T[T[y].notna()]
    m = smf.ols(f"{y} ~ C(wave, Treatment('early')) + logpop + I(logpop**2) + C(region)", data=dd).fit(cov_type="HC1")
    sc = 1000 if o == "income_fye2023" else 1
    res = {"n": int(m.nobs)}
    for w in ("mid", "late"):
        k = f"C(wave, Treatment('early'))[T.{w}]"
        res[w] = {"b": float(m.params[k] * sc), "lo": float(m.conf_int().loc[k, 0] * sc), "hi": float(m.conf_int().loc[k, 1] * sc), "p": float(m.pvalues[k])}
    m2 = smf.ols(f"{y} ~ last_closure + logpop + I(logpop**2) + C(region)", data=dd).fit(cov_type="HC1")
    res["per_decade"] = {"b": float(m2.params["last_closure"] * 10 * sc), "lo": float(m2.conf_int().loc["last_closure", 0] * 10 * sc),
                         "hi": float(m2.conf_int().loc["last_closure", 1] * 10 * sc), "p": float(m2.pvalues["last_closure"])}
    res["median"] = {w: float(T[T.wave == w][o].median()) for w in ("early", "mid", "late")}
    tm[o] = res
R["timing"] = {"n": {w: int((T.wave == w).sum()) for w in ("early", "mid", "late")}, "models": tm}
# number of pits (one vs several)
T["multi"] = (T.n_pits >= 2).astype(int)
R["timing"]["n_multi"] = int(T.multi.sum())
m = smf.ols("pct_sick ~ multi + logpop + I(logpop**2) + C(region)", data=T).fit(cov_type="HC1")
R["timing"]["multi_sick"] = {"b": float(m.params["multi"]), "lo": float(m.conf_int().loc["multi", 0]), "hi": float(m.conf_int().loc["multi", 1]), "p": float(m.pvalues["multi"])}

# ---------------------------------------------------------------- headline numbers
m = R["outcomes"]["models"]
hd = {}
for o, k in (("pct_sick", "sick"), ("pct_inactive_working_age", "inact"), ("pct_in_work", "work"), ("pct_routine", "routine"),
             ("pct_managerial", "mgr"), ("pct_65plus", "age65"), ("pct_no_car", "nocar")):
    hd[k + "_pts"] = m[o]["size_region_pit"]["b"] * 100
    hd[k + "_lo"] = m[o]["size_region_pit"]["lo"] * 100
    hd[k + "_hi"] = m[o]["size_region_pit"]["hi"] * 100
    hd[k + "_p"] = m[o]["size_region_pit"]["p"]
    hd[k + "_older_pts"] = m[o]["size_region_older"]["b"] * 100
    hd[k + "_older_p"] = m[o]["size_region_older"]["p"]
    hd[k + "_near_pts"] = m[o]["size_region_near"]["b"] * 100
    hd[k + "_remote_pts"] = m[o]["plus_remote_pit"]["b"] * 100
hd["income_gbp"] = m["income_fye2023"]["size_region_pit"]["b"]
hd["income_lo"] = m["income_fye2023"]["size_region_pit"]["lo"]
hd["income_hi"] = m["income_fye2023"]["size_region_pit"]["hi"]
hd["income_p"] = m["income_fye2023"]["size_region_pit"]["p"]
hd["income_older_gbp"] = m["income_fye2023"]["size_region_older"]["b"]
hd["income_near_gbp"] = m["income_fye2023"]["size_region_near"]["b"]
hd["income_remote_gbp"] = m["income_fye2023"]["plus_remote_pit"]["b"]
hd["income_n"] = m["income_fye2023"]["size_region_n"]
hd["income_pct_of_none"] = hd["income_gbp"] / desc["none"]["income_fye2023"]
hd["sick_ratio"] = (desc["none"]["pct_sick"] + m["pct_sick"]["size_region_pit"]["b"]) / desc["none"]["pct_sick"]
hd["sick_median_ratio"] = desc["pit"]["pct_sick"] / desc["none"]["pct_sick"]
R["headline"] = hd
hd["sick_per_1000"] = hd["sick_pts"] * 10
hd["income_median_gap"] = desc["pit"]["income_fye2023"] - desc["none"]["income_fye2023"]
hd["late_sick_pts"] = tm["pct_sick"]["late"]["b"] * 100
hd["late_sick_p"] = tm["pct_sick"]["late"]["p"]
hd["late_sick_word"] = "less" if hd["late_sick_pts"] < 0 else "more"
hd["mid_sick_pts"] = tm["pct_sick"]["mid"]["b"] * 100
hd["mid_sick_p"] = tm["pct_sick"]["mid"]["p"]
hd["late_income_gbp"] = tm["income_fye2023"]["late"]["b"]
hd["late_income_p"] = tm["income_fye2023"]["late"]["p"]
hd["decade_sick_pts"] = tm["pct_sick"]["per_decade"]["b"] * 100
hd["decade_sick_p"] = tm["pct_sick"]["per_decade"]["p"]

# named towns used in the text
spot = {}
for nm in ["Grimethorpe", "Easington", "Maerdy", "Knottingley", "Mansfield", "Barnsley", "Ashington (Northumberland)", "Castleford", "Cortonwood",
           "Edwinstowe", "Featherstone", "Goldthorpe", "Thurnscoe", "Horden", "Shirebrook", "Bolsover", "Hemsworth", "Ferryhill", "Tredegar",
           "Treharris", "Aberfan", "Ollerton", "Rossington", "Hatfield (Doncaster)", "Stainforth", "Maltby", "Aylsham", "Seaham"]:
    x = tw[tw.bua22 == nm]
    if len(x):
        r = x.iloc[0]
        spot[nm] = {"pop": int(r.pop2021) if pd.notna(r.pop2021) else None, "group": r.group, "pits": r.pits if isinstance(r.pits, str) else "",
                    "last": int(r.last_closure) if pd.notna(r.last_closure) else None,
                    "sick": float(r.pct_sick) if pd.notna(r.pct_sick) else None, "income": int(r.income_fye2023) if pd.notna(r.income_fye2023) else None}
R["spot"] = spot
json.dump(R, open(os.path.join(D, "results.json"), "w"), indent=1, default=float)

# ---------------------------------------------------------------- 5. page data
site = {
    "pits": [[round(r.lat, 4), round(r.lon, 4), int(r.closed_year), r.name, r.village, r.area, r.geo_method[0]] for r in P.itertuples()],
    "old": [],
    "towns": [[r.bua22, round(r.lat, 4), round(r.lon, 4), int(r.pop2021) if pd.notna(r.pop2021) else 0, r.group,
               r.pits if isinstance(r.pits, str) else "", int(r.last_closure) if pd.notna(r.last_closure) else 0,
               *[round(float(getattr(r, o)), 3) if pd.notna(getattr(r, o)) else None for o in ["pct_sick", "pct_inactive_working_age", "pct_in_work", "pct_routine", "pct_65plus"]],
               int(r.income_fye2023) if pd.notna(r.income_fye2023) else None, r.region if isinstance(r.region, str) else "",
               r.nearest_pit, int(r.nearest_pit_closed), round(float(r.km_to_pit), 1)]
              for r in tw.itertuples() if (pd.notna(r.pop2021) and r.pop2021 >= 2000) or r.group == "pit"],
}
json.dump(site, open(os.path.join(ROOT, "_site_data.json"), "w"), separators=(",", ":"), ensure_ascii=False)
print(json.dumps(R["pits"], default=float)[:900])
print(json.dumps(R["towns"]["groups_sample"]), R["towns"]["pit_last_wave"])
print(pd.DataFrame(R["outcomes"]["median"]).round(3).to_string())
for o in OUT:
    mm = R["outcomes"]["models"][o]
    print(o, {k: (round(v["b"], 4), round(v["p"], 4)) for k, v in mm.items() if isinstance(v, dict)})
    print("   matched", {k: round(v, 4) if isinstance(v, float) else v for k, v in (R["outcomes"]["matched_pit"][o] or {}).items()})
for c in chk:
    print(c, chk[c].get("n_pit"), {o: round(chk[c]["models"][o]["size_region_pit"]["b"], 4) for o in OUT})
for o in OUT:
    print("timing", o, R["timing"]["n"], {w: (round(tm[o][w]["b"], 4), round(tm[o][w]["p"], 3)) for w in ("mid", "late")}, tm[o]["median"])
print("multi", R["timing"]["multi_sick"])
print("site bytes", os.path.getsize(os.path.join(ROOT, "_site_data.json")))
