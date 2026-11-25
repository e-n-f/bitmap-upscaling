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

### Apple II MousePaint fonts

`phase-grid/square-ls2-apple2/` has grids for six bitmap fonts from MousePaint (Apple II). Despite some of their names,
they are not the Mac fonts. They are built the same way as `square-ls2-mac/`: short lines, the 32 ASCII symbols plus
any other glyphs the font has, 2 px letterspacing, squarish arrangement, and a Geneva 9 caption.

| Grid | MousePaint font | Line height / ascent (px) | Extra glyphs |
|---|---|---|---|
| `A2_Athens_sq_ls2` | ATHENS | 12 / 10 | none |
| `A2_NewYork_sq_ls2` | NEW.YORK | 11 / 9 | one glyph at U+F8FF |
| `A2_Toronto_sq_ls2` | TORONTO | 11 / 9 | DEL (<7F>) |
| `A2_Venice_sq_ls2` | VENICE | 10 / 8 | DEL (<7F>) |
| `A2_MPFont_sq_ls2` | MP.FONT | 9 / 7 | DEL (<7F>) |
| `A2_SystemCharset_sq_ls2` | SYSTEM.CHARSET | 8 / 7 | MouseText at U+E000–E01F and U+E07F |

`phase_grid.py --font` now reads BDF files. The fonts are read from the BDF conversions in `bdf/` (listed in
`SOURCES.txt`). In those BDFs, code points are Unicode, with MouseText in the Private Use Area. Each box's `code` in the
JSON is that BDF code point. `char` is the character itself, and codes below 32 and DEL are written `<7F>` etc.

