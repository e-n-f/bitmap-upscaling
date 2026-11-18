import os, sys
os.environ["FREETYPE_PROPERTIES"] = "truetype:interpreter-version=35"
import freetype, numpy as np
from PIL import Image, ImageDraw

def render(path, ppem, text, hinted):
    face = freetype.Face(path); face.set_pixel_sizes(0, ppem)
    flags = freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_MONO | (0 if hinted else freetype.FT_LOAD_NO_HINTING)
    W, H = ppem * len(text), ppem * 2; img = np.zeros((H, W), bool); pen = 2; base = int(ppem * 1.3)
    for ch in text:
        face.load_char(ch, flags); g = face.glyph; bm = g.bitmap
        rows, w, pitch = bm.rows, bm.width, bm.pitch
        buf = np.frombuffer(bytes(bm.buffer), np.uint8).reshape(rows, pitch) if rows else np.zeros((0, 1), np.uint8)
        bits = np.unpackbits(buf, axis=1)[:, :w].astype(bool)
        y0, x0 = base - g.bitmap_top, pen + g.bitmap_left
        if rows and 0 <= y0 and y0 + rows <= H and x0 + w <= W:
            img[y0:y0 + rows, x0:x0 + w] |= bits
        pen += (g.advance.x + 32) >> 6
    return img[:, :pen + 2]

text = "Hamburgefonstiv"
fams = ["Verdana", "Georgia", "Tahoma", "Arial", "Times New Roman", "Courier New"]
rows = []
for fam in fams:
    for ppem in (9, 11, 13, 16):
        for label, path, hinted in (("win98 hinted", f"mscore/win98/{fam}.ttf", True), ("win11 hinted", f"mscore/win11/{fam}.ttf", True), ("win11 unhinted", f"mscore/win11/{fam}.ttf", False)):
            if not os.path.exists(path): continue
            rows.append((f"{fam} {ppem}px {label}", render(path, ppem, text, hinted)))
S = 3; lw = 190
Wt = lw + max(r.shape[1] for _, r in rows) * S; Ht = sum(r.shape[0] * S + 4 for _, r in rows)
out = Image.new("L", (Wt, Ht), 255); d = ImageDraw.Draw(out); y = 0
for lab, r in rows:
    d.text((4, y + r.shape[0] * S // 2 - 6), lab, fill=0)
    out.paste(Image.fromarray(np.where(np.kron(r, np.ones((S, S), bool)), 0, 255).astype(np.uint8)), (lw, y)); y += r.shape[0] * S + 4
out.save(sys.argv[1]); print(out.size)
