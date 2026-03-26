import sys
from pathlib import Path
sys.path.append(str(Path.cwd()))
from measure import measure_height_tex
from zones import FONT_MAIN

text = "בדיקה של מדידת טקסט בעברית באמצעות קסלאטך"
width = 400.0

print("Measuring height...")
try:
    h = measure_height_tex(text, width, FONT_MAIN)
    print(f"Height: {h} pt")
except Exception as e:
    print(f"Error: {e}")