`phase-grid/pruna-picks-apple2/` has the `pick_typical.py` votes on Pruna 6× upscales of all six grids
(`A2_<font>_sq_ls2_6x_*`, with `_report.txt` giving each character's consistency). `A2_all_6x_avg_grey_contact.png`
stacks the six grey vote averages. In Toronto, Venice and MP.FONT, code 127 is an Apple logo (New York has it at U+F8FF).

### Atari, VIC-20, IBM MDA and TRS-80 Model I

`phase-grid/square-ls2-retro/` has grids, built the same way, for four more computers' character ROMs, drawn from
pixel TrueType fonts (copies in `ttf/`; sources and glyph ranges in `SOURCES.txt`):

| Grid | Font | Cell height / ascent (px) | Characters |
|---|---|---|---|
| `Atari_sq_ls2` | EightBit Atari | 11 / 9 | 259: ASCII plus ATASCII graphics, and inverse video |
| `VIC20_sq_ls2` | PetMe | 8 / 7 | 285: ASCII plus the uppercase/graphics set, and reverse |
| `IBM_MDA_sq_ls2` | Px437 IBM MDA | 14 / 11 | 252: code page 437 |
| `TRS80_M1_sq_ls2` | Another Man's Treasure MIB Raw | 12 / 7 | 165: ASCII, arrows and symbols, and 2×3 block graphics |

Each grid covers the machine's main 256-character ROM, from the font's private-use "raw ROM" range or (for the MDA) code
page 437. Glyphs that duplicate ones already shown are left out. Box `code`s in the JSON are the fonts' Unicode code
points. The EightBit Atari font's vertical metrics are not whole pixels, so its cell is rounded out to 11 px.

`phase_grid.py --extra HEXRANGES` adds such glyphs. `PixelTTF` (in `specimen2.py`) no longer needs fontTools: it reads
the font with Pillow and `ttfinfo.py`, and detects the size of a pixel in font units (100 for most, 128 for EightBit Atari).

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

London 18 also has a third Pruna 6× run, made from Gaussian-processed input (`_gauss1.2`,
`replicate-prediction-88f9c23zy9rmw0d221eawt82fw`), with the usual `pick_typical.py` outputs.
`London_18_sq_ls2_mac_6x_combined_gauss1.2_*` combines all three London runs (`--names earlier,v2,gauss1.2`), and
`compare_London_18_gauss1.2.png` shows the three vote averages and that combination.

### Size composites

`size-composite/NewYork_*` overlays every size of New York onto the 36-point design and averages them:

- **Sizes:** 9 (System 6.0.8), plus 10, 12, 14, 18, 20, 24 and 36 (LOSTFONTS).
- **Vertical alignment:** the reference lines are measured from each size's bitmaps: descender (bottom of "p"),
  baseline, x-height (top of "x") and cap height (top of "H", which equals the ascender in every size). Each glyph is
  mapped piecewise-linearly through those lines, so they coincide across sizes.
- **Horizontal alignment:** each glyph's ink is stretched onto the 36-point glyph's ink extent, so side stems and bowl
  edges align.
- **Averaging:** each source bitmap is sampled bilinearly at 6 subpixels per 36-point pixel, and the sizes are
  averaged with equal weight. Glyphs are laid out with the 36-point advance widths.

Outputs:

- `_composite_grey.png`: the average.
- `_composite.png`: the average thresholded at 50%.
- `_sizes.png`: selected characters as each size looks after the mapping, beside the average.
- `_composite_glyphs.json`: reference lines, positions and advances.

The x-height is 0.69–0.78 of the cap height at every size, so the sizes differ mainly in letter shapes and weight,
not proportions. 9 and 10 point are heavy and blocky, 12 and 14 light and open, 18 heavy, and 20–36 a Times-like design.

```
python -I tools/composite_sizes.py OUT_PREFIX 9=__MACOSX/._suitcase:FONT:265 ... 36=__MACOSX/._LOSTFONTS:FONT:292
```

`size-composite/Geneva_*` is the same composite for Geneva 9, 10, 12, 14, 18, 20 and 24 (System 6.0.8), mapped onto 24
point. Geneva splits into two designs: a heavy one at 9–12 point (u-shaped "y", short "Q" tail) and a light one at
14–24 point (v-shaped "y", long diagonal "Q" tail). Where the two groups draw a letter with a different structure, the
raster average is a double image ("y", "Q"). Where they share a structure, it averages cleanly.

`size-composite/NewYork_blur1_*` is the New York composite with `--blur 1`: each size's bitmap is blurred with a Gaussian of
sigma 1 in its own pixels before mapping and averaging. That is a strong blur for the small sizes (9 and 10 point become
soft blobs) and a slight one for 24 and 36, so the large sizes dominate the detail. The grey composite is the useful
output. Its hairlines and serifs are too faint for a clean threshold, so `_composite.png` is thresholded at 30%, not
50%, and is heavier than the design.

`size-composite/Geneva_blur1_*` is the Geneva composite (9–24 onto 24 point) with the same sigma-1 blur.

`size-composite/NewYork_12_24*` combines only New York 12 and 24, on the 24-point metrics, in three versions:

- `NewYork_12_24_*`: no blur.
- `NewYork_12_24_blur1_*`: each size blurred with sigma 1 in its own pixels. That is 2 px at 24 point for the 12-point
  half, so it is the softest.
- `NewYork_12_24_blur24px1_composite_grey*`: the unblurred average blurred once with sigma 1 px at 24-point scale.

The `_1x.png` files are the grey composites reduced to true 24-point size by averaging each 6×6 block, so they are
ordinary antialiased greyscale text, meant as input for an upscaler.

Pruna's 6× upscales of the three 12+24 versions: the unblurred one and the one blurred at 24-point scale came out with
doubled edges (the 12- and 24-point shapes drawn as two outlines), while the per-size-blurred one came out clean but
mostly the 24-point design. To give the 12 point more influence there are three more versions, each with a
`_composite_grey_1x.png` at true 24-point size:

- `NewYork_12_24_w2_*`: per-size blur 1, with the 12 point weighted 2:1.
- `NewYork_12_24_w3_*`: the same, weighted 3:1.
- `NewYork_12_24_eqblur_*`: both sizes blurred by the same 2 px at 24-point scale (`--blur-per 12=1,24=2`), weighted equally.

`composite_sizes.py` gains `--weights` and `--blur-per`, and now always writes the `_composite_grey_1x.png` reduction.

In Pruna's upscales of those, the 2:1 version stayed solid, but the 3:1 and equal-blur versions came out looking
outlined (an inline design). The blurred 12-point contribution never reaches full black, so stroke centres stay grey
while the 24-point edges are dark. `NewYork_12_24_{w2,w3,eqblur}_levels_*` apply a levels adjustment to fix that: ink
coverage at or below 10% becomes white, at or above 60% becomes black, and values in between are stretched linearly.
That makes stroke centres solid and drops the faint halo, at the cost of somewhat heavier letters.

The levels-adjusted versions came back from Pruna with stronger halos and inline outlines: broad grey edge bands
seem to read to it as shadows or outlines, whatever their shape. So instead of grey averages, the next attempt gives it
crisp antialiased text with blended letter shapes.

- `--mode sdf` in `composite_sizes.py` blends the sizes' outlines: it thresholds each size's mapped glyph, averages
  their signed distance fields, and fills where the average is inside. With the raw 12-point bitmap that fails
  (`NewYork_12_24_sdf_*`), because its one-pixel curves and diagonals either break apart or swell into blobs when
  thresholded.
- `blend_picks.py` blends the outlines of Pruna's own picked glyphs instead, using each size's `pick_typical.py`
  output (`_avg_grey.png` plus `_glyphs.json` for origins and scale) and its bitmap font for metrics. Each pick is
  mapped onto the target metrics as above, thresholded at 50%, and the signed distance fields are averaged with
  weights. `NewYork_12_24_pickblend_{only12,w2,eq,only24}` use weights 12:24 of 1:0 (12-point shapes on 24-point
  metrics), 2:1, 1:1 and 0:1. The `.png` files are the outlines at 6×; the `_1x.png` files are reduced to 24-point size,
  giving crisp antialiased text to feed back to an upscaler.

```
python -I tools/blend_picks.py OUT_PREFIX \
    12=__MACOSX/._LOSTFONTS:FONT:268=phase-grid/pruna-picks-mac/NewYork_12_sq_ls2_mac_6x=2 \
    24=__MACOSX/._LOSTFONTS:FONT:280=phase-grid/pruna-picks-mac/NewYork_24_sq_ls2_mac_6x=1
```

The thresholded outline blends (`pickblend_*`) have many dropouts in thin hairlines and serifs, both as they are and
after upscaling. `blend_picks.py` now defaults to `--mode grey`: the mapped picks' grey coverage is averaged with the
given weights, with no thresholding. `NewYork_12_24_pickgrey_{eq,w2}` are the equal and 2:1 (12-weighted) grey blends,
at 6× and reduced to 24-point size (`_1x`). Every stroke survives; there are soft grey fringes only where the two
designs differ.

**Stroke-centre alignment** (`blend_picks.py --align centers`, `NewYork_12_24_pickgrey_centres_{eq,w2}`). Measured on
Pruna's picks, New York 12's horizontal strokes are much heavier relative to the letter than New York 24's (9.6% of the
cap height against 5.6%), while the stems are similar (about 10–11%). With edges aligned, the heavier 12-point strokes
share the 24-point strokes' outer edges and extend inward, which looks like an inset. So `--align centers`:

