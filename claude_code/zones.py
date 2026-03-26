"""
Zone definitions for the Shulchan Aruch page layout.

A "zone" is a rectangular area on the page that holds one text stream.
The optimizer fills zones with text and checks if everything fits.

All measurements are in points (1 inch = 72.27 pt).
"""

from dataclasses import dataclass


PT_PER_INCH = 72.27
PT_PER_CM = 28.35


@dataclass
class FontConfig:
    """Font configuration for a zone."""
    size: float        # font size in pt
    leading: float     # line height (baselineskip) in pt
    family: str        # font family name (for TeX)
    chars_per_em: float = 1.8  # approximate characters per em (Hebrew ~1.8)

    @property
    def avg_char_width_pt(self) -> float:
        """Approximate average character width in pt."""
        em_width = self.size
        return em_width / self.chars_per_em

    def estimate_chars_per_line(self, column_width_pt: float) -> float:
        """Estimate how many characters fit on one line at this width."""
        return column_width_pt / self.avg_char_width_pt

    def estimate_lines(self, text: str, column_width_pt: float) -> int:
        """Estimate number of lines this text occupies at this width."""
        if not text or not text.strip():
            return 0
        cpl = self.estimate_chars_per_line(column_width_pt)
        if cpl <= 0:
            return 1
        # Hebrew: count characters (words are short, ~4 chars avg)
        # Add a small factor for word-wrap overhead
        char_count = len(text.replace(" ", ""))
        word_count = len(text.split())
        # Effective character count including inter-word spaces
        effective_chars = char_count + word_count
        lines = max(1, int(effective_chars / cpl) + 1)
        return lines

    def estimate_height_pt(self, text: str, column_width_pt: float) -> float:
        """Estimate the height in points of rendered text."""
        lines = self.estimate_lines(text, column_width_pt)
        return lines * self.leading


@dataclass
class Zone:
    """A rectangular zone on the page."""
    name: str
    x_pt: float         # left edge in pt from left margin
    y_pt: float         # top edge in pt from top of text area
    width_pt: float     # zone width in pt
    max_height_pt: float  # maximum available height in pt
    font: FontConfig
    commentary_name: str | None = None  # maps to Siman field name, None for main text

    def estimate_text_height(self, text: str) -> float:
        """Estimate height needed for this text in this zone."""
        return self.font.estimate_height_pt(text, self.width_pt)


# ============================================================
# Default font configs
# ============================================================

FONT_MAIN = FontConfig(
    size=14.0,
    leading=18.0,
    family="main_font",
    chars_per_em=1.6,  # main text is larger, fewer chars per em
)

FONT_COMMENTARY_LARGE = FontConfig(
    size=11.0,
    leading=14.0,
    family="commentary_font",
    chars_per_em=1.8,
)

FONT_COMMENTARY_SMALL = FontConfig(
    size=9.0,
    leading=11.5,
    family="small_commentary_font",
    chars_per_em=2.0,
)

FONT_SIDE = FontConfig(
    size=8.0,
    leading=10.0,
    family="side_font",
    chars_per_em=2.0,
)


# ============================================================
# Page geometry
# ============================================================

@dataclass
class PageGeometry:
    """Overall page dimensions."""
    page_width_pt: float
    page_height_pt: float
    margin_left_pt: float
    margin_right_pt: float
    margin_top_pt: float
    margin_bottom_pt: float
    column_gap_pt: float  # gap between adjacent zones

    @property
    def text_width_pt(self) -> float:
        return self.page_width_pt - self.margin_left_pt - self.margin_right_pt

    @property
    def text_height_pt(self) -> float:
        return self.page_height_pt - self.margin_top_pt - self.margin_bottom_pt


# Default: A4-ish page similar to standard SA editions
DEFAULT_GEOMETRY = PageGeometry(
    page_width_pt=597.5,    # ~210mm (A4 width)
    page_height_pt=845.0,   # ~297mm (A4 height)
    margin_left_pt=36.0,    # ~0.5in
    margin_right_pt=36.0,
    margin_top_pt=36.0,
    margin_bottom_pt=36.0,
    column_gap_pt=7.0,      # ~2.5mm between columns
)


