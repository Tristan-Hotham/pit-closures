"""Reddit collage (2400 x 3000 px). Reads only data/ files (and Natural Earth for the coastline).
Usage: python3 reddit/collage.py [font_dir]
"""
import json
import os
import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
F = sys.argv[1] if len(sys.argv) > 1 else "/tmp/claude-0/-home-claude/c232619d-81e0-53f3-9de6-41e973630753/scratchpad/fonts"
for f in ["FrauncesVar.ttf", "IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf", "SourceSerif4-Regular.ttf", "SourceSerif4-Semibold.ttf", "SourceSerif4-It.ttf"]:
    fm.fontManager.addfont(os.path.join(F, f))
DISP = fm.FontProperties(fname=os.path.join(F, "FrauncesVar.ttf"), weight=900)
SER, MONO = "Source Serif 4", "IBM Plex Mono"
BG, FG, MUT, LANDC, EDGE = "#E4E6E7", "#17181A", "#5A5E63", "#F4F5F4", "#C2C6C9"
RED, COAL, SLATE, AMBER = "#B3261E", "#1F2124", "#9AA6B0", "#B57A1C"

R = json.load(open(os.path.join(ROOT, "data", "results.json")))
P = pd.read_csv(os.path.join(ROOT, "data", "pits_1984.csv"))
TW = pd.read_csv(os.path.join(ROOT, "data", "towns.csv"))
K = np.cos(np.radians(54.0))
land = []
for ft in json.load(open("/home/claude/hist/_data3/ne/geojson/ne_10m_land.geojson"))["features"]:
    g = ft["geometry"]
    for p in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]):
        r = np.array(p[0])
        if ((r[:, 0] > -11) & (r[:, 0] < 3) & (r[:, 1] > 49) & (r[:, 1] < 61)).any():
            land.append(r)

PS, T, H, O = R["pits"], R["towns"], R["headline"], R["outcomes"]
fig = plt.figure(figsize=(12, 15), dpi=200, facecolor=BG)
fig.text(0.04, 0.968, "Can you still see where the pits were?", fontproperties=DISP, fontsize=40, color=FG, va="top")
fig.text(0.04, 0.917, f"Every deep coal mine working in Britain at the start of 1984 ({PS['n']} in my list), and the towns around them.\n"
         f"In the 2021 Census the pit towns of England and Wales still stand out, whenever their pit closed.",
         family=SER, fontsize=15.5, color=FG, va="top", linespacing=1.15)

# hero map: towns as dots, pit towns red, pits as black squares
ax = fig.add_axes([0.02, 0.335, 0.58, 0.53])
for r in land:
    ax.fill(r[:, 0] * K, r[:, 1], color=LANDC, ec=EDGE, lw=0.6, zorder=0)
S = TW[(TW.country != "Scotland") & (TW.pop2021 >= 2000) & (TW.pop2021 <= 100000)]
q = S[S.group == "none"]
ax.scatter(q.lon * K, q.lat, s=np.sqrt(q.pop2021) * 0.05, color=SLATE, alpha=0.55, lw=0, zorder=1, rasterized=True)
q = S[S.group == "pit"]
ax.scatter(q.lon * K, q.lat, s=np.sqrt(q.pop2021) * 0.32, color=RED, alpha=0.7, lw=0.5, edgecolor="white", zorder=3)
late = P.closed_year > 1994
ax.scatter(P[~late].lon * K, P[~late].lat, s=5, marker="s", color=COAL, alpha=0.9, lw=0, zorder=4)
ax.scatter(P[late].lon * K, P[late].lat, s=22, marker="s", color=COAL, lw=0.7, edgecolor="white", zorder=5)
ax.set_xlim(-5.4 * K, 1.7 * K)
ax.set_ylim(50.85, 56.35)
ax.set_aspect("equal")
ax.axis("off")
for nm, lon, lat, dx, dy, ha in [("Yorkshire", -1.35, 53.6, 0.55, 0.45, "left"), ("Nottinghamshire", -1.15, 53.1, 0.75, -0.2, "left"),
                                 ("Durham", -1.4, 54.75, 0.75, 0.0, "left"), ("South Wales", -3.5, 51.68, -0.35, -0.42, "center"),
                                 ("Fife and the Lothians", -3.3, 56.0, 1.0, -0.25, "left"), ("Kent", 1.25, 51.2, -0.2, 0.42, "right")]:
    ax.annotate(nm, (lon * K, lat), xytext=((lon + dx) * K, lat + dy), fontsize=11, family=MONO, color=FG, ha=ha, va="center",
                arrowprops=dict(arrowstyle="-", color=MUT, lw=0.7))
lx = 0.05
fig.text(lx, 0.326, "■", color=COAL, fontsize=10, va="center")
fig.text(lx + 0.018, 0.326, f"deep mine working in 1984 ({PS['n']}); larger if it lasted past 1994 ({PS['n_1995_2015']})", family=MONO, fontsize=10, color=MUT, va="center")
fig.text(lx, 0.313, "●", color=RED, fontsize=11, va="center")
fig.text(lx + 0.018, 0.313, f"pit town, 2,000 to 100,000 people ({T['groups_sample']['pit']})", family=MONO, fontsize=10, color=MUT, va="center")
fig.text(lx, 0.300, "●", color=SLATE, fontsize=11, va="center")
fig.text(lx + 0.018, 0.300, f"town with no pit nearby ({T['groups_sample']['none']:,})", family=MONO, fontsize=10, color=MUT, va="center")

