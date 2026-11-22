"""Composite specimen: every size of a bitmap font mapped onto the largest size and averaged.

usage: python -I composite_sizes.py OUT_PREFIX LABEL=APPLEDOUBLE:TYPE:ID ... [--ss 6]
The last size listed is the target (normally the largest).

For each size, the reference lines are measured from the bitmaps (y up from the baseline):
  descender = bottom of "p", baseline = 0, x-height = top of "x", cap height = top of "H" (also the ascender here).
Each glyph is mapped onto the target size's glyph:
  vertically   piecewise-linearly through those reference lines, so they coincide in every size (and beyond the
               outermost lines, by the ratio of the sizes' heights);
  horizontally by stretching its ink extent onto the target glyph's ink extent, so side stems and bowl edges align.
With --blur SIGMA, each source bitmap is first blurred with a Gaussian of that sigma in its own pixels; --blur-per sets it
per size. --weights sets per-size weights for the average (default equal). Outputs also include OUT_PREFIX_composite_grey_1x.png,
the grey composite reduced to the target size's own pixels (each pixel the mean of an SS x SS block).
Each source bitmap is sampled with bilinear interpolation at --ss subpixels per target pixel; the sizes are averaged
with equal weight. Glyphs are laid out with the target size's own advance widths and offsets.
Writes OUT_PREFIX_composite_grey.png, OUT_PREFIX_composite.png (thresholded at 50%, or at 30% with --blur, since blurring
leaves hairlines and serifs too faint for 50%), OUT_PREFIX_sizes.png (selected
characters in every size after mapping, with the composite) and OUT_PREFIX_composite_glyphs.json.
"""
import argparse, json, os, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from macspecimens import collect, QDFont

ap = argparse.ArgumentParser()
ap.add_argument("out"); ap.add_argument("sizes", nargs="+"); ap.add_argument("--ss", type=int, default=6)
ap.add_argument("--show", default="aegkmsyRQ&@3")
ap.add_argument("--mode", choices=("mean", "sdf"), default="mean",
                help="mean: average the sizes' coverage (grey). sdf: threshold each size's coverage at 50%%, average the "
                     "signed distance fields (weighted), and fill where the average is inside: one crisp blended outline")
ap.add_argument("--sdf-threshold", type=float, default=0.5, help="coverage level that counts as inside, in --mode sdf")
ap.add_argument("--blur-per", default="", help="per-size blur overriding --blur, e.g. 12=1,24=2 (sigma in that size's pixels)")
ap.add_argument("--weights", default="", help="per-size weights for the average, e.g. 12=2,24=1 (default: equal)")
ap.add_argument("--blur", type=float, default=0.0, help="Gaussian blur (sigma, in each size's own source pixels) applied to "
                                                         "every source bitmap before it is mapped and averaged")
a = ap.parse_args()
BLUR = {k: float(v) for k, v in (x.split("=") for x in a.blur_per.split(",") if x)}
WEIGHT = {k: float(v) for k, v in (x.split("=") for x in a.weights.split(",") if x)}

fonts = []
for spec in a.sizes:
    label, rest = spec.split("=", 1)
    path, t, i = rest.rsplit(":", 2)
    f = next(QDFont(c[6]) for c in collect(path) if c[1] == t and c[2] == int(i))
    fonts.append((label, f))


def ink_edges(f, code):
    g = f.glyph(code)
    if g is None or not g[0].any():
        return None
    r = np.nonzero(g[0].any(1))[0]; c = np.nonzero(g[0].any(0))[0]
    return dict(top=f.ascent - r[0], bottom=f.ascent - r[-1] - 1, left=g[1] + c[0], right=g[1] + c[-1] + 1)


def refs(f):
    return [ink_edges(f, ord("p"))["bottom"], 0, ink_edges(f, ord("x"))["top"], ink_edges(f, ord("H"))["top"]]


tlabel, T = fonts[-1]
tref = refs(T)


