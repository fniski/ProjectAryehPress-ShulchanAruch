"""
LaTeX generator for Shulchan Aruch pages.

Uses textpos for absolute zone placement. Each page is manually
constructed — the optimizer determines content, this renders it.
"""

from pathlib import Path
from zones import PageGeometry, DEFAULT_GEOMETRY, FONT_MAIN, FONT_COMMENTARY_LARGE, FONT_COMMENTARY_SMALL, FONT_SIDE
from optimizer import PagePlan, PageContent, BandHeights


ZONE_HEADERS = {
    "taz": "טורי זהב",
    "magen_avraham": "מגן אברהם",
    "machatzit_hashekel_left": "מחצית השקל",
    "machatzit_hashekel_right": "מחצית השקל",
    "mishbetzot_zahav": "משבצות זהב",
    "eshel_avraham": "אשל אברהם",
    "beer_hagolah": "באר הגולה",
    "biur_hagra": "ביאור הגר\"א",
    "ateret_zekeinim": "עטרת זקנים",
    "chidushei_rav_akiva_eiger": "חידושי רע\"א",
}


def _preamble(geom: PageGeometry) -> str:
    pw = f"{geom.page_width_pt}pt"
    ph = f"{geom.page_height_pt}pt"
    ml = f"{geom.margin_left_pt}pt"
    mr = f"{geom.margin_right_pt}pt"
    mt = f"{geom.margin_top_pt}pt"
    mb = f"{geom.margin_bottom_pt}pt"

    return rf"""\documentclass[11pt]{{article}}

\usepackage[
  paperwidth={pw}, paperheight={ph},
  left={ml}, right={mr}, top={mt}, bottom={mb},
]{{geometry}}

\usepackage[absolute,overlay]{{textpos}}
\setlength{{\TPHorizModule}}{{1pt}}
\setlength{{\TPVertModule}}{{1pt}}

\usepackage{{fontspec}}
\usepackage{{polyglossia}}
\setdefaultlanguage{{hebrew}}

\pagenumbering{{gobble}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{2pt}}
\tolerance=9999
\emergencystretch=3em
\hyphenpenalty=10000

% ── Hebrew fonts configuration ──
\setmainfont[
  Path=D:/Projects/ProjectAryehPress/Seforim/Fonts/,
  Extension=.otf,
  UprightFont=*-Medium,
  BoldFont=*-Bold,
  ItalicFont=*-MediumOblique,
  BoldItalicFont=*-BoldOblique
]{{FrankRuehlCLM}}

\newfontfamily\hebrewfont[
  Path=D:/Projects/ProjectAryehPress/Seforim/Fonts/,
  Extension=.otf,
  UprightFont=*-Medium,
  BoldFont=*-Bold,
  ItalicFont=*-MediumOblique,
  BoldItalicFont=*-BoldOblique
]{{FrankRuehlCLM}}

% Zone placement command
\newcommand{{\placezone}}[6]{{%
  \begin{{textblock*}}{{#3pt}}(#1pt, #2pt)%
    \fontsize{{#4}}{{#5}}\selectfont%
    #6%
  \end{{textblock*}}%
}}

% Zone with header
\newcommand{{\placezoneh}}[7]{{%
  \begin{{textblock*}}{{#3pt}}(#1pt, #2pt)%
    \fontsize{{#4}}{{#5}}\selectfont%
    \begin{{center}}\textbf{{#6}}\end{{center}}%
    \vspace{{-4pt}}\rule{{\linewidth}}{{0.3pt}}\vspace{{2pt}}%
    #7%
  \end{{textblock*}}%
}}

% Separator line
\newcommand{{\sepline}}[3]{{%
  \begin{{textblock*}}{{#3pt}}(#1pt, #2pt)%
    \rule{{\linewidth}}{{0.3pt}}%
  \end{{textblock*}}%
}}

\begin{{document}}
"""


def _escape_tex(text: str) -> str:
    for old, new in [("#", r"\#"), ("$", r"\$"), ("%", r"\%"),
                     ("&", r"\&"), ("_", r"\_"), ("~", r"\textasciitilde{}")]:
        text = text.replace(old, new)
    return text


