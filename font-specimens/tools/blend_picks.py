"""Blend the outlines of two or more sizes of a font, using upscaled picks (pick_typical.py) as the shapes.

usage: python -I blend_picks.py OUT_PREFIX LABEL=FONT_SPEC=PICK_PREFIX[=WEIGHT] ... [--ss 6] [--threshold 0.5]
  FONT_SPEC   APPLEDOUBLE:TYPE:ID of that size's bitmap font (for its metrics: reference lines and ink extents)
  PICK_PREFIX prefix of that size's pick_typical.py outputs (uses PREFIX_avg_grey.png and PREFIX_glyphs.json)
The last size listed is the target, whose metrics and advance widths are used.

Each size's picked glyph is mapped onto the target glyph as in composite_sizes.py: vertically piecewise-linearly
through descender, baseline, x-height and cap height; horizontally by stretching the source font's ink extent onto the
target's. By default (--mode grey) the mapped picks' grey coverage is averaged with the given weights. With --mode sdf, each
mapped glyph is thresholded at --threshold and the signed distance fields are averaged instead, for one crisp outline;
that loses thin hairlines and serifs. Writes:
  OUT_PREFIX_blend.png     the blend at --ss times the target size (grey, or black and white with --mode sdf)
  OUT_PREFIX_blend_1x.png  reduced to the target size by averaging SS x SS blocks
"""
import argparse, json, os, sys
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt as edt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from macspecimens import collect, QDFont

Image.MAX_IMAGE_PIXELS = None
ap = argparse.ArgumentParser()
ap.add_argument("out"); ap.add_argument("sizes", nargs="+"); ap.add_argument("--ss", type=int, default=6)
ap.add_argument("--threshold", type=float, default=0.5)
ap.add_argument("--align", choices=("edges", "centers"), default="edges",
                help="edges: align the bitmap fonts' ink edges and reference lines (descender, baseline, x-height, cap height). "
                     "centers: align stroke centres measured on the picks: each reference line moved inward by half that "
                     "size's horizontal stroke thickness, and each glyph's outer edges by half its stem width")
ap.add_argument("--mode", choices=("grey", "sdf"), default="grey",
                help="grey: weighted average of the mapped picks' grey coverage, no thresholding (default). "
                     "sdf: threshold each pick and average signed distance fields (crisp, but loses thin strokes)")
a = ap.parse_args()

sizes = []
for spec in a.sizes:
    parts = spec.split("=")
    label, fspec, prefix = parts[0], parts[1], parts[2]
    weight = float(parts[3]) if len(parts) > 3 else 1.0
    path, t, i = fspec.rsplit(":", 2)
    f = next(QDFont(c[6]) for c in collect(path) if c[1] == t and c[2] == int(i))
    J = json.load(open(prefix + "_glyphs.json"))
    cov = 1 - np.array(Image.open(prefix + "_avg_grey.png").convert("L")).astype(np.float32) / 255
    sizes.append(dict(label=label, font=f, glyphs={g["code"]: g for g in J["glyphs"]}, cov=cov, k=J["scale"][0], w=weight,
                      prefix=prefix))


def ink_edges(f, code):
    g = f.glyph(code)
    if g is None or not g[0].any():
        return None
    r = np.nonzero(g[0].any(1))[0]; c = np.nonzero(g[0].any(0))[0]
    return dict(top=f.ascent - r[0], bottom=f.ascent - r[-1] - 1, left=g[1] + c[0], right=g[1] + c[-1] + 1)


def refs(f):
    return [ink_edges(f, ord("p"))["bottom"], 0, ink_edges(f, ord("x"))["top"], ink_edges(f, ord("H"))["top"]]


T = sizes[-1]["font"]
if a.align == "centers":
    from pick_metrics import PickMetrics
    for s in sizes:
        pm = PickMetrics(s["prefix"]); r = pm.refs(); h = pm.bar(); v = pm.stem()
        s["pm"], s["stem"] = pm, v
        s["cref"] = [r[0] + h / 2, r[1] + h / 2, r[2] - h / 2, r[3] - h / 2]
        print(f"  {s['label']}: stem {v:.2f}, horizontal stroke {h:.2f}, stroke-centre lines {[round(x, 2) for x in s['cref']]} (source px)")
    tref = sizes[-1]["cref"]
else:
    tref = refs(T)
for s in sizes:
    sref = s["cref"] if a.align == "centers" else refs(s["font"])
    k_lo = (sref[1] - sref[0]) / (tref[1] - tref[0]); k_hi = (sref[3] - sref[2]) / (tref[3] - tref[2])
    s["inv"] = (lambda sref, k_lo, k_hi: lambda ty: np.where(ty < tref[0], sref[0] + (ty - tref[0]) * k_lo,
                np.where(ty > tref[3], sref[3] + (ty - tref[3]) * k_hi, np.interp(ty, tref, sref))))(sref, k_lo, k_hi)


