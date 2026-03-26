"""
Page optimizer for Shulchan Aruch layout.

The page layout has this vertical structure in the center area:
┌──────────────────────────────┐
│  TITLE ROW (fixed height)    │
├──────────────────────────────┤
│  MAIN TEXT (variable)        │
├──────────────┬───────────────┤
│  TAZ         │ MAGEN AVRAHAM │
├──────────────┴───────────────┤
│  MACHATZIT L │ MACHATZIT R   │
├──────────────┬───────────────┤
│  MISHB. ZAH. │ ESHEL AVR.   │
└──────────────┴───────────────┘

Side columns (Beer HaGolah, Biur HaGra, etc.) run the full page height independently.

Feasibility = center bands stack within page height AND each side column fits within page height.
"""
from dataclasses import dataclass, field
from data import Siman, Seif, SubSeif, CommentaryEntry
from zones import (
    PageGeometry, DEFAULT_GEOMETRY,
    FONT_MAIN, FONT_COMMENTARY_LARGE, FONT_COMMENTARY_SMALL, FONT_SIDE,
)
from measure import measure_height, MeasureConfig

def _to_hebrew_letter(n: int) -> str:
    if n <= 0:
        return str(n)
    letters = "אבגדהוזחטיכלמנסעפצקרשת"
    if n <= len(letters):
        return letters[n - 1]
    return str(n)

def _format_subseif_tag(s: SubSeif) -> str:
    if s.total_fragments <= 1:
        return _to_hebrew_letter(s.seif)
    return f"{_to_hebrew_letter(s.seif)}-{s.fragment}"


def concat_main_text(seifim: list[Seif] | list[SubSeif]) -> str:
    parts = []
    for s in seifim:
        if isinstance(s, SubSeif):
            parts.append(f"({_format_subseif_tag(s)})")
            if s.mechaber:
                parts.append(s.mechaber)
            if s.rema:
                parts.append(f"הגה: {s.rema}")
            if s.translation:
                parts.append(f"\\textenglish{{{s.translation}}}")
            continue

        parts.append(f"({_to_hebrew_letter(s.seif)})")
        parts.append(s.mechaber)
        if s.rema:
            parts.append(f"הגה: {s.rema}")
        if s.translation:
            parts.append(f"\\textenglish{{{s.translation}}}")
    return " ".join(parts)

def concat_commentary(entries: list[CommentaryEntry]) -> str:
    if not entries:
        return ""
    parts = []
    for e in entries:
        parts.append(f"({_to_hebrew_letter(e.seif_katan)}) {e.text}")
    return " ".join(parts)

def split_commentary_half(entries: list[CommentaryEntry]) -> tuple[str, str]:
    if not entries:
        return "", ""
    texts = [f"({_to_hebrew_letter(e.seif_katan)}) {e.text}" for e in entries]
    total_len = sum(len(t) for t in texts)
    half_target = total_len / 2
    left_parts, right_parts = [], []
    running, split_done = 0, False
    for t in texts:
        if not split_done and running + len(t) <= half_target:
            left_parts.append(t)
            running += len(t)
        else:
            split_done = True
            right_parts.append(t)
    return " ".join(left_parts), " ".join(right_parts)

@dataclass
class BandHeights:
    title: float = 36.0
    main_text: float = 0.0
    taz_ma: float = 0.0
    machatzit: float = 0.0
    pri_megadim: float = 0.0
    gap: float = 7.0

    @property
    def total_center_height(self) -> float:
        bands = [self.title, self.main_text]
        if self.taz_ma > 0: bands.append(self.taz_ma)
        if self.machatzit > 0: bands.append(self.machatzit)
        if self.pri_megadim > 0: bands.append(self.pri_megadim)
        num_gaps = len(bands) - 1
        return sum(bands) + num_gaps * self.gap

@dataclass
class PageContent:
    page_num: int
    seif_start: str
    seif_end: str
    zone_texts: dict[str, str] = field(default_factory=dict)
    band_heights: BandHeights = field(default_factory=BandHeights)

@dataclass
class PagePlan:
    siman: int
    pages: list[PageContent] = field(default_factory=list)

@dataclass
class SpreadContent:
    seif_start: str
    seif_end: str
    next_index: int
    core_page: PageContent
    comm_page: PageContent

