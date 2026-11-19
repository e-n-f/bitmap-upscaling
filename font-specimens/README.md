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
