"""
Text height measurement.

Provides two backends:
1. Heuristic: fast character-count-based estimation (default)
2. TeX: precise measurement by compiling a test document (slower but accurate)

The heuristic backend is used for the initial prototype.
The TeX backend can be swapped in once fonts are configured.
"""

import subprocess
import tempfile
import struct
from pathlib import Path
from dataclasses import dataclass

from zones import FontConfig


# ============================================================
# Heuristic measurement (fast, approximate)
# ============================================================

def measure_height_heuristic(
    text: str,
    width_pt: float,
    font: FontConfig,
) -> float:
    """
    Estimate the rendered height of `text` in points.
    
    This is a rough heuristic based on character count and average
    character width. Good enough for the optimization loop's initial
    guess, but should be replaced with TeX-based measurement for
    final output.
    """
    if not text or not text.strip():
        return 0.0

    lines = font.estimate_lines(text, width_pt)
    return lines * font.leading


def measure_lines_heuristic(
    text: str,
    width_pt: float,
    font: FontConfig,
) -> int:
    """Estimate the number of lines."""
    if not text or not text.strip():
        return 0
    return font.estimate_lines(text, width_pt)


# ============================================================
# TeX-based measurement (slow, precise)
# ============================================================

def _build_measurement_tex(
    text: str,
    width_pt: float,
    font_size: float,
    leading: float,
    font_dir: str = "",
    font_file: str = "",
) -> str:
    """
    Build a minimal TeX document that renders `text` in a parbox
    of the given width. We compile this to XDV and count the lines.
    """
    preamble = r"""
\documentclass[11pt]{article}
\usepackage[a4paper, margin=1in]{geometry}
\usepackage{fontspec}
\usepackage{polyglossia}
\setdefaultlanguage{hebrew}
\pagenumbering{gobble}
\newfontfamily\measurefont[
  Path=D:/Projects/ProjectAryehPress/Seforim/Fonts/,
  Extension=.otf,
  UprightFont=*-Medium,
  BoldFont=*-Bold,
  ItalicFont=*-MediumOblique,
  BoldItalicFont=*-BoldOblique
]{FrankRuehlCLM}
\measurefont
"""

    body = f"""
\\begin{{document}}
\\fontsize{{{font_size}}}{{{leading}}}\\selectfont
\\parbox{{{width_pt}pt}}{{
{text}
}}
\\end{{document}}
"""
    return preamble + body


def measure_height_tex(
    text: str,
    width_pt: float,
    font: FontConfig,
    font_dir: str = "",
    font_file: str = "",
) -> float:
    """
    Precisely measure text height by compiling a TeX document.
    
    Requires `tectonic` to be installed and accessible.
    Returns height in points.
    
    This is significantly slower than heuristic measurement but
    gives exact results.
    """
    tex_source = _build_measurement_tex(
        text, width_pt, font.size, font.leading, font_dir, font_file
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = Path(tmpdir) / "measure.tex"
        tex_path.write_text(tex_source, encoding="utf-8")

        try:
            result = subprocess.run(
                ["xelatex", "-interaction=nonstopmode", "-no-pdf", "measure.tex"],
                capture_output=True,
                timeout=30,
                cwd=tmpdir,
            )
            if result.returncode != 0:
                # Fall back to heuristic
                return measure_height_heuristic(text, width_pt, font)

            xdv_path = Path(tmpdir) / "measure.xdv"
            if not xdv_path.exists():
                return measure_height_heuristic(text, width_pt, font)

            # Parse XDV to count lines
            lines = _count_xdv_lines(xdv_path.read_bytes())
            if lines and lines[0] > 0:
                return lines[0] * font.leading
            else:
                return measure_height_heuristic(text, width_pt, font)

        except (subprocess.TimeoutExpired, FileNotFoundError):
            # tectonic not installed or timed out
            return measure_height_heuristic(text, width_pt, font)


def _count_xdv_lines(data: bytes) -> list[int]:
    """
    Minimal XDV parser that counts line breaks per page.
    Adapted from Talmudifier's XDV parser.
    """
    pos = 0
    num_lines_per_page = []
    num_lines = 1

    def read_u8():
        nonlocal pos
        if pos >= len(data):
            return None
        v = data[pos]
        pos += 1
        return v

    def advance(n):
        nonlocal pos
        pos += n

    # Skip preamble
    op = read_u8()
    if op == 247:  # PRE
        read_u8()  # version
        advance(12)  # num + den + mag
        k = read_u8()
        advance(k)  # comment

    while pos < len(data) - 1:
        op = read_u8()
        if op is None:
            break

        if op <= 127:  # set char
            pass
        elif op <= 131:  # set
            advance(4 - (131 - op))
        elif op == 132:  # set rule
            advance(8)
        elif op <= 136:  # put
            advance(4 - (136 - op))
        elif op == 137:  # put rule
            advance(8)
        elif op == 138:  # nop
            pass
        elif op == 139:  # bop
            advance(44)
        elif op == 140:  # eop
            num_lines_per_page.append(num_lines)
            num_lines = 1
        elif op <= 142:  # push/pop
            pass
        elif op <= 146:  # right
            advance(4 - (146 - op))
        elif op <= 151:  # w
            advance(4 - (151 - op))
        elif op <= 156:  # x
            advance(4 - (156 - op))
        elif op <= 160:  # down
            advance(4 - (160 - op))
        elif op <= 165:  # y (down + set)
            num_lines += 1
            advance(4 - (165 - op))
        elif op <= 170:  # z (down + set)
            num_lines += 1
            advance(4 - (170 - op))
        elif op <= 234:  # font_num
            pass
        elif op <= 238:  # set font
            advance(4 - (238 - op))
        elif op == 239:  # xxx1
            k = read_u8()
            advance(k)
        elif op == 240:  # xxx2
            advance(2)
            k = struct.unpack(">H", data[pos - 2:pos])[0]
            advance(k)
        elif op == 248:  # post
            break
        else:
            # Skip unknown ops conservatively
            break

    return num_lines_per_page


# ============================================================
# Measurement interface
# ============================================================

@dataclass
class MeasureConfig:
    """Configuration for text measurement."""
    backend: str = "heuristic"  # "heuristic" or "tex"
    font_dir: str = ""
    font_file: str = ""


_MEASURE_CACHE = {}


def measure_height(
    text: str,
    width_pt: float,
    font: FontConfig,
    config: MeasureConfig | None = None,
) -> float:
    """
    Measure the rendered height of text. Uses heuristic by default,
    TeX-based measurement if configured.
    """
    if not text or not text.strip():
        return 0.0

    # Cache check
    key = (text, width_pt, font.size, font.leading)
    if key in _MEASURE_CACHE:
        return _MEASURE_CACHE[key]

    if config and config.backend == "tex":
        h = measure_height_tex(
            text, width_pt, font, config.font_dir, config.font_file
        )
    else:
        h = measure_height_heuristic(text, width_pt, font)

    _MEASURE_CACHE[key] = h
    return h
