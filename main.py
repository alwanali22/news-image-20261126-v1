#!/usr/bin/env python3
"""news-image-20261126 v1 — "One Thursday, One World".

A one-page newspaper, 1024x1024, summing up Thursday 26 November
2026: 30 stories, 7 regions. The three lead stories carry real
Wikimedia file photographs (Ras Tanura refinery, Gaza City skyline,
an oil refinery for Samara); the Hormuz lead is a flat illustration
drawn in code, as are the other mid tiles and the world map.
Python 3.13 stdlib only, no network at grading time: main.py reads
atlas.bin.gz and photo_*.rgb.gz from its own directory and writes
$MAKEFUN_OUTPUT_DIR/entry.png (or ./output/entry.png when unset).

Deterministic: fixed zlib level, no timestamps, no randomness, no
iteration over unordered data. Two runs write byte-identical PNGs.

Every number below appears in exactly one version on the page
(stat bar = headline = list). Wires read to 01:00 UTC, Thursday
26 November 2026. Sources: Reuters, Xinhua, BBC, OilPrice, UN.
"""
import gzip
import os
import struct
import sys
import zlib

W, H = 1024, 1024
HERE = os.path.dirname(os.path.abspath(__file__))

# Palette — newsprint paper, ink, one red accent, muted blues/greys.
PAPER = (247, 243, 234)
INK = (22, 22, 22)
RED = (176, 30, 36)
NAVY = (31, 58, 95)
GREY = (96, 96, 96)
FAINT = (216, 210, 196)
PALE = (238, 233, 220)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SEA = (172, 202, 226)
LAND = (233, 226, 206)
STEEL = (74, 82, 92)
GOLD = (214, 164, 32)
GREEN = (46, 125, 60)
TEAL = (32, 110, 110)


# ---------------------------------------------------------------- PNG out
def _chunk(ctype, data):
    out = struct.pack(">I", len(data)) + ctype + data
    out += struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)
    return out


def write_png(path, w, h, rgb):
    """Write RGB bytes (row-major, 3 bytes/px) as a deterministic PNG."""
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 6)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += _chunk(b"IDAT", comp)
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


# ---------------------------------------------------------------- assets
def load_atlas(path):
    """Parse atlas.bin.gz into {name: (px, ascent, {cp: glyph})}.

    Glyph tuple: (advance, xoff, yoff, w, h, packed_rows).
    Format written by build_assets.py: magic b"ATL3", u32 font count;
    per font: u8 name length, name, u16 px, u16 ascent, u16 descent,
    u16 glyph count; per glyph: u32 cp, u16 advance, i16 xoff,
    i16 yoff, u16 w, u16 h, then the packed rows.
    """
    raw = gzip.open(path, "rb").read()
    assert raw[:4] == b"ATL3", "bad atlas magic"
    pos = 4
    nfonts = struct.unpack_from(">I", raw, pos)[0]
    pos += 4
    fonts = {}
    for _ in range(nfonts):
        nlen = raw[pos]
        pos += 1
        name = raw[pos:pos + nlen].decode("ascii")
        pos += nlen
        px, ascent, descent, ng = struct.unpack_from(">HHHH", raw, pos)
        pos += 8
        glyphs = {}
        for _ in range(ng):
            cp, adv, xoff, yoff, gw, gh = struct.unpack_from(">IHhhHH", raw, pos)
            pos += 14
            stride = (gw + 7) // 8
            packed = raw[pos:pos + stride * gh]
            pos += stride * gh
            glyphs[cp] = (adv, xoff, yoff, gw, gh, packed)
        fonts[name] = (px, ascent, glyphs)
    return fonts


def load_photo(name):
    """Load photo_<name>.rgb.gz (raw RGB bytes, size known by caller)."""
    path = os.path.join(HERE, f"photo_{name}.rgb.gz")
    return gzip.open(path, "rb").read()


# ---------------------------------------------------------------- canvas
class Page:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg * (w * h))

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(color)

    def rect(self, x0, y0, x1, y1, color):
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w, x1)
        y1 = min(self.h, y1)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for y in range(y0, y1):
            i = (y * self.w + x0) * 3
            self.px[i:i + (x1 - x0) * 3] = row

    def hline(self, x0, x1, y, color, thick=1):
        for t in range(thick):
            self.rect(x0, y + t, x1, y + t + 1, color)

    def vline(self, x, y0, y1, color, thick=1):
        for t in range(thick):
            self.rect(x + t, y0, x + t + 1, y1, color)

    def disc(self, cx, cy, r, color):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) * (x - cx) + (y - cy) * (y - cy) <= r * r:
                    self.set(x, y, color)

    def line(self, x0, y0, x1, y1, color, thick=1):
        """Bresenham line with square thickness."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        half = thick // 2
        while True:
            self.rect(x - half, y - half, x - half + thick, y - half + thick,
                      color)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def poly(self, pts, color):
        """Scanline fill of a simple polygon (even-odd rule)."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.rect(int(xs[i]), y, int(xs[i + 1]) + 1, y + 1, color)

    def blit(self, x0, y0, w, h, rgb):
        """Copy raw RGB rows onto the page, clipped."""
        for y in range(h):
            yy = y0 + y
            if yy < 0 or yy >= self.h:
                continue
            row = rgb[y * w * 3:(y + 1) * w * 3]
            sx0 = max(0, -x0)
            sx1 = min(w, self.w - x0)
            if sx1 <= sx0:
                continue
            i = (yy * self.w + x0 + sx0) * 3
            self.px[i:i + (sx1 - sx0) * 3] = row[sx0 * 3:sx1 * 3]