def build_zones(geom: PageGeometry, main_text_lines: int = 0) -> dict[str, Zone]:
    """
    Build all page zones based on geometry.
    
    The layout is built dynamically based on how much main text there is.
    `main_text_lines` is the estimated line count of the main text,
    which determines where the Taz/MA columns start.
    
    Returns a dict mapping zone names to Zone objects.
    """
    tw = geom.text_width_pt
    th = geom.text_height_pt
    gap = geom.column_gap_pt

    # ── Column widths ──
    side_width = tw * 0.10          # each side column ~10% of text width
    center_width = tw * 0.80 - 2 * gap  # center area ~80%

    # Positions (x from left edge of text area)
    x_left_side = 0.0
    x_center = side_width + gap
    x_right_side = tw - side_width

    # ── Vertical bands ──
    # The main text occupies the top portion of the center area.
    # Estimate main text height (will be refined by optimizer).
    main_height = main_text_lines * FONT_MAIN.leading if main_text_lines > 0 else th * 0.25
    main_height = min(main_height, th * 0.50)  # cap at 50% of page

    # Title row height
    title_height = FONT_MAIN.leading * 2

    # Below main text: Taz | MA
    taz_ma_top = title_height + main_height + gap
    taz_ma_width = (center_width - gap) / 2.0

    # Below Taz/MA: Machatzit HaShekel
    # Allocate remaining space proportionally
    remaining_height = th - taz_ma_top
    machatzit_height = remaining_height * 0.30
    pri_megadim_height = remaining_height * 0.30
    taz_ma_height = remaining_height - machatzit_height - pri_megadim_height - 2 * gap

    machatzit_top = taz_ma_top + taz_ma_height + gap
    pri_megadim_top = machatzit_top + machatzit_height + gap

    # Machatzit: two equal columns
    machatzit_col_width = (center_width - gap) / 2.0

    # Pri Megadim: two unequal columns (Mishbetzot Zahav ~40%, Eshel Avraham ~60%)
    pm_left_width = center_width * 0.40 - gap / 2
    pm_right_width = center_width * 0.60 - gap / 2

    # ── Side columns ──
    # Left side: Beer HaGolah (top half), Biur HaGra (bottom half)
    # With additional commentaries stacked below
    left_side_half = (th - gap) / 2.0

    # Right side: similar stacking
    right_side_third = (th - 2 * gap) / 3.0

    zones = {
        # ── MAIN TEXT ──
        "main_text": Zone(
            name="main_text",
            x_pt=x_center,
            y_pt=title_height,
            width_pt=center_width,
            max_height_pt=main_height,
            font=FONT_MAIN,
            commentary_name=None,  # special handling
        ),

        # ── CORE COMMENTARIES (flanking) ──
        "taz": Zone(
            name="taz",
            x_pt=x_center,
            y_pt=taz_ma_top,
            width_pt=taz_ma_width,
            max_height_pt=taz_ma_height,
            font=FONT_COMMENTARY_LARGE,
            commentary_name="taz",
        ),
        "magen_avraham": Zone(
            name="magen_avraham",
            x_pt=x_center + taz_ma_width + gap,
            y_pt=taz_ma_top,
            width_pt=taz_ma_width,
            max_height_pt=taz_ma_height,
            font=FONT_COMMENTARY_LARGE,
            commentary_name="magen_avraham",
        ),

        # ── BOTTOM COMMENTARIES ──
        "machatzit_hashekel_left": Zone(
            name="machatzit_hashekel_left",
            x_pt=x_center,
            y_pt=machatzit_top,
            width_pt=machatzit_col_width,
            max_height_pt=machatzit_height,
            font=FONT_COMMENTARY_SMALL,
            commentary_name="machatzit_hashekel",
        ),
        "machatzit_hashekel_right": Zone(
            name="machatzit_hashekel_right",
            x_pt=x_center + machatzit_col_width + gap,
            y_pt=machatzit_top,
            width_pt=machatzit_col_width,
            max_height_pt=machatzit_height,
            font=FONT_COMMENTARY_SMALL,
            commentary_name="machatzit_hashekel",
        ),
        "mishbetzot_zahav": Zone(
            name="mishbetzot_zahav",
            x_pt=x_center,
            y_pt=pri_megadim_top,
            width_pt=pm_left_width,
            max_height_pt=pri_megadim_height,
            font=FONT_COMMENTARY_SMALL,
            commentary_name="mishbetzot_zahav",
        ),
        "eshel_avraham": Zone(
            name="eshel_avraham",
            x_pt=x_center + pm_left_width + gap,
            y_pt=pri_megadim_top,
            width_pt=pm_right_width,
            max_height_pt=pri_megadim_height,
            font=FONT_COMMENTARY_SMALL,
            commentary_name="eshel_avraham",
        ),

        # ── LEFT SIDE ──
        "beer_hagolah": Zone(
            name="beer_hagolah",
            x_pt=x_left_side,
            y_pt=0,
            width_pt=side_width,
            max_height_pt=left_side_half,
            font=FONT_SIDE,
            commentary_name="beer_hagolah",
        ),
        "biur_hagra": Zone(
            name="biur_hagra",
            x_pt=x_left_side,
            y_pt=left_side_half + gap,
            width_pt=side_width,
            max_height_pt=left_side_half,
            font=FONT_SIDE,
            commentary_name="biur_hagra",
        ),

        # ── RIGHT SIDE ──
        "ateret_zekeinim": Zone(
            name="ateret_zekeinim",
            x_pt=x_right_side,
            y_pt=0,
            width_pt=side_width,
            max_height_pt=right_side_third,
            font=FONT_SIDE,
            commentary_name="ateret_zekeinim",
        ),
        "chidushei_rav_akiva_eiger": Zone(
            name="chidushei_rav_akiva_eiger",
            x_pt=x_right_side,
            y_pt=right_side_third + gap,
            width_pt=side_width,
            max_height_pt=right_side_third * 2,
            font=FONT_SIDE,
            commentary_name="chidushei_rav_akiva_eiger",
        ),
    }

    return zones
