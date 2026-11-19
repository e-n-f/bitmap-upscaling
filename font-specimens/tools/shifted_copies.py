"""Make shifted copies of an image, and recombine upscaled versions of them.

  python -I shifted_copies.py make SPECIMEN.png OUT_DIR
      Writes OUT_DIR/<name>_shift_DXxDY.png for each offset in OFFSETS: the specimen placed at (DX, DY) on a white
      canvas PAD pixels larger in each direction (all copies the same size), plus OUT_DIR/<name>_shifts.json.

  python -I shifted_copies.py combine OUT_DIR/<name>_shifts.json UPSCALED_DIR OUT_PREFIX
      UPSCALED_DIR holds the upscaled copies, named like the shifted copies (any image extension). Each is cut back
      to the original specimen's area (the scale is measured from its size) and the copies are averaged.
      Writes OUT_PREFIX_mean.png (grey average) and OUT_PREFIX_vote.png (pixelwise majority of the copies, each
      thresholded at 50%), both aligned with the original specimen at the upscaled scale.
"""
import glob, json, os, sys
import numpy as np
from PIL import Image

OFFSETS = [(0, 0), (5, 3), (11, 14), (14, 7)]     # distinct mod 4, mod 8 and mod 16 in both directions
PAD = 16


def make(src, outdir):
    os.makedirs(outdir, exist_ok=True)
    im = Image.open(src).convert("L"); name = os.path.splitext(os.path.basename(src))[0]
    W, H = im.size; files = []
    for dx, dy in OFFSETS:
        c = Image.new("L", (W + PAD, H + PAD), 255); c.paste(im, (dx, dy))
        f = f"{name}_shift_{dx}x{dy}.png"; c.convert("1").save(os.path.join(outdir, f)); files.append(dict(file=f, dx=dx, dy=dy))
    json.dump(dict(source=os.path.basename(src), width=W, height=H, pad=PAD, copies=files),
              open(os.path.join(outdir, f"{name}_shifts.json"), "w"), indent=1)
    print(f"wrote {len(files)} copies of {W}x{H} on {W + PAD}x{H + PAD} canvases to {outdir}")


def combine(manifest, updir, prefix):
    M = json.load(open(manifest)); W, H = M["width"], M["height"]; cw, ch = W + M["pad"], H + M["pad"]
    crops = []
    for c in M["copies"]:
        stem = os.path.splitext(c["file"])[0]
        found = [p for p in glob.glob(os.path.join(updir, stem + ".*"))]
        if not found:
            print(f"missing upscaled copy for {c['file']}"); continue
        up = Image.open(found[0]).convert("L")
        sx, sy = up.width / cw, up.height / ch
        box = (round(c["dx"] * sx), round(c["dy"] * sy), round((c["dx"] + W) * sx), round((c["dy"] + H) * sy))
        crop = up.crop(box)
        if crops and crop.size != crops[0].shape[::-1]:
            crop = crop.resize(crops[0].shape[::-1], Image.BICUBIC)
        crops.append(np.array(crop).astype(np.float32)); print(f"{os.path.basename(found[0])}: scale {sx:.3f} x {sy:.3f}")
    if not crops:
        sys.exit("no upscaled copies found")
    mean = np.mean(crops, axis=0)
    vote = np.mean([c < 128 for c in crops], axis=0) > 0.5
    Image.fromarray(mean.round().astype(np.uint8)).save(prefix + "_mean.png")
    Image.fromarray(np.where(vote, 0, 255).astype(np.uint8)).save(prefix + "_vote.png")
    print(f"combined {len(crops)} copies -> {prefix}_mean.png, {prefix}_vote.png")


if __name__ == "__main__":
    {"make": lambda: make(sys.argv[2], sys.argv[3]),
     "combine": lambda: combine(sys.argv[2], sys.argv[3], sys.argv[4])}[sys.argv[1]]()
