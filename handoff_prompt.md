# Handoff Prompt: Shulchan Aruch Layout Engine

**Context:**
I am building a custom XeLaTeX-based layout engine for the Shulchan Aruch (Orach Chayim, Siman 1). The goal is to transform the traditional folio into a two-page spread:
- **Page 1 (Core):** Shulchan Aruch Main Text (Mechaber/Rema) flanked by the `Taz` and `Magen Avraham` commentaries.
- **Page 2 (Commentaries):** `Machatzit HaShekel` (2 columns) above `Pri Megadim` (Mishbetzot/Eshel), with side columns for `Beer HaGolah`, `Biur HaGra`, etc.

**Current State:**
1. **Data:** Sefaria v3 API data for Siman 1 is saved in `sefaria/siman_1.json`.
2. **Engine:** A 6-module Python engine in `claude_code/` handles geometry, precise TeX-based height measurement, optimization, and `.tex` generation.
3. **Fonts:** Configured to use `FrankRuehlCLM` (OTF) with `XeLaTeX`.
4. **Layout:** The engine successfully generates a 4-page (2 spreads) PDF, but **Siman 1, Seif 1** is extremely long (~2500pt for core commentaries), causing it to overfill the page.

**The Task for You:**
1. **Implement Seif Splitting:** Refactor `optimizer.py` and `data.py` to support "Sub-Seif" fragments. A single long seif (like Seif 1) must be broken into parts so its commentaries can span multiple spreads.
2. **Handle Interleaved Rema:** Ensure the splitter correctly identifies where the Rema starts/ends within a seif to allow breaking at Rema boundaries.
3. **Refine PDF Layout:** Tune the vertical gaps and separator lines in `tex_gen.py` to match the aesthetic of traditional Hebrew typography.
4. **Translation Integration:** The layout allocates space for translation on Page 1 (currently empty). Implement the ingestion of translation data into the `main_text` zone.

**Files to review:**
- `claude_code/optimizer.py`: Core optimization and feasibility logic.
- `claude_code/data.py`: Data models and JSON parsing.
- `claude_code/tex_gen.py`: LaTeX template and `textpos` placement.
- `claude_code/measure.py`: Measurement caching and TeX backend.

**Running the engine:**
```bash
python main.py sefaria/siman_1.json --output out_spread.tex --compile --measure-backend tex
```
