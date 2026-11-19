"""Work out which phase grid each upscaled image came from, regardless of its filename.

usage: python -I identify_grid.py GRID_DIR UPSCALED... [--copy-to DIR]

Each upscaled image is shrunk to the size of every grid with the same aspect ratio (within 1%), thresholded, and
compared with that grid's PNG; the closest grid wins. With --copy-to, each image is also copied to
DIR/<grid name>_<scale>x<original extension>, so it can be passed straight to pick_typical.py with the grid's .json.
"""
import argparse, glob, os, shutil
import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("grid_dir"); ap.add_argument("upscaled", nargs="+"); ap.add_argument("--copy-to")
a = ap.parse_args()

grids = {}
for p in sorted(glob.glob(os.path.join(a.grid_dir, "*.png"))):
    if os.path.exists(p[:-4] + ".json"):
        im = Image.open(p).convert("L")
        grids[os.path.basename(p)[:-4]] = (im.size, np.array(im) < 128)
if a.copy_to:
    os.makedirs(a.copy_to, exist_ok=True)

for path in a.upscaled:
    up = Image.open(path).convert("L")
    results = []
    for name, ((w, h), bits) in grids.items():
        if abs((up.width / up.height) / (w / h) - 1) > 0.01:
            continue
        small = np.array(up.resize((w, h), Image.BOX))
        bg, ink = np.percentile(small, 90), np.percentile(small, 2)
        mism = ((small < (bg + ink) / 2) != bits).sum() / max(bits.sum(), 1) * 100
        results.append((mism, name, up.width / w))
    if not results:
        print(f"{path}: no grid with this aspect ratio ({up.width}x{up.height})"); continue
    results.sort()
    mism, name, scale = results[0]
    runner = f"; next best {results[1][1]} at {results[1][0]:.1f}%" if len(results) > 1 else ""
    print(f"{os.path.basename(path)}: {name} at {scale:.2f}x (mismatch {mism:.1f}% of ink{runner})")
    if a.copy_to:
        dest = os.path.join(a.copy_to, f"{name}_{round(scale)}x{os.path.splitext(path)[1]}")
        shutil.copyfile(path, dest); print(f"   copied to {dest}")
