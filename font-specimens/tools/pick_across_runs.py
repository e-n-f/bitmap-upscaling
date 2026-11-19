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
"""
import argparse, json
import numpy as np
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("upscaled", nargs="+"); ap.add_argument("--layout", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--force", default="", help="CHAR:SCALE pairs, comma-separated, e.g. g:6,d:8")
a = ap.parse_args()
L = json.load(open(a.layout))


def binarize(c):
    bg, ink = np.percentile(c, 90), np.percentile(c, 2)
    return c < (bg + ink) / 2 if bg - ink > 40 else np.zeros(c.shape, bool)


runs = []
for path in a.upscaled:
    up = np.array(Image.open(path).convert("L"))
    sx, sy = up.shape[1] / L["width"], up.shape[0] / L["height"]
    runs.append(dict(path=path, up=up, sx=sx, sy=sy, scale=int(round(sx))))
runs.sort(key=lambda r: r["scale"])
target = max(runs, key=lambda r: r["sx"])


def crop(r, b):
    X0, X1 = int(round((b["x0"] - 0.5) * r["sx"])), int(round((b["x1"] + 0.5) * r["sx"]))
    Y0, Y1 = int(round(b["y0"] * r["sy"])), int(round(b["y1"] * r["sy"]))
    return r["up"][Y0:Y1, X0:X1]


chars = []
for b in L["boxes"]:
    if b["char"] not in chars:
        chars.append(b["char"])
force = {p.split(":")[0]: int(p.split(":")[1]) for p in a.force.split(",") if p}

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
        best = next(k for k, c in enumerate(cands) if c["run"]["scale"] == force[ch])
    else:
        best = int(np.argmin([c["med"] for c in cands]))
    choice[ch] = cands[best]
    pad = 8; H = max(c["crop"].shape[0] for c in cands) + 16
    row = Image.new("L", (sum(c["crop"].shape[1] + 2 * pad for c in cands) + 40, H), 255); d = ImageDraw.Draw(row); x = 5
    for k, c in enumerate(cands):
        row.paste(Image.fromarray(np.where(binarize(c["crop"]), 0, 255).astype(np.uint8)), (x + pad, 0))
        if k == best:
            d.rectangle([x + pad - 3, 0, x + pad + c["crop"].shape[1] + 2, c["crop"].shape[0] + 1], outline=0, width=3)
        d.text((x + pad, H - 14), f"{c['run']['scale']}x {c['med']:.0f}" + ("*" if ch in force and k == best else ""),
               fill=0 if k == best else 140)
        x += c["crop"].shape[1] + 2 * pad
    rows.append(row)

W = max(r.width for r in rows); S = Image.new("L", (W, sum(r.height + 6 for r in rows)), 255); y = 0
for r in rows:
    S.paste(r, (0, y)); y += r.height + 6
S.save(a.out + "_compare.png")

first = [b for b in L["boxes"] if b["block"] == [0, 0]]
xk = "x0_unspaced" if "x0_unspaced" in first[0] else "x0"
x_min = min(b[xk] for b in first) - 2; y_min = min(b["y0"] for b in first) - 2
x_max = max(b[xk.replace("x0", "x1")] for b in first) + 2; y_max = max(b["y1"] for b in first) + 2
sx, sy = target["sx"], target["sy"]
shape = (int((y_max - y_min) * sy), int((x_max - x_min) * sx))
bw = np.full(shape, 255, np.uint8); grey = np.full(shape, 255, np.uint8)
for b in first:
    c = choice[b["char"]]["crop"]; cb = np.where(binarize(c), 0, 255).astype(np.uint8)
    X0, Y0 = int(round((b[xk] - 0.5 - x_min) * sx)), int(round((b["y0"] - y_min) * sy))
    for canvas, img in ((bw, cb), (grey, c)):
        region = canvas[Y0:Y0 + img.shape[0], X0:X0 + img.shape[1]]
        region[...] = np.minimum(region, img[:region.shape[0], :region.shape[1]])
Image.fromarray(bw).save(a.out + "_best.png"); Image.fromarray(grey).save(a.out + "_best_grey.png")
from collections import Counter
print("scale used per character:", " ".join(f"{ch}:{choice[ch]['run']['scale']}" for ch in chars))
print("count by scale:", dict(Counter(choice[ch]["run"]["scale"] for ch in chars)))