- **Measures** each size's stem width and horizontal stroke thickness on its picks (`pick_metrics.py`, using each
  glyph's own `ink_avg` box so neighbours don't interfere).
- **Vertical knots:** the centres of the horizontal strokes at the descender, baseline, x-height and cap height.
- **Horizontal mapping:** each glyph's outer stroke centres, its pick ink edges moved inward by half a stem. Glyphs
  narrower than two stems use their edges.

`size-composite/NewYork_12_on_24_aligned.png` is a Pruna 6× upscale of the New York 12 full-character-set rebuild
(`replicate-prediction-0qdfnd9yesrmy0d20hz9wa3vg8`) with every glyph moved onto the matching glyph of a Pruna 3× upscale
of the New York 24 rebuild (`replicate-prediction-26kqda4re1rmy0d20hzbka6yx0`). The image is the same size as the 24-point
image, 4050×8082, for side-by-side or layered comparison. Made with `tools/align_glyphs_between_sizes.py`.

- **Scale:** both are 324 px to the cap height, so there is no scaling. Each 12-point glyph is only translated.
- **Placement:** each 12-point glyph is centred on the 24-point glyph's ink box horizontally and sits on its baseline.
- **Which pixels belong to which glyph:** decided from the image itself, because neighbouring 12-point letters touch at
  their serifs. Connected blobs of ink go to the nearest glyph. A blob spanning several glyphs is split at its lightest
  column between their centres, which is the seam where the serifs merge. Every other pixel goes to the owner of the
  nearest ink.
- **Background:** greys at or above 92% of the paper brightness become white. Ink greys are otherwise unchanged.

`NewYork_12_on_24_overlay.png` overlays the two: ink only in the 12 point is blue, ink only in the 24 point is red,
ink in both is black.
