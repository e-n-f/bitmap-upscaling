"""sheet.py res_dir name x0 y0 x1 y1 out.png  -- crop box in 1x source pixels; stacks nearest/xBRZ/ML 4x/ML 8x(downsampled view)"""
import sys
from PIL import Image, ImageDraw

d, name = sys.argv[1], sys.argv[2]
x0, y0, x1, y1 = map(int, sys.argv[3:7])
rows = [("nearest4x", "Nearest neighbour 4x", 4), ("xbrz4x", "xBRZ 4x, thresholded", 4),
        ("ml4x", "Trained model 4x", 4), ("ml8x", "Trained model 8x (shown at half size)", 8)]
ims = []
for suf, label, k in rows:
    im = Image.open(f"{d}/{name}_{suf}.png").convert("L").crop((x0 * k, y0 * k, x1 * k, y1 * k))
    if k == 8:
        im = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
    ims.append((label, im))
w = ims[0][1].width; lab = 24
S = Image.new("L", (w, sum(im.height + lab for _, im in ims)), 255)
dr = ImageDraw.Draw(S); y = 0
for label, im in ims:
    dr.rectangle([0, y, w, y + lab - 2], fill=225); dr.text((6, y + 6), label, fill=0)
    S.paste(im, (0, y + lab)); y += im.height + lab
S.save(sys.argv[7])
