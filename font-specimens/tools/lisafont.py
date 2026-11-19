"""Parse Lisa/QuickDraw bitmap font records (.F files) and render specimen sheets.
usage: python -I lisafont.py OUT_DIR FONT.F...
"""
import os, struct, sys
import numpy as np
from PIL import Image, ImageDraw

def parse(data):
    hdr = struct.unpack(">H12h", data[:26])
    fontType, first, last, widMax, kernMax, nDescent, fRectW, fRectH, owTLoc, ascent, descent, leading, rowWords = hdr
    n = last - first + 3
    rb = rowWords * 2
    img_end = 26 + rb * fRectH
    need = img_end + 2 * n * 2
    if not (0 <= first <= last <= 255 and 0 < fRectH < 200 and 0 < rowWords < 4000 and len(data) >= need):
        return None
    bits = np.unpackbits(np.frombuffer(data[26:img_end], np.uint8)).reshape(fRectH, rb * 8).astype(bool)
    loc = struct.unpack(f">{n}H", data[img_end:img_end + 2 * n])
    owt_off = 16 + owTLoc * 2           # owTLoc counts words from the owTLoc field (byte 16)
    ow = struct.unpack(f">{n}h", data[owt_off:owt_off + 2 * n]) if owt_off + 2 * n <= len(data) else None
    glyphs = {}
    for i in range(last - first + 1):
        if ow is not None and ow[i] == -1:
            continue
        x0, x1 = loc[i], loc[i + 1]
        off, wid = ((ow[i] >> 8) & 0xFF, ow[i] & 0xFF) if ow is not None else (0, x1 - x0)
        glyphs[first + i] = (bits[:, x0:x1], off, wid)
    return dict(type=fontType, first=first, last=last, widMax=widMax, kernMax=kernMax, fRectW=fRectW, fRectH=fRectH,
                ascent=ascent, descent=descent, leading=leading, rowWords=rowWords, size=len(data), need=need, glyphs=glyphs)

def specimen(f, text_lines, scale):
    H = f["fRectH"]; lines = []
    for t in text_lines:
        W = sum(f["glyphs"].get(ord(c), (None, 0, f["widMax"]))[2] for c in t) + 8 - f["kernMax"] * len(t)
        canvas = np.zeros((H, max(W, 1)), bool); pen = 4
        for c in t:
            g = f["glyphs"].get(ord(c))
            if g is None: pen += f["widMax"] // 2; continue
            b, off, wid = g; x = pen + f["kernMax"] + off
            if b.shape[1] and 0 <= x and x + b.shape[1] <= canvas.shape[1]: canvas[:, x:x + b.shape[1]] |= b
            pen += wid
        lines.append(canvas[:, :pen + 4])
    W = max(l.shape[1] for l in lines)
    out = np.vstack([np.pad(l, ((1, 1), (0, W - l.shape[1]))) for l in lines])
    return np.kron(out, np.ones((scale, scale), bool))

if __name__ == "__main__":
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    TEXT = ["ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz", "0123456789 !\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~",
            "The quick brown fox jumps over the lazy dog."]
    for p in sys.argv[2:]:
        name = os.path.basename(p)
        data = open(p, "rb").read()
        f = parse(data)
        if f is None:
            print(f"{name:20s} {len(data):6d} bytes: not a plain font record (type {data[:2].hex()})"); continue
        print(f"{name:20s} type {f['type']:04x} chars {f['first']}-{f['last']} ({len(f['glyphs'])} glyphs) "
              f"rect {f['fRectW']}x{f['fRectH']} ascent {f['ascent']} descent {f['descent']} widMax {f['widMax']} "
              f"bytes {f['size']}/{f['need']}+owTable")
        if f["glyphs"]:
            Image.fromarray(np.where(specimen(f, TEXT, 1), 0, 255).astype(np.uint8)).convert("1").save(f"{out}/{name[:-2]}.png")
