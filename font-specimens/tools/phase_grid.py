"""Alignment-test specimen: the same few lines of a font repeated at all 16 combinations of x%4 and y%4.

usage: python -I phase_grid.py OUT_PREFIX (--mac APPLEDOUBLE --res FONT:396 | --font FONT.F|FONT.ttf)
Writes OUT_PREFIX.png (1x, pure black and white) and OUT_PREFIX.json (every glyph's box and its block's phase).

The image is a 4x4 grid of blocks. The block in column i, row j has its lines' origins at x = 4*k + i and y = 4*m + j
(the same base positions otherwise), so each glyph appears once at every horizontal and vertical phase modulo 4.
There are no labels in the image (labels might influence an upscaler); the JSON records which block is which.
"""
import argparse, json, os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from specimen2 import draw_line, BitmapFont, PixelTTF

LINES = ["ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz", "0123456789"]

ap = argparse.ArgumentParser()
ap.add_argument("out"); ap.add_argument("--font"); ap.add_argument("--mac"); ap.add_argument("--res")
a = ap.parse_args()
if a.mac:
    from macspecimens import collect, QDFont
    rtype, rid = a.res.split(":")
    font = next(QDFont(c[6]) for c in collect(a.mac) if c[1] == rtype and c[2] == int(rid))
    code = lambda ch: ch.encode("mac_roman")[0]
else:
    font = PixelTTF(a.font) if a.font.lower().endswith(".ttf") else BitmapFont(a.font)
    code = ord if a.font.lower().endswith(".ttf") else (lambda ch: ch.encode("mac_roman")[0])

lines = []
for t in LINES:
    pos = []
    lines.append((draw_line(font, [code(c) for c in t], positions=pos), pos, t))
line_w = max(l[0].shape[1] for l in lines)
H = font.height
pitch_y = -(-(H + 3) // 4) * 4                          # line pitch, a multiple of 4
block_w = -(-(line_w + 12) // 4) * 4                    # block width and height, multiples of 4
block_h = -(-(pitch_y * len(LINES) + 12) // 4) * 4
margin = 8
W, Hh = 2 * margin + 4 * block_w + 4, 2 * margin + 4 * block_h + 4
img = np.zeros((Hh, W), bool)
boxes = []
for j in range(4):            # y phase
    for i in range(4):        # x phase
        bx, by = margin + i * block_w + i, margin + j * block_h + j
        assert bx % 4 == (margin + i) % 4 and by % 4 == (margin + j) % 4
        for li, (bits, pos, text) in enumerate(lines):
            ox, oy = bx, by + li * pitch_y
            img[oy:oy + H, ox:ox + bits.shape[1]] |= bits
            for (c, x0, x1), ch in zip(pos, [ch for ch in text if font.glyph(code(ch)) is not None]):
                boxes.append(dict(char=ch, x0=ox + x0, x1=ox + x1, y0=oy, y1=oy + H,
                                  x_phase=ox % 4, y_phase=oy % 4, block=[i, j], line=li))
Image.fromarray(np.where(img, 0, 255).astype(np.uint8)).convert("1").save(a.out + ".png")
json.dump(dict(width=W, height=Hh, glyph_height=H, boxes=boxes), open(a.out + ".json", "w"))
print(f"{a.out}.png {W}x{Hh}; line origins have x%4 in {sorted({b['x_phase'] for b in boxes})} and "
      f"y%4 in {sorted({b['y_phase'] for b in boxes})}; {len(boxes)} glyphs")
