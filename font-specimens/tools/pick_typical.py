"""From an upscaled phase grid, pick each character's most frequently produced version.

usage: python -I pick_typical.py --layout GRID.json --upscaled UPSCALED.png --out OUT_PREFIX [--tolerance 6]

Each appearance is thresholded relative to its own background and ink levels (halfway between its 90th-percentile
grey and the typical grey of its clearly dark pixels), which removes the upscaler's uneven background tint. Appearances are compared pairwise (differing
pixels as % of the character's ink). The chosen version is the one with the smallest median difference from the
others: the most typical shape, which an occasional bad rendering cannot win. Appearances whose median difference is
more than 1.6x the chosen one's are flagged as outliers. Writes:
  OUT_PREFIX_choices.png  every appearance of every character (thresholded), the chosen one boxed, each labelled with
                          its median difference from the others; outliers are labelled "x"
  OUT_PREFIX_best.png     A-Z, a-z and 0-9 rebuilt from the chosen versions (thresholded, black and white), placed where
                          the glyphs are in the grid's first block, at their unspaced positions if the grid was
                          made with --letterspacing
  OUT_PREFIX_best_grey.png  the same, using the chosen versions' original grey pixels
  OUT_PREFIX_avg.png      the same lines rebuilt from averages instead of single versions: for each character, every
                          appearance that is not an outlier (the chosen one included) is normalised to its own
                          background (white) and ink (black) levels, the normalised appearances are averaged, and the
                          average is thresholded at 50%. This smooths edge jitter and background tint.
  OUT_PREFIX_avg_grey.png the averages before thresholding
  OUT_PREFIX_glyphs.json  for each character in the rebuilt images: its identity (char, Unicode, the font's byte code),
                          its cell and ink bounding boxes (single winner and average) in rebuilt-image pixels, and the
                          source font's metrics (advance width, left offset; pen origin and baseline in rebuilt-image
                          pixels), plus the pick statistics

Crop margins: each appearance is cut out with --margin-y source pixels above and below the font's glyph rectangle
(default 1.5; lines are always at least 3 px apart) and --margin-x to the left and right of its ink (default 1 for
grids with at least 2 px letterspacing, else 0.5 so kerned neighbours stay out), because upscaled strokes can extend
slightly beyond the source bitmap (e.g. Chicago's "g" and "y" descenders).
"""
import argparse, json, os
import numpy as np
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("--chars", help="only show these characters in _choices.png (all are still chosen)")
ap.add_argument("--layout", required=True); ap.add_argument("--upscaled", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--margin-x", type=float, default=None); ap.add_argument("--margin-y", type=float, default=1.5)
a = ap.parse_args()

L = json.load(open(a.layout))
MX = a.margin_x if a.margin_x is not None else (1.0 if L.get("letterspacing", 0) >= 2 else 0.5)
MY = a.margin_y
up = np.array(Image.open(a.upscaled).convert("L"))
sx, sy = up.shape[1] / L["width"], up.shape[0] / L["height"]


def crop(b):
    # the glyph's own columns plus MX source px each side; its glyph rectangle plus MY above and below
    X0, X1 = int(round((b["x0"] - MX) * sx)), int(round((b["x1"] + MX) * sx))
    Y0, Y1 = int(round((b["y0"] - MY) * sy)), int(round((b["y1"] + MY) * sy))
    return up[Y0:Y1, X0:X1]


def levels(c):
    """(background, ink) grey levels of a crop: background = 90th percentile; ink = 10th percentile of the pixels clearly
    darker than the background, so even very sparse glyphs (an ellipsis's three dots) are measured correctly.
    Returns None for a crop with no ink."""
    bg = np.percentile(c, 90)
    dark = c[c < bg - 40]
    if dark.size < 4:
        return None
    return bg, np.percentile(dark, 10)


def normalize(c):
    """Map this crop's background (90th percentile) to 255 and its ink (2nd percentile) to 0."""
    lv = levels(c)
    if lv is None:
        return np.full(c.shape, 255.0)
    bg, ink = lv
    return np.clip((c.astype(float) - ink) / (bg - ink), 0, 1) * 255


def binarize(c):
    """Threshold halfway between this crop's background and ink levels."""
    lv = levels(c)
    return c < sum(lv) / 2 if lv else np.zeros(c.shape, bool)


chars = []
for b in L["boxes"]:
    if b["char"] not in chars:
        chars.append(b["char"])
picks = {}; report = []; rows = []
for ch in chars:
    inst = sorted([b for b in L["boxes"] if b["char"] == ch], key=lambda b: (b["y_phase"], b["x_phase"]))
    crops = [crop(b) for b in inst]
    h = min(c.shape[0] for c in crops); w = min(c.shape[1] for c in crops)
    bits = [binarize(c[:h, :w]) for c in crops]
    ink = np.mean([x.sum() for x in bits]) or 1
    D = np.array([[(x != y).sum() / ink * 100 for y in bits] for x in bits])
    med = np.array([np.median(np.delete(D[i], i)) for i in range(len(bits))])
    best = int(np.argmin(med))
    outlier = med > 1.6 * med[best]
    inliers = [crops[i][:h, :w] for i in range(len(crops)) if not outlier[i]]
    avg = np.mean([normalize(c) for c in inliers], axis=0).round().astype(np.uint8)
    picks[ch] = (inst, crops, bits, best, avg, len(inliers))
    report.append((ch, med[best], int(outlier.sum())))
    pad = 6; H = max(c.shape[0] for c in crops) + 16
    row = Image.new("L", (sum(c.shape[1] + 2 * pad for c in crops) + 10, H), 255); d = ImageDraw.Draw(row); x = 5
    for i, c in enumerate(crops):
        row.paste(Image.fromarray(np.where(binarize(c), 0, 255).astype(np.uint8)), (x + pad, 0))
        if i == best:
            d.rectangle([x + pad - 3, 0, x + pad + c.shape[1] + 2, c.shape[0] + 1], outline=0, width=3)
        d.text((x + pad, H - 14), ("x " if outlier[i] else "") + str(int(round(med[i]))), fill=0 if i == best else 140)
        x += c.shape[1] + 2 * pad
    if not a.chars or ch in a.chars:
        rows.append(row)

W = max(r.width for r in rows); S = Image.new("L", (W, sum(r.height + 6 for r in rows)), 255); y = 0
for r in rows:
    S.paste(r, (0, y)); y += r.height + 6
S.save(a.out + "_choices.png")

# rebuild the first block's lines from the chosen versions
first = [b for b in L["boxes"] if b["block"] == [0, 0]]
xk = "x0_unspaced" if "x0_unspaced" in first[0] else "x0"          # take letterspacing back out when present
x_min = min(b[xk] for b in first) - MX - 2; y_min = min(b["y0"] for b in first) - MY - 2
x_max = max(b[xk.replace("x0", "x1")] for b in first) + MX + 2; y_max = max(b["y1"] for b in first) + MY + 2
shape = (int((y_max - y_min) * sy), int((x_max - x_min) * sx))
def rebuild(images, path):
    canvas = np.full(shape, 255, np.uint8)
    for b in first:
        img = images[b["char"]]
        X0, Y0 = int(round((b[xk] - MX - x_min) * sx)), int(round((b["y0"] - MY - y_min) * sy))
        region = canvas[Y0:Y0 + img.shape[0], X0:X0 + img.shape[1]]
        region[...] = np.minimum(region, img[:region.shape[0], :region.shape[1]])
    Image.fromarray(canvas).save(path)


def write_glyphs_json(path, chosen, chosen_avg, source_scale, extra=None):
    """Per-character identities, boxes and metrics for the rebuilt images (all *_best/*_avg images share one layout).
    chosen / chosen_avg: char -> greyscale crop placed in the rebuilt image (single winner / average)."""
    asc = L.get("ascent")
    out = dict(layout=os.path.basename(a.layout), upscaled=os.path.basename(a.upscaled if hasattr(a, "upscaled") and isinstance(a.upscaled, str) else ""),
               scale=[sx, sy], source_scale=source_scale, image_size=list(shape[::-1]),
               coordinates="pixels in the rebuilt *_best/*_avg images; x right, y down; boxes are [x0, y0, x1, y1), x1/y1 exclusive",
               ascent_px=asc, glyph_height_px=L["glyph_height"], glyphs=[])
    for b in first:
        ch = b["char"]
        X0, Y0 = int(round((b[xk] - MX - x_min) * sx)), int(round((b["y0"] - MY - y_min) * sy))
        g = dict(char=ch, code=b.get("code"), unicode=(f"U+{ord(ch):04X}" if len(ch) == 1 else None), line=b["line"])
        c = chosen[ch]
        g["cell"] = [X0, Y0, X0 + c.shape[1], Y0 + c.shape[0]]
        for key, img in (("ink_best", binarize(c)), ("ink_avg", chosen_avg[ch] < 128)):
            ys, xs = np.nonzero(img)
            g[key] = [X0 + int(xs.min()), Y0 + int(ys.min()), X0 + int(xs.max()) + 1, Y0 + int(ys.max()) + 1] if len(xs) else None
        if "x_offset" in b:
            pen = b[xk] - b["x_offset"]
            g["source"] = dict(advance=b["advance"], x_offset=b["x_offset"], ink_width=b["x1"] - b["x0"],
                               pen_x=pen, ink_x0=b[xk], top_y=b["y0"])
            g["origin"] = [round((pen - x_min) * sx, 2), round((b["y0"] + asc - y_min) * sy, 2) if asc is not None else None]
            g["advance_px"] = round(b["advance"] * sx, 2)
        if extra:
            g.update(extra.get(ch, {}))
        out["glyphs"].append(g)
    json.dump(out, open(path, "w"), indent=1, ensure_ascii=False)


rebuild({ch: np.where(binarize(p[1][p[3]]), 0, 255).astype(np.uint8) for ch, p in picks.items()}, a.out + "_best.png")
rebuild({ch: p[1][p[3]] for ch, p in picks.items()}, a.out + "_best_grey.png")
rebuild({ch: np.where(p[4] < 128, 0, 255).astype(np.uint8) for ch, p in picks.items()}, a.out + "_avg.png")
rebuild({ch: p[4] for ch, p in picks.items()}, a.out + "_avg_grey.png")
stats = {ch: dict(chosen_appearance=dict(zip(("x_phase", "y_phase"), p[0][p[3]]["block"])), averaged_appearances=int(p[5]),
                  median_difference_pct=round(float(m), 1), outliers=int(n))
         for (ch, p), (_, m, n) in zip(picks.items(), report)}
write_glyphs_json(a.out + "_glyphs.json", {ch: p[1][p[3]] for ch, p in picks.items()}, {ch: p[4] for ch, p in picks.items()},
                  None, stats)

print(f"averages use {np.mean([p[5] for p in picks.values()]):.1f} appearances per character on average")
print("chosen version's median difference from the other appearances (% of ink), and number of outliers:")
print("  ".join(f"{c}:{m:.0f}" + (f"({n}x)" if n else "") for c, m, n in report))
