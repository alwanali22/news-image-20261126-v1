#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One Thursday, One World - 30 stories from Thursday 26 November 2026.

Draws a one-page newspaper front page (1024x1024 PNG) summing up the
world news of Thursday 26 November 2026: masthead, six-number stat bar,
UTC wire strip, region bar, three lead stories (two with real file
photographs from Wikimedia Commons, one with a drawn illustration),
ten illustrated mid stories, a numbered world map, the 17 remaining
stories, and a red DATE CHECK box.

Everything is drawn here in code with the Python standard library only.
Glyph bitmaps and photographs come from the gzip assets beside this
file (built by build_assets.py); if an asset is missing the program
still draws the whole page, using a small built-in bitmap font and
drawn illustrations in place of the photos.

Usage: python3 main.py
Writes output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png).
"""

import gzip
import os
import struct
import sys
import zlib

W = 1024
H = 1024
HERE = os.path.dirname(os.path.abspath(__file__))

PAPER = (246, 241, 229)
INK = (17, 17, 17)
RED = (176, 24, 24)
NAVY = (28, 54, 92)
GREY = (96, 90, 78)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SKY = (213, 230, 239)
SEA = (38, 92, 122)
MAP_BG = (203, 222, 231)
MAP_LAND = (238, 228, 196)
SAND = (232, 222, 196)

# (font_id, size_px) slots, matching the atlas built by build_assets.py.
SERIF54 = (0, 54)
SERIF30 = (0, 30)
SERIF32 = (0, 32)
SERIF26 = (0, 26)
SERIF13 = (0, 13)
SERIF14 = (0, 14)
SANSB30 = (1, 30)
SANSB13 = (1, 13)
SANSB12 = (1, 12)
SANSB11 = (1, 11)
SANSB10 = (1, 10)
SANS14 = (2, 14)
SANS13 = (2, 13)
SANS11 = (2, 11)
SANS10 = (2, 10)


# --------------------------------------------------------------------------
# tiny built-in 5x7 bitmap font, used only when the atlas asset is absent
# --------------------------------------------------------------------------

_FALLBACK_ROWS = {
    "A": "01110/10001/10001/11111/10001/10001/10001",
    "B": "11110/10001/10001/11110/10001/10001/11110",
    "C": "01110/10001/10000/10000/10000/10001/01110",
    "D": "11110/10001/10001/10001/10001/10001/11110",
    "E": "11111/10000/10000/11110/10000/10000/11111",
    "F": "11111/10000/10000/11110/10000/10000/10000",
    "G": "01110/10001/10000/10111/10001/10001/01111",
    "H": "10001/10001/10001/11111/10001/10001/10001",
    "I": "01110/00100/00100/00100/00100/00100/01110",
    "J": "00111/00010/00010/00010/00010/10010/01100",
    "K": "10001/10010/10100/11000/10100/10010/10001",
    "L": "10000/10000/10000/10000/10000/10000/11111",
    "M": "10001/11011/10101/10101/10001/10001/10001",
    "N": "10001/11001/10101/10011/10001/10001/10001",
    "O": "01110/10001/10001/10001/10001/10001/01110",
    "P": "11110/10001/10001/11110/10000/10000/10000",
    "Q": "01110/10001/10001/10001/10101/10010/01101",
    "R": "11110/10001/10001/11110/10100/10010/10001",
    "S": "01111/10000/10000/01110/00001/00001/11110",
    "T": "11111/00100/00100/00100/00100/00100/00100",
    "U": "10001/10001/10001/10001/10001/10001/01110",
    "V": "10001/10001/10001/10001/10001/01010/00100",
    "W": "10001/10001/10001/10101/10101/10101/01010",
    "X": "10001/10001/01010/00100/01010/10001/10001",
    "Y": "10001/10001/01010/00100/00100/00100/00100",
    "Z": "11111/00001/00010/00100/01000/10000/11111",
    "a": "00000/00000/01110/00001/01111/10001/01111",
    "b": "10000/10000/11110/10001/10001/10001/11110",
    "c": "00000/00000/01110/10000/10000/10001/01110",
    "d": "00001/00001/01111/10001/10001/10001/01111",
    "e": "00000/00000/01110/10001/11111/10000/01110",
    "f": "00110/01001/01000/11110/01000/01000/01000",
    "g": "00000/01111/10001/10001/01111/00001/01110",
    "h": "10000/10000/11110/10001/10001/10001/10001",
    "i": "00100/00000/01100/00100/00100/00100/01110",
    "j": "00010/00000/00110/00010/00010/10010/01100",
    "k": "10000/10000/10010/10100/11000/10100/10001",
    "l": "01100/00100/00100/00100/00100/00100/01110",
    "m": "00000/00000/11010/10101/10101/10101/10101",
    "n": "00000/00000/11110/10001/10001/10001/10001",
    "o": "00000/00000/01110/10001/10001/10001/01110",
    "p": "00000/00000/11110/10001/11110/10000/10000",
    "q": "00000/00000/01111/10001/01111/00001/00001",
    "r": "00000/00000/10110/11001/10000/10000/10000",
    "s": "00000/00000/01111/10000/01110/00001/11110",
    "t": "01000/01000/11100/01000/01000/01001/00110",
    "u": "00000/00000/10001/10001/10001/10011/01101",
    "v": "00000/00000/10001/10001/10001/01010/00100",
    "w": "00000/00000/10001/10101/10101/10101/01010",
    "x": "00000/00000/10001/01010/00100/01010/10001",
    "y": "00000/00000/10001/10001/01111/00001/01110",
    "z": "00000/00000/11111/00010/00100/01000/11111",
    "0": "01110/10001/10011/10101/11001/10001/01110",
    "1": "00100/01100/00100/00100/00100/00100/01110",
    "2": "01110/10001/00001/00110/01000/10000/11111",
    "3": "11110/00001/00001/01110/00001/00001/11110",
    "4": "00010/00110/01010/10010/11111/00010/00010",
    "5": "11111/10000/11110/00001/00001/10001/01110",
    "6": "00110/01000/10000/11110/10001/10001/01110",
    "7": "11111/00001/00010/00100/01000/01000/01000",
    "8": "01110/10001/10001/01110/10001/10001/01110",
    "9": "01110/10001/10001/01111/00001/00010/01100",
    " ": "00000/00000/00000/00000/00000/00000/00000",
    ".": "00000/00000/00000/00000/00000/01100/01100",
    ",": "00000/00000/00000/00000/01100/00100/01000",
    ":": "00000/01100/01100/00000/01100/01100/00000",
    ";": "00000/01100/01100/00000/01100/00100/01000",
    "'": "00100/00100/01000/00000/00000/00000/00000",
    "-": "00000/00000/00000/01110/00000/00000/00000",
    "$": "00100/01111/10100/01110/00101/11110/00100",
    "%": "11001/11010/00010/00100/01000/01011/10011",
    "(": "00010/00100/01000/01000/01000/00100/00010",
    ")": "01000/00100/00010/00010/00010/00100/01000",
    "/": "00001/00010/00010/00100/01000/01000/10000",
    "!": "00100/00100/00100/00100/00100/00000/00100",
    "?": "01110/10001/00001/00010/00100/00000/00100",
    "+": "00000/00100/00100/11111/00100/00100/00000",
    "=": "00000/00000/11111/00000/11111/00000/00000",
    "&": "01100/10010/10100/01000/10101/10010/01101",
    '"': "01010/01010/01010/00000/00000/00000/00000",
    "~": "00000/00000/01010/10101/00000/00000/00000",
    "\u2014": "00000/00000/00000/11111/00000/00000/00000",
    "\u2013": "00000/00000/00000/01110/00000/00000/00000",
    "\u00b7": "00000/00000/00000/01100/01100/00000/00000",
    "\u2019": "00100/00100/01000/00000/00000/00000/00000",
    "\u2018": "00100/00100/01000/00000/00000/00000/00000",
    "\u201c": "01010/01010/01010/00000/00000/00000/00000",
    "\u201d": "01010/01010/01010/00000/00000/00000/00000",
    "\u20b9": "01111/10001/11110/10000/11110/10000/10000",
    "\u2026": "00000/00000/00000/00000/00000/10101/10101",
}


def _fallback_scale(size_px):
    """Bitmap scale for the fallback font at a given point size."""
    return max(1, int(round(size_px * 0.72 / 7.0)))


def _fallback_glyph(ch, size_px=14):
    """One fallback glyph as (advance, bear_x, bear_y, w, h, bitmap),
    drawn from the 5x7 patterns above, scaled to the slot size."""
    rows = _FALLBACK_ROWS.get(ch)
    if rows is None:
        rows = _FALLBACK_ROWS["?"]
    scale = _fallback_scale(size_px)
    w, h = 5 * scale, 7 * scale
    bmp = bytearray(w * h)
    for r, line in enumerate(rows.split("/")):
        for c, bit in enumerate(line):
            if bit == "1":
                for dy in range(scale):
                    for dx in range(scale):
                        bmp[(r * scale + dy) * w + c * scale + dx] = 255
    return (6 * scale, 0, 7 * scale, w, h, bytes(bmp))


# --------------------------------------------------------------------------
# asset loading
# --------------------------------------------------------------------------

def load_atlas():
    """Read atlas.bin.gz -> {(font_id, size): {char: glyph tuple}}.
    Returns an empty dict when the asset is absent."""
    path = os.path.join(HERE, "atlas.bin.gz")
    if not os.path.exists(path):
        return {}
    with gzip.open(path, "rb") as fh:
        raw = fh.read()
    if raw[:4] != b"ATL1":
        raise ValueError("bad atlas magic")
    n_slots = struct.unpack_from("<I", raw, 4)[0]
    off = 8
    slots = {}
    for _ in range(n_slots):
        size_px, fid, _zero, n_glyphs = struct.unpack_from("<HBBI", raw, off)
        off += 8
        glyphs = {}
        for _ in range(n_glyphs):
            ch, adv16, bx, by, w, h = struct.unpack_from("<IHhhHH", raw, off)
            off += 14
            bmp = raw[off:off + w * h]
            off += w * h
            glyphs[ch] = (adv16 / 16.0, bx, by, w, h, bmp)
        slots[(fid, size_px)] = glyphs
    return slots


def load_photo(name):
    """Read a photo .rgb.gz -> (width, height, rgb bytes) or None."""
    path = os.path.join(HERE, name + ".rgb.gz")
    if not os.path.exists(path):
        return None
    with gzip.open(path, "rb") as fh:
        raw = fh.read()
    if raw[:4] != b"PHO1":
        raise ValueError("bad photo magic in " + name)
    w, h = struct.unpack_from("<II", raw, 4)
    return (w, h, raw[12:12 + w * h * 3])


# --------------------------------------------------------------------------
# canvas
# --------------------------------------------------------------------------

class Canvas(object):
    def __init__(self, width, height, bg):
        self.w = width
        self.h = height
        self.px = bytearray(bytes(bg) * (width * height))
        self.atlas = load_atlas()

    # -- primitive fills ------------------------------------------------
    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, int(x))
        y0 = max(0, int(y))
        x1 = min(self.w, int(x) + int(w))
        y1 = min(self.h, int(y) + int(h))
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            o = (yy * self.w + x0) * 3
            self.px[o:o + (x1 - x0) * 3] = row

    def outline_rect(self, x, y, w, h, color, thick=1):
        self.fill_rect(x, y, w, thick, color)
        self.fill_rect(x, y + h - thick, w, thick, color)
        self.fill_rect(x, y, thick, h, color)
        self.fill_rect(x + w - thick, y, thick, h, color)

    def hline(self, x0, x1, y, color, thick=1):
        self.fill_rect(x0, y, x1 - x0, thick, color)

    def line(self, x0, y0, x1, y1, color):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.set_pixel(x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def set_pixel(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            o = (y * self.w + x) * 3
            self.px[o:o + 3] = bytes(color)

    def fill_circle(self, cx, cy, r, color):
        for yy in range(cy - r, cy + r + 1):
            span = int((r * r - (yy - cy) * (yy - cy)) ** 0.5)
            self.fill_rect(cx - span, yy, span * 2 + 1, 1, color)

    def fill_poly(self, points, color):
        """Scanline fill of a polygon (non-zero winding)."""
        if len(points) < 3:
            return
        edges = []
        n = len(points)
        for i in range(n):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % n]
            if y0 != y1:
                edges.append((x0, y0, x1, y1))
        ymin = max(0, int(min(p[1] for p in points)))
        ymax = min(self.h - 1, int(max(p[1] for p in points)))
        for yy in range(ymin, ymax + 1):
            y = yy + 0.5
            events = []
            for (x0, y0, x1, y1) in edges:
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / float(y1 - y0)
                    events.append((x0 + t * (x1 - x0), 1 if y1 > y0 else -1))
            if not events:
                continue
            events.sort(key=lambda e: e[0])
            winding = 0
            prev = None
            for (x, d) in events:
                if prev is not None and winding != 0:
                    self.fill_rect(int(prev + 0.5), yy,
                                   int(x + 0.5) - int(prev + 0.5), 1, color)
                winding += d
                prev = x

    # -- photos ----------------------------------------------------------
    def blit_photo(self, x, y, photo):
        w, h, rgb = photo
        for yy in range(h):
            dy = y + yy
            if 0 <= dy < self.h:
                src = yy * w * 3
                dst = (dy * self.w + x) * 3
                self.px[dst:dst + w * 3] = rgb[src:src + w * 3]

    # -- text ------------------------------------------------------------
    def _glyph(self, slot, ch):
        glyphs = self.atlas.get(slot)
        if glyphs is not None:
            g = glyphs.get(ord(ch))
            if g is not None:
                return g
            if ch == " ":
                return (self._space_adv(slot), 0, 0, 0, 0, b"")
            return glyphs.get(ord("?"))
        return _fallback_glyph(ch, slot[1])

    def _space_adv(self, slot):
        glyphs = self.atlas.get(slot)
        if glyphs is not None:
            g = glyphs.get(ord("i"))
            if g is not None:
                return g[0] * 0.45
        return 6.0 * _fallback_scale(slot[1])

    def text_width(self, s, slot):
        total = 0.0
        for ch in s:
            g = self._glyph(slot, ch)
            if g is not None:
                total += g[0]
        return total

    def draw_text(self, x, baseline, s, slot, color, align="left"):
        if align == "center":
            x = x - self.text_width(s, slot) / 2.0
        elif align == "right":
            x = x - self.text_width(s, slot)
        cx = float(x)
        for ch in s:
            g = self._glyph(slot, ch)
            if g is None:
                continue
            adv, bx, by, w, h, bmp = g
            if w and h:
                self._blit_gray(int(round(cx)) + bx, int(baseline) - by,
                                w, h, bmp, color)
            cx += adv

    def _blit_gray(self, x, y, w, h, bmp, color):
        for row in range(h):
            yy = y + row
            if yy < 0 or yy >= self.h:
                continue
            base = row * w
            for col in range(w):
                a = bmp[base + col]
                if not a:
                    continue
                xx = x + col
                if xx < 0 or xx >= self.w:
                    continue
                o = (yy * self.w + xx) * 3
                if a == 255:
                    self.px[o:o + 3] = bytes(color)
                else:
                    for k in range(3):
                        old = self.px[o + k]
                        self.px[o + k] = (old * (255 - a) + color[k] * a) // 255

    def wrap(self, s, slot, max_w):
        lines = []
        for word in s.split(" "):
            if not lines:
                lines.append(word)
                continue
            trial = lines[-1] + " " + word
            if self.text_width(trial, slot) <= max_w:
                lines[-1] = trial
            else:
                lines.append(word)
        return lines

    def draw_para(self, x, first_baseline, s, slot, max_w, lh, color):
        baseline = first_baseline
        for line in self.wrap(s, slot, max_w):
            self.draw_text(x, baseline, line, slot, color)
            baseline += lh
        return baseline


# --------------------------------------------------------------------------
# PNG output (stdlib only)
# --------------------------------------------------------------------------

def write_png(path, width, height, rgb):
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw += rgb[y * width * 3:(y + 1) * width * 3]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        return out + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(png)
    return len(png)


# --------------------------------------------------------------------------
# page content (numbers from STORIES-2026-11-26.md, one version everywhere)
# --------------------------------------------------------------------------

MASTHEAD = "ONE THURSDAY, ONE WORLD"
DATE_LINE = "THURSDAY, 26 NOVEMBER 2026"
SUB_LINE = "30 STORIES \u00b7 7 REGIONS \u00b7 EVERY ONE DATED THURSDAY 26 NOVEMBER 2026"

STATS = [
    ("550,000", "BPD \u00b7 RAS TANURA"),
    ("4", "DRONES DOWNED"),
    ("$93.60", "BRENT \u00b7 +2.41%"),
    ("2", "TANKERS MINED"),
    ("55%", "REFINING DISABLED"),
    ("204", "RUNS \u00b7 53 BALLS"),
]

UTC_STRIP = ("UTC WIRES \u00b7 06:00 SAMARA FIRES \u00b7 09:05 GAZA STRIKE \u00b7 "
             "13:51 GAZA DEAD NAMED \u00b7 15:16 BRENT $93.60 \u00b7 "
             "15:28 RAS TANURA CLAIM \u00b7 17:35 SMOKE OVER 600 SQ KM")

REGIONS = [
    ("MIDDLE EAST", 6, RED),
    ("EUROPE", 4, NAVY),
    ("ASIA-PACIFIC", 6, (46, 125, 50)),
    ("SOUTH ASIA", 4, (180, 83, 9)),
    ("AMERICAS", 5, (124, 72, 20)),
    ("AFRICA", 3, (15, 118, 110)),
    ("WORLD", 2, (75, 85, 99)),
]

LEAD1 = {
    "kicker": "MIDDLE EAST \u2014 CLAIM \u00b7 REUTERS",
    "headline": "HOUTHIS CLAIM STRIKE ON SAUDI ARABIA'S BIGGEST REFINERY",
    "body": ("Houthis say they hit the 550,000 bpd Ras Tanura refinery and "
             "Riyadh's financial district; the coalition says 4 drones "
             "were destroyed over Ras Tanura. Satellite images show black "
             "smoke over ~600 sq km. Brent $93.60 (+2.41%)."),
    "caption": "Ras Tanura refinery, Saudi Arabia (file photo)",
}

LEAD2 = {
    "kicker": "STRAIT OF HORMUZ \u2014 CLAIM \u00b7 IRNA / OILPRICE",
    "headline": "TWO TANKERS HIT BY NAVAL MINES IN STRAIT OF HORMUZ",
    "body": ("Fires in the engine rooms, the IRGC Navy says via IRNA; "
             "near-daily incidents for weeks. UKMTO and JMIC: claims "
             "unconfirmed."),
    "caption": "Tanker in the Strait of Hormuz (illustration)",
}

LEAD3 = {
    "kicker": "GAZA \u2014 CONFIRMED \u00b7 REUTERS / XINHUA",
    "headline": "ISRAELI STRIKE KILLS HAMAS SECURITY CHIEF AND FAMILY",
    "body": ("Col. Mohammad Abuelouf, 47, his wife Noura, 41, and daughters "
             "Yusra, 15, and Jana, 13, killed in Al-Shati camp, Gaza City "
             "\u2014 the 2nd senior Hamas security official killed in "
             "24 hours."),
    "caption": "Gaza City skyline (file photo)",
}

# (number, kicker, headline, illustration kind)
MIDS = [
    (4, "SAMARA \u2014 REPORTED", "UKRAINE DRONES HIT TWO ROSNEFT REFINERIES", "photo"),
    (5, "RIYADH \u2014 CONFIRMED", "INDIA CONDEMNS RIYADH TOWER ATTACK; 2 HURT", "tower"),
    (6, "SPACE \u2014 CONFIRMED", "PAKISTAN ASTRONAUT JOINS CHINA'S STATION", "rocket"),
    (7, "PACIFIC \u2014 CONFIRMED", "AUSTRALIA, SOLOMONS SIGN HISTORIC TREATY", "treaty"),
    (8, "DHAKA \u2014 CONFIRMED", "GARMENT MINIMUM WAGE UP 36%", "factory"),
    (9, "PEACE \u2014 CONFIRMED", "10 YEARS SINCE HISTORIC PEACE ACCORD", "dove"),
    (10, "BRAZIL \u2014 REPORTED", "PETROBRAS UNVEILS $122BN INVESTMENT PLAN", "pumpjack"),
    (11, "CARACAS \u2014 REPORTED", "VENEZUELA REVEALS $237.5BN PUBLIC DEBT", "bank"),
    (12, "USA \u2014 REPORTED", "CONSUMER CONFIDENCE NEAR TWO-YEAR HIGH", "chart"),
    (13, "SUDAN \u2014 REPORTED", "DRONE STRIKES KILL 19 CIVILIANS IN BLUE NILE", "drone"),
]

ALSO_COL1 = [
    "14. S. AFRICA \u2014 RAMAPHOSA WINS CASH-THEFT CASE",
    "15. LEBANON \u2014 2ND INTERNATIONAL AIRPORT PLANNED",
    "16. UK \u2014 AIRCRAFT MOVED AMID DRONE THREAT",
    "17. N. KOREA \u2014 SWITZERLAND: CLOSE PYONGYANG OFFICE",
    "18. INDIA \u2014 77TH CONSTITUTION DAY; IITS +6,000 SEATS",
    "19. SOORYAVANSHI, 15 \u2014 RECORD 204 OFF 53 BALLS",
    "20. CHESS \u2014 GUKESH-SINDAROV WORLD TITLE, GENEVA",
    "21. IPL \u2014 1,220 PLAYERS REGISTER FOR 2027 AUCTION",
    "22. BEPICOLOMBO \u2014 REACHES MERCURY AFTER 8 YEARS",
]
ALSO_COL2 = [
    "23. CHINA \u2014 XI GRAFT PROBE OF SHANGHAI RISING STAR",
    "24. RUSSIA \u2014 NEARLY 500,000 LOST IN UKRAINE WAR",
    "25. ASTEROID \u2014 CLOSE-UPS DUE OF DEFENCE-TEST ROCK",
    "26. COLOMBIA \u2014 POLICE FREE 20 HELD HOSTAGE 17 HOURS",
    "27. EGYPT \u2014 SUEZ CANAL REVENUES RECOVERING",
    "28. NEPAL \u2014 INDIA ANNOUNCES \u20b915,000 CRORE PACKAGE",
    "29. IRELAND \u2014 BATTLE OVER NEUTRALITY, PEACEKEEPING",
    "30. IRAN \u2014 FINANCIAL HARDSHIP DEEPENS",
]

DATE_CHECK = [
    "DATE CHECK \u2014 Wires read up to 01:00 UTC, Thu 26 Nov 2026. Every story here happened, or was first reported, on 26 Nov in at least one time zone.",
    "Left out on purpose: KAFD tower hit (Tue 24 Nov) \u00b7 Ras Tanura Oct 27 claim \u00b7 Hormuz mine claims of 16\u201317 Nov \u00b7 Ilsky/Afipsky fires (18 Nov) \u00b7 Peru 6.7 quake (Fri 20 Nov).",
    "Not yet decided: Brent's Thursday close \u00b7 Gukesh\u2013Sindarov opener \u00b7 IPL shortlist. CLAIM = one side's account \u00b7 CONFIRMED = 2+ sources \u00b7 REPORTED = one outlet.",
    "Photos: Wikimedia Commons (file photos); scenes and map drawn in code. PRESS TIME 01:00 UTC, Thursday 26 November 2026.",
]


# --------------------------------------------------------------------------
# drawn illustrations (flat vector scenes, drawn in code)
# --------------------------------------------------------------------------

def draw_tanker(c, x, y, w, h):
    c.fill_rect(x, y, w, h, SKY)
    c.fill_rect(x, y + h - 30, w, 30, SEA)
    # hull
    c.fill_poly([(x + 55, y + 44), (x + w - 95, y + 44), (x + w - 60, y + 62),
                 (x + 55, y + 62)], (40, 48, 58))
    c.fill_rect(x + 55, y + 38, w - 150, 6, (40, 48, 58))
    # bridge tower + funnel
    c.fill_rect(x + w - 150, y + 12, 34, 32, WHITE)
    c.fill_rect(x + w - 150, y + 12, 34, 5, RED)
    c.fill_rect(x + w - 108, y + 26, 10, 18, (200, 60, 40))
    c.line(x + w - 133, y + 12, x + w - 133, y + 2, INK)
    c.fill_rect(x + w - 138, y + 2, 10, 6, RED)
    # deck containers
    for i in range(5):
        c.fill_rect(x + 80 + i * 52, y + 28, 44, 10,
                    (150, 60, 40) if i % 2 else (60, 110, 140))
    # mines in the water
    for (mx, my) in ((x + 90, y + h - 14), (x + 300, y + h - 11)):
        c.fill_circle(mx, my, 6, BLACK)
        for dx, dy in ((-8, 0), (8, 0), (0, -8), (0, 8),
                       (-6, -6), (6, -6), (-6, 6), (6, 6)):
            c.line(mx, my, mx + dx, my + dy, BLACK)
    # wave lines
    for wx in (x + 180, x + 250, x + 380):
        c.hline(wx, wx + 34, y + h - 20, WHITE)


def draw_tower(c, x, y, w, h):
    c.fill_rect(x, y, w, h, (232, 222, 196))
    c.fill_rect(x + w // 2 - 14, y + 6, 28, h - 6, (30, 58, 92))
    c.fill_rect(x + w // 2 - 2, y + 1, 4, 5, (30, 58, 92))
    c.fill_rect(x + w // 2 + 2, y + 1, 9, 4, RED)
    for row in range(4):
        for col in range(3):
            c.fill_rect(x + w // 2 - 10 + col * 8, y + 12 + row * 7, 4, 4,
                        (255, 214, 120))
    c.fill_rect(x + w // 2 - 22, y + h - 6, 44, 6, (30, 58, 92))


def draw_rocket(c, x, y, w, h):
    c.fill_rect(x, y, w, h, NAVY)
    for (sx, sy) in ((x + 18, y + 8), (x + 165, y + 6), (x + 150, y + 30),
                      (x + 30, y + 30), (x + 95, y + 5)):
        c.fill_rect(sx, sy, 2, 2, WHITE)
    cx = x + w // 2
    c.fill_poly([(cx - 9, y + 6), (cx + 9, y + 6), (cx + 7, y + 26),
                 (cx - 7, y + 26)], WHITE)
    c.fill_poly([(cx - 9, y + 6), (cx + 9, y + 6), (cx, y - 2)], RED)
    c.fill_poly([(cx - 9, y + 22), (cx - 16, y + 30), (cx - 9, y + 28)], RED)
    c.fill_poly([(cx + 9, y + 22), (cx + 16, y + 30), (cx + 9, y + 28)], RED)
    c.fill_poly([(cx - 5, y + 26), (cx + 5, y + 26), (cx, y + h - 2)],
                (255, 150, 40))
    c.fill_circle(cx, y + 14, 3, (120, 180, 220))


def draw_treaty(c, x, y, w, h):
    c.fill_rect(x, y, w, h, (240, 234, 214))
    c.fill_poly([(x + 70, y + 4), (x + 120, y + 4), (x + 120, y + 34),
                 (x + 70, y + 34)], WHITE)
    c.fill_poly([(x + 110, y + 4), (x + 120, y + 4), (x + 110, y + 14)],
                (200, 195, 175))
    for i in range(3):
        c.fill_rect(x + 76, y + 10 + i * 6, 30, 2, (150, 145, 130))
    c.fill_circle(x + 112, y + 28, 5, RED)
    c.line(x + 60, y + 30, x + 130, y + 12, (60, 50, 30))
    c.fill_rect(x + 128, y + 10, 4, 4, (60, 50, 30))


def draw_factory(c, x, y, w, h):
    c.fill_rect(x, y, w, h, (224, 232, 222))
    c.fill_rect(x + 150, y + 4, 12, 22, (90, 90, 90))
    c.fill_circle(x + 156, y + 2, 4, (220, 220, 220))
    c.fill_poly([(x + 30, y + 34), (x + 30, y + 18), (x + 55, y + 18),
                 (x + 55, y + 26), (x + 80, y + 26), (x + 80, y + 18),
                 (x + 105, y + 18), (x + 105, y + 26), (x + 130, y + 26),
                 (x + 130, y + 18), (x + 155, y + 18), (x + 155, y + 34)],
                (110, 110, 110))
    for i in range(4):
        c.fill_rect(x + 40 + i * 28, y + 24, 8, 6, (255, 214, 120))


def draw_dove(c, x, y, w, h):
    c.fill_rect(x, y, w, h, (205, 225, 238))
    c.fill_circle(x + 168, y + 8, 6, (255, 210, 90))
    cx, cy = x + 85, y + 22
    c.fill_poly([(cx - 22, cy + 2), (cx + 18, cy - 4), (cx + 30, cy + 2),
                 (cx + 8, cy + 8), (cx - 14, cy + 8)], WHITE)
    c.fill_circle(cx + 26, cy - 4, 5, WHITE)
    c.fill_poly([(cx - 2, cy - 2), (cx + 10, cy - 12), (cx + 14, cy - 2)],
                WHITE)
    c.fill_circle(cx + 28, cy - 5, 1, INK)
    c.fill_poly([(cx - 20, cy - 10), (cx - 4, cy - 16), (cx + 2, cy - 8)],
                (230, 240, 245))
    c.line(x + 20, y + 34, x + 60, y + 28, (60, 130, 60))
    for i in range(4):
        c.fill_circle(x + 26 + i * 10, y + 32 - i, 2, (60, 130, 60))


def draw_pumpjack(c, x, y, w, h):
    c.fill_rect(x, y, w, h, (232, 180, 120))
    c.fill_circle(x + 160, y + 10, 8, (255, 220, 130))
    c.fill_rect(x, y + h - 6, w, 6, (90, 60, 30))
    cx = x + 80
    c.fill_poly([(cx - 22, y + h - 6), (cx + 6, y + 8), (cx + 12, y + 8),
                 (cx + 22, y + h - 6)], (60, 45, 30))
    c.line(cx - 28, y + 12, cx + 38, y + 6, (60, 45, 30))
    c.fill_rect(cx + 34, y + 6, 10, 8, (60, 45, 30))
    c.line(cx + 39, y + 14, cx + 39, y + h - 6, (60, 45, 30))
    c.line(cx + 10, y + 8, cx + 10, y + h - 6, (60, 45, 30))


def draw_bank(c, x, y, w, h):
    c.fill_rect(x, y, w, h, (232, 226, 200))
    cx = x + w // 2
    c.fill_poly([(cx - 40, y + 12), (cx + 40, y + 12), (cx, y + 2)],
                (90, 80, 60))
    for i in range(4):
        c.fill_rect(cx - 34 + i * 20, y + 14, 7, 18, (120, 108, 84))
    c.fill_rect(cx - 42, y + 32, 84, 4, (90, 80, 60))
    c.fill_circle(x + 22, y + 10, 6, (212, 175, 55))
    c.fill_circle(x + 168, y + 8, 5, (212, 175, 55))
    c.fill_circle(x + 176, y + 16, 4, (212, 175, 55))


def draw_chart(c, x, y, w, h):
    c.fill_rect(x, y, w, h, (242, 238, 226))
    bars = [8, 14, 20, 27]
    for i, bh in enumerate(bars):
        c.fill_rect(x + 28 + i * 34, y + h - 6 - bh, 20, bh,
                    (40, 90, 160))
    c.line(x + 20, y + h - 6, x + 170, y + h - 6, INK)
    c.line(x + 20, y + h - 6, x + 20, y + 4, INK)
    c.line(x + 32, y + h - 12, x + 150, y + 6, RED)
    c.fill_poly([(x + 150, y + 6), (x + 138, y + 6), (x + 150, y + 14)], RED)


def draw_drone(c, x, y, w, h):
    c.fill_rect(x, y, w, h, (210, 225, 235))
    cx, cy = x + w // 2, y + h // 2 + 2
    c.line(cx - 26, cy - 10, cx + 26, cy + 10, (50, 55, 60))
    c.line(cx - 26, cy + 10, cx + 26, cy - 10, (50, 55, 60))
    for (rx, ry) in ((cx - 30, cy - 12), (cx + 30, cy + 12),
                      (cx - 30, cy + 12), (cx + 30, cy - 12)):
        c.fill_circle(rx, ry, 3, (50, 55, 60))
        c.hline(rx - 8, rx + 8, ry - 5, (120, 125, 130))
    c.fill_rect(cx - 12, cy - 5, 24, 10, (50, 55, 60))
    c.fill_circle(cx, cy, 3, RED)


ILLUSTRATIONS = {
    "tanker": draw_tanker,
    "tower": draw_tower,
    "rocket": draw_rocket,
    "treaty": draw_treaty,
    "factory": draw_factory,
    "dove": draw_dove,
    "pumpjack": draw_pumpjack,
    "bank": draw_bank,
    "chart": draw_chart,
    "drone": draw_drone,
}


# --------------------------------------------------------------------------
# world map (rough continent outlines, lon/lat -> page coords)
# --------------------------------------------------------------------------

CONTINENTS = [
    # North America
    [(-168, 66), (-140, 70), (-125, 71), (-110, 68), (-95, 69), (-85, 66),
     (-80, 73), (-70, 62), (-55, 52), (-60, 47), (-70, 42), (-75, 35),
     (-80, 32), (-85, 30), (-90, 21), (-97, 16), (-94, 17), (-105, 20),
     (-110, 23), (-117, 32), (-125, 40), (-124, 48), (-135, 58),
     (-155, 58), (-165, 60)],
    # Greenland
    [(-58, 64), (-45, 60), (-40, 65), (-30, 68), (-22, 70), (-25, 76),
     (-45, 76), (-58, 74)],
    # South America
    [(-78, 7), (-72, 11), (-62, 10), (-52, 5), (-50, 0), (-44, -3),
     (-35, -8), (-40, -20), (-48, -28), (-58, -38), (-65, -45),
     (-70, -54), (-73, -40), (-72, -20), (-77, -12), (-81, -5), (-80, 1)],
    # Africa
    [(-17, 15), (-10, 5), (-8, -2), (9, -1), (12, -5), (13, -12),
     (19, -18), (26, -33), (32, -28), (35, -18), (40, -10), (42, -1),
     (48, 11), (43, 12), (38, 18), (35, 28), (32, 31), (22, 33),
     (10, 37), (0, 36), (-6, 35), (-10, 31), (-17, 21)],
    # Eurasia
    [(-10, 36), (-9, 43), (-2, 48), (-5, 50), (0, 51), (5, 53), (8, 57),
     (10, 59), (5, 60), (5, 62), (12, 65), (18, 69), (25, 71), (32, 70),
     (40, 68), (55, 69), (68, 73), (75, 73), (85, 76), (100, 77),
     (110, 74), (120, 73), (130, 72), (140, 72), (158, 69), (170, 66),
     (178, 65), (170, 60), (162, 56), (158, 52), (150, 59), (142, 55),
     (140, 50), (135, 43), (130, 42), (127, 40), (122, 38), (120, 32),
     (115, 23), (109, 18), (105, 10), (100, 8), (97, 16), (92, 21),
     (88, 22), (85, 19), (80, 13), (77, 8), (75, 20), (72, 20),
     (66, 25), (62, 25), (57, 26), (52, 28), (50, 30), (48, 29),
     (44, 29), (40, 31), (36, 36), (30, 36), (27, 40), (23, 40),
     (19, 42), (15, 44), (12, 44), (8, 44), (3, 43), (0, 40), (-2, 37),
     (-6, 36)],
    # Australia
    [(114, -22), (113, -26), (115, -33), (118, -35), (124, -33),
     (129, -32), (132, -32), (135, -35), (138, -35), (140, -38),
     (145, -38), (150, -37), (153, -32), (153, -27), (146, -19),
     (142, -11), (137, -12), (135, -15), (132, -12), (126, -14),
     (122, -17), (118, -20)],
    # Britain
    [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (0, 53), (1, 51)],
    # Japan
    [(130, 31), (132, 33), (135, 34), (137, 35), (139, 37), (141, 39),
     (141, 41), (143, 43), (145, 44), (142, 45), (140, 41), (139, 38),
     (137, 36), (135, 33), (132, 32)],
    # Indonesia / New Guinea
    [(95, 5), (98, 3), (100, 0), (103, -2), (106, -6), (110, -7),
     (114, -8), (118, -9), (120, -10), (124, -10), (128, -8), (131, -3),
     (134, -2), (137, -3), (140, -4), (141, -8)],
    # New Zealand
    [(167, -45), (170, -43), (173, -41), (175, -38), (177, -38),
     (175, -40), (172, -42), (168, -46)],
]

# story number -> (lon, lat) for the map pins
PINS = {
    1: (50, 26), 2: (56.5, 29), 3: (34.5, 33.5), 4: (50, 53),
    5: (46.7, 22), 6: (100, 32), 7: (160, -9), 8: (90, 24),
    9: (-74, 4), 10: (-52, -10), 11: (-66, 8), 12: (-98, 39),
    13: (34, 11),
}


def draw_map(c, x, y, w, h):
    c.fill_rect(x, y, w, h, MAP_BG)
    for lon in range(-150, 181, 30):
        px = x + int((lon + 170) / 360.0 * w)
        for yy in range(y, y + h, 3):
            c.set_pixel(px, yy, (190, 205, 215))
    for lat in (-60, -30, 0, 30, 60):
        py = y + int((75 - lat) / 135.0 * h)
        for xx in range(x, x + w, 3):
            c.set_pixel(xx, py, (190, 205, 215))

    def project(lon, lat):
        return (x + int((lon + 170) / 360.0 * w),
                y + int((75 - lat) / 135.0 * h))

    for continent in CONTINENTS:
        c.fill_poly([project(lon, lat) for (lon, lat) in continent],
                    MAP_LAND)
    for num in sorted(PINS):
        lon, lat = PINS[num]
        px, py = project(lon, lat)
        c.fill_circle(px, py, 6, RED)
        c.draw_text(px, py + 4, str(num), SANSB10, WHITE, align="center")


# --------------------------------------------------------------------------
# page assembly
# --------------------------------------------------------------------------

def number_badge(c, x, y, num):
    c.fill_rect(x, y, 28, 28, RED)
    c.draw_text(x + 14, y + 21, str(num), SANSB13, WHITE, align="center")


def caption_bar(c, x, y, w, text):
    c.fill_rect(x, y, w, 18, BLACK)
    c.draw_text(x + 8, y + 13, text, SANSB10, WHITE)


def draw_page():
    c = Canvas(W, H, PAPER)
    mx = 24
    right = 1000

    # masthead
    c.draw_text(512, 50, MASTHEAD, SERIF54, INK, align="center")
    c.fill_rect(mx, 60, right - mx, 3, RED)
    c.draw_text(512, 88, DATE_LINE, SERIF30, RED, align="center")
    c.draw_text(512, 106, SUB_LINE, SANSB11, NAVY, align="center")
    c.fill_rect(mx, 114, right - mx, 1, RED)

    # stat bar: six numbers
    c.fill_rect(mx, 120, right - mx, 2, RED)
    cell = (right - mx) / 6.0
    for i, (num, label) in enumerate(STATS):
        cx = mx + cell * i + cell / 2.0
        c.draw_text(int(cx), 148, num, SANSB30, RED, align="center")
        c.draw_text(int(cx), 166, label, SANSB10, INK, align="center")
        if i:
            c.fill_rect(int(mx + cell * i), 124, 1, 44, (210, 202, 182))
    c.fill_rect(mx, 172, right - mx, 1, RED)

    # UTC wire strip
    c.draw_text(512, 186, UTC_STRIP, SANSB10, INK, align="center")

    # region bar
    total = sum(n for _, n, _ in REGIONS)
    rx = mx
    widths = []
    for (_, n, _) in REGIONS:
        widths.append(int(round((right - mx) * n / float(total))))
    widths[-1] += (right - mx) - sum(widths)
    for (name, n, color), wseg in zip(REGIONS, widths):
        c.fill_rect(rx, 192, wseg, 18, color)
        c.draw_text(rx + wseg // 2, 205, "%s %d" % (name, n), SANSB10,
                    WHITE, align="center")
        rx += wseg

    # ---- lead 1: photo left, text right ----
    photo1 = load_photo("photo_rastanura")
    if photo1 is not None:
        c.blit_photo(mx, 218, photo1)
    else:
        draw_tanker(c, mx, 218, 430, 174)
    number_badge(c, mx, 218, 1)
    caption_bar(c, mx, 392, 430, LEAD1["caption"])
    tx = 470
    c.draw_text(tx, 232, LEAD1["kicker"], SANSB13, RED)
    end = c.draw_para(tx, 264, LEAD1["headline"], SERIF32, 530, 34, INK)
    c.draw_para(tx, end + 8, LEAD1["body"], SANS14, 530, 18, INK)

    # ---- leads 2 and 3 ----
    lead_y = 418
    col_w = 476
    for (lead, x0, photo_name, art) in (
            (LEAD2, mx, None, "tanker"),
            (LEAD3, 524, "photo_gaza", None)):
        if photo_name is not None:
            photo = load_photo(photo_name)
            if photo is not None:
                c.blit_photo(x0, lead_y, photo)
            else:
                ILLUSTRATIONS["tanker"](c, x0, lead_y, col_w, 84)
        else:
            ILLUSTRATIONS[art](c, x0, lead_y, col_w, 84)
        number_badge(c, x0, lead_y, 2 if x0 == mx else 3)
        caption_bar(c, x0, lead_y + 84, col_w, lead["caption"])
        c.draw_text(x0, lead_y + 122, lead["kicker"], SANSB12, RED)
        end = c.draw_para(x0, lead_y + 148, lead["headline"], SERIF26,
                          col_w, 28, INK)
        c.draw_para(x0, end + 6, lead["body"], SANS13, col_w, 15, INK)

    # ---- mid grid: 2 rows x 5 ----
    mid_y0 = 668
    mid_col_w = 189
    mid_gap = 8
    for idx, (num, kicker, headline, art) in enumerate(MIDS):
        row, col = divmod(idx, 5)
        x0 = mx + col * (mid_col_w + mid_gap)
        y0 = mid_y0 + row * 94
        if art == "photo":
            photo = load_photo("photo_samara")
            if photo is not None:
                c.blit_photo(x0, y0, photo)
            else:
                ILLUSTRATIONS["factory"](c, x0, y0, mid_col_w, 36)
        else:
            ILLUSTRATIONS[art](c, x0, y0, mid_col_w, 36)
        c.draw_text(x0, y0 + 49, "%d \u00b7 %s" % (num, kicker), SANSB10, RED)
        c.draw_para(x0, y0 + 62, headline, SERIF13, mid_col_w, 14, INK)

    # ---- map + also ----
    c.draw_text(mx, 866, "WORLD \u2014 PINS 1\u201313", SANSB11, NAVY)
    c.draw_text(376, 866, "ALSO ON \u2014 17 MORE STORIES", SANSB11, NAVY)
    draw_map(c, mx, 872, 336, 94)
    col_x = [376, 690]
    col_w = 307
    for ci, items in enumerate((ALSO_COL1, ALSO_COL2)):
        baseline = 878
        for item in items:
            for line in c.wrap(item, SANS10, col_w):
                c.draw_text(col_x[ci], baseline, line, SANS10, INK)
                baseline += 10

    # ---- date check ----
    c.outline_rect(mx, 970, right - mx, 48, RED, 2)
    baseline = 982
    for i, line in enumerate(DATE_CHECK):
        c.draw_text(mx + 10, baseline, line, SANS10, INK)
        baseline += 11 if i == 0 else 10

    return c


def main():
    page = draw_page()
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if not out_dir:
        out_dir = "/output" if os.path.isdir("/output") else \
            os.path.join(HERE, "output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    size = write_png(path, W, H, page.px)
    local_dir = os.path.join(HERE, "output")
    if os.path.abspath(out_dir) != os.path.abspath(local_dir):
        try:
            os.makedirs(local_dir, exist_ok=True)
            write_png(os.path.join(local_dir, "entry.png"), W, H, page.px)
        except OSError:
            # Graded runs mount the repository read-only; the entry in
            # $MAKEFUN_OUTPUT_DIR is already written, so a local copy
            # that cannot be written must not fail the run.
            pass
    print("wrote %s (%d bytes, %dx%d)" % (path, size, W, H))
    return 0


if __name__ == "__main__":
    sys.exit(main())
