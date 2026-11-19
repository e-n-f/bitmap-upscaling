"""Alignment-test specimen: the same few lines of a font repeated at all 16 combinations of x%4 and y%4.

usage: python -I phase_grid.py OUT_PREFIX (--mac APPLEDOUBLE --res FONT:396 | --font FONT.F|FONT.ttf) [--letterspacing N]
Writes OUT_PREFIX.png (1x, pure black and white) and OUT_PREFIX.json (every glyph's box and its block's phase).

The image is a 4x4 grid of blocks. The block in column i, row j has its lines' origins at x = 4*k + i and y = 4*m + j
(the same base positions otherwise), so each glyph appears once at every horizontal and vertical phase modulo 4.
There are no labels in the image (labels might influence an upscaler); the JSON records which block is which.

--short-lines splits the text into five shorter lines (A-M, N-Z, a-m, n-z, 0-9), and --square arranges the 16 blocks
in whichever number of columns (1 to 16; the last row may have empty cells) makes the whole image closest to square. Each block keeps its own
x and y phase wherever it is placed; "block" in the JSON is [x phase, y phase] and "cell" is [column, row].

--ascii adds three lines with the other 32 printable ASCII characters (!"#$%&'()*+,- ./:;<=>?@[\\]^ _`{|}~).

--letterspacing N adds N blank pixels between glyphs, and each glyph also advances past any ink that overhangs its
normal advance width, so kerned glyphs no longer touch. Each box in the JSON then also has x0_unspaced and x1_unspaced:
where that glyph sits on an unspaced line, so the spacing can be taken out again after upscaling.
"""
import argparse, json, os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from specimen2 import draw_line, BitmapFont, PixelTTF

LONG_LINES = ["ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz", "0123456789"]
SHORT_LINES = ["ABCDEFGHIJKLM", "NOPQRSTUVWXYZ", "abcdefghijklm", "nopqrstuvwxyz", "0123456789"]
ASCII_PUNCT_LINES = ["!\"#$%&'()*+,-", "./:;<=>?@[\\]^", "_`{|}~"]       # the other 32 printable ASCII characters

ap = argparse.ArgumentParser()
ap.add_argument("out"); ap.add_argument("--font"); ap.add_argument("--mac"); ap.add_argument("--res")
ap.add_argument("--letterspacing", type=int, default=0)
ap.add_argument("--short-lines", action="store_true"); ap.add_argument("--square", action="store_true")
ap.add_argument("--ascii", action="store_true", help="also include all printable ASCII punctuation and symbols")
ap.add_argument("--caption", help="text drawn in a bitmap font in a band above the grid (the grid moves down by a "
                                  "multiple of 4 px, so all phases are unchanged)")
ap.add_argument("--caption-font", default=None, help="APPLEDOUBLE:TYPE:ID of the caption's bitmap font "
                                                      "(default: Geneva 9 from the same suitcase as --mac, else the grid's font)")
a = ap.parse_args()
LINES = (SHORT_LINES if a.short_lines else LONG_LINES) + (ASCII_PUNCT_LINES if a.ascii else [])
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
    pos, plain = [], []
    draw_line(font, [code(c) for c in t], positions=plain)                      # normal (unspaced) positions
    lines.append((draw_line(font, [code(c) for c in t], gap=a.letterspacing, positions=pos), pos, t, plain))
line_w = max(l[0].shape[1] for l in lines)
H = font.height
pitch_y = -(-(H + 3) // 4) * 4                          # line pitch, a multiple of 4
block_w = -(-(line_w + 12) // 4) * 4                    # block width and height, multiples of 4
block_h = -(-(pitch_y * len(LINES) + 12) // 4) * 4
margin = 8
if a.square:      # columns of blocks giving the most nearly square image
    # any number of columns; the last row may have empty cells. Prefer squareness, then fewer empty cells.
    cols = min(range(1, 17), key=lambda c: (round(abs(np.log((c * (block_w + 4)) / (-(-16 // c) * (block_h + 4)))), 2),
                                              -(-16 // c) * c - 16))
else:
    cols = 4
rows_ = -(-16 // cols)
step_x, step_y = (block_w + 4, block_h + 4) if a.square else (block_w, block_h)   # original layout without --square
W, Hh = (2 * margin + cols * step_x, 2 * margin + rows_ * step_y) if a.square else (2 * margin + 4 * block_w + 4, 2 * margin + 4 * block_h + 4)
img = np.zeros((Hh, W), bool)
boxes = []
for n in range(16):
    xp, yp = n % 4, n // 4                     # this block's phase
    c, r = (xp, yp) if cols == 4 else (n % cols, n // cols)
    bx, by = margin + c * step_x + xp, margin + r * step_y + yp     # margin and the steps are multiples of 4
    assert bx % 4 == xp and by % 4 == yp
    for li, (bits, pos, text, plain) in enumerate(lines):
        ox, oy = bx, by + li * pitch_y
        img[oy:oy + H, ox:ox + bits.shape[1]] |= bits
        for (ch_code, x0, x1), (_, u0, u1), ch in zip(pos, plain, [ch for ch in text if font.glyph(code(ch)) is not None]):
            boxes.append(dict(char=ch, x0=ox + x0, x1=ox + x1, y0=oy, y1=oy + H,
                              x0_unspaced=ox + u0, x1_unspaced=ox + u1,
                              x_phase=ox % 4, y_phase=oy % 4, block=[xp, yp], cell=[c, r], line=li))
if a.caption:
    cfont = None
    if a.caption_font:
        f_, t_, i_ = a.caption_font.rsplit(":", 2)
        cfont = next(QDFont(c[6]) for c in collect(f_) if c[1] == t_ and c[2] == int(i_))
    elif a.mac:
        cfont = next((QDFont(c[6]) for c in collect(a.mac) if c[1] == "FONT" and c[2] == 393), None)   # Geneva 9
    cfont = cfont or font
    cap = draw_line(cfont, [ch.encode("mac_roman", "replace")[0] for ch in a.caption])
    band = -(-(cfont.height + 2 * margin) // 4) * 4            # multiple of 4, so phases are unchanged
    if cap.shape[1] + 2 * margin > W:                          # widen the canvas on the right if the caption needs it
        W2 = -(-(cap.shape[1] + 2 * margin) // 4) * 4
        img = np.hstack([img, np.zeros((Hh, W2 - W), bool)]); W = W2
    top = np.zeros((band, W), bool)
    top[margin:margin + cfont.height, margin:margin + cap.shape[1]] = cap[:, :W - margin]
    img = np.vstack([top, img]); Hh += band
    for b in boxes:
        b["y0"] += band; b["y1"] += band
        assert b["y0"] % 4 == b["y_phase"]
Image.fromarray(np.where(img, 0, 255).astype(np.uint8)).convert("1").save(a.out + ".png")
json.dump(dict(width=W, height=Hh, glyph_height=H, letterspacing=a.letterspacing, caption=a.caption or "", boxes=boxes),
          open(a.out + ".json", "w"))
print(f"{a.out}.png {W}x{Hh}; line origins have x%4 in {sorted({b['x_phase'] for b in boxes})} and "
      f"y%4 in {sorted({b['y_phase'] for b in boxes})}; {len(boxes)} glyphs")
