"""Measure stroke thickness and reference lines on upscaled picks (pick_typical.py output), in source pixels."""
import json
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None


def runs(v):
    out, n, start = [], 0, 0
    for i, x in enumerate(list(v) + [False]):
        if x and not n: start = i
        if x: n += 1
        elif n: out.append((start, n)); n = 0
    return out


class PickMetrics:
    def __init__(self, prefix):
        J = json.load(open(prefix + "_glyphs.json"))
        self.k = J["scale"][0]
        self.cov = 1 - np.array(Image.open(prefix + "_avg_grey.png").convert("L")).astype(np.float32) / 255
        self.g = {g["code"]: g for g in J["glyphs"]}

    def ink(self, code):
        """inked mask of one glyph and its (ox, oy) origin in the pick image. Limited to the glyph's own ink box
        (ink_avg, measured on the glyph before the rebuild packed it next to its neighbours), so a kerned neighbour's
        ink in the cell's margin is not counted."""
        g = self.g[code]; x0, y0, x1, y1 = g.get("ink_avg") or g["cell"]
        m = np.zeros(self.cov.shape, bool); m[y0:y1, x0:x1] = self.cov[y0:y1, x0:x1] >= 0.5
        return m, g["origin"], (x0, y0, x1, y1)

    def edges(self, code):
        """ink extent in source px: left/right from the pen, top/bottom up from the baseline"""
        m, (ox, oy), _ = self.ink(code); ys, xs = np.nonzero(m)
        return dict(left=(xs.min() - ox) / self.k, right=(xs.max() + 1 - ox) / self.k,
                    top=(oy - ys.min()) / self.k, bottom=(oy - ys.max() - 1) / self.k)

    def stem(self, chars="lIHnmdbpqh"):
        """median width of vertical strokes across the middle rows, source px"""
        w = []
        for ch in chars:
            m, _, (x0, y0, x1, y1) = self.ink(ord(ch)); ys = np.nonzero(m.any(1))[0]; mid = (ys.min() + ys.max()) // 2
            for r in range(mid - 2, mid + 3):
                w += [n for _, n in runs(m[r, x0:x1])]
        return float(np.median(w)) / self.k

    def bar(self, chars="EFTZz"):
        """median thickness of horizontal strokes down the middle columns, source px (excluding long vertical runs)"""
        t = []
        for ch in chars:
            m, _, (x0, y0, x1, y1) = self.ink(ord(ch)); xs = np.nonzero(m.any(0))[0]; mid = (xs.min() + xs.max()) // 2
            H = np.nonzero(m.any(1))[0]; Hh = H.max() - H.min() + 1
            for c in range(mid - 2, mid + 3):
                t += [n for _, n in runs(m[y0:y1, c]) if n < 0.4 * Hh]
        return float(np.median(t)) / self.k

    def refs(self):
        """edge reference lines (source px, y up): descender, baseline, x-height, cap height"""
        return [self.edges(ord("p"))["bottom"], self.edges(ord("H"))["bottom"], self.edges(ord("x"))["top"], self.edges(ord("H"))["top"]]
