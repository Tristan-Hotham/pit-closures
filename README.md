# Did the Pits Closing Still Show?

Every deep coal mine working in Great Britain at the start of 1984, when each closed, and how the towns around them compare in the 2021 Census with towns of the same size, in the same regions, that never had a pit. Northern Mine Research Society colliery tables, Wikipedia's colliery lists, OpenStreetMap, Wikidata, OS Open Names, Census 2021 and ONS income estimates.

**Interactive version:** https://tristan-hotham.github.io/pit-closures/

**Paper:** https://doi.org/10.5281/zenodo.23729637

This repository holds the interactive page, the datasets, the computed results and the analysis code for a data study by Dr Tristan Hotham (Independent researcher).

## Headline results

- My list holds 196 deep mine units working at the start of 1984 (151 in England, 35 in Wales, 10 in Scotland). Wikipedia's account of the miners' strike gives 173 pits; my count is higher because some combined mines appear under more than one name.
- 167 (85%) had closed by the end of 1994. The worst year was 1985, with 32 closures. The last 29 closed between 1995 and 2015, the last three (Hatfield, Thoresby, Kellingley) in 2015.
- 209 towns of 2,000 to 100,000 people in England and Wales (2.85 million residents) had a 1984 pit within reach.
- Against towns of the same size and region with no pit, the pit towns have 2.0 percentage points more adults long-term sick or disabled (95% interval 1.7 to 2.3; comparison town median 2.9%), 3.2 points more adults inactive for reasons other than retirement or study, 6.5 points more in routine or semi-routine work, 8.0 points fewer in managerial or professional work, 3.7 points more households without a car, and about £5,900 a year lower mean household income (10.7%).
- Their share of adults in work is no different (+0.2 points): they are younger (3.7 points fewer aged 65+), so fewer adults are retired, and more of those of working age are out of work through sickness.
- Towns near older collieries (mostly closed before 1984) show about half the gap (0.9 points more long-term sick, £3,403 less income).
- Among pit towns, the year the last pit closed makes no clear difference: towns whose last pit closed in 1995 to 2015 have 0.4 points less long-term sickness than those whose last pit closed in 1984 to 1987, well within chance.

These are associations, not causes. The coalfields differed from other places long before 1984, and there is no 1981 or 1991 baseline here.

## Files

- `index.html`: the interactive page (pit map with a year slider and play button, town map and "find your town" search, charts, tables). Data embedded; works as a single file.
- `header.png`: social card (1200 by 630).
- `data/pits_1984.csv`: the 196 colliery units: name, country, area, district, village, closure year and month, the NMRS year where it differs, which source gave the year (`year_source`), closure wave, coordinates and how they were found (`geo_method`: `osm_colliery`, `wikidata` or `village`, with `geo_source`), the village point, notes and the Wikipedia article where there is one.
- `data/nmrs_extract.csv`: my extract of the Northern Mine Research Society tables (collieries closed in 1984 or later), with the village used for placing and notes where I changed the town given in the table.
- `data/towns.csv`: every built-up area (BUA22) in Great Britain: its group under the main rule and two checks, the 1984 pits within reach and their closure years, the nearest 1984 pit and its distance, and for England and Wales the 2021 residents, age, car, work, inactivity, sickness and class shares and mean household income.
- `data/old_collieries.csv`: colliery sites named in OpenStreetMap or Wikidata that are not 1984 pits (used for the "older mining towns" group).
- `data/results.json`: every number quoted on the page, in the paper, the blog post and the collage.
- `data/_pit_stats.json`: matching statistics from step 1.
- `code/01_pits.py`: builds the pit list, merges the NMRS extract with Wikipedia's lists, places each pit.
- `code/02_towns.py`: links pits to built-up areas, assigns town groups, adds Census 2021 and income.
- `code/03_analyse.py`: counts, comparisons, regressions, checks and timing; writes `results.json` and a temporary page data file.
- `code/04_build_page.py`: fills `code/page_template.html` from `results.json` to make `index.html`.
- `code/05_header.py`: renders `header.png` with Playwright.
- `release/`: the paper (PDF, LaTeX source and figures), the blog post and figures, and the Zenodo files.
- `reddit/`: the collage and its script.

## How to rerun

The scripts read the source files in place (paths at the top of each script): the Wikipedia and Wikidata/OSM bundles retrieved on 28 October 2026, OS Open Names, ONS geography lookups, Census 2021 tables TS001, TS007A, TS045, TS062 and TS066, and the ONS small area income estimates for FYE2023.

