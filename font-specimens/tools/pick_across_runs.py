"""Choose each character's version from several upscales (e.g. 6x, 7x, 8x) of the same phase grid.

usage: python -I pick_across_runs.py --layout GRID.json --out OUT_PREFIX UPSCALED1.png UPSCALED2.png ... [--force g:6,d:8]

For each upscale, each character's most typical version is picked as in pick_typical.py (thresholded relative to its
own background and ink; smallest median difference from its other appearances). That median difference also measures
how consistent the upscaler is with itself for that character at that scale. By default each character comes from the
upscale where it is most consistent. --force CHAR:SCALE,... overrides that (SCALE is the rounded scale factor).
Writes:
  OUT_PREFIX_compare.png  for each character, the pick from every upscale (shown at the largest scale), labelled
                          with scale and consistency; the one used is boxed
  OUT_PREFIX_best.png     A-Z, a-z and 0-9 rebuilt at the largest scale from the chosen picks (thresholded), at
                          unspaced positions if the grid was made with --letterspacing
  OUT_PREFIX_best_grey.png  the same in grey
  OUT_PREFIX_glyphs.json  identities, boxes and source metrics for each character in the rebuilt images (as
                          pick_typical.py), plus which scale each character came from

Crop margins: each appearance is cut out with --margin-y source pixels above and below the font's glyph rectangle
(default 1.5; lines are always at least 3 px apart) and --margin-x to the left and right of its ink (default 1 for
grids with at least 2 px letterspacing, else 0.5 so kerned neighbours stay out), because upscaled strokes can extend
slightly beyond the source bitmap (e.g. Chicago's "g" and "y" descenders).
"""
import argparse, json, os
import numpy as np
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("upscaled", nargs="+"); ap.add_argument("--layout", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--force", default="", help="CHAR:RUN pairs, comma-separated, e.g. g:6,d:8 (RUN is a scale, or a --names label)")
ap.add_argument("--names", default="", help="comma-separated labels for the upscales, in order (default: their scales, e.g. 6x)")
ap.add_argument("--margin-x", type=float, default=None); ap.add_argument("--margin-y", type=float, default=1.5)
a = ap.parse_args()
L = json.load(open(a.layout))
MX = a.margin_x if a.margin_x is not None else (1.0 if L.get("letterspacing", 0) >= 2 else 0.5)
MY = a.margin_y


def levels(c):
    """(background, ink) grey levels of a crop: background = 90th percentile; ink = 10th percentile of the pixels clearly
    darker than the background, so even very sparse glyphs (an ellipsis's three dots) are measured correctly.
    Returns None for a crop with no ink."""
    bg = np.percentile(c, 90)
    dark = c[c < bg - 40]
    if dark.size < 4:
        return None
    return bg, np.percentile(dark, 10)


def binarize(c):
    lv = levels(c)
    return c < sum(lv) / 2 if lv else np.zeros(c.shape, bool)


runs = []
for path in a.upscaled:
    up = np.array(Image.open(path).convert("L"))
    sx, sy = up.shape[1] / L["width"], up.shape[0] / L["height"]
    runs.append(dict(path=path, up=up, sx=sx, sy=sy, scale=int(round(sx))))
names = [n.strip() for n in a.names.split(",")] if a.names else None
for i, r in enumerate(runs):
    r["name"] = names[i] if names else f"{r['scale']}x"
runs.sort(key=lambda r: r["scale"])
target = max(runs, key=lambda r: r["sx"])


def crop(r, b):
    X0, X1 = int(round((b["x0"] - MX) * r["sx"])), int(round((b["x1"] + MX) * r["sx"]))
    Y0, Y1 = int(round((b["y0"] - MY) * r["sy"])), int(round((b["y1"] + MY) * r["sy"]))
    return r["up"][Y0:Y1, X0:X1]


chars = []
for b in L["boxes"]:
    if b["char"] not in chars:
        chars.append(b["char"])
force = {p.rsplit(":", 1)[0]: p.rsplit(":", 1)[1] for p in a.force.split(",") if p}

choice = {}; rows = []
for ch in chars:
    inst = [b for b in L["boxes"] if b["char"] == ch]
    cands = []
    for r in runs:
        crops = [crop(r, b) for b in inst]
        h = min(c.shape[0] for c in crops); w = min(c.shape[1] for c in crops)
        bits = [binarize(c[:h, :w]) for c in crops]
        ink = np.mean([x.sum() for x in bits]) or 1
        D = np.array([[(x != y).sum() / ink * 100 for y in bits] for x in bits])
        med = np.array([np.median(np.delete(D[i], i)) for i in range(len(bits))])
        i = int(np.argmin(med))
        # resize the pick to the target scale
        c = crops[i]; tw = int(round(c.shape[1] * target["sx"] / r["sx"])); th = int(round(c.shape[0] * target["sy"] / r["sy"]))
        cands.append(dict(run=r, med=float(med[i]), crop=np.array(Image.fromarray(c).resize((tw, th), Image.BICUBIC))))
    if ch in force:
        best = next(k for k, c in enumerate(cands) if force[ch] in (c["run"]["name"], str(c["run"]["scale"]), f"{c['run']['scale']}x"))
    else:
        best = int(np.argmin([c["med"] for c in cands]))
    choice[ch] = cands[best]
    pad = 8; H = max(c["crop"].shape[0] for c in cands) + 16
    row = Image.new("L", (sum(c["crop"].shape[1] + 2 * pad for c in cands) + 40, H), 255); d = ImageDraw.Draw(row); x = 5
    for k, c in enumerate(cands):
        row.paste(Image.fromarray(np.where(binarize(c["crop"]), 0, 255).astype(np.uint8)), (x + pad, 0))
        if k == best:
            d.rectangle([x + pad - 3, 0, x + pad + c["crop"].shape[1] + 2, c["crop"].shape[0] + 1], outline=0, width=3)
        d.text((x + pad, H - 14), f"{c['run']['name']} {c['med']:.0f}" + ("*" if ch in force and k == best else ""),
               fill=0 if k == best else 140)
        x += c["crop"].shape[1] + 2 * pad
    rows.append(row)

W = max(r.width for r in rows); S = Image.new("L", (W, sum(r.height + 6 for r in rows)), 255); y = 0
for r in rows:
    S.paste(r, (0, y)); y += r.height + 6
S.save(a.out + "_compare.png")

first = [b for b in L["boxes"] if b["block"] == [0, 0]]
xk = "x0_unspaced" if "x0_unspaced" in first[0] else "x0"
x_min = min(b[xk] for b in first) - MX - 2; y_min = min(b["y0"] for b in first) - MY - 2
x_max = max(b[xk.replace("x0", "x1")] for b in first) + MX + 2; y_max = max(b["y1"] for b in first) + MY + 2
sx, sy = target["sx"], target["sy"]
shape = (int((y_max - y_min) * sy), int((x_max - x_min) * sx))
bw = np.full(shape, 255, np.uint8); grey = np.full(shape, 255, np.uint8)
for b in first:
    c = choice[b["char"]]["crop"]; cb = np.where(binarize(c), 0, 255).astype(np.uint8)
    X0, Y0 = int(round((b[xk] - MX - x_min) * sx)), int(round((b["y0"] - MY - y_min) * sy))
    for canvas, img in ((bw, cb), (grey, c)):
        region = canvas[Y0:Y0 + img.shape[0], X0:X0 + img.shape[1]]
        region[...] = np.minimum(region, img[:region.shape[0], :region.shape[1]])
Image.fromarray(bw).save(a.out + "_best.png"); Image.fromarray(grey).save(a.out + "_best_grey.png")
a.upscaled = ", ".join(os.path.basename(u) for u in a.upscaled)

def write_glyphs_json(path, chosen, chosen_avg, source_scale, extra=None):
    """Per-character identities, boxes and metrics for the rebuilt images (all *_best/*_avg images share one layout).
    chosen / chosen_avg: char -> greyscale crop placed in the rebuilt image (single winner / average)."""
    asc = L.get("ascent")
    out = dict(layout=os.path.basename(a.layout), upscaled=a.upscaled,
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

write_glyphs_json(a.out + "_glyphs.json", {ch: choice[ch]["crop"] for ch in chars},
                  {ch: np.where(binarize(choice[ch]["crop"]), 0, 255).astype(np.uint8) for ch in chars}, None,
                  {ch: dict(run_used=choice[ch]["run"]["name"], scale_used=choice[ch]["run"]["scale"], median_difference_pct=round(choice[ch]["med"], 1)) for ch in chars})
from collections import Counter
print("run used per character:", " ".join(f"{ch}:{choice[ch]['run']['name']}" for ch in chars))
print("count by run:", dict(Counter(choice[ch]["run"]["name"] for ch in chars)))
