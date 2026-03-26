# Shulchan Aruch Two-Page Layout Project Handoff

## Goal
The goal is to generate a custom LaTeX template for a two-page spread of the Shulchan Aruch that mimics the classic layout seen in `SA_page_sample.png`, but with a twist. This is for *Orach Chaim, Siman 1 (Hilchos Hashkamat HaBoker)*.

The final output should be a custom LaTeX document using `polyglossia` and `fontspec` for Hebrew and RTL support.

## Source Material Gathered
We have successfully developed a Python script (`fetch_siman_1.py`) and pulled the following texts from the Sefaria API for *Shulchan Aruch, Orach Chaim, Siman 1* into `sefaria/siman_1.json`:
- **Shulchan Arukh (Mechaber & Rema)**: 9 Seifim 
- **Taz**: 8 comments
- **Magen Avraham**: 12 comments
- **Mishbetzot Zahav (Pri Megadim on Taz)**: 1 comment
- **Eshel Avraham (Pri Megadim on Magen Avraham)**: 4 comments
- **Ba'er Heitev**: 14 comments
- **Be'er HaGolah**: 14 comments
- **Bi'ur HaGra**: 15 comments
- **Sha'arei Teshuvah**: 11 comments
- **Ateret Zekeinim**: 5 comments
- **Mishnah Berurah**: 20 comments
- **Chidushei Rabbi Akiva Eiger**: 6 comments

*Note:* Machatzit HaShekel has no comments on Siman 1, so its array is empty. For the layout test, layout placeholders or duplicated text can be used where necessary to fill out visual boxes.

## Layout Requirements

### Page 1 (Hebrew + Translation)
This page features **Hebrew + Translation** in their respective blocks.
- **Top Grey Box:** The section title (e.g., שולחן ערוך אורח חיים סימן א).
- **Center Red Box:** The main text (Mechaber and Rema).
- **Orange Section:** Magen Avraham (wrapped around or below the core text).
- **Yellow Section:** Taz (or another main commentary like Mishnah Berurah, next to Magen Avraham).

### Page 2 (Translations Only / Overflow)
This page features **Translations Only** (use English Lorem Ipsum for the test).
- **Green Section (Top):** Machatzit HaShekel (use placeholder since Siman 1 is empty), formatted as 2 columns.
- **Blue Section (Middle):** Peri Megadim, which is further subdivided horizontally or vertically into two:
  - Eshel Avraham (Purple tones)
  - Mishbetzot Zahav (Purple tones)
- **Pink Side Panels (Left & Right margins):** Smaller commentaries wrapping the main blocks. Include placeholders for:
  - Be'er HaGolah
  - Bi'ur HaGra
  - Chidushei R' Akiva Eiger
  - Ateres Zekinim
  - Ba'er Heitiv
  - Sha'arei Teshuvah

## Technical Considerations
1. The project requires `XeLaTeX` for compilation.
2. Hebrew fonts available in `D:\Projects\ProjectAryehPress\Seforim\Fonts` include `FrankRuhlLibre`, `FrankRuehlCLM`, etc. 
3. The layout goes far beyond a standard column layout. It requires advanced box manipulation, `paracol`, `minipages`, or `tcolorbox` to achieve the distinct sections and side panels.

## Next Steps for Claude Code
1. Read the `SA_page_sample.png` to understand the visual hierarchy.
2. Parse `sefaria/siman_1.json` to extract the Hebrew text arrays.
3. Develop a `latex` document (e.g., `sa_layout_test.tex`) that implements this two-page structure using the real Hebrew text for Page 1.
4. Use Lorem Ipsum English for the translation on Page 1 and all of Page 2.
5. Compile the PDF to verify the layout boxes and column flow.
