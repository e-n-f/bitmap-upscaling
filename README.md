# bitmap-upscaling

Also here: [`font-specimens/`](font-specimens/), pixel-exact specimens of Lisa and classic Mac bitmap fonts, decoded from the Lisa source release and from classic Mac resource forks.

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

## 3. Second-round model (v3, `scripts/ml_v2`)

Same network design as v1, but wider (48 base channels, 1.1M parameters). The data and training changed as follows.

### Training data

**Rendered from outline fonts** (`gen2.py`), 200k samples:

- **Fonts:** 2,143 families, each family sampled with equal weight rather than each file:
  - nearly all of [Google Fonts](https://github.com/google/fonts): 1,094 text families, plus display and handwriting families at 0.3 weight
  - system fonts, including all 35 URW Ghostscript base fonts
  - [e-n-f/type-revivals](https://github.com/e-n-f/type-revivals) at ordinary weight
  - 5% of samples from dingbat and symbol fonts (URW Dingbats and Standard Symbols, Noto Symbols, math and music fonts)
- **Text:** 75% of samples are 1–3 consecutive characters from real text (`build_corpus.py`): 2 MB of English
  novels from NLTK's Gutenberg selection, and the Universal Declaration of Human Rights in 23 other languages, including Greek
  and Cyrillic. The other 25% are random characters.
- **Sizes:** cap height 4–22 px, with 40% at 4–9 px. Samples whose 1-bit rendering has lost most of the glyph are rejected.
- **Non-text patterns:** 10% of samples add dithers, Mac-style fill patterns, rules or boxes. Their target is plain pixel
  blocks, so these should pass through unchanged.
- **Inversion:** 10% of samples are inverted.

**Hand-hinted pairs** (`gen_hinted.py`), 50k samples (20% of training): Windows 11 Arial, Courier New, Georgia, Tahoma,
Times New Roman and Verdana in all styles (22 files).

- **Input:** the font's own fully hinted bilevel rendering from FreeType's v35 TrueType interpreter, at 8–24 ppem.
- **Target:** the unhinted outline, with each glyph placed at its hinted origin.
- `results/v3/hinting/hinted_vs_unhinted.png` shows what the hinting does to these fonts.
- The fonts themselves are proprietary and are not in this repository. The v3 weights were trained partly on them.

### Training

115 minutes on 4 CPU threads: 9,033 steps of batch 64. See `logs/v3_train.log`.

One bug was fixed along the way. The loss previously clamped predictions to ±1.5, which zeroes the gradient
whenever a freshly initialised network predicts out of range. The wider network got stuck because of this.

### Results

- **Full outputs:** `results/v3/ml/` holds the 4×, 8×, xBRZ and nearest versions of every input, now including a Lisa screenshot
  (`inputs/lisa`, from [guidebookgallery.org](https://guidebookgallery.org/pics/gui/desktop/full/lisaos31.png)).
- **Training progression:** `results/v3/progression/` shows nearest, xBRZ, v1, and v3 at 15, 30, 60 and 90 minutes and final.
- **Outline recovery:** `results/v3/outline-recovery/` takes hinted screen bitmaps of Verdana and Georgia (in training) and Palatino
  Linotype and Lucida Console (not in training), and compares the model, xBRZ and nearest against the true outline. Red marks
  outline that was missed; blue marks ink outside the outline. Run `recovery.py` for the numbers.
- **Weights:** `weights/v3/` holds the final model plus the 15-minute and 60-minute snapshots.

### Observations

- **Plateau:** most of the improvement came in the first hour, and validation loss flattened after that.
- **Better than v1:** small dots and punctuation survive, dithers and dotted rules pass through, and Geneva's "e" crossbar
  survives. On Georgia at 9–11 px the output is closer to the true outline than xBRZ or nearest.
- **Outline recovery is not exact:** edges land about 0.25 px from the true outline on average, for every method. Hinting
  snaps stems to whole pixels and draws ~1.4 px stems 1 px wide, so the true stroke weight and sub-pixel position are lost.
- **Still bad: 1-pixel diagonals.** In bitmap fonts such as Geneva and New York 9 they break ("k", "w", "x", "2", "4"). Likely cause:
  rasterising a normal-weight outline never produces an 8-connected single-pixel diagonal, because ≥50% coverage gives a
  2-pixel-thick staircase. So the model reads such diagonals as hairlines. Bitmap designers draw them to mean the same
  weight as a 1-pixel stem. `results/v3/sheets/geneva9_vs_pruna.png` compares a general-purpose image upscaler, which
  handles them better.
- **Wrong typographic guess:** straight quotes (Lisa) become curly.

### Running v3

```
cd scripts/ml_v2
python build_corpus.py <nltk data dir> corpus.json
GF_CATEGORIES=gf_cat.txt python gen2.py <type-revivals> <google-fonts checkout> train2.npz 200000   # see gen2.py
python gen_hinted.py <dir of hinted .ttf> trainh.npz 50000
TRAIN=train2.npz,trainh.npz VAL=val2.npz,valh.npz OUT=glyphsdf3 python train2.py 115 48
python infer.py ../../weights/v3/glyphsdf3_final_115min.pt out ../../inputs/sun-console.png
```

`gf_cat.txt` lists each Google Fonts family directory with its category (`ofl/abel SANS_SERIF`), read from the families'
`METADATA.pb` files.

## Reproducing v1

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
