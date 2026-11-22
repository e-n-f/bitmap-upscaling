# Lisa and classic Mac bitmap font specimens

Pixel-exact specimens of Apple Lisa and early Macintosh bitmap fonts. Each specimen shows:

- the ASCII alphabet, digits and punctuation, and a pangram
- every glyph the font defines outside printable ASCII, 32 per row
- the whole character set three more times (rows labelled `s1`, `s2` and `s3`):
  - each pass shuffles every inked glyph in an order fixed by its seed (Python's `random.Random(1)`, `(2)` and `(3)`)
  - glyphs are grouped into word-like clusters of 2-7 characters separated by spaces, and wrapped to the width of the pangram line
  - each of these lines has 0, 1, 2 or 3 pixels of extra space above it, cycling, so line positions vary modulo 4
  - every glyph therefore appears in several different neighbourhoods and vertical alignments, to show how
    context-dependent upscalers treat the same glyph

Row labels give the code of the row's first glyph. They are byte codes for Lisa `.F` and Mac FONT/NFNT fonts (0x80 and up is the Mac
Roman layout), and Unicode code points for the Kreative TrueType fonts. Some fonts define empty glyphs at the low control
codes, so their first non-ASCII row starts with blank space.

**Pixel-exact:** each glyph is copied from the font's bitmap and placed using the font's own kern, offset and width values,
as QuickDraw draws text. Nothing is smoothed or resampled.

- **1× images:** the individual specimens and everything in `sheets-1x/` have one font pixel per image pixel. The label
  bands and text are grey and anti-aliased; glyph pixels are pure black or white.
- **2× images:** everything in `sheets-2x/` is enlarged 2× by pixel doubling, for easier viewing.

## Contents