def vmap_inverse(sref, f):
    """target y (y up, target px) -> source y, piecewise linear through the reference lines, linear beyond them"""
    k_lo = (sref[1] - sref[0]) / (tref[1] - tref[0]); k_hi = (sref[3] - sref[2]) / (tref[3] - tref[2])

    def inv(ty):
        sy = np.interp(ty, tref, sref)
        sy = np.where(ty < tref[0], sref[0] + (ty - tref[0]) * k_lo, sy)
        return np.where(ty > tref[3], sref[3] + (ty - tref[3]) * k_hi, sy)
    return inv


def sample(f, code, tx, ty, inv, tbox, sbox, blur):
    """coverage of the source glyph at target points (tx right from target pen, ty up from baseline)"""
    bits, xo, adv = f.glyph(code)
    sx = sbox["left"] + (tx - tbox["left"]) * (sbox["right"] - sbox["left"]) / (tbox["right"] - tbox["left"])
    sy = inv(ty)
    # source pixel (r, c) covers x in [xo + c, xo + c + 1), y in [asc - r - 1, asc - r); its centre is the sample point
    cf = sx - xo - 0.5; rf = (f.ascent - sy) - 0.5
    P = 1 + int(np.ceil(3 * blur))
    img = np.pad(bits.astype(np.float32), P)
    if blur > 0:
        from scipy.ndimage import gaussian_filter
        img = gaussian_filter(img, blur, mode="constant")
    c0 = np.floor(cf).astype(int); r0 = np.floor(rf).astype(int); dc = cf - c0; dr = rf - r0
    def at(r, c):
        r = np.clip(r + P, 0, img.shape[0] - 1); c = np.clip(c + P, 0, img.shape[1] - 1)
        return img[r, c]
    return (at(r0, c0) * (1 - dr) * (1 - dc) + at(r0, c0 + 1) * (1 - dr) * dc +
            at(r0 + 1, c0) * dr * (1 - dc) + at(r0 + 1, c0 + 1) * dr * dc)


SS = a.ss
codes_t = [c for c in T.codes() if c != 32 and (g := T.glyph(c)) is not None and g[0].any() and (c >= 32 or c < 32)]
SHORT = ["ABCDEFGHIJKLM", "NOPQRSTUVWXYZ", "abcdefghijklm", "nopqrstuvwxyz", "0123456789",
         "!\"#$%&'()*+,-", "./:;<=>?@[\\]^", "_`{|}~"]
lines = [[ord(ch) for ch in l if ord(ch) in codes_t] for l in SHORT]
used = {c for l in lines for c in l}
extra = [c for c in codes_t if c not in used and (c < 32 or c >= 127)]
lines += [extra[i:i + 13] for i in range(0, len(extra), 13)]

srefs = {label: refs(f) for label, f in fonts}
invs = {label: vmap_inverse(srefs[label], f) for label, f in fonts}
y_top = T.ascent + 2; y_bot = -(T.height - T.ascent) - 2          # rows rendered per line, target px
line_h = y_top - y_bot


def composite_glyph(code, members=None):
    """-> (grey image at SS, number of sizes used, per-size images) for one character, in its target cell"""
    tb = ink_edges(T, code)
    bits, xo, adv = T.glyph(code)
    x_lo, x_hi = min(0, xo) - 2, max(adv, xo + bits.shape[1]) + 2
    xs = x_lo + (np.arange((x_hi - x_lo) * SS) + 0.5) / SS
    ys = y_top - (np.arange(line_h * SS) + 0.5) / SS
    TX, TY = np.meshgrid(xs, ys)
    per = []
    for label, f in fonts:
        if members and label not in members:
            continue
        sb = ink_edges(f, code)
        if sb is None:
            continue
        per.append((label, sample(f, code, TX, TY, invs[label], tb, sb, BLUR.get(label, a.blur))))
    w = np.array([WEIGHT.get(label, 1.0) for label, _ in per])
    if a.mode == "sdf":
        from scipy.ndimage import distance_transform_edt as edt
        sd = [edt(p >= a.sdf_threshold) - edt(p < a.sdf_threshold) for _, p in per]          # + inside, - outside, in supersampled px
        acc = (np.tensordot(w / w.sum(), np.array(sd), axes=1) > 0).astype(np.float32)
    else:
        acc = np.tensordot(w / w.sum(), np.array([p for _, p in per]), axes=1)
    return acc, len(per), per, x_lo