def check_spread_feasibility(
    siman: Siman,
    start_idx: int,
    end_idx: int,
    geom: PageGeometry,
    config: MeasureConfig | None = None,
) -> tuple[bool, "SpreadContent"]:
    tw = geom.text_width_pt
    th = geom.text_height_pt
    gap = geom.column_gap_pt
    side_width = tw * 0.10
    center_width = tw * 0.80 - 2 * gap
    half_center = (center_width - gap) / 2.0
    pm_left_w = center_width * 0.40 - gap / 2
    pm_right_w = center_width * 0.60 - gap / 2

    # --- Assemble text for all zones ---
    seifim = siman.get_main_text_for_subseif_range(start_idx, end_idx)
    sub_ids = {s.id for s in seifim}
    all_texts: dict[str, str] = {}
    all_texts["main_text"] = concat_main_text(seifim)

    for name in ["taz", "magen_avraham", "mishbetzot_zahav", "eshel_avraham", "beer_hagolah", "biur_hagra", "ateret_zekeinim", "chidushei_rav_akiva_eiger"]:
        entries = siman.get_commentary_for_subseif_ids(name, sub_ids)
        all_texts[name] = concat_commentary(entries)

    machatzit_entries = siman.get_commentary_for_subseif_ids("machatzit_hashekel", sub_ids)
    left_m, right_m = split_commentary_half(machatzit_entries)
    all_texts["machatzit_hashekel_left"] = left_m
    all_texts["machatzit_hashekel_right"] = right_m

    # --- Page 1 (Core): Title + Main Text + Taz + MA ---
    bands1 = BandHeights()
    print(f"      Measuring main_text ({len(all_texts['main_text'])} chars)...")
    bands1.main_text = measure_height(all_texts["main_text"], center_width, FONT_MAIN, config)
    
    print(f"      Measuring taz/ma...")
    h_taz = measure_height(all_texts["taz"], half_center, FONT_COMMENTARY_LARGE, config)
    h_ma = measure_height(all_texts["magen_avraham"], half_center, FONT_COMMENTARY_LARGE, config)
    bands1.taz_ma = max(h_taz, h_ma)

    # Core page only has Title, Main, and Taz/MA
    # We set others to 0 so total_center_height is correct
    bands1.machatzit = 0
    bands1.pri_megadim = 0
    core_fits = bands1.total_center_height <= th

    # --- Page 2 (Commentaries): Machatzit + PM + SideColumns ---
    bands2 = BandHeights()
    bands2.title = 0 # No title on page 2? Or maybe "Continuation"
    bands2.main_text = 0
    bands2.taz_ma = 0
    
    print(f"      Measuring machatzit...")
    h_ml = measure_height(all_texts["machatzit_hashekel_left"], half_center, FONT_COMMENTARY_SMALL, config)
    h_mr = measure_height(all_texts["machatzit_hashekel_right"], half_center, FONT_COMMENTARY_SMALL, config)
    bands2.machatzit = max(h_ml, h_mr)

    print(f"      Measuring pri_megadim...")
    h_mz = measure_height(all_texts["mishbetzot_zahav"], pm_left_w, FONT_COMMENTARY_SMALL, config)
    h_ea = measure_height(all_texts["eshel_avraham"], pm_right_w, FONT_COMMENTARY_SMALL, config)
    bands2.pri_megadim = max(h_mz, h_ea)
    comm_fits = bands2.total_center_height <= th

    # Side columns (only on page 2)
    print(f"      Measuring side columns...")
    h_beer = measure_height(all_texts["beer_hagolah"], side_width, FONT_SIDE, config)
    h_biur = measure_height(all_texts["biur_hagra"], side_width, FONT_SIDE, config)
    left_fits = (h_beer + h_biur + gap) <= th

    h_ateret = measure_height(all_texts["ateret_zekeinim"], side_width, FONT_SIDE, config)
    h_rae = measure_height(all_texts["chidushei_rav_akiva_eiger"], side_width, FONT_SIDE, config)
    right_fits = (h_ateret + h_rae + gap) <= th

    feasible = core_fits and comm_fits and left_fits and right_fits
    print(f"      Feasible: {feasible}")

    # Group texts for each page
    core_texts = {k: all_texts[k] for k in ["main_text", "taz", "magen_avraham"] if k in all_texts}
    comm_texts = {k: all_texts[k] for k in all_texts if k not in ["main_text", "taz", "magen_avraham"]}

    spread = SpreadContent(
        seif_start=seifim[0].id,
        seif_end=seifim[-1].id,
        next_index=end_idx + 1,
        core_page=PageContent(0, seifim[0].id, seifim[-1].id, core_texts, bands1),
        comm_page=PageContent(0, seifim[0].id, seifim[-1].id, comm_texts, bands2)
    )
    return feasible, spread

def optimize_spread(
    siman: Siman,
    start_idx: int,
    geom: PageGeometry = DEFAULT_GEOMETRY,
    config: MeasureConfig | None = None,
) -> SpreadContent:
    max_idx = len(siman.sub_seifim) - 1
    lo, hi = start_idx, max_idx
    best_spread = None
    while lo <= hi:
        mid = (lo + hi) // 2
        feasible, spread = check_spread_feasibility(siman, start_idx, mid, geom, config)
        if feasible:
            best_spread = spread
            lo = mid + 1
        else:
            hi = mid - 1
            
    if best_spread is None:
        # If even one seif doesn't fit, we force it and it will overfill
        _, best_spread = check_spread_feasibility(siman, start_idx, start_idx, geom, config)
    return best_spread

def optimize_siman(
    siman: Siman,
    geom: PageGeometry = DEFAULT_GEOMETRY,
    measure_config: MeasureConfig | None = None,
) -> PagePlan:
    plan = PagePlan(siman=siman.siman)
    current_idx = 0
    page_num = 1
    while current_idx < len(siman.sub_seifim):
        spread = optimize_spread(siman, current_idx, geom, measure_config)
        
        # Add Core page
        spread.core_page.page_num = page_num
        plan.pages.append(spread.core_page)
        
        # Add Commentary page
        spread.comm_page.page_num = page_num + 1
        plan.pages.append(spread.comm_page)
        
        print(f"  Spread {page_num}-{page_num+1}: seifim {spread.seif_start}-{spread.seif_end}")
        print(f"    Core height: {spread.core_page.band_heights.total_center_height:.0f}pt")
        print(f"    Comm height: {spread.comm_page.band_heights.total_center_height:.0f}pt")
        
        current_idx = spread.next_index
        page_num += 2

    return plan
