# Shulchan Aruch Typesetter

Generates PDFs with page layouts similar to the printed Shulchan Aruch,
with the Mechaber, Rema, and surrounding commentaries arranged in their
traditional zone layout.

## How It Works

1. **Input**: A JSON file containing all text streams for a siman (main text + commentaries),
   keyed by seif number.

2. **Optimizer**: Binary-searches over seif counts to find how many seifim fit on each page,
   given that all commentary text for those seifim must fit in its designated zone.

3. **TeX Generator**: Produces a `.tex` file with absolute positioning (via `textpos`)
   for each zone on each page.

4. **Compilation**: The `.tex` file is compiled to PDF using XeLaTeX or Tectonic.

## Page Layout

```
┌─────────┬──────────────────────────────────────┬─────────┐
│ Beer    │          MAIN SA TEXT                 │ Ateret  │
│ HaGolah │       (Mechaber + Rema)              │ Zekeinim│
│         │       large font, wide               │         │
├─────────┤                                      ├─────────┤
│ Biur    ├──────────────────┬───────────────────┤ Chid.   │
│ HaGra   │     TAZ          │  MAGEN AVRAHAM    │ RAE     │
│         │                  │                   │         │
├─────────┴──────────────────┴───────────────────┴─────────┤
│      MACHATZIT HASHEKEL (two equal columns)              │
├──────────────────┬───────────────────────────────────────┤
│  MISHBETZOT      │         ESHEL AVRAHAM                 │
│  ZAHAV           │         (Pri Megadim)                  │
└──────────────────┴───────────────────────────────────────┘
```

## Requirements

- Python 3.10+
- XeLaTeX or [Tectonic](https://tectonic-typesetting.github.io/) for PDF compilation
- Hebrew fonts (the system will use whatever Hebrew font is available)

## Quick Start

```bash
# 1. Run with the sample data
python main.py sample_siman_1.json --output out.tex --debug

# 2. Compile to PDF (requires xelatex or tectonic)
python main.py sample_siman_1.json --output out.tex --compile

# 3. Or compile manually
xelatex out.tex
```

## Input JSON Format

```json
{
  "siman": 1,
  "sefer": "Orach Chayim",
  "main_text": [
    {
      "seif": 1,
      "mechaber": "Hebrew text...",
      "rema": "Hebrew text or null"
    }
  ],
  "taz": [
    {
      "seif_katan": 1,
      "on_seif": 1,
      "text": "Hebrew text..."
    }
  ],
  "magen_avraham": [...],
  "machatzit_hashekel": [...],
  "mishbetzot_zahav": [...],
  "eshel_avraham": [...],
  "beer_hagolah": [...],
  "biur_hagra": [...],
  "ateret_zekeinim": [...],
  "chidushei_rav_akiva_eiger": [...]
}
```

The critical field is `on_seif` — it links each commentary entry to the
seif of the Shulchan Aruch it comments on. This is the synchronization
constraint that the optimizer uses.

## Architecture

```
main.py          Entry point, CLI
data.py          JSON loading, data models
zones.py         Page geometry, zone definitions, font configs
measure.py       Text height measurement (heuristic + TeX backends)
optimizer.py     Page optimization (binary search over seif counts)
tex_gen.py       LaTeX generation with absolute positioning
```

## Customization

### Fonts

Edit the font definitions in `tex_gen.py` (`_preamble` function) to point
to your Hebrew font files. You need:

- A main text font (large, for Mechaber/Rema)
- A commentary font (medium, for Taz/MA)
- A small font (for bottom commentaries)
- A side font (small, for margin commentaries)

### Page Geometry

Edit `zones.py` to adjust page size, margins, and zone proportions.

### Measurement Accuracy

The default heuristic measurement estimates text height from character
counts. For more precise results:

```bash
python main.py siman_1.json --measure-backend tex
```

This compiles test TeX documents to measure actual rendered heights,
similar to the Talmudifier approach. It's slower but more accurate.

## How the Optimizer Works

The core problem: given a siman with N seifim, determine which seifim
go on each page such that ALL commentary text for those seifim fits
in the designated zones.

Algorithm:
1. Start at seif 1
2. Binary search: what's the maximum seif_end such that all zone
   heights are within bounds?
3. For each candidate seif_end, measure the text height of every
   zone (main text, Taz, MA, etc.) at its designated width
4. If all zones fit → try more seifim. If any overflows → try fewer.
5. Lock in the page, advance to the next seif, repeat.

This is conceptually similar to the Talmudifier's approach but extended
to handle 10+ independent text zones instead of 3.
