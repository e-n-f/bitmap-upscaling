"""How exactly does the model recover a hinted font's true outline?

recovery.py WEIGHTS OUT_PREFIX FONT.ttf...
For each font and ppem: x = hinted bilevel rendering (what the screen showed), truth = unhinted outline at 4x,
placed glyph-by-glyph at the hinted origins. Compares model 4x, xBRZ 4x and nearest 4x against the truth.
"""
import os
os.environ["FREETYPE_PROPERTIES"] = "truetype:interpreter-version=35"
import subprocess, sys
import numpy as np, torch, torch.nn.functional as F, freetype
from PIL import Image, ImageDraw
from scipy import ndimage
from model import GlyphSDF
from gen_hinted import bits_of, paste

torch.set_num_threads(int(os.environ.get("THREADS", "1")))
sd = torch.load(sys.argv[1]); net = GlyphSDF(sd["e1.0.weight"].shape[0]); net.load_state_dict(sd); net.eval()
prefix = sys.argv[2]; fonts = sys.argv[3:]
TEXT = "Hamburgefonstiv Quick"
SS = 8
HERE = os.path.dirname(os.path.abspath(__file__))


def render(path, ppem):
    lo = freetype.Face(path); lo.set_pixel_sizes(0, ppem)
    hi = freetype.Face(path); hi.set_char_size(ppem * SS * 64, 0, 72, 72)
    H = int(ppem * 1.6) + 4; W = int(ppem * 0.75 * len(TEXT)) + 8
    x = np.zeros((H, W), bool); m = np.zeros((H * SS, W * SS), bool)
    pen, base = 3, int(ppem * 1.2) + 2
    for ch in TEXT:
        lo.load_char(ch, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_MONO); g = lo.glyph
        paste(x, bits_of(g.bitmap, True), base - g.bitmap_top, pen + g.bitmap_left)
        hi.load_char(ch, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_NO_HINTING); h = hi.glyph
        paste(m, bits_of(h.bitmap, False), base * SS - h.bitmap_top, pen * SS + h.bitmap_left)
        pen += (g.advance.x + 32) >> 6
    x = x[:, :pen + 3]; m = m[:, :(pen + 3) * SS]
    truth = m.reshape(m.shape[0] // 2, 2, m.shape[1] // 2, 2).mean(axis=(1, 3)) >= 0.5   # 4x
    return x, truth


def model4x(x):
    with torch.no_grad():
        s = net(torch.from_numpy(x.astype(np.float32))[None, None])
        r = 3; t = torch.arange(-r, r + 1, dtype=torch.float32); g = torch.exp(-t * t / 2); g /= g.sum()
        s = F.conv2d(F.conv2d(F.pad(s, (r, r, r, r), mode="replicate"), g.view(1, 1, 1, -1)), g.view(1, 1, -1, 1))
    return s[0, 0].numpy() > 0


def xbrz4x(x):
    h, w = x.shape; a, b = prefix + ".in", prefix + ".out"
    np.where(x, 0, 0xFFFFFF).astype("<u4").tofile(a)
    subprocess.run([os.environ.get("XBRZ", os.path.join(HERE, "..", "xbrz", "xbrz_raw")), "4", str(w), str(h), a, b], check=True)
    o = (np.fromfile(b, "<u4").reshape(h * 4, w * 4) & 0xFF) < 128; os.remove(a); os.remove(b)
    return o


def err(pred, truth):
    """Mismatched 4x pixels as % of true ink area, and mean distance (in 1x px) of predicted edge from true edge."""
    xor = (pred != truth).sum() / truth.sum() * 100
    dt = ndimage.distance_transform_edt(~(truth ^ ndimage.binary_erosion(truth)))        # distance to true edge
    pe = pred ^ ndimage.binary_erosion(pred)
    return xor, dt[pe].mean() / 4


def overlay(pred, truth):
    """white bg; black = both; red = true outline missed; blue = model ink outside the outline"""
    o = np.full(truth.shape + (3,), 255, np.uint8)
    o[truth & pred] = (0, 0, 0); o[truth & ~pred] = (230, 40, 40); o[~truth & pred] = (40, 90, 230)
    return o


rows = []
print(f"{'font':28s} ppem   {'mismatch % of ink (dist px)':>40s}")
print(f"{'':28s}       {'nearest':>12s} {'xBRZ':>12s} {'model':>12s}")
for f in fonts:
    for ppem in (9, 11, 13, 16):
        x, truth = render(f, ppem)
        res = {k: fn(x) for k, fn in (("nearest", lambda z: np.kron(z, np.ones((4, 4), bool))), ("xBRZ", xbrz4x), ("model", model4x))}
        e = {k: err(v, truth) for k, v in res.items()}
        name = os.path.basename(f)[:-4]
        print(f"{name:28s} {ppem:4d}   " + " ".join(f"{e[k][0]:6.1f} ({e[k][1]:.2f})" for k in ("nearest", "xBRZ", "model")), flush=True)
        rows.append((f"{name} {ppem}px", x, truth, res))

# sheet: for each row: hinted input (nearest 4x) | truth | model | overlay(model vs truth)
blocks = []
for lab, x, truth, res in rows:
    w = truth.shape[1]
    def gray(b): return np.stack([np.where(b, 0, 255).astype(np.uint8)] * 3, -1)
    parts = [("hinted input (screen bitmap)", gray(res["nearest"])), ("true outline", gray(truth)),
             ("model", gray(res["model"])), ("model vs outline (red = missed, blue = extra)", overlay(res["model"], truth)),
             ("xBRZ vs outline", overlay(res["xBRZ"], truth))]
    for t, im in parts:
        hdr = Image.new("RGB", (w, 16), (225, 225, 225)); ImageDraw.Draw(hdr).text((4, 2), f"{lab}: {t}", fill=0)
        blocks += [np.array(hdr), im, np.full((3, w, 3), 255, np.uint8)]
    blocks.append(np.full((14, w, 3), 255, np.uint8))
Wm = max(b.shape[1] for b in blocks)
blocks = [np.pad(b, ((0, 0), (0, Wm - b.shape[1]), (0, 0)), constant_values=255) for b in blocks]
Image.fromarray(np.vstack(blocks)).save(prefix + ".png")
