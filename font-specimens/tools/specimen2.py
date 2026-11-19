"""Pixel-exact specimens of Lisa .F bitmap fonts and Kreative pixel-outline TTFs, including every non-ASCII glyph.

usage: python -I specimen2.py OUT_DIR FONTFILE...
Writes OUT_DIR/<name>.png at 1x (no scaling). Lines: ASCII alphabet/digits/punctuation, a pangram, then every code
outside printable ASCII that the font defines, 32 per row, each row labelled with its first code (hex).
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lisafont import parse

ASCII_LINES = ["ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz",
               "0123456789 !\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~", "The quick brown fox jumps over the lazy dog."]


class BitmapFont:
    """A .F QuickDraw font record: glyphs indexed by byte code."""
    def __init__(self, path):
        self.f = parse(open(path, "rb").read())
        self.height, self.ascent = self.f["fRectH"], self.f["ascent"]

    def codes(self):
        return sorted(self.f["glyphs"])

    def glyph(self, code):
        """-> (bits HxW, x offset from pen, advance) exactly as QuickDraw places it."""
        g = self.f["glyphs"].get(code)
        if g is None:
            return None
        bits, off, wid = g
        return bits, self.f["kernMax"] + off, wid


class PixelTTF:
    """A TrueType font whose outlines are pixel squares of 100 units (Kreative 1X1Y); rasterised exactly."""
    K = 10

    def __init__(self, path):
        from fontTools.ttLib import TTFont
        t = TTFont(path)
        self.cmap = t.getBestCmap(); self.hmtx = t["hmtx"]
        upm = t["head"].unitsPerEm
        self.ascent = t["hhea"].ascent // 100; self.descent = -t["hhea"].descent // 100
        self.height = self.ascent + self.descent
        self.font = ImageFont.truetype(path, upm * self.K // 100, layout_engine=ImageFont.Layout.BASIC)

    def codes(self):
        return sorted(self.cmap)

    def glyph(self, code):
        if code not in self.cmap:
            return None
        adv = self.hmtx[self.cmap[code]][0] // 100
        lsb_pad = 4                                   # room for glyphs that extend left of the origin
        W = adv + 2 * lsb_pad + 8; K = self.K
        im = Image.new("L", (W * K, self.height * K), 0)
        ImageDraw.Draw(im).text((lsb_pad * K, self.ascent * K), chr(code), font=self.font, fill=255, anchor="ls")
        bits = np.array(im).astype(float).reshape(self.height, K, W, K).mean(axis=(1, 3)) >= 128
        cols = np.where(bits.any(0))[0]
        if len(cols) == 0:
            return np.zeros((self.height, 0), bool), 0, adv
        return bits[:, cols[0]:cols[-1] + 1], cols[0] - lsb_pad, adv


def draw_line(font, codes, gap=0, positions=None):
    """Render codes on one line. If `positions` is a list, append (code, x0, x1) for each glyph's ink columns."""
    H = font.height
    glyphs = [font.glyph(c) for c in codes]
    W = 8 + sum(max(g[2], g[1] + g[0].shape[1]) + gap if g else 4 for g in glyphs) + 16
    canvas = np.zeros((H, W), bool); pen = 4
    for c, g in zip(codes, glyphs):
        if g is None:
            pen += 4; continue
        bits, x_off, adv = g
        x = pen + x_off
        if bits.shape[1] and x >= 0:
            canvas[:, x:x + bits.shape[1]] |= bits[:, :max(0, min(bits.shape[1], W - x))]
            if positions is not None:
                positions.append((c, x, x + bits.shape[1]))
        pen += max(adv, x_off + bits.shape[1]) + gap if gap else adv
    return canvas[:, :pen + 4]


SHUFFLE_SEEDS = (1, 2, 3)


