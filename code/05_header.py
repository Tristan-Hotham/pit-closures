"""Step 5. Make header.png (1200x630 social card) by rendering a small HTML card with Playwright.

Usage:
    python3 code/05_header.py [font_dir]

Fonts come from Google Fonts. Where Google Fonts is unreachable, pass a folder holding
FrauncesVar.ttf, IBMPlexMono-Regular.ttf, IBMPlexMono-Medium.ttf and SourceSerif4-Regular.ttf.
"""
import asyncio
import csv
import json
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = json.load(open(os.path.join(ROOT, "data", "results.json")))
FONTS = sys.argv[1] if len(sys.argv) > 1 else None
pts = [[round(float(r["lon"]), 3), round(float(r["lat"]), 3), int(r["closed_year"])]
       for r in csv.DictReader(open(os.path.join(ROOT, "data", "pits_1984.csv"), encoding="utf-8")) if r["lat"]]
coast = json.load(open("/home/claude/hist/_data3/ne/geojson/ne_10m_land.geojson"))["features"]
rings = []
for ft in coast:
    g = ft["geometry"]
    for p in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]):
        r = p[0]
        if any(-6.5 < x < 2 and 50 < y < 57.2 for x, y in r) and len(r) > 30:
            rings.append([[round(x, 3), round(y, 3)] for x, y in r[::3]])
dek = (f"{R['pits']['n']} deep mines were working at the start of 1984; {R['pits']['n_by_1994']} had closed by 1994. "
       f"In 2021 the pit towns had {R['headline']['sick_pts']:.1f} points more adults long-term sick than similar towns.")

HTML = """<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,900&family=IBM+Plex+Mono:wght@400;500&family=Source+Serif+4:opsz,wght@8..60,400&display=swap">
<style>
body{margin:0;width:1200px;height:630px;background:#EEEEEA;color:#1B1C1E;overflow:hidden;position:relative;font-family:'Source Serif 4',Georgia,serif}
.l{position:absolute;left:72px;top:60px;width:640px}
.k{font:500 17px/1 'IBM Plex Mono',monospace;letter-spacing:.14em;text-transform:uppercase;color:#5E6064;display:flex;gap:14px;align-items:center}
.k b{background:#B3261E;color:#fff;padding:8px 10px;font-weight:500}
h1{font:900 88px/.9 'Fraunces',Georgia,serif;letter-spacing:-.02em;margin:24px 0 0}
h1 em{font-style:normal;color:#B3261E}
p{font-size:27px;line-height:1.34;margin:24px 0 0;color:#2B2720;max-width:560px}
.f{position:absolute;left:72px;bottom:36px;font:400 15px/1 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:#5E6064}
canvas{position:absolute;right:16px;top:8px}
</style></head><body>
<div class="l"><div class="k"><b>Data study</b><span>History × data</span></div>
<h1>Did the pits<br>closing <em>still<br>show?</em></h1>
<p>__DEK__</p></div>
<div class="f">Dr Tristan Hotham · Independent researcher</div>
<canvas id="c" width="900" height="1228" style="width:450px;height:614px"></canvas>
<script>
const P = __PTS__, RINGS = __RINGS__;
const cv = document.getElementById("c"), x = cv.getContext("2d"); x.scale(2, 2);
const k = Math.cos(54 * Math.PI / 180), lo0 = -5.4, lo1 = 1.6, la0 = 50.9, la1 = 56.6;
const sc = Math.min(450 / ((lo1 - lo0) * k), 614 / (la1 - la0));
const X = l => (l - lo0) * k * sc + (450 - (lo1 - lo0) * k * sc) / 2, Y = l => (la1 - l) * sc;
RINGS.forEach(r => { x.beginPath(); r.forEach((p, i) => i ? x.lineTo(X(p[0]), Y(p[1])) : x.moveTo(X(p[0]), Y(p[1]))); x.closePath(); x.fillStyle = "#E0E0DA"; x.fill(); x.strokeStyle = "#C4C5BE"; x.lineWidth = .6; x.stroke(); });
P.sort((a, b) => a[2] - b[2]).forEach(p => { x.beginPath(); x.arc(X(p[0]), Y(p[1]), p[2] > 1994 ? 4 : 3, 0, 7); x.fillStyle = p[2] > 1994 ? "rgba(37,39,43,.95)" : "rgba(179,38,30,.8)"; x.fill(); });
</script></body></html>"""
html = HTML.replace("__DEK__", dek).replace("__PTS__", json.dumps(pts, separators=(",", ":"))).replace("__RINGS__", json.dumps(rings, separators=(",", ":")))
if FONTS:
    css = "".join(f"@font-face{{font-family:'{fam}';src:url(file://{FONTS}/{f});font-weight:{w}}}" for fam, f, w in
                  [("Fraunces", "FrauncesVar.ttf", "100 900"), ("IBM Plex Mono", "IBMPlexMono-Regular.ttf", "400"),
                   ("IBM Plex Mono", "IBMPlexMono-Medium.ttf", "500"), ("Source Serif 4", "SourceSerif4-Regular.ttf", "400")])
    html = html.replace('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,900&family=IBM+Plex+Mono:wght@400;500&family=Source+Serif+4:opsz,wght@8..60,400&display=swap">', f"<style>{css}</style>")


async def main():
    tmp = os.path.join(ROOT, "_header.html")
    open(tmp, "w", encoding="utf-8").write(html)
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--allow-file-access-from-files"])
        pg = await b.new_page(viewport={"width": 1200, "height": 630})
        await pg.goto("file://" + tmp)
        await pg.wait_for_timeout(1500)
        await pg.screenshot(path=os.path.join(ROOT, "header.png"))
        await b.close()
    os.remove(tmp)


asyncio.run(main())
print("header.png written")
