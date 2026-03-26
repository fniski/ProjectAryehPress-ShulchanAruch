"""
Data models for Shulchan Aruch typesetting.

Loads the JSON produced by the Sefaria fetcher and provides
structured access to all text streams.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Seif:
    """One seif (paragraph) of the Shulchan Aruch main text."""
    seif: int
    mechaber: str
    rema: Optional[str] = None


@dataclass
class CommentaryEntry:
    """One entry in a commentary (seif katan)."""
    seif_katan: int
    on_seif: int
    text: str


@dataclass
class Siman:
    """All text streams for a single siman."""
    siman: int
    sefer: str

    main_text: list[Seif] = field(default_factory=list)

    # Core commentaries (flank the main text)
    taz: list[CommentaryEntry] = field(default_factory=list)
    magen_avraham: list[CommentaryEntry] = field(default_factory=list)

    # Bottom commentaries
    machatzit_hashekel: list[CommentaryEntry] = field(default_factory=list)
    mishbetzot_zahav: list[CommentaryEntry] = field(default_factory=list)
    eshel_avraham: list[CommentaryEntry] = field(default_factory=list)

    # Side commentaries
    beer_hagolah: list[CommentaryEntry] = field(default_factory=list)
    biur_hagra: list[CommentaryEntry] = field(default_factory=list)
    ateret_zekeinim: list[CommentaryEntry] = field(default_factory=list)
    chidushei_rav_akiva_eiger: list[CommentaryEntry] = field(default_factory=list)

    @property
    def num_seifim(self) -> int:
        return len(self.main_text)

    def get_seif(self, seif_num: int) -> Optional[Seif]:
        for s in self.main_text:
            if s.seif == seif_num:
                return s
        return None

    def get_commentary_for_seifim(
        self, commentary_name: str, seif_start: int, seif_end: int
    ) -> list[CommentaryEntry]:
        """Get all commentary entries for seifim in range [seif_start, seif_end] inclusive."""
        entries = getattr(self, commentary_name, [])
        return [e for e in entries if seif_start <= e.on_seif <= seif_end]

    def get_main_text_for_seifim(self, seif_start: int, seif_end: int) -> list[Seif]:
        """Get main text entries for seifim in range [seif_start, seif_end] inclusive."""
        return [s for s in self.main_text if seif_start <= s.seif <= seif_end]

    @property
    def all_commentary_names(self) -> list[str]:
        """All commentary field names."""
        return [
            "taz", "magen_avraham",
            "machatzit_hashekel", "mishbetzot_zahav", "eshel_avraham",
            "beer_hagolah", "biur_hagra", "ateret_zekeinim",
            "chidushei_rav_akiva_eiger",
        ]


def load_siman(path: str | Path) -> Siman:
    """Load a siman from the JSON file produced by the Sefaria fetcher."""
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    siman = Siman(
        siman=data["siman"],
        sefer=data["sefer"],
    )

    # Load main text.
    for entry in data.get("shulchan_arukh", []):
        siman.main_text.append(Seif(
            seif=entry["seif"],
            mechaber=entry["mechaber"],
            rema=entry.get("rema"),
        ))

    # Load all commentaries.
    for name in siman.all_commentary_names:
        entries = data.get(name, [])
        for entry in entries:
            getattr(siman, name).append(CommentaryEntry(
                seif_katan=entry.get("seif_katan", 1),
                on_seif=entry.get("on_seif", 1),
                text=entry.get("text", ""),
            ))

    return siman
