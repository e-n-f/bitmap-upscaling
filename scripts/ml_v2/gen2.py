"""v2: family-balanced sampling (system + Google Fonts + type-revivals), sizes down to 4px cap height,
non-text patterns (dithers, rules) that should upscale as plain blocks, and inverted samples.

Generate (1-bit glyph image, 4x signed-distance target) training pairs from outline fonts.

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


def family_pool(revivals_dir, gf_dir):
    """Return {family_name: [font files]}; sampling is uniform over families."""
    out = subprocess.run(["fc-list", "-f", "%{file}|%{family[0]}\n"], capture_output=True, text=True).stdout
    fams = {}
    for l in out.splitlines():
        p, _, fam = l.partition("|")
        if not p.lower().endswith((".ttf", ".otf")) or "type-revivals" in p:
            continue
        if is_symbol_font(p):
            fams.setdefault("sym:" + fam, []).append(p)
            continue
        if any(b in p.lower() for b in ("emoji", "kufi", "naskh")):
            continue
        fams.setdefault("sys:" + fam, []).append(p)
    for p in glob.glob(os.path.join(revivals_dir, "**/fonts/ttf/*.ttf"), recursive=True):
        fams["rev:" + os.path.basename(p)] = [p]
    cats = dict(l.split() for l in open(os.environ.get("GF_CATEGORIES", os.path.join(gf_dir, "..", "gf_cat.txt"))) if l.strip())
    for p in glob.glob(os.path.join(gf_dir, "*/*/*.ttf")):
        d = os.path.relpath(os.path.dirname(p), gf_dir)
        if "emoji" in d:
            continue
        key = ("sym:" if is_symbol_font(p) else "gf-" + cats.get(d, "?").lower() + ":") + d
        fams.setdefault(key, []).append(p)
    return fams


def family_weight(name):
    if name.startswith("sym:"):
        return None                       # sampled from a separate 5% pool
    if name.startswith(("gf-display:", "gf-handwriting:")):
        return 0.3
    return 1.0


def font_list(revivals_dir):
    out = subprocess.run(["fc-list", ":", "file"], capture_output=True, text=True).stdout
    sys_fonts = sorted({l.split(":")[0].strip() for l in out.splitlines()
                        if l.split(":")[0].strip().lower().endswith((".ttf", ".otf"))})
    rev = sorted(glob.glob(os.path.join(revivals_dir, "**/fonts/ttf/*.ttf"), recursive=True))
    bad = ("emoji", "symbol", "dingbat", "music", "kufi", "naskh")
    sys_fonts = [f for f in sys_fonts if not any(b in f.lower() for b in bad) and "type-revivals" not in f]
    return sys_fonts, rev


_cache = {}


SYMBOL_HINTS = ("d050000l", "standardsymbolsps", "notosanssymbols", "notomusic", "notosansmath",
                "stixtwomath", "libertinusmath", "jsmathcmsy10", "jsmathcmex10")


def is_symbol_font(path):
    return any(h in path.lower().replace("-", "").replace("_", "") for h in SYMBOL_HINTS)


def prep_symbol_font(path):
    from fontTools.ttLib import TTFont
    cmap = TTFont(path, fontNumber=0, lazy=True).getBestCmap() or {}
    cps = [c for c in cmap if c > 0x20 and not (0x7F <= c < 0xA0) and not (0xE000 <= c < 0xF900)]
    if len(cps) < 20:
        return None
    rs = random.Random(0)
    f = ImageFont.truetype(path, 200)
    hs = sorted(-f.getbbox(chr(c), anchor="ls")[1] for c in rs.sample(cps, min(40, len(cps))))
    hh = hs[len(hs) // 2]
    if hh <= 20:
        return None
    return (path, "".join(chr(c) for c in cps), 200.0 / hh, None)


def prep_font(path):
    """Return (path, chars available, size factor so that cap height = 1 hi-res px per unit) or None."""
    if path in _cache:
        return _cache[path]
    res = None
    if is_symbol_font(path):
        try:
            res = prep_symbol_font(path)
        except Exception:
            res = None
        _cache[path] = res
        return res
    try:
        from fontTools.ttLib import TTFont
        cmap = TTFont(path, fontNumber=0, lazy=True).getBestCmap() or {}
        chars = [c for c in CHARS if ord(c) in cmap]
        if "H" in chars and "o" in chars and len(chars) > 40:
            f = ImageFont.truetype(path, 200)
            b = f.getbbox("H", anchor="ls")
            hh = -b[1]
            if hh > 20:
                res = (path, "".join(chars), 200.0 / hh, frozenset(chr(c) for c in cmap))
    except Exception:
        res = None
    _cache[path] = res
    return res


MAC_PATTERNS = [  # 8x8 1-bit fill patterns in the spirit of classic Mac desktop/fill patterns
    [0xAA, 0x55] * 4, [0x88, 0x22] * 4, [0x77, 0xDD] * 4, [0x88, 0x00, 0x22, 0x00] * 2,
    [0xFF, 0x00] * 4, [0xAA] * 8, [0x11, 0x22, 0x44, 0x88] * 2, [0x88, 0x44, 0x22, 0x11] * 2,
    [0x80, 0x00, 0x08, 0x00] * 2, [0xEE, 0xBB] * 4, [0xF0, 0xF0, 0xF0, 0xF0, 0x0F, 0x0F, 0x0F, 0x0F],
]
BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16 + 1 / 32


def nontext(rng):
    """A 1x pattern element that should be upscaled as plain pixel blocks."""
    z = np.zeros((N, N), bool)
    x0, y0 = rng.randrange(0, N - 4), rng.randrange(0, N - 4)
    x1, y1 = rng.randrange(x0 + 3, N + 1), rng.randrange(y0 + 3, N + 1)
    k = rng.random()
    yy, xx = np.mgrid[0:N, 0:N]
    if k < 0.45:
        pat = rng.choice(MAC_PATTERNS)
        if rng.random() < 0.3:
            pat = [(~b) & 0xFF for b in pat]
        P = np.array([[(row >> (7 - i)) & 1 for i in range(8)] for row in pat], bool)
        full = P[(yy + rng.randrange(8)) % 8, (xx + rng.randrange(8)) % 8]
    elif k < 0.65:   # ordered dither of a gradient
        g = rng.uniform(0, 1) + rng.uniform(-0.05, 0.05) * (xx * rng.uniform(-1, 1) + yy * rng.uniform(-1, 1))
        full = g > BAYER4[yy % 4, xx % 4]
    elif k < 0.75:   # random noise
        full = np.array([[rng.random() < 0.3 for _ in range(N)] for _ in range(N)])
    else:            # 1px rules / box outlines
        full = np.zeros((N, N), bool)
        if rng.random() < 0.5:
            full[y0, :] = True if rng.random() < 0.5 else False
            full[:, x0] = True if rng.random() < 0.5 else full[:, x0]
        full[y0, x0:x1] = full[y1 - 1, x0:x1] = full[y0:y1, x0] = full[y0:y1, x1 - 1] = True
        return full
    z[y0:y1, x0:x1] = full[y0:y1, x0:x1]
    return z


LANG_WEIGHTS = {"en": 0.55, "ru": 0.04, "uk": 0.02, "bg": 0.02, "sr": 0.02, "el": 0.05}
_LATIN = ["fr", "de", "es", "it", "pt", "nl", "sv", "da", "no", "fi", "is", "hu", "pl", "cs", "ro", "hr", "tr", "vi"]
LANG_WEIGHTS.update({l: 0.27 / len(_LATIN) for l in _LATIN})
_corpus = None


def corpus():
    global _corpus
    if _corpus is None:
        import json
        c = json.load(open(os.environ.get("CORPUS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "corpus.json"))))
        c["en"] = c["en"][:2_000_000]
        _corpus = c
    return _corpus


def pick_string(rng, chars, cmapset):
    """1-3 consecutive characters of real text in a language the font covers (75%), else random characters."""
    n = rng.choice([1, 2, 2, 3, 3])
    if cmapset is not None and rng.random() < 0.75:
        c = corpus()
        langs = list(LANG_WEIGHTS)
        for _ in range(30):
            l = rng.choices(langs, weights=[LANG_WEIGHTS[x] for x in langs])[0]
            t = c[l]
            i = rng.randrange(len(t) - n)
            s = t[i:i + n]
            if s.strip() and all(ch == " " or ch in cmapset for ch in s):
                return s
    return "".join(rng.choice(chars) for _ in range(n))


def make_sample(rng, fams):
    text, wts, sym = fams
    while True:
        if rng.random() < 0.05:
            path = rng.choice(rng.choice(sym))
        else:
            path = rng.choice(rng.choices(text, weights=wts)[0])
        info = prep_font(path)
        if info:
            break
    _, chars, k, cmapset = info
    # cap height in 1x pixels: mixture covering Mac (~7-10) and Sun console (~14) sizes
    r0 = rng.random()
    cap = rng.uniform(4, 9) if r0 < 0.4 else rng.uniform(9, 14) if r0 < 0.75 else rng.uniform(14, 22)
    size = max(8, int(round(cap * SS * k)))
    f = ImageFont.truetype(path, size)
    s = pick_string(rng, chars, cmapset)
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
    t = rng.uniform(0.3, 0.6)
    # reject samples whose 1-bit rendering has lost most of the glyph (nothing to learn from)
    if (m.reshape(N, SS, N, SS).mean(axis=(1, 3)) >= t).sum() < 0.5 * m.sum() / (SS * SS):
        raise ValueError("glyph lost at this size")
    if rng.random() < 0.1:   # non-text patterns (dithers, rules, boxes)
        m = m | ndimage.zoom(nontext(rng), SS, order=0).astype(bool)
        sdf = (ndimage.distance_transform_edt(m) - ndimage.distance_transform_edt(~m)) / SS
    if rng.random() < 0.1:
        m = ~m; sdf = -sdf
    cov = m.reshape(N, SS, N, SS).mean(axis=(1, 3))
    x = (cov >= t).astype(np.uint8)
    y = sdf.reshape(4 * N, 2, 4 * N, 2).mean(axis=(1, 3))
    y = np.clip(y, -CLIP, CLIP)
    return x, np.round(y * 80).astype(np.int8)


def worker(args):
    seed, n, fams = args
    rng = random.Random(seed)
    xs, ys = [], []
    while len(xs) < n:
        try:
            x, y = make_sample(rng, fams)
        except Exception:
            continue
        if x.sum() < 3:
            continue
        xs.append(x); ys.append(y)
    return np.stack(xs), np.stack(ys)


if __name__ == "__main__":
    revdir, gfdir, outpath, total = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
    pool = family_pool(revdir, gfdir)
    allf = sorted({f for fs in pool.values() for f in fs})
    with Pool(4) as p:
        ok = dict(zip(allf, p.map(prep_font, allf)))
    good = {n: [f for f in fs if ok[f]] for n, fs in pool.items()}
    good = {n: fs for n, fs in good.items() if fs}
    names = list(good)
    text = [good[n] for n in names if family_weight(n)]
    wts = [family_weight(n) for n in names if family_weight(n)]
    sym = [good[n] for n in names if not family_weight(n)]
    import collections
    print(len(names), "families,", sum(map(len, good.values())), "files:",
          dict(collections.Counter(n.split(":")[0] for n in names)), flush=True)
    print("symbol families:", [n for n in names if n.startswith("sym:")], flush=True)
    fams = (text, wts, sym)
    chunk = 500
    base = 10**6 if "val" in os.path.basename(outpath) else 0   # disjoint seeds for validation
    jobs = [(base + i, chunk, fams) for i in range(total // chunk)]
    with Pool(4) as p:
        parts = p.map(worker, jobs)
    X = np.concatenate([a for a, _ in parts]); Y = np.concatenate([b for _, b in parts])
    np.savez(outpath, x=X, y=Y, families=np.array(names))
    print("saved", X.shape, Y.shape)
