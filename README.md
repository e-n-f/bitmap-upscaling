# bitmap-upscaling

Experiments in upscaling 1-bit bitmap fonts so that stair-stepped diagonals and implied curves come back as real
slopes and curves, while the output stays strictly 1-bit.

Test images:

- `inputs/sun-console.png`: the Sun console font (12×22 cells, 456×88 px)
- `inputs/desktop.gif`: classic Mac Finder screenshot (Chicago and Geneva)
- `inputs/macfonts-OS1-7.5/`: specimen screenshots of classic Mac OS bitmap fonts, from
  [JohnDDuncanIII/macfonts](https://github.com/JohnDDuncanIII/macfonts/tree/master/Screenshots/OS1-7.5)

All outputs are 4× unless noted, and every output is 1-bit. Methods that produce grey levels were thresholded at 50%.

## 1. Existing algorithms (Sun console font)

| Method | File | Notes |
|---|---|---|
| Nearest neighbour | `results/classic/sun-console_nearest4.png` | baseline |
| Scale2x ×2 (EPX) | `sun-console_scale4x.png` | only handles 45° steps; preserves weight |
| MMPX ×2 | `sun-console_mmpx4x.png` | my own implementation, written from memory of the paper; thickens strokes here |
| Potrace (default, and alphamax 0.6 `-n`) | `sun-console_potrace_*.png` | wobbly and uneven at 2 px stroke width |
| xBRZ 4× | `sun-console_xbrz4x.png` (`_aa` = before threshold) | best of the classic scalers |
| Kopf–Lischinski ([libdepixelize](https://gitlab.com/inkscape/devel/libdepixelize), as used in Inkscape's "Pixel art" trace) | `sun-console_kl4x.png`, `sun-console_kl.svg` | curves overshoot and small details distort at this size |

Comparison sheets: `results/classic/cmp_*.png` (nearest, Scale2x, MMPX, Potrace) and `cmp2_*.png` (nearest, Scale2x, xBRZ, Kopf–Lischinski).

## 2. Trained model (`scripts/ml`)

A small U-Net (`model.py`, 0.78M parameters) maps a 1-bit image to a **signed distance field at 4×** (in 1× pixel
units, positive inside the ink). Thresholding at 0 gives the 4× bitmap. Bicubic-upsampling the distance field before
thresholding gives smooth output at 8× or higher.

Training data (`gen.py`) is rendered from outline fonts:

- **Fonts:** 356 system fonts (DejaVu, Liberation, URW base35, IBM Plex, TeX Gyre, Noto, Courier Prime, Roboto Slab, and others), plus
  the 43 fonts in [e-n-f/type-revivals](https://github.com/e-n-f/type-revivals), which are sampled 35% of the time.
- **Rendering:** 1–3 random characters (Latin, Greek, Cyrillic, some math and arrows) on a 32×32 canvas, with cap heights of
  6–18 px and random sub-pixel offset, drawn at 8× supersampling.
- **Weight augmentation:** uniform emboldening or thinning, or horizontal-only thickening to imitate thick-stem,
  thin-horizontal bitmap fonts like the Sun font.
- **Input:** each pixel is inked if its area coverage is at or above a random threshold between 0.3 and 0.6.
- **Target:** the true outline's signed distance at 4×, clipped to ±1.5 px.

The model was trained for 45 minutes on 4 CPU threads (about 3,900 steps of batch 64, from 80k samples); see `scripts/ml/train.log`.
At inference the 4× distance field gets a light Gaussian smoothing (σ = 1 at 4× pixels, `SMOOTH` env var) before thresholding.

Results:

- `results/ml/<name>_ml4x.png`, `_ml8x.png`, plus `_xbrz4x.png` and `_nearest4x.png`, for every input
- `results/sheets/*.png`: crops comparing nearest / xBRZ / model 4× / model 8× (shown at half size)

### Observations

- **Better than xBRZ:** At the Sun font's size, and for Mac fonts at about 12 pt and up, the model recovers real curves
  (C, G, O, a, e, g, S) instead of smoothed stair-steps, keeps slab serifs, and its 8× output is genuinely smoother.
- **Worse than xBRZ:** Small sizes (6–7 px glyphs, e.g. New York 9), where the eye of "e" closes, "z" breaks, and the small dots in
  `; , .` fade. Thin symbols such as `@ # * { }` get garbled.
- **Out of scope:** Dithered greys (the desktop pattern, dithered icons) become blobs, because the model never saw non-text
  patterns in training.
- Edges are still slightly rough.

### Ideas for improvement

- Train on fonts that ship both outlines and hand-tuned embedded bitmaps, so the model learns what designers actually do
  at small sizes rather than what mechanical rasterisation does.
- Add more small sizes, protect 1-pixel dots, and add dither and noise patterns that should pass through unchanged.
- Train longer and with a larger network. Validation error was still falling when training stopped.

## Reproducing

```
pip install torch numpy pillow scipy fonttools
git clone https://github.com/e-n-f/type-revivals
cd scripts/ml
python gen.py ../../type-revivals train.npz 80000    # also needs fc-list and system fonts
python gen.py ../../type-revivals val.npz 2000
python train.py 45                                  # minutes
python infer.py glyphsdf.pt out ../../inputs/sun-console.png
python sheet.py out sun-console 0 0 144 44 sheet.png
```

`infer.py` also runs xBRZ for comparison. Build `scripts/xbrz/xbrz_raw` first, following the instructions in `xbrz_raw.cpp`.
The pretrained weights are in `weights/glyphsdf.pt`. The classic scalers (Scale2x, MMPX, nearest) are in `scripts/classic/scalers.py`.