# right column numbers
tx = fig.add_axes([0.6, 0.32, 0.38, 0.54])
tx.axis("off")
notes = [(f"{PS['n_by_1994']} of {PS['n']}", f"deep mines closed by the end of 1994.\nThe worst year was {PS['peak_year']}, with {PS['peak_n']}.\nThe last, Kellingley, closed in 2015."),
         (f"{O['median']['pit']['pct_sick'] * 100:.1f}% vs {O['median']['none']['pct_sick'] * 100:.1f}%", f"of adults long-term sick or disabled:\nmedian pit town against median town\nwith no pit. Size for size and region\nfor region, +{H['sick_pts']:.1f} points."),
         (f"£{abs(H['income_gbp']):,.0f}", f"lower household income a year\n({abs(H['income_pct_of_none']) * 100:.1f}%) than similar towns, with\n{H['routine_pts']:.1f} points more adults in routine\njobs. The share in work is no lower."),
         ("No clear gap", "between towns whose last pit shut in\n1984 to 1987 and those whose pit\nworked on until 1995 to 2015.")]
for (big, small), y in zip(notes, [1.0, 0.755, 0.48, 0.215]):
    tx.text(0, y, big, fontproperties=DISP, fontsize=30, color=RED, va="top", transform=tx.transAxes)
    tx.text(0, y - 0.072, small, family=SER, fontsize=12.5, color=FG, va="top", transform=tx.transAxes, linespacing=1.15)


def style(a):
    for s_ in ("top", "right"):
        a.spines[s_].set_visible(False)
    a.spines["left"].set_color(MUT)
    a.spines["bottom"].set_color(MUT)
    a.tick_params(colors=MUT, labelsize=10)
    for t in a.get_xticklabels() + a.get_yticklabels():
        t.set_family(MONO)


# bottom row: closures per year, and sickness by closure wave
a1 = fig.add_axes([0.07, 0.10, 0.48, 0.14], facecolor=BG)
by = {int(k): v for k, v in PS["by_year"].items()}
ys = list(range(1984, 2016))
a1.bar(ys, [by.get(y, 0) for y in ys], width=0.8, color=[RED if y <= 1994 else COAL for y in ys])
a1.set_xticks([1985, 1990, 1995, 2000, 2005, 2010, 2015])
style(a1)
a1.axvline(1994.5, color=FG, lw=0.9, ls=(0, (2, 3)))
a1.text(1995.2, by[PS["peak_year"]] * 0.95, "1994:\nprivatised", family=MONO, fontsize=10, color=FG, va="top")
a1.text(PS["peak_year"] + 0.8, by[PS["peak_year"]], f"{PS['peak_year']}: {by[PS['peak_year']]}", family=MONO, fontsize=10, color=FG, va="center")
fig.text(0.04, 0.258, "DEEP MINES CLOSED EACH YEAR, 1984 TO 2015", family=MONO, fontsize=11, color=MUT)

a2 = fig.add_axes([0.73, 0.10, 0.23, 0.14], facecolor=BG)
tm = R["timing"]["models"]["pct_sick"]["median"]
rows = [("Pit shut 1984 to 87", tm["early"], RED), ("1988 to 94", tm["mid"], RED), ("1995 to 2015", tm["late"], RED),
        ("No pit nearby", O["median"]["none"]["pct_sick"], SLATE)]
yy = np.arange(len(rows))[::-1]
a2.barh(yy, [r[1] * 100 for r in rows], color=[r[2] for r in rows], height=0.62)
a2.set_yticks(yy, [r[0] for r in rows])
for y_, r in zip(yy, rows):
    a2.text(r[1] * 100 + 0.2, y_, f"{r[1] * 100:.1f}%", va="center", family=MONO, fontsize=10, color=FG)
a2.set_xlim(0, 8)
a2.set_xticks([])
style(a2)
a2.spines["bottom"].set_visible(False)
a2.tick_params(colors=FG, length=0)
fig.text(0.585, 0.258, "LONG-TERM SICK, MEDIAN TOWN, 2021", family=MONO, fontsize=11, color=MUT)

fig.text(0.04, 0.066, "Association, not cause: the coalfields were different before 1984 too, and towns near older pits (mostly closed long before) show about half the gap.",
         family=SER, style="italic", fontsize=10.5, color=FG)
fig.text(0.04, 0.008, "Data: Northern Mine Research Society, NCB collieries tables; Wikipedia colliery lists (CC BY-SA 4.0); OpenStreetMap contributors (ODbL); Wikidata (CC0);\n"
         "ONS Census 2021 and small area income FYE2023, ONS built-up areas (OGL v3); OS Open Names, contains OS data © Crown copyright and\n"
         "database right 2026; Natural Earth. Pit towns: a 1984 pit within 3 km of the centre or 2 km of the edge.\n"
         "Analysis and chart: Tristan Hotham, with Python and matplotlib.",
         family=MONO, fontsize=9, color=MUT, linespacing=1.2)
fig.savefig(os.path.join(HERE, "can_you_still_see_the_pits.png"), facecolor=BG, dpi=200)
print("ok")
