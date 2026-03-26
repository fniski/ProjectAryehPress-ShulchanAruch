"""
LaTeX generator for Shulchan Aruch pages.

Uses textpos for absolute zone placement. Each page is manually
constructed — the optimizer determines content, this renders it.
"""

from pathlib import Path
from zones import PageGeometry, DEFAULT_GEOMETRY, FONT_MAIN, FONT_COMMENTARY_LARGE, FONT_COMMENTARY_SMALL, FONT_SIDE
from optimizer import PagePlan, PageContent

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

def _to_hebrew_gematria(n: int) -> str:
    """Convert number to Hebrew gematria (simplified)."""
    if n <= 0: return str(n)
    thousands = n // 1000
    n %= 1000
    res = "'" * thousands
    
    hundreds_chars = " קרשת"
    if n >= 400:
        res += "ת" * (n // 400)
        n %= 400
    if n >= 100:
        res += hundreds_chars[n // 100]
        n %= 100
        
    if n == 15: return res + "טו"
    if n == 16: return res + "טז"
    
    tens_chars = " יכלמנסעפצ"
    if n >= 10:
        res += tens_chars[n // 10]
        n %= 10
        
    ones_chars = " אבגדהוזחט"
    if n > 0:
        res += ones_chars[n]
        
    return res

def _escape_tex(text: str) -> str:
    for old, new in [("#", r"\#"), ("$", r"\$"), ("%", r"\%"),
                     ("&", r"\&"), ("_", r"\_"), ("~", r"\textasciitilde{}")]:
        text = text.replace(old, new)
    return text

def _preamble(geom: PageGeometry, font_dir: str = "") -> str:
    pw = f"{geom.page_width_pt}pt"
    ph = f"{geom.page_height_pt}pt"
    ml = f"{geom.margin_left_pt}pt"
    mr = f"{geom.margin_right_pt}pt"
    mt = f"{geom.margin_top_pt}pt"
    mb = f"{geom.margin_bottom_pt}pt"
    
    fpath = font_dir.replace("\\", "/") if font_dir else "D:/Projects/ProjectAryehPress/Seforim/Fonts/"
    if not fpath.endswith("/"): fpath += "/"

    return rf"""\documentclass[11pt]{{article}}
\usepackage[paperwidth={pw}, paperheight={ph}, left={ml}, right={mr}, top={mt}, bottom={mb}]{{geometry}}
\usepackage[absolute,overlay]{{textpos}}
\setlength{{\TPHorizModule}}{{1pt}}
\setlength{{\TPVertModule}}{{1pt}}
\usepackage{{fontspec}}
\usepackage{{polyglossia}}
\setdefaultlanguage{{hebrew}}
\setotherlanguage{{english}}
\pagenumbering{{gobble}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{2pt}}

\setmainfont[Path={fpath}, Extension=.otf, UprightFont=*-Medium, BoldFont=*-Bold]{{FrankRuehlCLM}}
\newfontfamily\hebrewfont[Path={fpath}, Extension=.otf, UprightFont=*-Medium, BoldFont=*-Bold]{{FrankRuehlCLM}}
\newfontfamily\englishfont{{Arial}}

\newcommand{{\placezone}}[6]{{%
  \begin{{textblock*}}{{#3pt}}(#1pt, #2pt)%
    \fontsize{{#4}}{{#5}}\selectfont%
    #6%
  \end{{textblock*}}%
}}

\newcommand{{\placezoneh}}[7]{{%
  \begin{{textblock*}}{{#3pt}}(#1pt, #2pt)%
    \fontsize{{#4}}{{#5}}\selectfont%
    \begin{{center}}\textbf{{#6}}\end{{center}}%
    \vspace{{-4pt}}\rule{{\linewidth}}{{0.3pt}}\vspace{{2pt}}%
    #7%
  \end{{textblock*}}%
}}

\newcommand{{\sepline}}[3]{{%
  \begin{{textblock*}}{{#3pt}}(#1pt, #2pt)%
    \rule{{\linewidth}}{{0.3pt}}%
  \end{{textblock*}}%
}}

\begin{{document}}
"""

def _render_page(page: PageContent, geom: PageGeometry, siman_num: int) -> str:
    is_core = (page.page_num % 2 != 0)
    tex = f"\\newpage % Page {page.page_num} ({'Core' if is_core else 'Commentary'})\n"
    
    tw = geom.text_width_pt
    mx = 0 # Relative to textblockorigin which is margins
    my = 0
    
    gap = geom.column_gap_pt
    side_w = tw * 0.10
    center_w = tw * 0.80 - 2 * gap
    half_c = (center_w - gap) / 2.0
    pm_left_w = center_w * 0.40 - gap/2
    pm_right_w = center_w * 0.60 - gap/2
    
    x_left_side = 0
    x_center = side_w + gap
    x_right_side = side_w + gap + center_w + gap
    
    b = page.band_heights
    current_y = my

    # Header
    if is_core:
        start_label = page.seif_start_label if hasattr(page, 'seif_start_label') else str(page.seif_start)
        end_label = page.seif_end_label if hasattr(page, 'seif_end_label') else str(page.seif_end)
        tex += (f"\\begin{{textblock*}}{{{tw}pt}}({mx}pt, {current_y}pt)\n"
                f"  \\begin{{center}}\\Large\\textbf{{אורח חיים סימן "
                f"{_to_hebrew_gematria(siman_num)}"
                f" --- סעיפים {start_label}--{end_label}}}\\end{{center}}\n"
                f"  \\rule{{\\linewidth}}{{0.5pt}}\n"
                f"\\end{{textblock*}}\n\n")
        current_y += b.title + b.gap
    else:
        tex += (f"\\begin{{textblock*}}{{{tw}pt}}({mx}pt, {current_y}pt)\n"
                f"  \\begin{{center}}\\small (המשך סימן {_to_hebrew_gematria(siman_num)})\\end{{center}}\n"
                f"\\end{{textblock*}}\n\n")
        current_y += 20 + b.gap

    # Core zones
    if is_core:
        # Main text
        main_txt = _escape_tex(page.zone_texts.get("main_text", ""))
        if main_txt.strip():
            tex += (f"\\placezone{{{x_center:.1f}}}{{{current_y:.1f}}}"
                    f"{{{center_w:.1f}}}{{{FONT_MAIN.size}}}{{{FONT_MAIN.leading}}}"
                    f"{{{main_txt}}}\n\n")
            current_y += b.main_text + b.gap
            tex += f"\\sepline{{{x_center:.1f}}}{{{current_y - b.gap/2:.1f}}}{{{center_w:.1f}}}\n"

        # Taz | MA
        if "taz" in page.zone_texts or "magen_avraham" in page.zone_texts:
            y_row = current_y
            for name, x, w in [("taz", x_center, half_c), ("magen_avraham", x_center + half_c + gap, half_c)]:
                txt = _escape_tex(page.zone_texts.get(name, ""))
                if txt.strip():
                    header = ZONE_HEADERS[name]
                    tex += (f"\\placezoneh{{{x:.1f}}}{{{y_row:.1f}}}"
                            f"{{{w:.1f}}}{{{FONT_COMMENTARY_LARGE.size}}}"
                            f"{{{FONT_COMMENTARY_LARGE.leading}}}"
                            f"{{{header}}}{{{txt}}}\n\n")
            current_y += b.taz_ma + b.gap
    else:
        # Commentary page zones
        # Machatzit
        if "machatzit_hashekel_left" in page.zone_texts or "machatzit_hashekel_right" in page.zone_texts:
            y_row = current_y
            for suffix, x, w in [("left", x_center, half_c), ("right", x_center + half_c + gap, half_c)]:
                txt = _escape_tex(page.zone_texts.get(f"machatzit_hashekel_{suffix}", ""))
                if txt.strip():
                    header = ZONE_HEADERS[f"machatzit_hashekel_{suffix}"]
                    tex += (f"\\placezoneh{{{x:.1f}}}{{{y_row:.1f}}}"
                            f"{{{w:.1f}}}{{{FONT_COMMENTARY_SMALL.size}}}"
                            f"{{{FONT_COMMENTARY_SMALL.leading}}}"
                            f"{{{header}}}{{{txt}}}\n\n")
            current_y += b.machatzit + b.gap
            tex += f"\\sepline{{{x_center:.1f}}}{{{current_y - b.gap/2:.1f}}}{{{center_w:.1f}}}\n"

        # Pri Megadim
        if "mishbetzot_zahav" in page.zone_texts or "eshel_avraham" in page.zone_texts:
            y_row = current_y
            for name, x, w in [("mishbetzot_zahav", x_center, pm_left_w), ("eshel_avraham", x_center + pm_left_w + gap, pm_right_w)]:
                txt = _escape_tex(page.zone_texts.get(name, ""))
                if txt.strip():
                    header = ZONE_HEADERS[name]
                    tex += (f"\\placezoneh{{{x:.1f}}}{{{y_row:.1f}}}"
                            f"{{{w:.1f}}}{{{FONT_COMMENTARY_SMALL.size}}}"
                            f"{{{FONT_COMMENTARY_SMALL.leading}}}"
                            f"{{{header}}}{{{txt}}}\n\n")
            current_y += b.pri_megadim + b.gap

        # Side columns
        # Left side
        y_side = 30
        for name in ["beer_hagolah", "biur_hagra"]:
            txt = _escape_tex(page.zone_texts.get(name, ""))
            if txt.strip():
                header = ZONE_HEADERS[name]
                tex += (f"\\placezoneh{{{x_left_side:.1f}}}{{{y_side:.1f}}}"
                        f"{{{side_w:.1f}}}{{{FONT_SIDE.size}}}{{{FONT_SIDE.leading}}}"
                        f"{{{header}}}{{{txt}}}\n\n")
                h = FONT_SIDE.estimate_height_pt(txt, side_w)
                y_side += h + 25
        
        # Right side
        y_side = 30
        for name in ["ateret_zekeinim", "chidushei_rav_akiva_eiger"]:
            txt = _escape_tex(page.zone_texts.get(name, ""))
            if txt.strip():
                header = ZONE_HEADERS[name]
                tex += (f"\\placezoneh{{{x_right_side:.1f}}}{{{y_side:.1f}}}"
                        f"{{{side_w:.1f}}}{{{FONT_SIDE.size}}}{{{FONT_SIDE.leading}}}"
                        f"{{{header}}}{{{txt}}}\n\n")
                h = FONT_SIDE.estimate_height_pt(txt, side_w)
                y_side += h + 25

    return tex

def generate_tex(plan: PagePlan, geom: PageGeometry = DEFAULT_GEOMETRY, font_dir: str = "", output_path: str = "output.tex") -> str:
    tex = _preamble(geom, font_dir)
    for page in plan.pages:
        tex += _render_page(page, geom, plan.siman)
    
    tex += "\\end{document}\n"
    
    if output_path:
        Path(output_path).write_text(tex, encoding="utf-8")
        print(f"  Wrote {output_path}")
    
    return tex