# lay out the target size's lines with its own advances
out_lines, glyph_info = [], []
for li, l in enumerate(lines):
    pen = 4; parts = []
    for code in l:
        acc, n, per, x_lo = composite_glyph(code)
        bw = None
        parts.append((pen + x_lo, acc, bw)); _, xo, adv = T.glyph(code)
        tb = ink_edges(T, code)
        glyph_info.append(dict(char=(f"<{code:02X}>" if code < 32 else bytes([code]).decode("mac_roman")), code=code,
                               line=li, sizes_averaged=n, pen_x_px=pen * SS, advance_px=adv * SS))
        pen += adv
    W = (pen + 8) * SS; canvas = np.zeros((line_h * SS, W), np.float32)
    for x0, acc, bw in parts:
        X = int(round(x0 * SS)); w = acc.shape[1]
        canvas[:, X:X + w] = np.maximum(canvas[:, X:X + w], acc[:, :W - X])
    out_lines.append((canvas, None))
Wmax = max(c.shape[1] for c, _ in out_lines)
grey = np.vstack([np.pad(c, ((0, 0), (0, Wmax - c.shape[1]))) for c, _ in out_lines])
img = (255 - np.clip(grey, 0, 1) * 255).round().astype(np.uint8)
Image.fromarray(img).save(a.out + "_composite_grey.png")
_h, _w = img.shape[0] // SS * SS, img.shape[1] // SS * SS
Image.fromarray(img[:_h, :_w]).resize((_w // SS, _h // SS), Image.BOX).save(a.out + "_composite_grey_1x.png")
THRESH = 0.5 if (a.blur == 0 and not any(BLUR.values())) or a.mode == "sdf" else 0.3     # blurred composites have faint hairlines; 50% would drop them
Image.fromarray(np.where(grey >= THRESH, 0, 255).astype(np.uint8)).save(a.out + "_composite.png")
json.dump(dict(target=tlabel, sizes=[l for l, _ in fonts], supersampling=SS, blur_sigma_source_px=a.blur, blur_per_size=BLUR, weights=WEIGHT, mode=a.mode, sdf_threshold=a.sdf_threshold, line_height_px=line_h * SS,
               baseline_from_line_top_px=y_top * SS,
               reference_lines={l: dict(zip(("descender", "baseline", "x_height", "cap_height"), map(int, r))) for l, r in srefs.items()},
               glyphs=glyph_info), open(a.out + "_composite_glyphs.json", "w"), indent=1, ensure_ascii=False)

# per-size comparison for selected characters
rows = []
for ch in a.show:
    code = ord(ch.encode("mac_roman").decode("latin-1")) if False else ch.encode("mac_roman")[0]
    acc, n, per, _ = composite_glyph(code)
    cells = [(lab, p) for lab, p in per] + [("average", acc)]
    H = cells[0][1].shape[0]
    row = Image.new("L", (sum(c.shape[1] + 12 for _, c in cells) + 12, H + 16), 255); d = ImageDraw.Draw(row); x = 6
    for lab, c in cells:
        row.paste(Image.fromarray((255 - np.clip(c, 0, 1) * 255).astype(np.uint8)), (x, 0))
        d.text((x, H + 2), lab, fill=0 if lab == "average" else 110); x += c.shape[1] + 12
    rows.append(row)
W = max(r.width for r in rows); S = Image.new("L", (W, sum(r.height + 6 for r in rows)), 255); y = 0
for r in rows:
    S.paste(r, (0, y)); y += r.height + 6
S.save(a.out + "_sizes.png")
print(f"{len(glyph_info)} glyphs; sizes {[l for l, _ in fonts]}; image {Wmax}x{grey.shape[0]}")
