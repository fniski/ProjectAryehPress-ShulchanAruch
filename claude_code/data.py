"""
Data models for Shulchan Aruch typesetting.
Loads the JSON produced by the Sefaria fetcher and provides structured access to all text streams.
"""
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

@dataclass
class Seif:
    """One seif (paragraph) of the Shulchan Aruch main text."""
    seif: int
    mechaber: str
    rema: Optional[str] = None
    translation: Optional[str] = None


@dataclass
class SubSeif:
    """One fragment of a seif used for long-entry pagination."""
    seif: int
    fragment: int
    total_fragments: int
    mechaber: str = ""
    rema: str = ""
    translation: str = ""

    @property
    def id(self) -> str:
        if self.total_fragments <= 1:
            return str(self.seif)
        return f"{self.seif}.{self.fragment}"

@dataclass
class CommentaryEntry:
    """One entry in a commentary (seif katan)."""
    seif_katan: int
    on_seif: int
    text: str
    on_subseif: Optional[str] = None

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
    sub_seifim: list[SubSeif] = field(default_factory=list)

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

    def get_subseif(self, subseif_id: str) -> Optional[SubSeif]:
        for s in self.sub_seifim:
            if s.id == subseif_id:
                return s
        return None

    def build_sub_seifim(self, max_chars_per_fragment: int = 700) -> None:
        """Split long seifim into fragments and remap commentaries to fragment ids."""
        self.sub_seifim = []
        seif_to_ids: dict[int, list[str]] = {}
        seif_commentary_chars: dict[int, int] = {}
        for name in self.all_commentary_names:
            for entry in getattr(self, name):
                seif_commentary_chars[entry.on_seif] = (
                    seif_commentary_chars.get(entry.on_seif, 0) + len(entry.text or "")
                )

        for seif in self.main_text:
            mech_chunks = _split_text_chunks(seif.mechaber, max_chars_per_fragment)
            rema_chunks = _split_text_chunks(seif.rema or "", max_chars_per_fragment)
            trans_chunks = _split_text_chunks(seif.translation or "", max_chars_per_fragment)

            comm_fragments = min(4, max(1, math.ceil(seif_commentary_chars.get(seif.seif, 0) / 2400)))
            non_empty_content = len(mech_chunks) + len(rema_chunks)
            total = max(1, non_empty_content, len(trans_chunks), comm_fragments)
            if non_empty_content and total > non_empty_content:
                if rema_chunks:
                    rema_chunks = _expand_chunks(rema_chunks, len(rema_chunks) + (total - non_empty_content), max_chars_per_fragment)
                else:
                    mech_chunks = _expand_chunks(mech_chunks, len(mech_chunks) + (total - non_empty_content), max_chars_per_fragment)
                non_empty_content = len(mech_chunks) + len(rema_chunks)
                total = max(1, non_empty_content, len(trans_chunks), comm_fragments)

            frags: list[SubSeif] = []
            for idx in range(total):
                mech = mech_chunks[idx] if idx < len(mech_chunks) else ""
                rema_idx = idx - len(mech_chunks)
                rema = rema_chunks[rema_idx] if 0 <= rema_idx < len(rema_chunks) else ""
                trans = trans_chunks[idx] if idx < len(trans_chunks) else ""
                frags.append(SubSeif(
                    seif=seif.seif,
                    fragment=idx + 1,
                    total_fragments=total,
                    mechaber=mech,
                    rema=rema,
                    translation=trans,
                ))

            self.sub_seifim.extend(frags)
            seif_to_ids[seif.seif] = [f.id for f in frags]

        for name in self.all_commentary_names:
            remapped: list[CommentaryEntry] = []
            grouped: dict[int, list[CommentaryEntry]] = {}
            for entry in getattr(self, name):
                grouped.setdefault(entry.on_seif, []).append(entry)

            for on_seif, entries in grouped.items():
                ids = seif_to_ids.get(on_seif) or [str(on_seif)]
                target = max(1, sum(len(e.text) for e in entries) // len(ids))
                current_id_idx = 0
                current_bucket_chars = 0
                for entry in entries:
                    chunks = _split_text_chunks(entry.text, max_chars_per_fragment)
                    for chunk in chunks:
                        remapped.append(CommentaryEntry(
                            seif_katan=entry.seif_katan,
                            on_seif=entry.on_seif,
                            text=chunk,
                            on_subseif=ids[current_id_idx],
                        ))
                        current_bucket_chars += len(chunk)
                        if current_id_idx < len(ids) - 1 and current_bucket_chars >= target:
                            current_id_idx += 1
                            current_bucket_chars = 0
            setattr(self, name, remapped)

    def get_main_text_for_subseif_range(self, start_idx: int, end_idx: int) -> list[SubSeif]:
        return self.sub_seifim[start_idx:end_idx + 1]

    def get_commentary_for_subseif_ids(
        self, commentary_name: str, sub_ids: set[str]
    ) -> list[CommentaryEntry]:
        entries = getattr(self, commentary_name, [])
        return [e for e in entries if (e.on_subseif or str(e.on_seif)) in sub_ids]

    @property
    def all_commentary_names(self) -> list[str]:
        """All commentary field names."""
        return [
            "taz",
            "magen_avraham",
            "machatzit_hashekel",
            "mishbetzot_zahav",
            "eshel_avraham",
            "beer_hagolah",
            "biur_hagra",
            "ateret_zekeinim",
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
    main_entries = data.get("main_text", data.get("shulchan_arukh", []))
    top_translations = data.get("translations", {})
    for entry in main_entries:
        seif_num = entry["seif"]
        translation = (
            entry.get("translation")
            or entry.get("english")
            or top_translations.get(str(seif_num), "")
        )
        siman.main_text.append(Seif(
            seif=seif_num,
            mechaber=entry["mechaber"],
            rema=entry.get("rema"),
            translation=translation or None,
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

    siman.build_sub_seifim()
    return siman


def _split_text_chunks(text: str, max_chars: int) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    parts = [p.strip() for p in re.split(r"(?<=[\.\!\?\:\;׃])\s+", text) if p.strip()]
    if not parts:
        parts = text.split()

    chunks: list[str] = []
    current = ""
    for part in parts:
        if len(part) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            for i in range(0, len(part), max_chars):
                chunks.append(part[i:i + max_chars].strip())
            continue
        candidate = f"{current} {part}".strip()
        if current and len(candidate) > max_chars:
            chunks.append(current.strip())
            current = part
        else:
            current = candidate
    if current:
        chunks.append(current.strip())
    return chunks


def _expand_chunks(chunks: list[str], target_count: int, max_chars: int) -> list[str]:
    """Split existing chunks further until we reach target_count (best effort)."""
    chunks = [c for c in chunks if c and c.strip()]
    if not chunks:
        return chunks

    while len(chunks) < target_count:
        idx = max(range(len(chunks)), key=lambda i: len(chunks[i]))
        longest = chunks[idx].strip()
        if len(longest) <= max(30, max_chars // 3):
            break

        mid = len(longest) // 2
        split_at = longest.rfind(" ", 0, mid)
        if split_at < 0:
            split_at = longest.find(" ", mid)
        if split_at < 0:
            break

        left = longest[:split_at].strip()
        right = longest[split_at + 1:].strip()
        if not left or not right:
            break
        chunks[idx:idx + 1] = [left, right]

    return chunks