def centre_box(s, code):
    """left/right outer-stroke centres of a glyph on its pick (source px), or its edges for very narrow glyphs"""
    e = s["pm"].edges(code); v = s["stem"]
    if e["right"] - e["left"] < 2 * v:
        return dict(left=e["left"], right=e["right"])
    return dict(left=e["left"] + v / 2, right=e["right"] - v / 2)


def sample_pick(s, code, TX, TY, tb):
    """coverage of size s's picked glyph at target points (target px; x from target pen, y up from baseline)"""
    g = s["glyphs"].get(code); sb = ink_edges(s["font"], code)
    if g is None or sb is None or g.get("origin") is None:
        return None
    if a.align == "centers":
        sb = centre_box(s, code); tb = centre_box(sizes[-1], code)
    sx = sb["left"] + (TX - tb["left"]) * (sb["right"] - sb["left"]) / (tb["right"] - tb["left"])   # source px from pen
    sy = s["inv"](TY)                                                                               # source px up
    ox, oy = g["origin"]; k = s["k"]
    px = ox + sx * k - 0.5; py = oy - sy * k - 0.5                                                  # pick image px
    x0, y0, x1, y1 = g["cell"]
    img = np.zeros_like(s["cov"]); img[y0:y1, x0:x1] = s["cov"][y0:y1, x0:x1]                       # only this glyph
    c0 = np.floor(px).astype(int); r0 = np.floor(py).astype(int); dc = px - c0; dr = py - r0
    H, W = img.shape
    def at(r, c):
        ok = (r >= 0) & (r < H) & (c >= 0) & (c < W)
        return np.where(ok, img[np.clip(r, 0, H - 1), np.clip(c, 0, W - 1)], 0)
    return (at(r0, c0) * (1 - dr) * (1 - dc) + at(r0, c0 + 1) * (1 - dr) * dc +
            at(r0 + 1, c0) * dr * (1 - dc) + at(r0 + 1, c0 + 1) * dr * dc)


SS = a.ss
SHORT = ["ABCDEFGHIJKLM", "NOPQRSTUVWXYZ", "abcdefghijklm", "nopqrstuvwxyz", "0123456789",
         "!\"#$%&'()*+,-", "./:;<=>?@[\\]^", "_`{|}~"]
have = set.intersection(*[set(s["glyphs"]) for s in sizes])
codes_t = [c for c in T.codes() if c in have and c != 32]
lines = [[ord(ch) for ch in l if ord(ch) in codes_t] for l in SHORT]
used = {c for l in lines for c in l}
extra = [c for c in codes_t if c not in used and (c < 32 or c >= 127)]
lines += [extra[i:i + 13] for i in range(0, len(extra), 13)]
y_top = T.ascent + 2; line_h = T.height + 4
out_lines = []
for l in lines:
    pen = 4; parts = []
    for code in l:
        tb = ink_edges(T, code); bits, xo, adv = T.glyph(code)
        x_lo, x_hi = min(0, xo) - 2, max(adv, xo + bits.shape[1]) + 2
        xs = x_lo + (np.arange((x_hi - x_lo) * SS) + 0.5) / SS
        ys = y_top - (np.arange(line_h * SS) + 0.5) / SS
        TX, TY = np.meshgrid(xs, ys)
        sd, ws = [], []
        for s in sizes:
            cv = sample_pick(s, code, TX, TY, tb)
            if cv is None:
                continue
            if a.mode == "sdf":
                inside = cv >= a.threshold
                sd.append(edt(inside) - edt(~inside))
            else:
                sd.append(cv)
            ws.append(s["w"])
        w = np.array(ws) / sum(ws)
        shape = (np.tensordot(w, np.array(sd), axes=1) > 0) if a.mode == "sdf" else np.tensordot(w, np.array(sd), axes=1)
        parts.append((pen + x_lo, shape)); pen += adv
    W = (pen + 8) * SS; canvas = np.zeros((line_h * SS, W), np.float32)
    for x0, shape in parts:
        X = int(round(x0 * SS)); w_ = shape.shape[1]
        canvas[:, X:X + w_] = np.maximum(canvas[:, X:X + w_], shape[:, :W - X].astype(np.float32))
    out_lines.append(canvas)
Wm = max(c.shape[1] for c in out_lines)
img = np.vstack([np.pad(c, ((0, 0), (0, Wm - c.shape[1]))) for c in out_lines])
im = Image.fromarray((255 - np.clip(img, 0, 1) * 255).round().astype(np.uint8)); im.save(a.out + "_blend.png")
h, w = img.shape[0] // SS * SS, img.shape[1] // SS * SS
im.crop((0, 0, w, h)).resize((w // SS, h // SS), Image.BOX).save(a.out + "_blend_1x.png")
print(f"{sum(len(l) for l in lines)} glyphs; sizes {[s['label'] + ' x' + str(s['w']) for s in sizes]}; {img.shape[1]}x{img.shape[0]} -> {w // SS}x{h // SS}")
