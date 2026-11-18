"""Training pairs from hand-hinted TrueType fonts.

x: the font's own bilevel hinted rendering (FreeType, v35 TrueType interpreter = full native hinting) at an
   integer ppem, i.e. the bitmap the font's hinter designed for that size.
y: signed distance (1x px units, + = ink) at 4x of the *unhinted* outline, each glyph placed at the same origin
   as its hinted counterpart.

Usage: gen_hinted.py FONT_DIR OUT.npz COUNT
"""
import os
os.environ["FREETYPE_PROPERTIES"] = "truetype:interpreter-version=35"
import glob, random, sys
import numpy as np
import freetype
from multiprocessing import Pool
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen2 import pick_string, CHARS, CLIP

N, SS = 32, 8
_faces = {}


def faces(path, ppem):
    k = (path, ppem)
    if k not in _faces:
        lo = freetype.Face(path); lo.set_pixel_sizes(0, ppem)
        hi = freetype.Face(path); hi.set_char_size(ppem * SS * 64, 0, 72, 72)   # exactly ppem*8 px/em, unhinted
        _faces[k] = (lo, hi)
    return _faces[k]


def bits_of(bm, mono):
    if bm.rows == 0 or bm.width == 0:
        return np.zeros((0, 0), bool)
    buf = np.frombuffer(bytes(bm.buffer), np.uint8).reshape(bm.rows, bm.pitch)
    if mono:
        return np.unpackbits(buf, axis=1)[:, :bm.width].astype(bool)
    return buf[:, :bm.width] >= 128


def paste(dst, src, y0, x0):
    h, w = src.shape
    ya, xa = max(0, -y0), max(0, -x0)
    yb, xb = min(h, dst.shape[0] - y0), min(w, dst.shape[1] - x0)
    if yb > ya and xb > xa:
        dst[y0 + ya:y0 + yb, x0 + xa:x0 + xb] |= src[ya:yb, xa:xb]


def make(rng, fonts):
    path, cmapset = rng.choice(fonts)
    ppem = rng.choice([8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 15, 16, 17, 18, 20, 22, 24])
    lo, hi = faces(path, ppem)
    s = pick_string(rng, CHARS, cmapset)
    x = np.zeros((N, N), bool); m = np.zeros((N * SS, N * SS), bool)
    pen = rng.randrange(1, 10); base = rng.randrange(N // 2 + 2, N - 5)
    for ch in s:
        lo.load_char(ch, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_MONO)
        g = lo.glyph
        paste(x, bits_of(g.bitmap, True), base - g.bitmap_top, pen + g.bitmap_left)
        hi.load_char(ch, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_NO_HINTING)
        h = hi.glyph
        paste(m, bits_of(h.bitmap, False), base * SS - h.bitmap_top, pen * SS + h.bitmap_left)
        pen += (g.advance.x + 32) >> 6          # hinted (integer) advance, as the screen would lay it out
    if x.sum() < 3:
        raise ValueError("empty")
    sdf = (ndimage.distance_transform_edt(m) - ndimage.distance_transform_edt(~m)) / SS
    if rng.random() < 0.1:
        x = ~x; sdf = -sdf
    y = np.clip(sdf.reshape(4 * N, 2, 4 * N, 2).mean(axis=(1, 3)), -CLIP, CLIP)
    return x.astype(np.uint8), np.round(y * 80).astype(np.int8)


def worker(args):
    seed, n, fonts = args
    rng = random.Random(seed); xs, ys = [], []
    while len(xs) < n:
        try:
            a, b = make(rng, fonts)
        except Exception:
            continue
        xs.append(a); ys.append(b)
    return np.stack(xs), np.stack(ys)


if __name__ == "__main__":
    from fontTools.ttLib import TTFont
    fdir, out, total = sys.argv[1], sys.argv[2], int(sys.argv[3])
    fonts = [(p, frozenset(chr(c) for c in TTFont(p, lazy=True).getBestCmap())) for p in sorted(glob.glob(fdir + "/*.ttf"))]
    print(len(fonts), "fonts:", [os.path.basename(p) for p, _ in fonts], flush=True)
    base = 5 * 10**6 if "val" in os.path.basename(out) else 3 * 10**6
    with Pool(4) as p:
        parts = p.map(worker, [(base + i, 500, fonts) for i in range(total // 500)])
    X = np.concatenate([a for a, _ in parts]); Y = np.concatenate([b for _, b in parts])
    np.savez(out, x=X, y=Y)
    print("saved", X.shape)
