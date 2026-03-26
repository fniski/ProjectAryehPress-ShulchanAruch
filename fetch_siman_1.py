import requests
import json
import re
import os
from pathlib import Path

# Ordered by layout placement requirements
REFS = {
    "shulchan_arukh": [
        "Shulchan_Arukh,_Orach_Chayim.1"
    ],
    "rema": [
        "Rema_on_Shulchan_Arukh,_Orach_Chayim.1"
    ],
    "taz": [
        "Turei_Zahav_on_Shulchan_Arukh,_Orach_Chayim.1"
    ],
    "magen_avraham": [
        "Magen_Avraham.1",
        "Magen_Avraham_on_Shulchan_Arukh,_Orach_Chayim.1"
    ],
    "machatzit_hashekel": [
        "Machatzit_HaShekel_on_Orach_Chayim.1"
    ],
    "mishbetzot_zahav": [
        "Peri_Megadim_on_Orach_Chayim,_Mishbezot_Zahav.1",
        "Mishbetzot_Zahav_on_Orach_Chayim.1"
    ],
    "eshel_avraham": [
        "Eshel_Avraham_on_Shulchan_Arukh,_Orach_Chayim.1"
    ],
    "beer_hagolah": [
        "Beer_Hagolah_on_Shulchan_Arukh,_Orach_Chayim.1",
        "Ba'er_Hetev_on_Shulchan_Arukh,_Orach_Chayim.1",
        "Be'er_Hagolah_on_Shulchan_Arukh,_Orach_Chayim.1"
    ],
    "biur_hagra": [
        "Beur_HaGra_on_Shulchan_Arukh,_Orach_Chayim.1",
        "Biur_HaGra_on_Shulchan_Arukh,_Orach_Chayim.1"
    ],
    "baer_heitiv": [
        "Ba'er_Heitev_on_Shulchan_Arukh,_Orach_Chayim.1",
        "Ba'er_Hetev_on_Shulchan_Arukh,_Orach_Chayim.1"
    ],
    "shaarei_teshuvah": [
        "Sha'arei_Teshuvah_on_Shulchan_Arukh,_Orach_Chayim.1"
    ],
    "ateret_zekeinim": [
        "Ateret_Zekeinim.1",
        "Ateret_Zekeinim_on_Shulchan_Arukh,_Orach_Chayim.1"
    ],
    "mishnah_berurah": [
        "Mishnah_Berurah.1"
    ],
    "chidushei_rav_akiva_eiger": [
        "Rabbi_Akiva_Eiger_on_Shulchan_Arukh,_Orach_Chayim.1"
    ]
}

def clean_html(raw_html: str) -> str:
    """Basic HTML cleaner."""
    if not isinstance(raw_html, str):
        return ""
    cleaned = re.sub(r'<[^>]+>', '', raw_html)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def fetch_sefaria_v3(ref: str):
    """Fetch text from Sefaria v3 API with default format."""
    url = f"https://www.sefaria.org/api/v3/texts/{ref}?return_format=default"
    print(f"Fetching: {url}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  Error fetching {ref}: {e}")
        return None

def extract_mechaber_rema(html_text: str):
    """Fallback text cleaning for main text."""
    if not isinstance(html_text, str):
        return html_text, None
    match = re.search(r'<small>\s*הגה.*?</small>', html_text)
    if match:
        rema_html = match.group(0)
        mechaber_html = html_text.replace(rema_html, '')
        return clean_html(mechaber_html), clean_html(rema_html)
    
    match = re.search(r'\bהגה\b(.*)', html_text)
    if match:
        rema_text = match.group(0)
        mechaber_text = html_text[:match.start()]
        return clean_html(mechaber_text), clean_html(rema_text)

    return clean_html(html_text), None

def main():
    siman_1_data = {
        "siman": 1,
        "sefer": "Orach Chayim"
    }
    
    for key, variations in REFS.items():
        if key not in siman_1_data:
            siman_1_data[key] = []
            
        found = False
        for ref in variations:
            data = fetch_sefaria_v3(ref)
            if data and "versions" in data and len(data["versions"]) > 0:
                # Get text array for the highest priority version
                text_array = data["versions"][0].get("text", [])
                
                # Sefaria depth > 1 check (if it returned the full book instead of just Siman 1)
                if text_array and isinstance(text_array, list) and isinstance(text_array[0], list):
                    print(f"  Note: Sefaria returned depth > 1. Extracting index 0 as Siman 1.")
                    text_array = text_array[0]
                
                # Process main text differently (Shulchan Arukh, Rema)
                if key in ["shulchan_arukh", "rema"]:
                    seifim = []
                    for idx, raw_seif in enumerate(text_array):
                        if raw_seif:
                            mechaber, rema = extract_mechaber_rema(raw_seif)
                            seifim.append({
                                "seif": idx + 1,
                                "mechaber": mechaber or "",
                                "rema": rema if key == "shulchan_arukh" else clean_html(raw_seif)
                            })
                    siman_1_data[key] = seifim
                    print(f"  Found {key}: {len(seifim)} seifim")
                    found = True
                    break
                else:
                    # Generic Commentary Processing
                    comments = []
                    for idx, comment_html in enumerate(text_array):
                        cleaned = clean_html(comment_html)
                        if cleaned:
                            comments.append({
                                "seif_katan": len(comments) + 1,
                                "text": cleaned
                            })
                    siman_1_data[key] = comments
                    print(f"  Found {key}: {len(comments)} comments")
                    found = True
                    break
        
        if not found:
            print(f"  WARNING: Could not find any text for {key}")

    out_path = Path("sefaria/siman_1.json")
    out_path.parent.mkdir(exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(siman_1_data, f, ensure_ascii=False, indent=2)
        
    print(f"\nSuccessfully wrote texts to {out_path.absolute()}")

if __name__ == "__main__":
    main()