def _to_hebrew_gematria(n: int) -> str:
    if n <= 0:
        return str(n)
    result = ""
    if n >= 100:
        result += "קרשת"[(n // 100) - 1]
        n %= 100
    if n == 15:
        return result + "ט״ו"
    if n == 16:
        return result + "ט״ז"
    tens = " יכלמנסעפצ"
    # Use 10pt Frank Ruehl CLM (or similar) as the default
    return f"""\\documentclass[10pt]{{article}}
\\usepackage[paperwidth={geom.width_pt}pt, paperheight={geom.height_pt}pt, margin=0pt]{{geometry}}
\\usepackage[absolute,overlay]{{textpos}}
\\usepackage{{fontspec}}
\\usepackage{{polyglossia}}
\\setdefaultlanguage{{hebrew}}
\\setotherlanguage{{english}}
\\usepackage{{xcolor}}

\\newfontfamily\\hebrewfont[
    Path=D:/Projects/ProjectAryehPress/Seforim/Fonts/,
    Extension=.otf,
    BoldFont=FrankRuehlCLM-Bold,
    ItalicFont=FrankRuehlCLM-Medium
]{{FrankRuehlCLM-Medium}}

\\newfontfamily\\mainfont[
    Path=D:/Projects/ProjectAryehPress/Seforim/Fonts/,
    Extension=.otf
]{{FrankRuehlCLM-Medium}}

\\newfontfamily\\sidefont[
    Path=D:/Projects/ProjectAryehPress/Seforim/Fonts/,
    Extension=.otf
]{{FrankRuehlCLM-Medium}}

\\setlength{{\\TPHorizModule}}{{1pt}}
\\setlength{{\\TPVertModule}}{{1pt}}
\\textblockorigin{{0pt}}{{0pt}}

% Custom command for English
\\newcommand{{\\textenglish}}[1]{{\\begin{{otherlanguage}}{{english}}#1\\end{{otherlanguage}}}}

\\parindent=0pt
\\parskip=2pt
"""

def _render_page(page: PageContent, geom: PageGeometry) -> str:
    is_core = (page.page_num % 2 != 0)
    lines = []
    lines.append(f"\\newpage % Page {page.page_num} ({'Core' if is_core else 'Commentary'})")
    
    tw = geom.text_width_pt
    th = geom.text_height_pt
    top = geom.margin_top_pt
    left = geom.margin_left_pt
    gap = geom.column_gap_pt
    
    side_w = tw * 0.10
    center_w = tw * 0.80 - 2 * gap
    half_center = (center_w - gap) / 2.0
    pm_left_w = center_w * 0.40 - gap / 2
    pm_right_w = center_w * 0.60 - gap / 2


    b = page.band_heights
    is_core = (page.page_num % 2 != 0)
    tex = ""

    # ── Title (Only on Core page) ──
    current_y = my
    if is_core:
        tex += (f"\\begin{{textblock*}}{{{tw}pt}}({mx}pt, {current_y}pt)\n"
                f"  \\begin{{center}}\\Large\\textbf{{אורח חיים סימן "
                f"{_to_hebrew_gematria(siman_num)}"
                f" — סעיפים {_to_hebrew_gematria(page.seif_start)}"
                f"–{_to_hebrew_gematria(page.seif_end)}"
                f"}}\\end{{center}}\n"
                f"  \\rule{{\\linewidth}}{{0.5pt}}\n"
                f"\\end{{textblock*}}\n\n")
        current_y += b.title + b.gap
    else:
        # On commentary page, maybe a smaller header or just start lower
        tex += (f"\\begin{{textblock*}}{{{tw}pt}}({mx}pt, {current_y}pt)\n"
                f"  \\begin{{center}}\\small (המשך סימן {_to_hebrew_gematria(siman_num)})\\end{{center}}\n"
                f"\\end{{textblock*}}\n\n")
        current_y += 20 + b.gap

    # ── Main text (Core only) ──
    main_txt = _escape_tex(page.zone_texts.get("main_text", ""))
    if main_txt.strip():
        tex += (f"\\placezone{{{x_center:.1f}}}{{{current_y:.1f}}}"
                f"{{{center_w:.1f}}}{{{FONT_MAIN.size}}}{{{FONT_MAIN.leading}}}"
                f"{{{main_txt}}}\n\n")
        current_y += b.main_text + b.gap
        # Separator after main text
        tex += f"\\sepline{{{x_center:.1f}}}{{{current_y - b.gap/2:.1f}}}{{{center_w:.1f}}}\n"

    # ── Taz | Magen Avraham (Core only) ──
    if "taz" in page.zone_texts or "magen_avraham" in page.zone_texts:
        y_row = current_y
        for name, x, w in [("taz", x_center, half_c),
                            ("magen_avraham", x_center + half_c + gap, half_c)]:
            txt = _escape_tex(page.zone_texts.get(name, ""))
            if txt.strip():
                header = ZONE_HEADERS[name]
                tex += (f"\\placezoneh{{{x:.1f}}}{{{y_row:.1f}}}"
                        f"{{{w:.1f}}}{{{FONT_COMMENTARY_LARGE.size}}}"
                        f"{{{FONT_COMMENTARY_LARGE.leading}}}"
                        f"{{{header}}}{{{txt}}}\n\n")
        current_y += b.taz_ma + b.gap

    # ── Machatzit HaShekel (Commentary page) ──
    if "machatzit_hashekel_left" in page.zone_texts or "machatzit_hashekel_right" in page.zone_texts:
        y_row = current_y
        for suffix, x, w in [("left", x_center, half_c),
                               ("right", x_center + half_c + gap, half_c)]:
            txt = _escape_tex(page.zone_texts.get(f"machatzit_hashekel_{suffix}", ""))
            if txt.strip():
                header = ZONE_HEADERS[f"machatzit_hashekel_{suffix}"]
                tex += (f"\\placezoneh{{{x:.1f}}}{{{y_row:.1f}}}"
                        f"{{{w:.1f}}}{{{FONT_COMMENTARY_SMALL.size}}}"
                        f"{{{FONT_COMMENTARY_SMALL.leading}}}"
                        f"{{{header}}}{{{txt}}}\n\n")
        current_y += b.machatzit + b.gap
        tex += f"\\sepline{{{x_center:.1f}}}{{{current_y - b.gap/2:.1f}}}{{{center_w:.1f}}}\n"

    # ── Pri Megadim (Commentary page) ──
    if "mishbetzot_zahav" in page.zone_texts or "eshel_avraham" in page.zone_texts:
        y_row = current_y
        for name, x, w in [("mishbetzot_zahav", x_center, pm_left_w),
                             ("eshel_avraham", x_center + pm_left_w + gap, pm_right_w)]:
            txt = _escape_tex(page.zone_texts.get(name, ""))
            if txt.strip():
                header = ZONE_HEADERS[name]
                tex += (f"\\placezoneh{{{x:.1f}}}{{{y_row:.1f}}}"
                        f"{{{w:.1f}}}{{{FONT_COMMENTARY_SMALL.size}}}"
                        f"{{{FONT_COMMENTARY_SMALL.leading}}}"
                        f"{{{header}}}{{{txt}}}\n\n")
        current_y += b.pri_megadim + b.gap

    # ── Side columns (Commentary page) ──
    if not is_core:
        # Left side: Beer HaGolah + Biur HaGra
        y_side = my + 30
        for name in ["beer_hagolah", "biur_hagra"]:
            txt = _escape_tex(page.zone_texts.get(name, ""))
            if txt.strip():
                header = ZONE_HEADERS[name]
                tex += (f"\\placezoneh{{{x_left_side:.1f}}}{{{y_side:.1f}}}"
                        f"{{{side_w:.1f}}}{{{FONT_SIDE.size}}}{{{FONT_SIDE.leading}}}"
                        f"{{{header}}}{{{txt}}}\n\n")
                # Estimate height for stacking side commentary
                h = FONT_SIDE.estimate_height_pt(page.zone_texts.get(name, ""), side_w)
                y_side += h + gap + 25 

        # Right side: Ateret Zekeinim + Chidushei RAE
        y_side = my + 30
        for name in ["ateret_zekeinim", "chidushei_rav_akiva_eiger"]:
            txt = _escape_tex(page.zone_texts.get(name, ""))
            if txt.strip():
                header = ZONE_HEADERS[name]
                tex += (f"\\placezoneh{{{x_right_side:.1f}}}{{{y_side:.1f}}}"
                        f"{{{side_w:.1f}}}{{{FONT_SIDE.size}}}{{{FONT_SIDE.leading}}}"
                        f"{{{header}}}{{{txt}}}\n\n")
                h = FONT_SIDE.estimate_height_pt(page.zone_texts.get(name, ""), side_w)
                y_side += h + gap + 25

    return tex

    return tex


def generate_tex(
    plan: PagePlan,
    geom: PageGeometry = DEFAULT_GEOMETRY,
    font_dir: str = "",
    output_path: str = "output.tex",
) -> str:
    tex = _preamble(geom)
    for i, page in enumerate(plan.pages):
        tex += f"% ════ Page {page.page_num} (seifim {page.seif_start}-{page.seif_end}) ════\n"
        tex += _render_page(page, geom, plan.siman)
        if i < len(plan.pages) - 1:
            tex += "\\newpage\n\n"
    tex += r"\end{document}" + "\n"
    Path(output_path).write_text(tex, encoding="utf-8")
    print(f"  Wrote {output_path}")
    return tex