| Folder | What |
|---|---|
| `lisa-source-fonts/` | All 46 bitmap fonts in `LISA_OS/FONTS/*.F` from the Lisa source code release, at 1× |
| `lisa-kreative/` | Twiggy Raw (the Lisa system font) and Some Acronym Raw (the Lisa icon-label font), from Kreative Software's pixel-outline TrueType versions, at 1× |
| `mac-classic/` | 94 distinct FONT/NFNT resources from `Macintosh OS 1-6/Originals/Originals.zip` in [JohnDDuncanIII/macfonts](https://github.com/JohnDDuncanIII/macfonts), at 1×. `INDEX.txt` maps every resource (suitcase, type and ID) to its specimen or notes it as an exact duplicate |
| `sheets-1x/`, `sheets-2x/` | The same specimens combined into sheets by family, built by `tools/build_sheets.py` |
| `lisa-screenshot-match/` | Twiggy Raw rendered against text cut from the Lisa screenshot (`inputs/lisa/lisaos31.png`), and a test showing the menu font is not Modern 12 with synthetic bold |
| `phase-grid/` | Alignment test: Geneva 12 (System 0.85, FONT 396) and New York 9 (System 6.0.8, FONT 265), each with A–Z, a–z and 0–9 repeated in a 4×4 grid of blocks, one block for each combination of x%4 and y%4 of the line origins. The image has no labels; the `.json` lists every glyph's box with its x and y phase |
| `tools/` | The parsers and specimen generators, plus `phase_grid.py` and `glyph_instances.py` (below) |

## Lisa source fonts (`.F` files)

Each `.F` file is a single QuickDraw font record: the same layout as the Mac's later FONT/NFNT resources, with a 26-byte
header, one bitmap strip holding every glyph, a glyph-location table and an offset/width table. For all 54 bitmap files,
those parts add up exactly to the file size.

The naming is explained by the font manager source, `LIBS/LIBFM/libfm-fontmgr.text`:

- **Families:**
  - `TILE` is Lisa's Modern (sans-serif) family and `CENTURY` its Classic (serif) family. The code maps between them with `ToModern[cent12] := tile12`.
  - `HELV14` is Helvetica 14.
  - `WMFONTS`, `TOOLKITS` and `CALCFONTS` are icon fonts for the window manager, the toolkit and the calculator.
- **Sizes:**
  - `12RP` is 12-point proportional.
  - `12R12` and `12R10` are monospaced at 12 and 10 characters per inch.
  - `7R15` and `7R20` are small monospaced fonts.
  - `VT` is the VT100 terminal font, with box-drawing characters.
- **Device suffix:**
  - **S:** screen; also used for draft dot-matrix printing.
  - **H:** high-resolution dot-matrix printer, at about twice the screen resolution.
  - **C:** a later printer that the code adds as `edev1` without naming it.
  - **T:** a 448-byte width table for the daisy-wheel printer, with no bitmaps. These are not rendered.
  - **L:** laser printer; no L files are in the release.
- **APPLEW.F** has a different layout (type `0005`) with no bitmap strike, probably the daisy-wheel character table. It is not rendered.

The Lisa system font (`sysText`) is not among the `.F` files; the font manager loads it from the boot disk's `FONT.LIB`.
Kreative's **Twiggy Raw** matches the menu and window-title text in the screenshot pixel for pixel, and **Some Acronym Raw**
matches the icon labels.

## Classic Mac fonts

The `.dfont` files in macfonts' `Macintosh OS 1-6/OS X` folder hold a pixel-traced TrueType font plus an empty 26-byte
NFNT header, so these specimens come from `Originals.zip`. Its resource forks are preserved in the `__MACOSX/._*` AppleDouble
files.

- **Naming:**
  - FONT resources are named by family number (`id >> 7`) and size (`id & 127`).
  - When a suitcase doesn't name a family, Apple's standard family numbers are used: 16 Palatino, 20 Times, 21 Helvetica, 23 Symbol, 24 Mobile. Family 24 is called Taliesin in LOSTFONTS.
  - NFNT resources are named through each FOND's size/style association table.
  - The `CairoSplices` files all carry a FOND named "Cairo", so their specimens are named after the file.
- **Accuracy:** Geneva 9 and 12 and New York 9 and 12 rendered from these resources match macfonts' own specimen screenshots exactly.
- **Damaged fonts:** four System 0.85 fonts (Chicago 10, Geneva 24, New York 14, Swan Song 12) have corrupt glyph-location tables. They are skipped and listed in `INDEX.txt`.
- **Missing end markers:** many width tables omit their final end-marker word, which QuickDraw never reads. The parser accepts them.

## Running the tools

```
python -I tools/specimen2.py OUT_DIR FONT.F|FONT.ttf ...        # Lisa .F files or 1X1Y Kreative TTFs
python -I tools/macspecimens.py OUT_DIR __MACOSX/._suitcase ...  # AppleDouble resource forks
python -I tools/build_sheets.py font-specimens font-specimens/sheets-1x font-specimens/sheets-2x
python -I tools/phase_grid.py OUT_PREFIX --mac __MACOSX/._suitcase --res FONT:396     # or --font FILE
```

To compare how an upscaler draws the same character in different places, `glyph_instances.py` cuts every
appearance of the chosen characters out of an upscaled copy of a specimen and lines them up beside the original glyph.
The upscaled image only needs to be a uniformly scaled copy, at any scale.

```
# a phase grid: 16 appearances per character, ordered by x and y phase
python -I tools/glyph_instances.py --layout phase-grid/Geneva_12_phase_grid.json --upscaled UPSCALED.png --chars "vxwk" --out OUT.png
# an ordinary specimen (layout recomputed from the font)
python -I tools/glyph_instances.py --mac __MACOSX/._suitcase --res FONT:396 --upscaled UPSCALED.png --chars "vxwk" --out OUT.png
```

Requirements: numpy, Pillow and fontTools.

### Shifted copies

Pruna's output is deterministic, but identical glyphs with identical neighbours come out differently depending on
where they are in the image. In both phase grids that variation shows no pattern by alignment modulo 4. So
`phase-grid/shifted/` has four copies of each grid, offset by (0,0), (5,3), (11,14) and (14,7) on a canvas 16 px
larger in each direction. Upscale each copy, then realign and combine them:

```
python -I tools/shifted_copies.py combine phase-grid/shifted/NewYork_9_phase_grid_shifts.json DIR_OF_UPSCALED_COPIES OUT_PREFIX
```

The upscaled copies must keep the shifted copies' file names; any image extension works. The script measures each
copy's scale, cuts it back to the original grid's area, and writes `OUT_PREFIX_mean.png` (grey average) and
`OUT_PREFIX_vote.png` (a pixel is black when at least 3 of the 4 thresholded copies agree). Both line up with the original
grid at the upscaled scale, so `glyph_instances.py --layout` works on them too. If a glyph's quirks come from its position,
they should change between the copies and mostly disappear in the combined result.

### Picking the most typical version of each character

Since every character appears 16 times in a phase grid, a simpler alternative to the shifted copies is to pick, for each
character, the version the upscaler produces most typically:

```
python -I tools/pick_typical.py --layout phase-grid/NewYork_9_phase_grid.json --upscaled UPSCALED.png --out OUT_PREFIX
```

How it picks:

- **Thresholding:** each appearance is thresholded halfway between its own background and ink levels, to remove the
  upscaler's uneven background tint.
- **Comparing:** appearances are compared pairwise, counting differing pixels as a % of the character's ink.
- **Choosing:** the chosen version has the smallest median difference from the others, so occasional bad renderings
  can't win. Versions more than 1.6× as far from the rest are flagged as outliers.

It writes:

- `_choices.png`: every appearance, with the pick boxed and outliers marked `x`. `--chars` limits this sheet to particular characters.
- `_best.png`: A–Z, a–z and 0–9 rebuilt from the picks, thresholded.
- `_best_grey.png`: the same, with the picks' original grey pixels.

`phase-grid/pruna-picks/` has the results for the Pruna upscales of both grids.

### Letterspaced grid

`phase-grid/NewYork_9_phase_grid_ls4.png` is the New York 9 grid with 4 extra blank pixels between glyphs, made with
`phase_grid.py --letterspacing 4`. Each glyph also advances past any ink that overhangs its normal width, so kerned
glyphs (like the "f" serif that reaches into the "g") no longer touch their neighbours in the upscaler's input. Its
`.json` records each glyph's normal unspaced position as well (`x0_unspaced`, `x1_unspaced`). `pick_typical.py` uses
those to rebuild the alphabet with normal spacing after picking:

```
python -I tools/pick_typical.py --layout phase-grid/NewYork_9_phase_grid_ls4.json --upscaled UPSCALED.png --out OUT_PREFIX
```

Round trip: a nearest-neighbour 8× "upscale" of the spaced grid, picked and rebuilt this way, matches the unspaced
grid exactly.

### Combining upscales at several scales

Pruna's renderings of some characters depend on the scale factor; for example, New York 9's "g" ear comes out as a
detached dot at 8× but as a connected stroke at 6× and 7×. `pick_across_runs.py` takes several upscales of the same
grid, picks each character's most typical version in each, and uses the scale where that character is most consistent
(smallest median difference among its 16 appearances). `--force g:6,...` overrides the choice. It rebuilds the
alphabet at the largest scale, with normal spacing for a letterspaced grid.

```
python -I tools/pick_across_runs.py --layout phase-grid/NewYork_9_phase_grid_ls4.json --out OUT_PREFIX up6x.png up7x.png up8x.png
```

`phase-grid/pruna-picks/NewYork_9_ls4_6x7x8x_*` is the result for Pruna's 6×, 7× and 8× upscales of the letterspaced
New York 9 grid. 42 characters came from 6× and 20 from 8×; none from 7×. `_compare.png` shows each scale's pick with
its consistency score.

Shrinking each upscaled version back to 1× reproduces the source bitmap almost exactly at every scale, so pixel
fidelity can't separate good renderings from bad ones; consistency can.

### Squarer letterspaced grids for 28 classic Mac fonts

`phase-grid/square-ls2/` has phase grids for 28 classic Mac fonts and sizes (listed with their sources in `SOURCES.txt`):

- **Chicago:** 12
- **Geneva:** 9, 10, 12, 14
- **New York:** 9, 10, 12, 14
- **Monaco:** 9, 12
- **Times, Helvetica and Courier:** 9, 10, 12
- **Palatino:** 10, 12
- **Venice:** 14
- **Toronto, Los Angeles:** 12
- **London, Athens, San Francisco:** 18

Compared with the earlier grids:

- **Full printable ASCII:** each block has eight short lines: A–M, N–Z, a–m, n–z, 0–9, and the 32 punctuation and
  symbol characters in three lines. A few decorative fonts lack some characters, which are skipped: London 18
  (`< > ^ ` ~`), San Francisco 18 (`^ ` ~`), Los Angeles 12 (`` ` ``) and Venice 14 (`@`).
- **Letterspacing:** 2 px instead of 4.
- **Squarer images:** the 16 blocks are arranged in whichever number of columns makes the image closest to square,
  between 0.88:1 and 1.19:1. Some grids have a few empty cells.
- **Caption:** the top of each image has a caption in Geneva 9 bitmap pixels naming the grid, font, size, source
  suitcase and resource, so an upscaled output can be identified by eye. The grid sits below it, moved down by a
  multiple of 4 px, so the phases are unchanged.

Each block keeps its own x and y phase wherever it is placed. In the JSON, `block` is `[x phase, y phase]` and `cell`
is `[column, row]`. `pick_typical.py` and `pick_across_runs.py` work with these unchanged, and rebuild the text at
normal spacing.

Made with:

```
python -I tools/phase_grid.py OUT_PREFIX --mac __MACOSX/._suitcase --res FONT:id --letterspacing 2 --short-lines --square --ascii --caption "TEXT"
```

Without `--short-lines`, `--square`, `--ascii` and `--caption`, `phase_grid.py` produces exactly the original layouts.

To find out which grid an upscaled image belongs to, whatever its filename, run `identify_grid.py`. It shrinks
each upscale to the size of every grid with the same aspect ratio, compares them, and reports the best match and the scale.
`--copy-to` also copies each upscale to `<grid name>_<scale>x.png`, ready for the picking tools:

```
python -I tools/identify_grid.py phase-grid/square-ls2 ~/Downloads/replicate-prediction-*.png --copy-to upscales/
```

### Crop margins in the picking tools

`pick_typical.py` and `pick_across_runs.py` cut each appearance out with a margin, because upscaled strokes can extend
slightly beyond the source bitmap. For example, Pruna draws Chicago 12's "g" and "y" descenders a little below the
font's glyph rectangle.

- **Vertical:** 1.5 source px above and below the glyph rectangle (`--margin-y`). Lines are always at least 3 px apart.
- **Horizontal:** 1 source px beyond the glyph's ink for grids with at least 2 px letterspacing, otherwise 0.5 px so
  kerned neighbours stay out (`--margin-x`).

Round trips through the picker are still exact with these margins.

### Averaged picks

`pick_typical.py` also writes `_avg.png` and `_avg_grey.png`. These rebuild the text from averages rather than single winners:

- **Which versions:** every appearance of the character that is not an outlier, the winner included. That is about
  13–14 of the 16 in Pruna's 6× upscales of Chicago 12 and Geneva 9.
- **Normalising:** each appearance is first normalised to its own background (white) and ink (black) levels, which
  removes the upscaler's uneven background grey.
- **Averaging:** the normalised appearances are averaged (`_avg_grey.png`), then thresholded at 50% (`_avg.png`).

Compared with the single winners, the averages have clean white backgrounds and slightly smoother edges, with the same
shapes. On an exact (nearest-neighbour) upscale, both methods give identical results.

### Full Mac character set grids

`phase-grid/square-ls2-mac/` has grids like `square-ls2/` (2 px letterspacing, short lines, squarish, captioned), but
with the font's full character set. That means the 94 printable ASCII characters plus every other inked glyph the font
defines: Mac Roman 128–255, and Chicago's special glyphs at 0x11–0x14 (command key, check mark, diamond, Apple logo).
There are 20 grids:

- **Chicago:** 12
- **Geneva:** 9, 10, 12, 14, 24
- **New York:** 9, 10, 12, 14, 24
- **Monaco:** 9, 12
- **Venice:** 14
- **Toronto:** 12, 24
- **Los Angeles:** 12
- **London, Athens, San Francisco:** 18

The LaserWriter families (Times, Helvetica, Courier, Palatino) are left out, since good outline versions exist.
Character counts range from 96 (London, San Francisco) to 186 (Chicago). Sources are in `SOURCES.txt`.

Made with `phase_grid.py ... --ascii --macroman`. Each box in the JSON has `code` (the font's byte code) and `char`
(its Unicode equivalent, or `<11>` etc. for codes below 32).

The 24-point grids are large: Toronto 24 is 1656×1900, so a 6× upscale is about 10,000×11,000 px.

The picking tools now measure each crop's ink level from its clearly dark pixels, so very sparse glyphs (like the
ellipsis's three dots) are no longer mistaken for blank crops. Round trips through the picker are exact for all 20 grids.

### Picks for the full-character-set grids

`phase-grid/pruna-picks-mac/` has `pick_typical.py` results for Pruna's 6× upscales of 13 of the full-character-set
grids:

- **Chicago:** 12
- **Geneva:** 12, 24
- **New York:** 12, 24
- **Monaco:** 12
- **Toronto:** 12, 24
- **Venice:** 14
- **Los Angeles:** 12
- **London, Athens, San Francisco:** 18

`contact_6x_avg_mac_a.png` and `_b.png` show the averaged rebuilds side by side.

### Glyph identities, boxes and metrics (`_glyphs.json`)

Every set of picks has a `_glyphs.json` describing the rebuilt images (`_best`, `_best_grey`, `_avg` and `_avg_grey`
share one layout). The top level gives the layout and upscale it came from, the scale, the image size, and the source
font's ascent and glyph height in source pixels. Each entry in `glyphs` has:

- **Identity:** `char`, `unicode` and `code` (the font's byte code). Codes below 32 are written `<11>` etc.
- **Position:** `line`, the text line in the rebuilt image.
- **Boxes:** in rebuilt-image pixels, as `[x0, y0, x1, y1)` with x right and y down.
  - `cell`: the area the glyph was cut from, including the crop margins.
  - `ink_best` and `ink_avg`: the ink bounding boxes of the single winner and of the average.
- **Source metrics:** `source` holds the font's metrics in source pixels: `advance`, `x_offset` (from the pen position
  to the first ink column), `ink_width`, and positions. `origin` is the pen position on the baseline in rebuilt-image
  pixels, and `advance_px` is the advance width in rebuilt-image pixels. These are what a TrueType build needs to
  reproduce the bitmap font's spacing.
- **Pick statistics:**
  - `pick_typical.py`: `chosen_appearance`, `averaged_appearances`, `median_difference_pct` and `outliers`.
  - `pick_across_runs.py`: `scale_used` and `median_difference_pct`.

To support this, the grids' layout files now also record the font's `ascent` and each glyph's `advance` and
`x_offset`. All the layout files were regenerated; their images and all existing fields are unchanged except for one
correction. In the earlier ASCII grids for Los Angeles 12 and San Francisco 18, an empty backquote glyph had shifted
the labels of the last few characters on the last line by one. Boxes are now labelled by the glyph's own code, and
all picks were re-run.

### Second runs, and combining runs

`pruna-picks-mac/` also has second Pruna 6× runs of six fonts. Some were made from Gaussian-processed input (`_gauss`:
New York 24, Geneva 24, Chicago 12) and some are plain new runs (`_v2`: London 18, Geneva 12, New York 12). Each has the
usual `pick_typical.py` outputs.

`_combined_*` merges each font's earlier and new runs with `pick_across_runs.py --names earlier,<tag>`: every
character comes from whichever run's 16 appearances agree more closely. `_combined_glyphs.json` records the run used for
each character (`run_used`). `compare_<font>_<tag>.png` shows the earlier vote, the new vote and the combination side by
side.

`pick_across_runs.py` now accepts `--names` to label upscales that share a scale. `--force` takes those labels
(e.g. `--force "=:earlier,g:v2"`).
