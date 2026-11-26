#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the binary assets for the news-image entry.

Reads three raw JPEG photographs and three system TrueType fonts and
writes gzip-compressed asset files that main.py (stdlib only) can read:

  atlas.bin.gz          glyph bitmaps for every (font, size) this page uses
  photo_rastanura.rgb.gz  raw RGB24 photo, cropped to its page slot
  photo_gaza.rgb.gz       raw RGB24 photo, cropped to its page slot
  photo_samara.rgb.gz     raw RGB24 photo, cropped to its page slot

Only the Python standard library is imported. JPEG decoding is done by
the system ffmpeg binary through subprocess; font rasterisation is done
by a small TrueType parser written here (cmap + glyf, quadratic
outlines, supersampled scanline fill), so no font library is needed.

Asset formats (all little-endian, gzip-compressed on disk):

  atlas:  b"ATL1" u32 slot_count
          per slot: u16 size_px, u8 font_id, u8 0, u32 glyph_count
          per glyph: u32 codepoint, u16 advance_x16, i16 bear_x, i16 bear_y,
                     u16 w, u16 h, then w*h grayscale bytes (0..255)
  photo:  b"PHO1" u32 width, u32 height, then width*height*3 RGB bytes

Run from the repository root:  python3 build_assets.py
"""

import gzip
import math
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.normpath(os.path.join(HERE, "..", "work"))
RAW = os.path.join(WORK, "raw_photos")
FONT_DIR = "/usr/share/fonts/truetype/dejavu"

# font_id -> filename
FONTS = {
    0: "DejaVuSerif-Bold.ttf",
    1: "DejaVuSans-Bold.ttf",
    2: "DejaVuSans.ttf",
}

# (pixel size, font_id) slots the page needs.
SLOTS = [
    (54, 0),  # masthead
    (30, 0),  # date line
    (32, 0),  # lead 1 headline
    (26, 0),  # lead 2/3 headlines
    (13, 0),  # mid headlines
    (14, 0),  # (unused spare)
    (30, 1),  # stat numbers
    (13, 1),  # kickers, stat labels
    (12, 1),  # UTC strip, captions
    (11, 1),  # region bar, section headers
    (10, 1),  # tiny labels
    (14, 2),  # lead body
    (13, 2),  # lead 2/3 body
    (11, 2),  # also list
    (10, 2),  # date-check body
]

# Characters the page uses: printable ASCII plus a few punctuation marks.
EXTRA_CHARS = [0x2014, 0x2013, 0x00B7, 0x2019, 0x2018, 0x201C, 0x201D,
               0x20B9, 0x2026]
CHARSET = list(range(32, 127)) + EXTRA_CHARS

# photo name -> (raw file, slot width, slot height)
PHOTOS = {
    "photo_rastanura": ("rastanura.jpg", 430, 174),
    "photo_gaza": ("gaza.jpg", 476, 84),
    "photo_samara": ("refinery.jpg", 189, 36),
}

SS = 3  # supersampling factor for glyph antialiasing


# --------------------------------------------------------------------------
# small binary readers
# --------------------------------------------------------------------------

def u16(b, o):
    return struct.unpack_from(">H", b, o)[0]


def i16(b, o):
    return struct.unpack_from(">h", b, o)[0]


def u32(b, o):
    return struct.unpack_from(">I", b, o)[0]


def i8(b, o):
    return struct.unpack_from(">b", b, o)[0]


# --------------------------------------------------------------------------
# TrueType parsing
# --------------------------------------------------------------------------

class Font(object):
    """A TrueType font read straight from its file bytes."""

    def __init__(self, path):
        with open(path, "rb") as fh:
            self.data = fh.read()
        d = self.data
        n_tables = u16(d, 4)
        self.tables = {}
        for i in range(n_tables):
            o = 12 + i * 16
            tag = d[o:o + 4].decode("latin-1")
            self.tables[tag] = (u32(d, o + 8), u32(d, o + 12))
        head = self._table("head")
        self.units_per_em = u16(head, 18)
        self.loc_format = i16(head, 50)
        maxp = self._table("maxp")
        self.num_glyphs = u16(maxp, 4)
        hhea = self._table("hhea")
        self.num_hmetrics = u16(hhea, 34)
        self.cmap = self._parse_cmap()
        self._outline_cache = {}

    def _table(self, tag):
        off, length = self.tables[tag]
        return self.data[off:off + length]

    def _parse_cmap(self):
        c = self._table("cmap")
        n = u16(c, 2)
        best4 = None
        best12 = None
        for i in range(n):
            o = 4 + i * 8
            platform, encoding = u16(c, o), u16(c, o + 2)
            sub = u32(c, o + 4)
            fmt = u16(c, sub)
            if fmt == 12 and best12 is None:
                best12 = (platform, encoding, sub)
            elif fmt == 4 and best4 is None:
                best4 = (platform, encoding, sub)
        mapping = {}
        if best12 is not None:
            _, _, sub = best12
            groups = u32(c, sub + 12)
            for i in range(groups):
                o = sub + 16 + i * 12
                start, end, glyph = u32(c, o), u32(c, o + 4), u32(c, o + 8)
                for ch in range(start, end + 1):
                    mapping[ch] = glyph + (ch - start)
        elif best4 is not None:
            _, _, sub = best4
            seg_count = u16(c, sub + 6) // 2
            end_base = sub + 14
            start_base = end_base + 2 * seg_count + 2
            delta_base = start_base + 2 * seg_count
            range_base = delta_base + 2 * seg_count
            for s in range(seg_count):
                end_c = u16(c, end_base + 2 * s)
                start_c = u16(c, start_base + 2 * s)
                delta = i16(c, delta_base + 2 * s)
                roff = u16(c, range_base + 2 * s)
                for ch in range(start_c, end_c + 1):
                    if roff == 0:
                        mapping[ch] = (ch + delta) % 65536
                    else:
                        addr = range_base + 2 * s + roff + 2 * (ch - start_c)
                        g = u16(c, addr)
                        if g != 0:
                            mapping[ch] = (g + delta) % 65536
        return mapping

    def glyph_id(self, char):
        return self.cmap.get(char, 0)

    def advance(self, gid):
        hmtx = self._table("hmtx")
        if gid < self.num_hmetrics:
            return u16(hmtx, gid * 4)
        return u16(hmtx, (self.num_hmetrics - 1) * 4)

    def glyph_offset(self, gid):
        loca = self._table("loca")
        if self.loc_format == 0:
            start = u16(loca, gid * 2) * 2
            end = u16(loca, (gid + 1) * 2) * 2
        else:
            start = u32(loca, gid * 4)
            end = u32(loca, (gid + 1) * 4)
        return start, end

    def outline(self, gid):
        """Return a list of contours; each contour is a list of
        (x, y, on_curve) points in font units. Handles simple and
        composite glyphs."""
        if gid in self._outline_cache:
            return self._outline_cache[gid]
        glyf = self._table("glyf")
        start, end = self.glyph_offset(gid)
        contours = []
        if end > start:
            contours = self._parse_glyph(glyf, start, end)
        self._outline_cache[gid] = contours
        return contours

    def _parse_glyph(self, glyf, start, end):
        n_contours = i16(glyf, start)
        if n_contours >= 0:
            return self._parse_simple(glyf, start, n_contours)
        return self._parse_composite(glyf, start)

    def _parse_simple(self, glyf, start, n_contours):
        o = start + 10
        end_pts = [u16(glyf, o + 2 * i) for i in range(n_contours)]
        o += 2 * n_contours
        instr_len = u16(glyf, o)
        o += 2 + instr_len
        n_points = end_pts[-1] + 1 if end_pts else 0
        flags = []
        while len(flags) < n_points:
            f = glyf[o]
            o += 1
            flags.append(f)
            if f & 0x08:
                rep = glyf[o]
                o += 1
                flags.extend([f] * rep)
        xs = []
        x = 0
        for f in flags:
            if f & 0x02:
                dx = glyf[o]
                o += 1
                if not (f & 0x10):
                    dx = -dx
            elif f & 0x10:
                dx = 0
            else:
                dx = i16(glyf, o)
                o += 2
            x += dx
            xs.append(x)
        ys = []
        y = 0
        for f in flags:
            if f & 0x04:
                dy = glyf[o]
                o += 1
                if not (f & 0x20):
                    dy = -dy
            elif f & 0x20:
                dy = 0
            else:
                dy = i16(glyf, o)
                o += 2
            y += dy
            ys.append(y)
        points = [(xs[i], ys[i], bool(flags[i] & 0x01))
                  for i in range(n_points)]
        contours = []
        prev = 0
        for ep in end_pts:
            contours.append(points[prev:ep + 1])
            prev = ep + 1
        return contours

    def _parse_composite(self, glyf, start):
        o = start + 10
        contours = []
        while True:
            flags = u16(glyf, o)
            comp_gid = u16(glyf, o + 2)
            o += 4
            if flags & 0x0001:
                dx = i16(glyf, o)
                dy = i16(glyf, o + 2)
                o += 4
            else:
                dx = i8(glyf, o)
                dy = i8(glyf, o + 1)
                o += 2
            if not (flags & 0x0002):
                dx = dy = 0  # point matching; treat as no offset
            a = d = 1.0
            b = c = 0.0
            if flags & 0x0008:
                s = i16(glyf, o) / 16384.0
                o += 2
                a = d = s
            elif flags & 0x0040:
                a = i16(glyf, o) / 16384.0
                d = i16(glyf, o + 2) / 16384.0
                o += 4
            elif flags & 0x0080:
                a = i16(glyf, o) / 16384.0
                b = i16(glyf, o + 2) / 16384.0
                c = i16(glyf, o + 4) / 16384.0
                d = i16(glyf, o + 6) / 16384.0
                o += 8
            for contour in self.outline(comp_gid):
                moved = []
                for (x, y, on) in contour:
                    nx = a * x + c * y + dx
                    ny = b * x + d * y + dy
                    moved.append((nx, ny, on))
                contours.append(moved)
            if not (flags & 0x0020):
                break
        return contours


# --------------------------------------------------------------------------
# outline flattening + rasterisation
# --------------------------------------------------------------------------

def _expand_contour(pts):
    """Insert implied on-curve midpoints between consecutive off-curve
    points and rotate so the contour starts on an on-curve point."""
    out = []
    n = len(pts)
    for i in range(n):
        x, y, on = pts[i]
        out.append((x, y, on))
        nx, ny, non = pts[(i + 1) % n]
        if not on and not non:
            out.append(((x + nx) / 2.0, (y + ny) / 2.0, True))
    for j, p in enumerate(out):
        if p[2]:
            return out[j:] + out[:j]
    return out


def _quad_samples(p0, pc, p1, scale):
    dist = math.hypot(p1[0] - p0[0], p1[1] - p0[1]) * scale
    n = max(2, min(24, int(dist / 1.2) + 1))
    pts = []
    for i in range(1, n + 1):
        t = i / float(n)
        mt = 1.0 - t
        x = mt * mt * p0[0] + 2 * mt * t * pc[0] + t * t * p1[0]
        y = mt * mt * p0[1] + 2 * mt * t * pc[1] + t * t * p1[1]
        pts.append((x * scale, -y * scale))
    return pts


def flatten_contour(pts, scale):
    """A contour (font-unit points) -> closed polygon in pixel space
    (y down, baseline at y=0)."""
    exp = _expand_contour(pts)
    if not exp:
        return []
    x0, y0, _ = exp[0]
    poly = [(x0 * scale, -y0 * scale)]
    cur = (x0, y0)
    ctrl = None
    for (x, y, on) in exp[1:]:
        if on:
            if ctrl is None:
                poly.append((x * scale, -y * scale))
            else:
                poly.extend(_quad_samples(cur, ctrl, (x, y), scale))
                ctrl = None
            cur = (x, y)
        else:
            ctrl = (x, y)
    if ctrl is not None:
        poly.extend(_quad_samples(cur, ctrl, (x0, y0), scale))
    return poly


def rasterize(polys, width, height):
    """Fill polygons (non-zero winding) into a grayscale bitmap of the
    given size, supersampled SSx and box-averaged down."""
    sw, sh = width * SS, height * SS
    grid = bytearray(sw * sh)
    edges = []
    for poly in polys:
        n = len(poly)
        for i in range(n):
            x0, y0 = poly[i]
            x1, y1 = poly[(i + 1) % n]
            if y0 == y1:
                continue
            edges.append((x0 * SS, y0 * SS, x1 * SS, y1 * SS))
    for row in range(sh):
        y = row + 0.5
        events = []
        for (x0, y0, x1, y1) in edges:
            if (y0 <= y < y1) or (y1 <= y < y0):
                t = (y - y0) / (y1 - y0)
                events.append((x0 + t * (x1 - x0), 1 if y1 > y0 else -1))
        if not events:
            continue
        events.sort(key=lambda e: e[0])
        winding = 0
        prev = None
        base = row * sw
        for (x, d) in events:
            if prev is not None and winding != 0:
                xa = int(math.ceil(prev))
                xb = int(math.floor(x))
                if xb > xa:
                    xa = max(xa, 0)
                    xb = min(xb, sw)
                    for xx in range(xa, xb):
                        grid[base + xx] = 1
            winding += d
            prev = x
    out = bytearray(width * height)
    for py in range(height):
        for px in range(width):
            total = 0
            for sy in range(SS):
                row = grid[(py * SS + sy) * sw + px * SS:
                           (py * SS + sy) * sw + px * SS + SS]
                total += sum(row)
            out[py * width + px] = (total * 255) // (SS * SS)
    return bytes(out)


def render_glyph(font, gid, size_px):
    """Return (advance_px, bear_x, bear_y, w, h, bitmap) for one glyph."""
    scale = size_px / float(font.units_per_em)
    adv = font.advance(gid) * scale
    contours = font.outline(gid)
    polys = []
    for contour in contours:
        poly = flatten_contour(contour, scale)
        if len(poly) >= 3:
            polys.append(poly)
    if not polys:
        return adv, 0, 0, 0, 0, b""
    xs = [p[0] for poly in polys for p in poly]
    ys = [p[1] for poly in polys for p in poly]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    w = int(math.ceil(max_x - min_x)) + 1
    h = int(math.ceil(max_y - min_y)) + 1
    moved = [[(x - min_x, y - min_y) for (x, y) in poly] for poly in polys]
    bitmap = rasterize(moved, w, h)
    bear_x = int(round(min_x))
    bear_y = int(round(-min_y))
    return adv, bear_x, bear_y, w, h, bitmap


# --------------------------------------------------------------------------
# atlas + photo building
# --------------------------------------------------------------------------

def build_atlas():
    fonts = {}
    for fid, name in FONTS.items():
        fonts[fid] = Font(os.path.join(FONT_DIR, name))
    missing = []
    payload = bytearray()
    payload += b"ATL1"
    payload += struct.pack("<I", len(SLOTS))
    for (size_px, fid) in SLOTS:
        font = fonts[fid]
        glyphs = []
        for ch in CHARSET:
            gid = font.glyph_id(ch)
            if gid == 0 and ch != 32:
                missing.append((fid, size_px, ch))
                continue
            adv, bx, by, w, h, bitmap = render_glyph(font, gid, size_px)
            glyphs.append((ch, adv, bx, by, w, h, bitmap))
        payload += struct.pack("<HBBI", size_px, fid, 0, len(glyphs))
        for (ch, adv, bx, by, w, h, bitmap) in glyphs:
            payload += struct.pack("<I H h h H H", ch,
                                   int(round(adv * 16)), bx, by, w, h)
            payload += bitmap
    if missing:
        shown = ", ".join("U+%04X" % c for _, _, c in missing[:12])
        print("warning: %d glyphs missing from fonts: %s"
              % (len(missing), shown), file=sys.stderr)
    with gzip.open(os.path.join(HERE, "atlas.bin.gz"), "wb",
                   compresslevel=9) as fh:
        fh.write(bytes(payload))
    print("atlas.bin.gz: %d slots, %d bytes on disk"
          % (len(SLOTS),
             os.path.getsize(os.path.join(HERE, "atlas.bin.gz"))))


def build_photo(name, raw_file, width, height):
    src = os.path.join(RAW, raw_file)
    filt = ("scale=%d:%d:force_original_aspect_ratio=increase,"
            "crop=%d:%d" % (width, height, width, height))
    cmd = ["ffmpeg", "-v", "error", "-i", src, "-vf", filt,
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg failed for %s" % raw_file)
    rgb = proc.stdout
    if len(rgb) != width * height * 3:
        raise RuntimeError("bad photo size for %s: got %d bytes, want %d"
                           % (raw_file, len(rgb), width * height * 3))
    payload = struct.pack("<4sII", b"PHO1", width, height) + rgb
    out_path = os.path.join(HERE, name + ".rgb.gz")
    with gzip.open(out_path, "wb", compresslevel=9) as fh:
        fh.write(payload)
    print("%s.rgb.gz: %dx%d, %d bytes on disk"
          % (name, width, height, os.path.getsize(out_path)))


def selftest():
    """Render a test strip of every slot's alphabet to /tmp/atlas-test.png
    so the rasteriser can be eyeballed before the real build."""
    font = Font(os.path.join(FONT_DIR, FONTS[2]))
    sample = "ABCDEFGabcdefg0123456789.,:;-$%()'" + chr(0x2014) + chr(0x2019)
    size = 40
    canvas_w, canvas_h = 900, 70
    grid = bytearray(canvas_w * canvas_h)
    x = 8.0
    baseline = 55
    for ch in sample:
        gid = font.glyph_id(ord(ch))
        adv, bx, by, w, h, bitmap = render_glyph(font, gid, size)
        top = baseline - by
        left = int(round(x)) + bx
        for row in range(h):
            for col in range(w):
                v = bitmap[row * w + col]
                if v:
                    gx, gy = left + col, top + row
                    if 0 <= gx < canvas_w and 0 <= gy < canvas_h:
                        grid[gy * canvas_w + gx] = v
        x += adv
    ppm = ("P6\n%d %d\n255\n" % (canvas_w, canvas_h)).encode("ascii")
    rgb = bytearray()
    for v in grid:
        g = 255 - v
        rgb += bytes((g, g, g))
    with open("/tmp/atlas-test.ppm", "wb") as fh:
        fh.write(ppm + bytes(rgb))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "/tmp/atlas-test.ppm",
                    "/tmp/atlas-test.png"], check=True)
    print("selftest wrote /tmp/atlas-test.png")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        selftest()
        return 0
    build_atlas()
    for name, (raw_file, w, h) in PHOTOS.items():
        build_photo(name, raw_file, w, h)
    return 0


if __name__ == "__main__":
    sys.exit(main())