```
python3 code/01_pits.py
python3 code/02_towns.py
python3 code/03_analyse.py
python3 code/04_build_page.py
python3 code/05_header.py [font_dir]
python3 release/paper/figures.py [font_dir]
python3 release/paper/build_paper.py
python3 release/blog/build_post.py
python3 release/build_release_meta.py
python3 reddit/collage.py [font_dir]
```

It needs Python 3 with pandas, numpy, scipy, statsmodels, openpyxl, matplotlib and playwright, and xelatex for the paper.

## Method in brief

- Pit list: every colliery in the NMRS tables of National Coal Board collieries (England, Wales, Scotland) that closed in 1984 or later, read on 28 October 2026 and transcribed to `data/nmrs_extract.csv`; for Yorkshire, Wikipedia's List of collieries in Yorkshire (1984 to 2015). Where Wikipedia's Yorkshire, Derbyshire or UK lists give a plain year, that year is used; otherwise the NMRS year. Where both give a year they agree exactly for 81% of 77 pits and within a year for 90%.
- Placing: an OpenStreetMap feature named "<pit> Colliery/Pit/Mine/Drift" within 12 km of the pit's village (37 pits); else a Wikidata mine with a matching label (64); else the village in OS Open Names (95).
- Towns: a pit belongs to a built-up area if it lies within 3 km of its centre, or within 2 km beyond the edge of a circle of the same area. Checks use 2 km or 1 km beyond the edge, and 5 km or 3 km beyond the edge. Coalfield neighbours (a 1984 pit within 10 km beyond the edge) and older mining towns (an older colliery within reach) are kept apart from the comparison towns.
- Comparisons: least-squares regressions of each outcome on the town group, log 2021 population and its square, and region (robust standard errors), for built-up areas of 2,000 to 100,000 people in England and Wales; checks add distance to a city of 100,000 or more, the share aged 65+, other rules and subsets, and a nearest-neighbour match on population within region.

## Known limits

- Association, not cause: mining towns differed from other places before 1984; no 1981 or 1991 town figures are used.
- The NMRS figures were read from its web pages through a summarising web tool and transcribed; I checked them against Wikipedia where possible, but some years may be out by one, and dating the closure of merged mines is hard.
- 95 pits are placed at their village, not the pit head. For some pits I replaced the nearby town named in the table with the village where the pit stood; these changes are noted in `data/nmrs_extract.csv`.
- The comparison towns were not untouched by industrial decline.
- Census 2021 was taken during the pandemic. Census outcomes are for England and Wales only; Scottish towns are mapped but not compared. Income estimates exist only for towns with a best-fit MSOA.

## Sources and licences

- Colliery closure years: Northern Mine Research Society, Britain's nationalised coal mines from 1947 (NCB collieries in England, Wales and Scotland), https://nmrs.org.uk/resources/britains-nationalised-coal-mines-from-1947/ . Used with credit; only factual fields (names, places, years) are reproduced.
- Wikipedia (CC BY-SA 4.0, retrieved 28 October 2026): List of collieries in Yorkshire (1984 to 2015), List of collieries in Derbyshire, List of coal mines in the United Kingdom, 1984 to 1985 United Kingdom miners' strike, Coal mining in the United Kingdom, Kellingley Colliery.
- Wikidata (mine items): CC0.
- OpenStreetMap (colliery features): © OpenStreetMap contributors, Open Database Licence (ODbL), https://www.openstreetmap.org/copyright
- Census 2021 (TS001, TS007A, TS045, TS062, TS066) and Income estimates for small areas, England and Wales, financial year ending 2023: Office for National Statistics, Open Government Licence v3.0.
- OS Open Names and ONS geography (BUA22, MSOA and LSOA lookups): contains OS data © Crown copyright and database right 2026; Open Government Licence v3.0.
- Coastline: Natural Earth (public domain). Base map tiles: Esri.

The data in `data/` and the text of the page are released under CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/), because they derive from Wikipedia lists; pit coordinates derived from OpenStreetMap are available under the ODbL. The code (`code/`) is released under the MIT licence (see `LICENSE`).

## Citation

Hotham, T. (2026). Did the Pits Closing Still Show? Britain's Coalfield Towns, 1984 to 2021. Zenodo. https://doi.org/10.5281/zenodo.23729637

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