def shuffled_lines(font, seed, max_width):
    """Every inked glyph in the font, in an order fixed by `seed`, split into word-like groups of 2-7 glyphs and
    wrapped into lines no wider than `max_width` pixels."""
    import random
    rng = random.Random(seed)
    codes = [c for c in font.codes() if c != 32 and (g := font.glyph(c)) is not None and g[0].any()]
    rng.shuffle(codes)
    words, i = [], 0
    while i < len(codes):
        k = rng.randint(2, 7); words.append(codes[i:i + k]); i += k
    lines, cur = [], []
    for w in words:
        trial = cur + ([32] if cur else []) + w
        if cur and draw_line(font, trial).shape[1] > max_width:
            lines.append(cur); cur = list(w)
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def _row(font, label, codes, gap=0, pad=0):
    pos = []
    return (label, draw_line(font, codes, gap=gap, positions=pos), pad, pos)


def specimen(font):
    """-> (rows, number of non-ASCII glyphs). Each row is (label, bitmap, extra space above, [(code, x0, x1), ...])."""
    rows = [_row(font, None, [ord(c) for c in t]) for t in ASCII_LINES]
    extra = [c for c in font.codes() if not (32 <= c <= 126)]
    for i in range(0, len(extra), 32):
        chunk = extra[i:i + 32]
        rows.append(_row(font, f"{chunk[0]:04X}" if chunk[0] > 255 else f"{chunk[0]:02X}", chunk, gap=2))
    # The whole character set again, shuffled with fixed seeds, so every glyph appears in several different contexts.
    # Each of these lines gets 0-3 px of extra space above it (cycling), so line positions also vary modulo 4.
    max_width = max(r[1].shape[1] for r in rows[:len(ASCII_LINES)])
    k = 0
    for seed in SHUFFLE_SEEDS:
        for j, line in enumerate(shuffled_lines(font, seed, max_width)):
            rows.append(_row(font, f"s{seed}" if j == 0 else None, line, pad=k % 4)); k += 1
    return rows, len(extra)


LABEL_WIDTH, HEADER_HEIGHT = 40, 14


def glyph_boxes(rows):
    """Where to_image() puts each glyph: list of (code, row index, label, x0, y0, x1, y1) in specimen pixels."""
    out = []; y = HEADER_HEIGHT; label = None
    for ri, row in enumerate(rows):
        lab, r, pad, pos = row
        label = lab or label
        y += pad
        for c, x0, x1 in pos:
            out.append((c, ri, label or "ascii", LABEL_WIDTH + x0, y + 1, LABEL_WIDTH + x1, y + 1 + r.shape[0]))
        y += r.shape[0] + 2
    return out


def to_image(title, rows):
    LW = LABEL_WIDTH
    W = LW + max(r[1].shape[1] for r in rows)
    parts = []
    hdr = Image.new("L", (W, HEADER_HEIGHT), 215); ImageDraw.Draw(hdr).text((3, 1), title, fill=0); parts.append(np.array(hdr))
    for row in rows:
        lab, r = row[0], row[1]
        if len(row) > 2 and row[2]:
            parts.append(np.full((row[2], W), 255, np.uint8))     # extra space above this line
        line = np.full((r.shape[0] + 2, W), 255, np.uint8)
        line[1:-1, LW:LW + r.shape[1]] = np.where(r, 0, 255)
        if lab:
            l = Image.fromarray(line); ImageDraw.Draw(l).text((2, max(0, (r.shape[0] - 10) // 2)), lab, fill=140)
            line = np.array(l)
        parts.append(line)
    return np.vstack(parts)


if __name__ == "__main__":
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    for p in sys.argv[2:]:
        name = os.path.splitext(os.path.basename(p))[0]
        font = PixelTTF(p) if p.lower().endswith(".ttf") else BitmapFont(p)
        rows, n_extra = specimen(font)
        Image.fromarray(to_image(f"{name}  ({n_extra} non-ASCII glyphs)", rows)).save(f"{out}/{name}.png")
        print(f"{name:28s} non-ASCII glyphs: {n_extra}")
