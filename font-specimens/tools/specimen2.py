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


def draw_line(font, codes, gap=0):
    H = font.height
    glyphs = [font.glyph(c) for c in codes]
    W = 8 + sum(max(g[2], g[1] + g[0].shape[1]) + gap if g else 4 for g in glyphs) + 16
    canvas = np.zeros((H, W), bool); pen = 4
    for g in glyphs:
        if g is None:
            pen += 4; continue
        bits, x_off, adv = g
        x = pen + x_off
        if bits.shape[1] and x >= 0:
            canvas[:, x:x + bits.shape[1]] |= bits[:, :max(0, min(bits.shape[1], W - x))]
        pen += max(adv, x_off + bits.shape[1]) + gap if gap else adv
    return canvas[:, :pen + 4]


def specimen(font):
    rows = [(None, draw_line(font, [ord(c) for c in t])) for t in ASCII_LINES]
    extra = [c for c in font.codes() if not (32 <= c <= 126)]
    for i in range(0, len(extra), 32):
        chunk = extra[i:i + 32]
        rows.append((f"{chunk[0]:04X}" if chunk[0] > 255 else f"{chunk[0]:02X}", draw_line(font, chunk, gap=2)))
    return rows, len(extra)


def to_image(title, rows):
    LW = 40
    W = LW + max(r.shape[1] for _, r in rows)
    parts = []
    hdr = Image.new("L", (W, 14), 215); ImageDraw.Draw(hdr).text((3, 1), title, fill=0); parts.append(np.array(hdr))
    for lab, r in rows:
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
