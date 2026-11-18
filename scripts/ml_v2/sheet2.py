"""sheet2.py name x0 y0 x1 y1 out.png label=dir ...   rows: nearest, xBRZ, then <label> 4x for each dir"""
import sys
from PIL import Image, ImageDraw
name = sys.argv[1]; x0, y0, x1, y1 = map(int, sys.argv[2:6]); out = sys.argv[6]
first = sys.argv[7].split("=", 1)[1]
rows = [("Nearest neighbour 4x", f"{first}/{name}_nearest4x.png"), ("xBRZ 4x, thresholded", f"{first}/{name}_xbrz4x.png")]
for a in sys.argv[7:]:
    lab, d = a.split("=", 1)
    rows.append((lab, f"{d}/{name}_ml4x.png"))
ims = [(l, Image.open(p).convert("L").crop((x0 * 4, y0 * 4, x1 * 4, y1 * 4))) for l, p in rows]
w = ims[0][1].width; lab = 24
S = Image.new("L", (w, sum(im.height + lab for _, im in ims)), 255); dr = ImageDraw.Draw(S); y = 0
for l, im in ims:
    dr.rectangle([0, y, w, y + lab - 2], fill=225); dr.text((6, y + 6), l, fill=0); S.paste(im, (0, y + lab)); y += im.height + lab
S.save(out)
