#!/usr/bin/env python3
"""
Shulchan Aruch Typesetter

Usage:
    python main.py siman_1.json
    python main.py siman_1.json --output out.tex
    python main.py siman_1.json --output out.tex --compile
    python main.py siman_1.json --font-dir /path/to/hebrew/fonts

The input JSON must follow the schema defined in the prompt
(see README.md for the full spec).
"""

import argparse
import subprocess
import sys
from pathlib import Path

from data import load_siman
from zones import DEFAULT_GEOMETRY
from optimizer import optimize_siman
from measure import MeasureConfig
from tex_gen import generate_tex


def main():
    parser = argparse.ArgumentParser(
        description="Typeset Shulchan Aruch pages from JSON input"
    )
    parser.add_argument(
        "input",
        type=str,
        help="Path to siman JSON file (e.g. siman_1.json)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="output.tex",
        help="Output .tex file path (default: output.tex)",
    )
    parser.add_argument(
        "--compile", "-c",
        action="store_true",
        help="Compile the .tex to PDF using tectonic or xelatex",
    )
    parser.add_argument(
        "--font-dir",
        type=str,
        default="",
        help="Path to directory containing Hebrew font files",
    )
    parser.add_argument(
        "--measure-backend",
        type=str,
        choices=["heuristic", "tex"],
        default="heuristic",
        help="Text measurement backend (default: heuristic)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print debug information about zone sizing",
    )

    args = parser.parse_args()

    # Load the siman
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Loading {input_path}...")
    siman = load_siman(input_path)
    print(f"  Siman {siman.siman} ({siman.sefer})")
    print(f"  {siman.num_seifim} seifim")

    # Print commentary stats
    for name in siman.all_commentary_names:
        entries = getattr(siman, name)
        if entries:
            print(f"  {name}: {len(entries)} entries")

    # Configure measurement
    measure_config = MeasureConfig(
        backend=args.measure_backend,
        font_dir=args.font_dir,
    )

    # Run the optimizer
    print(f"\nOptimizing page layout...")
    plan = optimize_siman(siman, DEFAULT_GEOMETRY, measure_config)
    print(f"  Result: {len(plan.pages)} pages")

    # Debug output
    if args.debug:
        from zones import build_zones, FONT_MAIN
        from measure import measure_height
        print(f"\n  Zone details for page 1:")
        page = plan.pages[0]
        main_text = page.zone_texts.get("main_text", "")
        main_lines = FONT_MAIN.estimate_lines(main_text, DEFAULT_GEOMETRY.text_width_pt * 0.80)
        zones = build_zones(DEFAULT_GEOMETRY, main_lines)
        for zone_name, zone in zones.items():
            text = page.zone_texts.get(zone_name, "")
            if text.strip():
                h = measure_height(text, zone.width_pt, zone.font, measure_config)
                print(f"    {zone_name}: {h:.1f}pt / {zone.max_height_pt:.1f}pt max "
                      f"({len(text)} chars)")

    # Generate TeX
    print(f"\nGenerating TeX...")
    tex = generate_tex(plan, DEFAULT_GEOMETRY, args.font_dir, args.output)

    # Compile if requested
    if args.compile:
        print(f"\nCompiling to PDF...")
        pdf_path = Path(args.output).with_suffix(".pdf")
        compiled = compile_tex(args.output, pdf_path)
        if compiled:
            print(f"  Output: {pdf_path}")
        else:
            print(f"  Compilation failed. You can try manually:")
            print(f"    xelatex {args.output}")
            print(f"    # or")
            print(f"    tectonic {args.output}")

    print("\nDone.")


def compile_tex(tex_path: str, pdf_path: Path) -> bool:
    """Try to compile the .tex file to PDF."""
    # Try tectonic first
    try:
        result = subprocess.run(
            ["tectonic", tex_path],
            capture_output=True,
            timeout=120,
        )
        if result.returncode == 0:
            return True
        print(f"  tectonic error: {result.stderr.decode()[:200]}")
    except FileNotFoundError:
        pass
    except subprocess.TimeoutExpired:
        print("  tectonic timed out")

    # Try xelatex
    try:
        result = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", tex_path],
            capture_output=True,
            timeout=120,
        )
        if result.returncode == 0:
            return True
        print(f"  xelatex error: {result.stderr.decode()[:200]}")
    except FileNotFoundError:
        print("  Neither tectonic nor xelatex found. Install one of them.")
    except subprocess.TimeoutExpired:
        print("  xelatex timed out")

    return False


if __name__ == "__main__":
    main()
