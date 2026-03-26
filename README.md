# Shulchan Aruch Layout Engine

A custom XeLaTeX-based layout engine for the Shulchan Aruch, transforming traditional folio pages into a structured two-page spread.

## Features
- **Two-Page Spread**: Split core text (Mechaber/Rema/Taz/MA) and commentaries (Machatzit/PM/Side) across facing pages.
- **Sefaria Integration**: Fetches Hebrew text and commentaries via Sefaria v3 API.
- **Precise Layout**: Uses `XeLaTeX` with `textpos` for absolute positioning and `FrankRuehlCLM` fonts.
- **Optimization Loop**: Binary searches for the maximum seifim that fit per spread using precise TeX-based height measurement.

## Project Structure
- `data.py`: Data models and Sefaria JSON parsing.
- `zones.py`: Page geometry and font configurations.
- `measure.py`: Text height measurement (Heuristic + XeLaTeX).
- `optimizer.py`: Layout optimization and spread feasibility logic.
- `tex_gen.py`: LaTeX generation for `textpos`.
- `main.py`: CLI entry point.

## Running
```bash
python main.py sefaria/siman_1.json --output out.tex --compile --measure-backend tex
```

## Known Issues / Next Steps
- **Seif Splitting**: Very long seifim (like Siman 1, Seif 1) with massive commentaries currently exceed page limits. Needs a mechanism to split single seifim into sub-fragments.
- **Translation**: Space allocated in layout but text ingestion yet to be implemented.
