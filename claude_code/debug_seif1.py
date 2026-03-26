import sys
from pathlib import Path
sys.path.append(str(Path.cwd()))
from measure import measure_height, MeasureConfig
from zones import FONT_MAIN
from data import load_siman

siman = load_siman("../sefaria/siman_1.json")
seif = siman.main_text[0]
text = seif.mechaber
if seif.rema:
    text += " הגה: " + seif.rema
width = 406.4 # Default center width

config = MeasureConfig(backend="tex", font_dir="D:/Projects/ProjectAryehPress/Seforim/Fonts/", font_file="FrankRuehlCLM")

from zones import FONT_MAIN, FONT_COMMENTARY_LARGE

print(f"Measuring Seif 1 Main ({len(text)} chars)...")
h_main = measure_height(text, width, FONT_MAIN, config)
print(f"Main Height: {h_main} pt")

taz_text = " ".join([e.text for e in siman.get_commentary_for_seifim("taz", 1, 1)])
ma_text = " ".join([e.text for e in siman.get_commentary_for_seifim("magen_avraham", 1, 1)])

print(f"Measuring Taz ({len(taz_text)} chars)...")
h_taz = measure_height(taz_text, 200, FONT_COMMENTARY_LARGE, config)
print(f"Taz Height: {h_taz} pt")

print(f"Measuring MA ({len(ma_text)} chars)...")
h_ma = measure_height(ma_text, 200, FONT_COMMENTARY_LARGE, config)
print(f"MA Height: {h_ma} pt")

