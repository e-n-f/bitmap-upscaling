"""Generate (1-bit glyph image, 4x signed-distance target) training pairs from outline fonts.

Each sample: render 1-3 characters of a random font at 8x supersampling on a 32x32 (1x) canvas,
optionally embolden (uniformly and/or horizontally only, to mimic thick-stem bitmap fonts),
then derive
  x: 1-bit image at 1x = (area coverage of each pixel >= random threshold)
  y: signed distance (in 1x pixel units, + = ink) sampled at 4x resolution, clipped to +-1.5
"""
import glob, os, random, subprocess, sys
import numpy as np
from multiprocessing import Pool
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

SS = 8          # supersampling factor
N = 32          # 1x canvas
CLIP = 1.5

CHARS = ("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
         "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~£¥§©®°±µ¶¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÑÒÓÔÕÖØÙÚÛÜßàáâãäåæçèéêëìíîïñòóôõöøùúûüÿ"
         "ŠšŽžŒœ€†‡•…‰‹›“”‘’–—™"
         "ΑΒΓΔΕΘΛΞΠΣΦΨΩαβγδεζηθλμξπρσφχψω"
         "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдежзийклмнопрстуфхцчшщъыьэюя"
         "∀∂∃∈∉∧∨∩∪≡≠≤≥∞∑√∫←↑→↓↔")


def font_list(revivals_dir):
    out = subprocess.run(["fc-list", ":", "file"], capture_output=True, text=True).stdout
    sys_fonts = sorted({l.split(":")[0].strip() for l in out.splitlines()
                        if l.split(":")[0].strip().lower().endswith((".ttf", ".otf"))})
    rev = sorted(glob.glob(os.path.join(revivals_dir, "**/fonts/ttf/*.ttf"), recursive=True))
    bad = ("emoji", "symbol", "dingbat", "music", "kufi", "naskh")
    sys_fonts = [f for f in sys_fonts if not any(b in f.lower() for b in bad) and "type-revivals" not in f]
    return sys_fonts, rev


_cache = {}


def prep_font(path):
    """Return (path, chars available, size factor so that cap height = 1 hi-res px per unit) or None."""
    if path in _cache:
        return _cache[path]
    res = None
    try:
        from fontTools.ttLib import TTFont
        cmap = TTFont(path, fontNumber=0, lazy=True).getBestCmap() or {}
        chars = [c for c in CHARS if ord(c) in cmap]
        if "H" in chars and "o" in chars and len(chars) > 40:
            f = ImageFont.truetype(path, 200)
            b = f.getbbox("H", anchor="ls")
            hh = -b[1]
            if hh > 20:
                res = (path, "".join(chars), 200.0 / hh)
    except Exception:
        res = None
    _cache[path] = res
    return res


def make_sample(rng, fonts_sys, fonts_rev, p_rev):
    while True:
        path = rng.choice(fonts_rev) if rng.random() < p_rev else rng.choice(fonts_sys)
        info = prep_font(path)
        if info:
            break
    _, chars, k = info
    # cap height in 1x pixels: mixture covering Mac (~7-10) and Sun console (~14) sizes
    cap = rng.choice([rng.uniform(6, 11), rng.uniform(11, 18)])
    size = max(8, int(round(cap * SS * k)))
    f = ImageFont.truetype(path, size)
    s = "".join(rng.choice(chars) for _ in range(rng.choice([1, 2, 2, 3])))
    W = N * SS
    img = Image.new("L", (W, W), 0)
    d = ImageDraw.Draw(img)
    bx = f.getbbox(s, anchor="ls")
    # centre roughly, with random sub-pixel jitter
    ox = (W - (bx[2] - bx[0])) / 2 - bx[0] + rng.uniform(-3, 3) * SS
    oy = W * 0.5 + cap * SS * 0.5 + rng.uniform(-3, 3) * SS
    d.text((ox, oy), s, font=f, fill=255, anchor="ls")
    m = np.array(img) >= 128
    # weight augmentation via signed distance offsets
    sdf = (ndimage.distance_transform_edt(m) - ndimage.distance_transform_edt(~m)) / SS
    r = rng.random()
    if r < 0.35:   # horizontal-only thickening (thick stems, thin horizontals)
        kx = int(rng.uniform(1, 7))
        m = ndimage.binary_dilation(m, structure=np.ones((1, 2 * kx + 1), bool))
        sdf = (ndimage.distance_transform_edt(m) - ndimage.distance_transform_edt(~m)) / SS
    elif r < 0.7:
        off = rng.uniform(-0.15, 0.5)
        sdf = sdf + off
        m = sdf > 0
    cov = m.reshape(N, SS, N, SS).mean(axis=(1, 3))
    x = (cov >= rng.uniform(0.3, 0.6)).astype(np.uint8)
    y = sdf.reshape(4 * N, 2, 4 * N, 2).mean(axis=(1, 3))
    y = np.clip(y, -CLIP, CLIP)
    return x, np.round(y * 80).astype(np.int8)


def worker(args):
    seed, n, fonts_sys, fonts_rev, p_rev = args
    rng = random.Random(seed)
    xs, ys = [], []
    while len(xs) < n:
        try:
            x, y = make_sample(rng, fonts_sys, fonts_rev, p_rev)
        except Exception:
            continue
        if x.sum() < 3:
            continue
        xs.append(x); ys.append(y)
    return np.stack(xs), np.stack(ys)


if __name__ == "__main__":
    revdir, outpath, total = sys.argv[1], sys.argv[2], int(sys.argv[3])
    fs, fr = font_list(revdir)
    with Pool(4) as p:
        good_sys = [f for f, ok in zip(fs, p.map(prep_font, fs)) if ok]
        good_rev = [f for f, ok in zip(fr, p.map(prep_font, fr)) if ok]
    print(f"fonts: {len(good_sys)} system, {len(good_rev)} type-revivals", flush=True)
    chunk = 500
    base = 10**6 if "val" in os.path.basename(outpath) else 0   # disjoint seeds for validation
    jobs = [(base + i, chunk,good_sys, good_rev, 0.35) for i in range(total // chunk)]
    with Pool(4) as p:
        parts = p.map(worker, jobs)
    X = np.concatenate([a for a, _ in parts]); Y = np.concatenate([b for _, b in parts])
    np.savez(outpath, x=X, y=Y, fonts_sys=np.array(good_sys), fonts_rev=np.array(good_rev))
    print("saved", X.shape, Y.shape)
