"""Pixel-exact specimens of classic Mac FONT/NFNT bitmap fonts from resource forks (AppleDouble ._ files).

usage: python -I macspecimens.py OUT_DIR APPLEDOUBLE_FILE...
FONT resources are named by family (id >> 7, name from the size-0 FONT or FOND) and size (id & 127).
NFNT resources are named through the FOND association table (size, style). Identical bitmaps are written once.
"""
import hashlib, os, struct, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rsrc import resources, appledouble_rsrc
from specimen2 import ASCII_LINES, to_image

# Apple's standard font family numbers, used when a suitcase has no FOND or size-0 FONT naming the family.
APPLE_FAMILIES = {0: "Chicago", 2: "New York", 3: "Geneva", 4: "Monaco", 5: "Venice", 6: "London", 7: "Athens",
                  8: "San Francisco", 9: "Toronto", 11: "Cairo", 12: "Los Angeles", 16: "Palatino", 20: "Times",
                  21: "Helvetica", 22: "Courier", 23: "Symbol", 24: "Mobile"}
STYLE = {0: "", 1: "Bold", 2: "Italic", 3: "BoldItalic", 4: "Underline", 8: "Outline", 16: "Shadow"}


def parse_qd(data):
    """QuickDraw font record (FONT/NFNT) -> dict with glyphs {code: (bits, x_offset, advance)}."""
    if len(data) < 26:
        return None
    fontType, first, last, widMax, kernMax, nDescent, fRectW, fRectH, owTLoc, ascent, descent, leading, rowWords = \
        struct.unpack(">H12h", data[:26])
    owTLoc &= 0xFFFF
    if nDescent > 0:                                   # high word of owTLoc for big fonts
        owTLoc |= nDescent << 16
    if not (0 <= first <= last <= 255) or fRectH <= 0 or rowWords <= 0:
        return None
    n = last - first + 3; rb = rowWords * 2; img_end = 26 + rb * fRectH
    if len(data) < img_end + 2 * n:
        return None
    bits = np.unpackbits(np.frombuffer(data[26:img_end], np.uint8)).reshape(fRectH, rb * 8).astype(bool)
    loc = struct.unpack(f">{n}H", data[img_end:img_end + 2 * n])
    if any(b < a for a, b in zip(loc, loc[1:])) or loc[-1] > rb * 8:
        return "damaged"                               # location table not monotonic / outside the strike
    owt = 16 + 2 * owTLoc
    if owt + 2 * (n - 1) > len(data):                  # nDescent was a real (negative-sense) value, not a high word
        owt = 16 + 2 * (owTLoc & 0xFFFF)
    # Many fonts omit the owTable's final end-marker word (QuickDraw never reads it): accept n-1 entries.
    k = min(n, (len(data) - owt) // 2)
    if k < n - 1:
        return None
    ow = struct.unpack(f">{k}h", data[owt:owt + 2 * k]) + (-1,) * (n - k)
    glyphs = {}
    for i in range(last - first + 1):
        if ow[i] == -1:
            continue
        glyphs[first + i] = (bits[:, loc[i]:loc[i + 1]], kernMax + ((ow[i] >> 8) & 0xFF), ow[i] & 0xFF)
    missing = (bits[:, loc[n - 2]:loc[n - 1]], kernMax + ((ow[n - 2] >> 8) & 0xFF), ow[n - 2] & 0xFF) if ow[n - 2] != -1 else None
    return dict(height=fRectH, ascent=ascent, descent=descent, glyphs=glyphs, missing=missing, first=first, last=last)


class QDFont:
    def __init__(self, f):
        self.f = f; self.height = f["height"]; self.ascent = f["ascent"]

    def codes(self):
        return sorted(self.f["glyphs"])

    def glyph(self, code):
        return self.f["glyphs"].get(code)


def fond_assoc(data):
    """FOND -> list of (size, style, resource id)."""
    if len(data) < 54:
        return []
    k = struct.unpack(">H", data[52:54])[0] + 1
    return [struct.unpack(">hhh", data[54 + 6 * i:60 + 6 * i]) for i in range(k) if 60 + 6 * i <= len(data)]


def collect(path):
    fork = appledouble_rsrc(open(path, "rb").read())
    if not fork:
        return []
    rs = resources(fork)
    src = os.path.basename(path)[2:]
    fonds = {i: (n, d) for t, i, n, d in rs if t == "FOND"}
    fam_names = dict(APPLE_FAMILIES)
    fam_names.update({i >> 7: n for t, i, n, d in rs if t == "FONT" and (i & 127) == 0 and n})
    fam_names.update({i: n for i, (n, d) in fonds.items() if n})
    out = []
    for t, i, n, d in rs:
        if t == "FONT" and (i & 127):
            fam, size, style = fam_names.get(i >> 7, f"family{i >> 7}"), i & 127, 0
        elif t == "NFNT":
            fam, size, style = None, None, 0
            for fid, (fn, fd) in fonds.items():
                for sz, st, rid in fond_assoc(fd):
                    if rid == i:
                        fam, size, style = fn, sz, st
            if fam is None:
                fam, size = f"NFNT{i}", 0
        else:
            continue
        f = parse_qd(d)
        if f == "damaged":
            print(f"DAMAGED  {fam} {size}  [{src}: {t} {i}]  (glyph location table is corrupt; skipped)")
            continue
        if f and f["glyphs"]:
            out.append((src, t, i, fam, size, style, f, hashlib.sha1(d).hexdigest()))
    return out


if __name__ == "__main__":
    outdir = sys.argv[1]; os.makedirs(outdir, exist_ok=True)
    seen = {}; rows = []
    for p in sys.argv[2:]:
        for src, t, rid, fam, size, style, f, h in collect(p):
            # The "CairoSplices" files carry a FOND named Cairo; name them after the file instead.
            if "CairoSplices" in p:
                fam = src
            label = f"{fam} {size}{(' ' + STYLE.get(style, f'style{style}')) if style else ''}"
            if h in seen:
                rows.append((label, src, t, rid, f"duplicate of {seen[h]}")); continue
            fname = f"{fam}_{size}{('_' + STYLE.get(style, str(style))) if style else ''}".replace(" ", "")
            k = 2
            while os.path.exists(f"{outdir}/{fname}.png"):
                fname = f"{fname.split('~')[0]}~{k}"; k += 1
            seen[h] = fname
            font = QDFont(f)
            from specimen2 import specimen
            lines, n_extra = specimen(font)
            title = f"{label}   [{src}: {t} {rid}]  height {f['height']}, ascent {f['ascent']}, {n_extra} non-ASCII glyphs"
            Image.fromarray(to_image(title, lines)).save(f"{outdir}/{fname}.png")
            rows.append((label, src, t, rid, fname))
    for r in rows:
        print("%-28s %-26s %s %-6d -> %s" % r)
