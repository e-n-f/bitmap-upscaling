"""Line up every appearance of chosen characters in an upscaled copy of a specimen, for side-by-side comparison.

usage:
  python -I glyph_instances.py --upscaled IMG --chars "vxk" --out OUT.png  (--font FONT.F|FONT.ttf |
                                                                          --mac APPLEDOUBLE --res FONT:396)

The specimen layout is recomputed from the font (it is deterministic), so the upscaled image only needs to be a
uniformly scaled copy of the specimen PNG; any scale factor works. Each output row is one character: first the original
glyph (nearest-neighbour at the same scale, for reference), then each appearance in the upscaled image, labelled with the
specimen row it came from (ascii, the hex row of the non-ASCII table, or s1/s2/s3 for the shuffled passes) and its line's
vertical position modulo 4.
"""
import argparse, os, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from specimen2 import specimen, glyph_boxes, to_image, BitmapFont, PixelTTF

ap = argparse.ArgumentParser()
ap.add_argument("--upscaled", required=True); ap.add_argument("--chars", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--font"); ap.add_argument("--mac"); ap.add_argument("--res", help="TYPE:ID, e.g. FONT:396 or NFNT:2828")
ap.add_argument("--layout", help="a phase_grid.py .json: use its glyph boxes and the .png beside it as the original")
ap.add_argument("--encoding", default="mac_roman", help="how --chars map to byte codes for Lisa/Mac fonts")
a = ap.parse_args()

if a.layout:
    import json
    L = json.load(open(a.layout))
    ref = np.array(Image.open(a.layout[:-5] + ".png").convert("L"))
    up = Image.open(a.upscaled).convert("L")
    sx, sy = up.width / L["width"], up.height / L["height"]
    print(f"specimen {L['width']}x{L['height']}, upscaled {up.width}x{up.height}, scale {sx:.3f} x {sy:.3f}")
    up = np.array(up); lines = []
    for ch in a.chars:
        inst = sorted([b for b in L["boxes"] if b["char"] == ch], key=lambda b: (b["y_phase"], b["x_phase"]))
        if not inst:
            print(f"{ch!r}: not in this specimen"); continue
        cells = []
        for b in inst:
            X0, X1 = int(round((b["x0"] - 1) * sx)), int(round((b["x1"] + 1) * sx))
            Y0, Y1 = int(round(b["y0"] * sy)), int(round(b["y1"] * sy))
            cells.append((f"x{b['x_phase']} y{b['y_phase']}", up[Y0:Y1, X0:X1]))
        b = inst[0]
        orig = ref[b["y0"]:b["y1"], b["x0"] - 1:b["x1"] + 1]
        cells.insert(0, ("original", np.array(Image.fromarray(orig).resize(cells[0][1].shape[::-1], Image.NEAREST))))
        H = max(c[1].shape[0] for c in cells) + 14
        cw = [max(im.shape[1], 6 * len(lab) + 4) for lab, im in cells]
        line = Image.new("L", (sum(w + 8 for w in cw) + 10, H), 255); d = ImageDraw.Draw(line); x = 5
        for (lab, im), w in zip(cells, cw):
            line.paste(Image.fromarray(im), (x + (w - im.shape[1]) // 2, 0)); d.text((x, H - 12), lab, fill=90); x += w + 8
        lines.append(line); print(f"{ch!r}: {len(inst)} appearances")
    W = max(l.width for l in lines); S = Image.new("L", (W, sum(l.height + 8 for l in lines)), 255); y = 0
    for l in lines:
        S.paste(l, (0, y)); y += l.height + 8
    S.save(a.out); sys.exit()

if a.mac:
    from macspecimens import collect, QDFont
    rtype, rid = a.res.split(":")
    font = None
    for c in collect(a.mac):
        if c[1] == rtype and c[2] == int(rid):
            font = QDFont(c[6])
    if font is None:
        sys.exit(f"{a.res} not found in {a.mac}")
    to_code = lambda ch: ch.encode(a.encoding)[0]
else:
    font = PixelTTF(a.font) if a.font.lower().endswith(".ttf") else BitmapFont(a.font)
    to_code = ord if a.font.lower().endswith(".ttf") else (lambda ch: ch.encode(a.encoding)[0])

rows, _ = specimen(font)
ref = to_image("", rows)                                  # the specimen at 1x, to get its size and reference pixels
up = Image.open(a.upscaled).convert("L")
sx, sy = up.width / ref.shape[1], up.height / ref.shape[0]
print(f"specimen {ref.shape[1]}x{ref.shape[0]}, upscaled {up.width}x{up.height}, scale {sx:.3f} x {sy:.3f}")
up = np.array(up)

# vertical position of each row's top, modulo 4 (only the shuffled rows vary it)
row_mod = {}
y = 14
for ri, row in enumerate(rows):
    y += row[2]; row_mod[ri] = (y + 1) % 4; y += row[1].shape[0] + 2

boxes = glyph_boxes(rows)
lines = []
for ch in a.chars:
    code = to_code(ch)
    inst = [b for b in boxes if b[0] == code]
    if not inst:
        print(f"{ch!r}: not in this font"); continue
    cells = []
    for c, ri, label, x0, y0, x1, y1 in inst:
        X0, X1 = int(round((x0 - 1) * sx)), int(round((x1 + 1) * sx))
        Y0, Y1 = int(round(y0 * sy)), int(round(y1 * sy))
        cells.append((f"{label} y%4={row_mod[ri]}", up[Y0:Y1, X0:X1]))
    # reference: the original glyph pixels from the first appearance, nearest-neighbour at the same scale
    c, ri, label, x0, y0, x1, y1 = inst[0]
    orig = ref[y0:y1, x0 - 1:x1 + 1]
    orig = np.array(Image.fromarray(orig).resize(cells[0][1].shape[::-1], Image.NEAREST))
    cells.insert(0, ("original", orig))
    H = max(c[1].shape[0] for c in cells) + 14
    cw = [max(im.shape[1], 6 * len(lab) + 4) for lab, im in cells]      # wide enough for the label
    W = sum(w + 10 for w in cw) + 10
    line = Image.new("L", (W, H), 255); d = ImageDraw.Draw(line); x = 5
    for (lab, im), w in zip(cells, cw):
        line.paste(Image.fromarray(im), (x + (w - im.shape[1]) // 2, 0)); d.text((x, H - 12), lab, fill=90); x += w + 10
    lines.append(line)
    print(f"{ch!r}: {len(inst)} appearances")

W = max(l.width for l in lines); S = Image.new("L", (W, sum(l.height + 8 for l in lines)), 255); y = 0
for l in lines:
    S.paste(l, (0, y)); y += l.height + 8
S.save(a.out)
