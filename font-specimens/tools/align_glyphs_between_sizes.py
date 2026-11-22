"""Move each glyph of an upscaled New York 12 rebuild onto the matching glyph of an upscaled New York 24 rebuild."""
import json, sys, numpy as np
from PIL import Image
from scipy import ndimage
Image.MAX_IMAGE_PIXELS = None
img12, img24, json12, json24, out_prefix = sys.argv[1:6]
up12 = np.array(Image.open(img12).convert('L')); up24 = np.array(Image.open(img24).convert('L'))
J12 = json.load(open(json12)); J24 = json.load(open(json24))
k12 = up12.shape[1] / J12['image_size'][0]; k24 = up24.shape[1] / J24['image_size'][0]
paper = np.percentile(up12, 90)
dark = np.clip(1 - up12.astype(float) / paper, 0, 1)
g12 = {g['code']: g for g in J12['glyphs']}
lines = {}
for g in J12['glyphs']: lines.setdefault(g['line'], []).append(g)
pieces = {}
for li, gs in lines.items():
    gs.sort(key=lambda g: g['ink_avg'][0])
    T = int(min(g['cell'][1] for g in gs) * k12); B = int(max(g['cell'][3] for g in gs) * k12)
    X0 = int(min(g['cell'][0] for g in gs) * k12); X1 = int(max(g['cell'][2] for g in gs) * k12)
    ink = dark[T:B, X0:X1] > 0.35                                      # ownership only; output keeps the greys
    centres = np.array([(g['ink_avg'][0] + g['ink_avg'][2]) / 2 * k12 - X0 for g in gs])
    spans = [((g['ink_avg'][0] - 1) * k12 - X0, (g['ink_avg'][2] + 1) * k12 - X0) for g in gs]
    lab, n = ndimage.label(ink)
    owner = np.full(ink.shape, -1, int)
    nearest_centre = np.abs(np.arange(ink.shape[1])[None, :] - centres[:, None]).argmin(0)
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        m = lab[sl] == i; xs = np.nonzero(m.any(0))[0] + sl[1].start
        cover = [j for j, (a, b) in enumerate(spans) if min(b, xs.max()) - max(a, xs.min()) > 0.25 * (b - a)]
        sub = owner[sl]
        if len(cover) <= 1:
            sub[m] = int(np.abs(centres - (np.nonzero(m)[1] + sl[1].start).mean()).argmin())
        else:
            # touching letters: split at the thinnest column of the blob between each pair of neighbouring centres
            cover = sorted(cover); cuts = []
            # darkness-weighted: a faint seam where two serifs merge is the lightest column
            colsum = (dark[T:B, X0:X1][sl] * m).sum(0); x_off = sl[1].start
            for j0, j1 in zip(cover, cover[1:]):
                lo = int(max(centres[j0] - x_off, 0)); hi = int(min(centres[j1] - x_off, m.shape[1]))
                if hi - lo < 2:
                    cuts.append((lo + hi) // 2); continue
                seg = colsum[lo:hi]; idx = np.nonzero(seg <= seg.min() + 1e-6)[0]
                cuts.append(lo + int(idx[len(idx) // 2]))
            colowner = np.full(m.shape[1], cover[-1])
            prev = 0
            for j, c in zip(cover, cuts):
                colowner[prev:c] = j; prev = c
            sub[m] = np.broadcast_to(colowner[None, :], m.shape)[m]
    _, (iy, ix) = ndimage.distance_transform_edt(owner < 0, return_indices=True)
    full = owner[iy, ix]
    for j, g in enumerate(gs):
        mine = full == j; cols = np.nonzero(mine.any(0))[0]; c0, c1 = cols.min(), cols.max() + 1
        pieces[g['code']] = (np.where(mine, up12[T:B, X0:X1], 255)[:, c0:c1], X0 + c0, T)
WHITE = 0.92 * paper                    # greys at or above this become white: removes the paper tint, keeps ink
out = np.full(up24.shape, 255, np.uint8)
for b in J24['glyphs']:
    a = g12[b['code']]; piece, X0, T = pieces[b['code']]
    piece = np.clip(piece.astype(float) * 255 / WHITE, 0, 255).astype(np.uint8)
    c12 = (a['ink_avg'][0] + a['ink_avg'][2]) / 2 * k12; c24 = (b['ink_avg'][0] + b['ink_avg'][2]) / 2 * k24
    tx = int(round(X0 - c12 + c24)); ty = int(round(T - a['origin'][1] * k12 + b['origin'][1] * k24))
    h, w = piece.shape; ya, xa = max(0, -ty), max(0, -tx); yb, xb = min(h, out.shape[0] - ty), min(w, out.shape[1] - tx)
    region = out[ty + ya:ty + yb, tx + xa:tx + xb]; region[...] = np.minimum(region, piece[ya:yb, xa:xb])
Image.fromarray(out).save(out_prefix + '_aligned.png')
r = out.astype(int); bl = up24.astype(int)
Image.fromarray(np.stack([r, np.minimum(r, bl), bl], -1).astype(np.uint8)).save(out_prefix + '_overlay.png')
print('scales', k12, k24, 'paper', paper)
