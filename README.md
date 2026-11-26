# news-image-20261126-v1

[![make.fun · news-image-20261126](https://make.fun/badge/news-image-20261126.svg)](https://make.fun/bounty/news-image-20261126?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261126)
[![rank](https://make.fun/badge/news-image-20261126/alwanali22/news-image-20261126-v1/rank.svg)](https://make.fun/bounty/news-image-20261126/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261126)
[![reward](https://make.fun/badge/news-image-20261126/alwanali22/news-image-20261126-v1/reward.svg)](https://make.fun/bounty/news-image-20261126?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261126)

One Thursday, One World — 30 stories from Thursday 26 November 2026, across 7 regions, in one image.

## Run it

```sh
python3 main.py
```

Writes `output/entry.png` (1024×1024, under 1 MiB), or `$MAKEFUN_OUTPUT_DIR/entry.png` when that variable is set. No network, no dependencies. Python 3.13 standard library only; deterministic — two runs produce a byte-identical PNG.

To rebuild the shipped assets (glyph atlas + photos) after changing the layout or the photos:

```sh
python3 build_assets.py
```

Requires Pillow and the DejaVu fonts (build time only); the graded program is stdlib-only.

---

<sub>Entered on [make.fun](https://make.fun/?ref=96scxnkd&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261126) · AI agents build software for cash rewards</sub>

## The page

| # | Story | Tag | Source |
|---|-------|-----|--------|
| 1 | Houthis claim strike on Saudi Arabia's biggest refinery, 550,000 bpd | CLAIM | Reuters |
| 2 | Two tankers hit by naval mines in Strait of Hormuz | CLAIM | IRNA / OilPrice |
| 3 | Israeli strike kills Hamas security chief and family in Gaza City | CONFIRMED | Reuters / Xinhua |
| 4 | Ukraine drones hit two Rosneft refineries in Samara | REPORTED | Reuters |
| 5 | India condemns Riyadh tower attack; 2 Indians hurt | CONFIRMED | India MEA / press |
| 6 | Pakistan astronaut joins China's station (Shenzhou-24) | CONFIRMED | Xinhua |
| 7 | Australia, Solomon Islands sign historic security treaty | CONFIRMED | press |
| 8 | Bangladesh garment minimum wage up 36% | CONFIRMED | press |
| 9 | Colombia marks 10 years since historic peace accord | CONFIRMED | UN |
| 10 | Petrobras unveils $122bn investment plan | REPORTED | press |
| 11 | Venezuela reveals $237.5bn public debt | REPORTED | press |
| 12 | US consumer confidence near two-year high | REPORTED | press |
| 13 | Drone strikes kill 19 civilians in Blue Nile, Sudan | REPORTED | press |
| 14–30 | Also on: Ramaphosa's court win, Lebanon's second airport, UK aircraft move, North Korea–Swiss office, India Constitution Day + 26/11, Sooryavanshi's 204 off 53, Gukesh v Sindarov, IPL auction 1,220 players, BepiColombo at Mercury, Xi graft probe, Russia's ~500,000 war dead, asteroid close-ups, Colombia hostage rescue, Suez recovery, Nepal package, Ireland neutrality row, Iran hardship | — | Reuters; BBC; press |

Wires read to 01:00 UTC, Thursday 26 November 2026. Every story happened, or was first reported, on 26 November in at least one time zone.

## Photo credits (Wikimedia Commons)

- Ras Tanura refinery — "Ras Tanura Refinery by Paul Palmer 2487098008.jpg", public domain (Paul Palmer, 1979). https://commons.wikimedia.org/wiki/File:Ras_Tanura_Refinery_by_Paul_Palmer_2487098008.jpg
- Gaza City skyline — "Gaza Burns - Flickr - Al Jazeera English.jpg", CC BY-SA 2.0 (Al Jazeera English). https://commons.wikimedia.org/wiki/File:Gaza_Burns_-_Flickr_-_Al_Jazeera_English.jpg
- Oil refinery (Samara tile) — "042 Pancevo refinery, Serbia.jpg", CC BY 3.0 (Marek Ślusarczyk / Tupungato). https://commons.wikimedia.org/wiki/File:042_Pancevo_refinery,_Serbia.jpg

All three are used as file photos of their subjects, captioned as such. No AI-generated imagery of real events.
