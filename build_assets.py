#!/usr/bin/env python3
"""Asset builder for news-image-20261126 v1 (local use only).

Turns the raw Wikimedia photos in ../work/raw_photos and the system
DejaVu fonts into the binary blobs the graded program ships:

  atlas.bin.gz      - 1-bit bitmap glyphs for every font the page needs
  photo_<k>.rgb.gz  - one lead photo each, cropped + resized to display size
  samara.rgb.gz     - the Samara mid tile's refinery file photo

The graded program (main.py) is stdlib-only: at grade time it reads
only these blobs plus its own embedded story data. No network then.

Run from the repo directory:  python3 build_assets.py
Deterministic: gzip mtime=0, fixed crop boxes, fixed render order.
Re-running produces byte-identical assets.
"""
import gzip
import io
import os
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "work", "raw_photos")
FONT_DIR = "/usr/share/fonts/truetype/dejavu"

# (atlas name, ttf file, pixel height)
FONT_SPECS = [
    ("mast", "DejaVuSerif-Bold.ttf", 40),
    ("date", "DejaVuSans-Bold.ttf", 24),
    ("sub", "DejaVuSans-Bold.ttf", 12),
    ("head28", "DejaVuSerif-Bold.ttf", 28),
    ("head21", "DejaVuSerif-Bold.ttf", 21),
    ("deck14", "DejaVuSans.ttf", 14),
    ("deck12", "DejaVuSans.ttf", 12),
    ("kick12", "DejaVuSans-Bold.ttf", 12),
    ("stat20", "DejaVuSans-Bold.ttf", 20),
    ("stat10", "DejaVuSans-Bold.ttf", 10),
    ("strip11", "DejaVuSans-Bold.ttf", 11),
    ("also10", "DejaVuSans.ttf", 10),
    ("map9", "DejaVuSans-Bold.ttf", 9),
    ("check10", "DejaVuSans.ttf", 10),
]

# (asset name, raw file, crop box (x0, y0, x1, y1), target (w, h))
PHOTO_SPECS = [
    ("rastanura", "rastanura.jpg", (0, 20, 500, 274), (440, 210)),
    ("gaza", "gaza.jpg", (300, 700, 3156, 1640), (476, 126)),
    ("samara", "refinery.jpg", (100, 150, 1000, 450), (188, 46)),
]

# Codepoints baked in: printable ASCII + the punctuation this page uses.
CODEPOINTS = list(range(32, 127)) + [
    0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D,
    0x2022, 0x00B7, 0x20AC, 0x20B9, 0x00D7,
]


def pack_bits(img, box):
    """Crop a greyscale glyph to 1 bit/px, MSB first, threshold 110."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    px = img.crop(box).load()
    stride = (w + 7) // 8
    out = bytearray()
    for y in range(h):
        for bx in range(stride):
            byte = 0
            for bit in range(8):
                xx = bx * 8 + bit
                if xx < w and px[xx, y] > 110:
                    byte |= 0x80 >> bit
            out.append(byte)
    return w, h, bytes(out)


def build_atlas(path):
    """Write atlas.bin.gz.

    Layout: magic b"ATL3", u32 font count; per font: u8 name length,
    name bytes, u16 pixel size, u16 ascent, u16 descent, u16 glyph
    count; per glyph: u32 codepoint, u16 advance, i16 x offset,
    i16 y offset, u16 width, u16 height, then packed rows.
    Ink for a glyph lands at (pen_x + xoff, baseline + yoff).
    """
    blob = io.BytesIO()
    blob.write(b"ATL3")
    blob.write(struct.pack(">I", len(FONT_SPECS)))
    for name, ttf, px in FONT_SPECS:
        font = ImageFont.truetype(os.path.join(FONT_DIR, ttf), px)
        ascent, descent = font.getmetrics()
        glyphs = []
        for cp in CODEPOINTS:
            ch = chr(cp)
            pad = px
            canvas = Image.new("L", (px * 3, px * 3), 0)
            ImageDraw.Draw(canvas).text((pad, pad), ch, font=font, fill=255)
            box = canvas.getbbox()
            adv = int(round(font.getlength(ch)))
            if box is None:
                glyphs.append((cp, adv, 0, 0, 0, 0, b""))
                continue
            w, h, packed = pack_bits(canvas, box)
            xoff = box[0] - pad
            yoff = (box[1] - pad) - ascent
            glyphs.append((cp, adv, xoff, yoff, w, h, packed))
        nb = name.encode("ascii")
        blob.write(struct.pack(">B", len(nb)))
        blob.write(nb)
        blob.write(struct.pack(">HHH H", px, ascent, descent, len(glyphs)))
        for cp, adv, xoff, yoff, w, h, packed in glyphs:
            blob.write(struct.pack(">IHhhHH", cp, adv, xoff, yoff, w, h))
            blob.write(packed)
        print(f"  font {name}: {px}px ascent={ascent} glyphs={len(glyphs)}")
    with gzip.GzipFile(path, "wb", compresslevel=9, mtime=0) as f:
        f.write(blob.getvalue())
    print(f"wrote {path}: {os.path.getsize(path)} bytes")


def build_photo(name, raw_file, crop, target):
    """Crop a raw photo to the target aspect (centre trim), resize,
    and store raw RGB gzipped."""
    img = Image.open(os.path.join(RAW, raw_file)).convert("RGB")
    img = img.crop(crop)
    tw, th = target
    sw, sh = img.size
    want = tw / th
    cur = sw / sh
    if cur > want:  # too wide: trim left/right
        nw = int(sh * want)
        ox = (sw - nw) // 2
        img = img.crop((ox, 0, ox + nw, sh))
    else:  # too tall: trim top/bottom
        nh = int(sw / want)
        oy = (sh - nh) // 2
        img = img.crop((0, oy, sw, oy + nh))
    img = img.resize((tw, th), Image.LANCZOS)
    path = os.path.join(HERE, f"photo_{name}.rgb.gz")
    with gzip.GzipFile(path, "wb", compresslevel=9, mtime=0) as f:
        f.write(img.tobytes())
    print(f"wrote {path}: {tw}x{th} gz={os.path.getsize(path)} bytes")


def main():
    build_atlas(os.path.join(HERE, "atlas.bin.gz"))
    for name, raw_file, crop, target in PHOTO_SPECS:
        build_photo(name, raw_file, crop, target)
    print("assets done")


if __name__ == "__main__":
    sys.exit(main())