# ---------------------------------------------------------------- text
class Typer:
    def __init__(self, fonts):
        self.fonts = fonts

    def width(self, font_name, text):
        _, _, glyphs = self.fonts[font_name]
        total = 0
        for ch in text:
            g = glyphs.get(ord(ch))
            if g is None:
                g = glyphs.get(32)
            total += g[0]
        return total

    def draw(self, page, font_name, x, baseline, text, color):
        _, _, glyphs = self.fonts[font_name]
        pen = x
        for ch in text:
            g = glyphs.get(ord(ch))
            if g is None:
                g = glyphs.get(32)
            adv, xoff, yoff, gw, gh, packed = g
            if gw and gh:
                stride = (gw + 7) // 8
                for gy in range(gh):
                    for gx in range(gw):
                        if packed[gy * stride + gx // 8] & (0x80 >> (gx % 8)):
                            page.set(pen + xoff + gx, baseline + yoff + gy,
                                     color)
            pen += adv
        return pen

    def draw_centred(self, page, font_name, cx, baseline, text, color):
        w = self.width(font_name, text)
        return self.draw(page, font_name, cx - w // 2, baseline, text, color)

    def wrap(self, font_name, text, max_w):
        """Greedy word wrap; returns lines that fit max_w."""
        words = text.split(" ")
        lines = []
        cur = ""
        for word in words:
            trial = word if not cur else cur + " " + word
            if self.width(font_name, trial) <= max_w:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines

    def draw_wrapped(self, page, font_name, x, baseline, text, color,
                     max_w, line_h, max_lines=None):
        lines = self.wrap(font_name, text, max_w)
        if max_lines is not None:
            lines = lines[:max_lines]
        y = baseline
        for line in lines:
            self.draw(page, font_name, x, y, line, color)
            y += line_h
        return y


# ---------------------------------------------------------------- stories
MASTHEAD = "ONE THURSDAY, ONE WORLD"
DATE_LINE = "THURSDAY, 26 NOVEMBER 2026"
SUBHEAD = ("30 STORIES \u00b7 7 REGIONS \u00b7 EVERY ONE DATED "
           "THURSDAY 26 NOVEMBER 2026")

# One consistent version of each number, used in stat bar, headlines
# and the story list alike.
STATS = [
    ("550,000", "BPD \u00b7 RAS TANURA"),
    ("4", "DRONES DOWNED"),
    ("$93.60", "BRENT +2.41%"),
    ("2", "TANKERS MINED"),
    ("55%", "REFINING DISABLED"),
    ("204", "RUNS \u00b7 53 BALLS"),
]

STRIP = ("UTC WIRES \u00b7 06:00 SAMARA FIRES \u00b7 09:05 GAZA STRIKE \u00b7 "
         "13:51 GAZA DEAD \u00b7 15:16 BRENT $93.60 \u00b7 15:28 RAS TANURA "
         "CLAIM \u00b7 17:35 SMOKE 600 SQ KM")

REGIONS = [
    ("MIDDLE EAST", 6, (176, 30, 36)),
    ("EUROPE", 4, (31, 58, 95)),
    ("ASIA-PACIFIC", 6, (46, 125, 60)),
    ("SOUTH ASIA", 4, (214, 164, 32)),
    ("AMERICAS", 5, (120, 82, 40)),
    ("AFRICA", 3, (32, 110, 110)),
    ("WORLD", 2, (74, 82, 92)),
]

LEAD1 = {
    "kicker": "MIDDLE EAST \u2014 CLAIM \u00b7 REUTERS",
    "headline": "HOUTHIS CLAIM STRIKE ON SAUDI ARABIA'S BIGGEST REFINERY",
    "deck": ("Houthis say they hit the 550,000 bpd Ras Tanura refinery and "
             "Riyadh\u2019s financial district; the coalition says 4 drones "
             "were destroyed over Ras Tanura. Satellite images show black "
             "smoke over ~600 sq km. Brent $93.60 (+2.41%)."),
    "photo": "rastanura",
    "caption": "Ras Tanura refinery, Saudi Arabia (file photo)",
}

LEAD2 = {
    "kicker": "STRAIT OF HORMUZ \u2014 CLAIM \u00b7 IRNA / OILPRICE",
    "headline": "TWO TANKERS HIT BY NAVAL MINES IN STRAIT OF HORMUZ",
    "deck": ("Fires in the engine rooms, the IRGC Navy says via IRNA; "
             "near-daily incidents for weeks. UKMTO and JMIC: claims "
             "unconfirmed."),
    "scene": "tanker",
    "caption": "Tanker in the Strait of Hormuz (illustration)",
}

LEAD3 = {
    "kicker": "GAZA \u2014 CONFIRMED \u00b7 REUTERS / XINHUA",
    "headline": "ISRAELI STRIKE KILLS HAMAS SECURITY CHIEF AND FAMILY",
    "deck": ("Col. Mohammad Abuelouf, 47, his wife Noura, 41, and daughters "
             "Yusra, 15, and Jana, 13, killed in Al-Shati camp, Gaza City "
             "\u2014 the 2nd senior Hamas security official killed in 24 "
             "hours. IDF confirms the strike; the ceasefire is under strain."),
    "photo": "gaza",
    "caption": "Gaza City skyline (file photo)",
}

# Ten mid stories, 4-13. Each tile: a flat illustration drawn in code
# (key = the scene function in SCENES below), except no. 4, which
# carries a real refinery file photo; a kicker with its certainty tag
# and a headline. No deck — the tile is 188px wide.
MIDS = [
    {"n": 4, "scene": "photo_samara", "bg": (228, 228, 232),
     "kicker": "SAMARA \u2014 REPORTED",
     "headline": "UKRAINE DRONES HIT TWO ROSNEFT REFINERIES"},
    {"n": 5, "scene": "tower", "bg": (244, 228, 228),
     "kicker": "RIYADH \u2014 CONFIRMED",
     "headline": "INDIA CONDEMNS RIYADH TOWER ATTACK; 2 HURT"},
    {"n": 6, "scene": "rocket", "bg": (222, 236, 244),
     "kicker": "SPACE \u2014 CONFIRMED",
     "headline": "PAKISTAN ASTRONAUT JOINS CHINA'S STATION"},
    {"n": 7, "scene": "treaty", "bg": (232, 240, 232),
     "kicker": "PACIFIC \u2014 CONFIRMED",
     "headline": "AUSTRALIA, SOLOMONS SIGN HISTORIC TREATY"},
    {"n": 8, "scene": "factory", "bg": (238, 233, 220),
     "kicker": "DHAKA \u2014 CONFIRMED",
     "headline": "GARMENT MINIMUM WAGE UP 36%"},
    {"n": 9, "scene": "dove", "bg": (222, 236, 244),
     "kicker": "PEACE \u2014 CONFIRMED",
     "headline": "10 YEARS SINCE HISTORIC PEACE ACCORD"},
    {"n": 10, "scene": "chart", "bg": (244, 228, 228),
     "kicker": "BRAZIL \u2014 REPORTED",
     "headline": "PETROBRAS UNVEILS $122BN INVESTMENT PLAN"},
    {"n": 11, "scene": "coins", "bg": (238, 233, 220),
     "kicker": "CARACAS \u2014 REPORTED",
     "headline": "VENEZUELA REVEALS $237.5BN PUBLIC DEBT"},
    {"n": 12, "scene": "flag", "bg": (222, 236, 244),
     "kicker": "USA \u2014 REPORTED",
     "headline": "CONSUMER CONFIDENCE NEAR TWO-YEAR HIGH"},
    {"n": 13, "scene": "drone", "bg": (228, 228, 232),
     "kicker": "SUDAN \u2014 REPORTED",
     "headline": "DRONE STRIKES KILL 19 CIVILIANS IN BLUE NILE"},
]

ALSO = [
    "S. AFRICA \u2014 RAMAPHOSA WINS CASH-THEFT CASE",
    "LEBANON \u2014 SECOND AIRPORT PLANNED",
    "UK \u2014 AIRCRAFT MOVED AMID DRONE THREAT",
    "N. KOREA \u2014 SWISS OFFICE IN PYONGYANG TO CLOSE",
    "INDIA \u2014 77TH CONSTITUTION DAY; 26/11 REMEMBERED",
    "SOORYAVANSHI, 15 \u2014 RECORD 204 OFF 53 BALLS",
    "CHESS \u2014 GUKESH v SINDAROV, WORLD TITLE, GENEVA",
    "IPL \u2014 1,220 PLAYERS REGISTER FOR 2027 AUCTION",
    "BEPICOLOMBO REACHES MERCURY AFTER 8-YEAR TRIP",
    "CHINA \u2014 XI GRAFT PROBE OF SHANGHAI RISING STAR",
    "RUSSIA \u2014 NEARLY 500,000 LOST IN UKRAINE WAR",
    "ASTEROID \u2014 CLOSE-UPS DUE OF DEFENCE-TEST ROCK",
    "COLOMBIA \u2014 20 FREED AFTER 17-HOUR SIEGE",
    "EGYPT \u2014 SUEZ CANAL REVENUES RECOVERING",
    "NEPAL \u2014 INDIA ANNOUNCES \u20b915,000 CRORE PACKAGE",
    "IRELAND \u2014 NEUTRALITY ROW OVER PEACEKEEPING",
    "IRAN \u2014 FINANCIAL HARDSHIP DEEPENS",
]

DATE_CHECK = [
    "DATE CHECK \u2014 Wires read up to 01:00 UTC, Thu 26 Nov 2026. "
    "Every story happened, or was first reported, on 26 Nov in at "
    "least one time zone.",
    "Left out on purpose: KAFD tower hit (Tue 24 Nov) \u00b7 Ras Tanura "
    "Oct 27 claim \u00b7 Hormuz mines 16\u201317 Nov \u00b7 Ilsky/Afipsky "
    "fires (18 Nov) \u00b7 Peru quake (Fri 20 Nov).",
    "Not yet decided: Brent close \u00b7 Gukesh\u2013Sindarov opener \u00b7 "
    "IPL shortlist. Photos: Wikimedia Commons (file photos); "
    "scenes/map drawn in code. PRESS TIME 01:00 UTC.",
]

# World map pins: (story no., longitude, latitude, nudge dx, nudge dy).
PINS = [
    (1, 50.0, 26.6, 6, -10),     # Ras Tanura
    (2, 56.5, 26.6, 16, 6),      # Strait of Hormuz
    (3, 34.5, 31.5, -6, -4),     # Gaza City
    (4, 50.1, 53.2, 0, -8),      # Samara
    (5, 46.7, 24.7, -12, 10),    # Riyadh
    (6, 100.3, 40.9, 0, 0),      # Jiuquan (Shenzhou-24)
    (7, 160.0, -9.6, 0, 0),      # Solomon Islands
    (8, 90.4, 23.8, 0, 0),       # Dhaka
    (9, -74.0, 4.7, 0, 0),       # Bogota
    (10, -47.9, -15.8, 0, 0),    # Brasilia
    (11, -66.9, 10.5, 0, 0),     # Caracas
    (12, -77.0, 38.9, 0, 0),     # Washington
    (13, 34.3, 11.2, 14, 8),     # Blue Nile, Sudan
]

# Simplified continent outlines (lon, lat), drawn as flat landmasses.
CONTINENTS = [
    # North America
    [(-168, 66), (-158, 58), (-152, 60), (-140, 60), (-130, 54),
     (-125, 49), (-124, 42), (-120, 34), (-114, 29), (-110, 24),
     (-105, 20), (-97, 16), (-94, 17), (-90, 14), (-86, 12),
     (-83, 9), (-79, 9), (-81, 13), (-84, 16), (-87, 21),
     (-90, 21), (-91, 19), (-97, 26), (-93, 30), (-89, 30),
     (-84, 30), (-81, 25), (-80, 32), (-76, 35), (-74, 40),
     (-70, 42), (-68, 45), (-65, 44), (-60, 47), (-55, 47),
     (-60, 52), (-64, 58), (-68, 58), (-72, 62), (-78, 62),
     (-85, 66), (-92, 66), (-95, 69), (-110, 68), (-125, 70),
     (-140, 70), (-155, 71), (-165, 68)],
    # South America
    [(-79, 9), (-77, 4), (-80, -3), (-81, -6), (-77, -12),
     (-72, -18), (-70, -23), (-70, -30), (-72, -37), (-73, -44),
     (-74, -50), (-69, -52), (-66, -55), (-68, -50), (-65, -45),
     (-62, -41), (-58, -35), (-52, -32), (-48, -28), (-41, -23),
     (-39, -17), (-35, -9), (-35, -6), (-40, -3), (-44, -2),
     (-50, 0), (-53, 4), (-58, 6), (-62, 9), (-68, 11),
     (-72, 12), (-76, 10)],
    # Eurasia
    [(-10, 36), (-9, 43), (-2, 44), (-4, 48), (0, 51), (3, 53),
     (8, 57), (10, 59), (5, 62), (12, 65), (18, 69), (30, 70),
     (45, 68), (60, 69), (68, 70), (70, 68), (75, 72), (90, 75),
     (105, 73), (120, 70), (135, 62), (142, 59), (142, 54),
     (141, 50), (138, 46), (132, 43), (127, 40), (122, 38),
     (120, 35), (122, 31), (118, 25), (110, 21), (106, 20),
     (108, 18), (105, 9), (103, 1), (100, 8), (95, 16),
     (91, 22), (88, 22), (85, 19), (80, 13), (80, 7),
     (76, 10), (72, 20), (66, 25), (60, 25), (57, 26),
     (54, 27), (50, 29), (48, 30), (44, 30), (43, 29),
     (40, 31), (36, 33), (36, 36), (30, 36), (26, 38),
     (23, 36), (19, 40), (15, 44), (12, 44), (8, 44),
     (3, 42), (0, 40), (-2, 37), (-6, 36)],
    # Africa
    [(-6, 35), (-10, 31), (-15, 27), (-17, 21), (-17, 15),
     (-15, 11), (-13, 8), (-8, 5), (-4, 5), (2, 6), (6, 4),
     (9, 4), (9, 0), (12, -4), (13, -8), (12, -12), (13, -17),
     (12, -22), (14, -27), (16, -29), (19, -34), (20, -35),
     (25, -34), (28, -33), (32, -29), (35, -24), (36, -20),
     (40, -15), (40, -10), (42, -5), (46, -1), (51, 2),
     (51, 11), (48, 11), (44, 11), (40, 15), (39, 18),
     (37, 22), (35, 28), (33, 31), (30, 31), (25, 32),
     (20, 32), (15, 32), (11, 34), (10, 37), (5, 37),
     (0, 36)],
    # Australia
    [(113, -22), (114, -30), (115, -34), (118, -35), (124, -33),
     (129, -32), (132, -32), (135, -35), (138, -35), (140, -38),
     (142, -39), (145, -38), (147, -39), (150, -37), (153, -32),
     (153, -27), (150, -23), (146, -19), (142, -11), (142, -15),
     (137, -12), (135, -12), (132, -12), (130, -13), (126, -14),
     (122, -17), (118, -20), (114, -22)],
    # United Kingdom
    [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (0, 53),
     (1, 51), (-3, 50)],
    # Japan
    [(130, 31), (132, 33), (134, 34), (136, 35), (138, 35),
     (140, 37), (141, 39), (141, 41), (140, 43), (142, 44),
     (144, 44), (143, 42), (141, 40), (139, 38), (137, 36),
     (135, 34), (133, 34), (131, 32)],
    # New Zealand
    [(167, -45), (168, -47), (170, -43), (174, -41), (176, -38),
     (178, -38), (175, -40), (172, -43), (168, -46)],
]


# ---------------------------------------------------------------- scenes
# Flat illustrations for the mid tiles and the Hormuz lead. Each draws
# inside the box (x, y, w, h) — the caller paints the tile background
# first. The Samara tile instead blits its file photo (see render).

def _scene_tanker(page, x, y, w, h):
    page.rect(x + 20, y + 26, x + 148, y + 40, (40, 48, 60))
    page.poly([(x + 148, y + 26), (x + 168, y + 33), (x + 148, y + 40)],
              (40, 48, 60))
    page.rect(x + 56, y + 16, x + 72, y + 26, RED)
    page.rect(x + 84, y + 20, x + 128, y + 26, WHITE)
    page.hline(x + 8, x + 60, y + 46, (58, 124, 188), 2)
    page.hline(x + 90, x + 170, y + 46, (58, 124, 188), 2)
    page.hline(x + 30, x + 140, y + 50, (58, 124, 188), 2)
    # A naval mine, floating: spiked black disc with a red glint.
    page.disc(x + 168, y + 12, 5, BLACK)
    page.line(x + 168, y + 4, x + 168, y + 20, BLACK, 1)
    page.line(x + 160, y + 12, x + 176, y + 12, BLACK, 1)
    page.disc(x + 170, y + 10, 2, RED)


def _scene_tower(page, x, y, w, h):
    page.rect(x + 66, y + 4, x + 122, y + 50, (31, 58, 95))
    for r in range(4):
        for c in range(4):
            page.rect(x + 72 + c * 13, y + 10 + r * 10,
                      x + 80 + c * 13, y + 16 + r * 10, (220, 228, 235))
    page.rect(x + 122, y + 20, x + 150, y + 50, (74, 82, 92))
    page.rect(x + 38, y + 30, x + 66, y + 50, (120, 128, 140))
    page.poly([(x + 80, y + 4), (x + 94, y + 0), (x + 108, y + 4)],
              RED)
    page.disc(x + 94, y + 12, 4, GOLD)


def _scene_rocket(page, x, y, w, h):
    page.poly([(x + 88, y + 2), (x + 100, y + 2), (x + 104, y + 20),
               (x + 84, y + 20)], WHITE)
    page.poly([(x + 88, y + 2), (x + 94, y + 2), (x + 94, y + 10),
               (x + 88, y + 10)], RED)
    page.poly([(x + 84, y + 20), (x + 78, y + 32), (x + 84, y + 28)],
              RED)
    page.poly([(x + 104, y + 20), (x + 110, y + 32), (x + 104, y + 28)],
              RED)
    page.poly([(x + 90, y + 32), (x + 94, y + 32), (x + 98, y + 46),
               (x + 94, y + 50), (x + 90, y + 46)], GOLD)
    page.disc(x + 20, y + 12, 2, GOLD)
    page.disc(x + 160, y + 8, 2, GOLD)
    page.disc(x + 150, y + 40, 2, GOLD)
    page.disc(x + 30, y + 40, 2, GOLD)


def _scene_treaty(page, x, y, w, h):
    page.rect(x + 58, y + 6, x + 130, y + 48, WHITE)
    page.hline(x + 58, x + 130, y + 6, STEEL, 1)
    page.hline(x + 58, x + 130, y + 48, STEEL, 1)
    page.vline(x + 58, y + 6, y + 48, STEEL, 1)
    page.vline(x + 130, y + 6, y + 48, STEEL, 1)
    page.hline(x + 66, x + 122, y + 14, GREY, 1)
    page.hline(x + 66, x + 122, y + 20, GREY, 1)
    page.hline(x + 66, x + 122, y + 26, GREY, 1)
    page.hline(x + 66, x + 100, y + 32, GREY, 1)
    page.disc(x + 112, y + 40, 6, RED)
    page.line(x + 130, y + 30, x + 158, y + 44, STEEL, 2)
    page.poly([(x + 152, y + 38), (x + 158, y + 44), (x + 152, y + 50)],
              STEEL)


def _scene_factory(page, x, y, w, h):
    page.rect(x + 14, y + 22, x + 120, y + 50, (74, 82, 92))
    page.poly([(x + 14, y + 22), (x + 34, y + 8), (x + 54, y + 22)],
              (74, 82, 92))
    page.poly([(x + 54, y + 22), (x + 74, y + 8), (x + 94, y + 22)],
              (74, 82, 92))
    page.rect(x + 128, y + 10, x + 138, y + 50, STEEL)
    page.rect(x + 148, y + 18, x + 158, y + 50, STEEL)
    for cx in (24, 48, 72, 96):
        page.rect(x + cx, y + 30, x + cx + 12, y + 40, (220, 228, 235))
    page.disc(x + 168, y + 14, 5, GOLD)
    page.hline(x + 8, x + 180, y + 50, STEEL, 1)


def _scene_dove(page, x, y, w, h):
    page.poly([(x + 60, y + 14), (x + 110, y + 6), (x + 130, y + 16),
               (x + 100, y + 30), (x + 70, y + 30)], WHITE)
    page.poly([(x + 96, y + 8), (x + 120, y + 2), (x + 118, y + 16)],
              WHITE)
    page.disc(x + 128, y + 14, 5, WHITE)
    page.poly([(x + 132, y + 12), (x + 140, y + 14), (x + 132, y + 16)],
              GOLD)
    page.disc(x + 130, y + 13, 1, INK)
    page.poly([(x + 60, y + 14), (x + 70, y + 30), (x + 56, y + 34)],
              WHITE)
    page.line(x + 30, y + 42, x + 158, y + 42, GREEN, 2)
    page.disc(x + 40, y + 38, 3, GREEN)
    page.disc(x + 148, y + 38, 3, GREEN)


def _scene_chart(page, x, y, w, h):
    page.hline(x + 10, x + w - 10, y + 16, FAINT, 1)
    page.hline(x + 10, x + w - 10, y + 30, FAINT, 1)
    page.hline(x + 10, x + w - 10, y + 44, FAINT, 1)
    page.line(x + 12, y + 10, x + 12, y + 46, STEEL, 1)
    page.line(x + 12, y + 46, x + w - 12, y + 46, STEEL, 1)
    page.line(x + 16, y + 40, x + 60, y + 30, GREEN, 2)
    page.line(x + 60, y + 30, x + 110, y + 18, GREEN, 2)
    page.line(x + 110, y + 18, x + 164, y + 8, GREEN, 2)
    page.poly([(x + 164, y + 8), (x + 154, y + 8), (x + 160, y + 16)],
              GREEN)


def _scene_coins(page, x, y, w, h):
    for i, (cx, cy, col) in enumerate(
            [(60, 36, GOLD), (86, 30, GOLD), (112, 36, GOLD),
             (73, 18, (200, 150, 40)), (99, 18, (200, 150, 40))]):
        page.disc(x + cx, y + cy, 11, col)
        page.disc(x + cx, y + cy, 8, (240, 210, 120))
    page.rect(x + 130, y + 10, x + 170, y + 46, WHITE)
    page.hline(x + 136, x + 164, y + 18, GREY, 1)
    page.hline(x + 136, x + 164, y + 24, GREY, 1)
    page.hline(x + 136, x + 164, y + 30, GREY, 1)
    page.hline(x + 136, x + 164, y + 36, RED, 2)


def _scene_flag(page, x, y, w, h):
    for i in range(7):
        col = RED if i % 2 == 0 else WHITE
        page.rect(x + 40, y + 8 + i * 5, x + 148, y + 8 + (i + 1) * 5, col)
    page.rect(x + 40, y + 8, x + 84, y + 28, NAVY)
    for r in range(3):
        for c in range(4):
            page.disc(x + 48 + c * 9, y + 13 + r * 6, 1, WHITE)
    page.line(x + 40, y + 4, x + 40, y + 50, STEEL, 2)


def _scene_drone(page, x, y, w, h):
    page.rect(x + 70, y + 22, x + 118, y + 34, STEEL)
    page.disc(x + 94, y + 28, 6, (40, 48, 60))
    page.line(x + 70, y + 28, x + 30, y + 14, STEEL, 2)
    page.line(x + 118, y + 28, x + 158, y + 14, STEEL, 2)
    page.line(x + 70, y + 28, x + 30, y + 42, STEEL, 2)
    page.line(x + 118, y + 28, x + 158, y + 42, STEEL, 2)
    page.hline(x + 16, x + 44, y + 14, INK, 2)
    page.hline(x + 144, x + 172, y + 14, INK, 2)
    page.hline(x + 16, x + 44, y + 42, INK, 2)
    page.hline(x + 144, x + 172, y + 42, INK, 2)
    page.disc(x + 94, y + 46, 3, RED)


SCENES = {
    "tanker": _scene_tanker,
    "tower": _scene_tower,
    "rocket": _scene_rocket,
    "treaty": _scene_treaty,
    "factory": _scene_factory,
    "dove": _scene_dove,
    "chart": _scene_chart,
    "coins": _scene_coins,
    "flag": _scene_flag,
    "drone": _scene_drone,
}

PHOTO_SIZE = {"rastanura": (440, 210), "gaza": (476, 126),
              "samara": (188, 46)}


# ---------------------------------------------------------------- map
def draw_map(page, t, x0, y0, w, h):
    page.rect(x0, y0, x0 + w, y0 + h, SEA)

    def px(lon):
        return x0 + (lon + 170.0) / 360.0 * w

    def py(lat):
        return y0 + (78.0 - lat) / 136.0 * h

    for cont in CONTINENTS:
        pts = [(int(px(lon)), int(py(lat))) for lon, lat in cont]
        page.poly(pts, LAND)
    t.draw(page, "map9", x0 + 4, y0 + 10, "WORLD \u2014 PINS 1\u201313", NAVY)
    for n, lon, lat, dx, dy in PINS:
        cx = int(px(lon)) + dx
        cy = int(py(lat)) + dy
        page.disc(cx, cy, 6, WHITE)
        page.disc(cx, cy, 5, RED)
        t.draw_centred(page, "map9", cx, cy + 3, str(n), WHITE)
    page.hline(x0, x0 + w, y0, STEEL, 1)
    page.hline(x0, x0 + w, y0 + h - 1, STEEL, 1)
    page.vline(x0, y0, y0 + h, STEEL, 1)
    page.vline(x0 + w - 1, y0, y0 + h, STEEL, 1)


# ---------------------------------------------------------------- render
def render(fonts, photos):
    page = Page(W, H, PAPER)
    t = Typer(fonts)

    # Masthead.
    t.draw_centred(page, "mast", 512, 48, MASTHEAD, INK)
    page.hline(28, 996, 58, RED, 3)
    t.draw_centred(page, "date", 512, 86, DATE_LINE, RED)
    t.draw_centred(page, "sub", 512, 104, SUBHEAD, NAVY)

    # Stat bar: six big numbers, one consistent version each.
    for i, (num, lab) in enumerate(STATS):
        x = 28 + i * 162
        page.rect(x, 110, x + 158, 150, PALE)
        page.hline(x, x + 158, 110, RED, 2)
        t.draw_centred(page, "stat20", x + 79, 135, num, RED)
        t.draw_centred(page, "stat10", x + 79, 147, lab, INK)

    # UTC wire strip.
    t.draw_centred(page, "strip11", 512, 168, STRIP, INK)

    # Region bar: segment widths proportional to story counts.
    x = 28
    cum = 0
    for name, cnt, col in REGIONS:
        cum += cnt
        x_end = 28 + round(cum / 30.0 * 968)
        page.rect(x, 174, x_end, 190, col)
        t.draw_centred(page, "sub", (x + x_end) // 2, 186,
                       f"{name} {cnt}", WHITE)
        x = x_end

    # Lead story 1, photo left, text right.
    pw, ph = PHOTO_SIZE["rastanura"]
    page.blit(28, 196, pw, ph, photos["rastanura"])
    page.rect(28, 196, 52, 220, RED)
    t.draw_centred(page, "kick12", 40, 213, "1", WHITE)
    page.rect(28, 390, 468, 406, BLACK)
    t.draw(page, "check10", 36, 402, LEAD1["caption"], WHITE)
    t.draw(page, "kick12", 484, 212, LEAD1["kicker"], RED)
    hlines = t.wrap("head28", LEAD1["headline"], 512)
    t.draw_wrapped(page, "head28", 484, 248, LEAD1["headline"], INK,
                   512, 33, 3)
    deck_y = 248 + (len(hlines) - 1) * 33 + 27
    t.draw_wrapped(page, "deck14", 484, deck_y, LEAD1["deck"], INK,
                   512, 19, 4)

    # Lead stories 2 and 3, side by side.
    for i, card in enumerate((LEAD2, LEAD3)):
        cx = 28 + i * 492
        if "photo" in card:
            pw, ph = PHOTO_SIZE[card["photo"]]
            page.blit(cx, 414, pw, ph, photos[card["photo"]])
        else:
            pw, ph = 476, 126
            page.rect(cx, 414, cx + pw, 414 + ph, (222, 236, 244))
            SCENES[card["scene"]](page, cx, 414, pw, ph)
        page.rect(cx, 414, cx + 24, 438, RED)
        t.draw_centred(page, "kick12", cx + 12, 431, str(i + 2), WHITE)
        page.rect(cx, 524, cx + 476, 540, BLACK)
        t.draw(page, "check10", cx + 8, 536, card["caption"], WHITE)
        t.draw(page, "kick12", cx, 554, card["kicker"], RED)
        hlines = t.wrap("head21", card["headline"], 476)
        t.draw_wrapped(page, "head21", cx, 580, card["headline"],
                       INK, 476, 25, 2)
        deck_y = 580 + (len(hlines) - 1) * 25 + 19
        t.draw_wrapped(page, "deck12", cx, deck_y, card["deck"], INK,
                       476, 15, 2)

    # Mid stories 4-13, two rows of five tiles.
    for row in range(2):
        for col in range(5):
            mid = MIDS[row * 5 + col]
            tx = 28 + col * 195
            ty = 660 + row * 92
            if mid["scene"] == "photo_samara":
                pw, ph = PHOTO_SIZE["samara"]
                page.blit(tx, ty, pw, ph, photos["samara"])
            else:
                page.rect(tx, ty, tx + 188, ty + 46, mid["bg"])
                SCENES[mid["scene"]](page, tx, ty, 188, 46)
            t.draw(page, "kick12", tx, ty + 58,
                   f"{mid['n']} \u00b7 {mid['kicker']}", RED)
            t.draw_wrapped(page, "kick12", tx, ty + 72, mid["headline"],
                           INK, 188, 14, 2)

    # World map + ALSO ON list.
    t.draw(page, "kick12", 28, 852, "ALSO ON \u2014 17 MORE STORIES", RED)
    page.hline(28, 996, 858, RED, 2)
    draw_map(page, t, 28, 864, 340, 92)
    for i, item in enumerate(ALSO):
        col = i // 9
        r = i % 9
        ax = 384 + col * 300
        ay = 876 + r * 10
        num = f"{14 + i}. "
        t.draw(page, "also10", ax, ay, num, RED)
        t.draw(page, "also10", ax + t.width("also10", num), ay, item, INK)

    # Date check box, red border. The credit line and press time live
    # on its third line, so nothing hangs below the box.
    box_y0 = 962
    box_y1 = 962 + 10 + len(DATE_CHECK) * 12 + 6
    page.rect(28, box_y0, 996, box_y0 + 2, RED)
    page.rect(28, box_y1 - 2, 996, box_y1, RED)
    page.rect(28, box_y0, 30, box_y1, RED)
    page.rect(994, box_y0, 996, box_y1, RED)
    for j, line in enumerate(DATE_CHECK):
        t.draw(page, "check10", 38, box_y0 + 12 + j * 12, line, INK)
    return page


def main():
    fonts = load_atlas(os.path.join(HERE, "atlas.bin.gz"))
    photos = {name: load_photo(name) for name in PHOTO_SIZE}
    page = render(fonts, photos)
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR") or os.path.join(HERE, "output")
    os.makedirs(outdir, exist_ok=True)
    write_png(os.path.join(outdir, "entry.png"), W, H, bytes(page.px))
    print("wrote entry.png")


if __name__ == "__main__":
    sys.exit(main())
