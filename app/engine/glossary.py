"""
Anotasi glosarium istilah Prancis sesuai PRD R11 dan System Design Bagian 6.6.
Aturan:
  - Setiap istilah Prancis dari glosarium selalu diikuti maknanya dalam tanda kurung.
  - Pencocokan terpanjang lebih dulu (longest match first).
  - Teks dalam protected spans (nama hidangan, minuman, atau baris teknik) tidak dianotasi.
  - Istilah yang sudah memiliki arti di sampingnya tidak dianotasi ganda.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Sequence


def remove_accents_for_regex(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# --- Anotator Glosarium Istilah Prancis ---
# Mengelola penambahan makna bahasa Indonesia pada setiap istilah kuliner Prancis (PRD R11).
# Istilah diurutkan berdasarkan panjang karakter menurun (longest match first) agar istilah
# majemuk seperti "les entrées" teranotasi sebelum kata tunggal "entrées".
class GlossaryAnnotator:
    def __init__(self, glossary_items: Sequence[dict[str, str]]) -> None:
        self.items = sorted(
            glossary_items,
            key=lambda x: len(x["istilah"]),
            reverse=True,
        )

    # --- Proses Anotasi 3 Tahap ---
    # Tahap 1: Masking protected spans (nama hidangan, minuman, atau baris teknik yang sudah ada definisinya).
    # Tahap 2: Regex replacement untuk menambahkan " (makna)" setelah istilah, dengan pengecekan
    #          agar istilah yang sudah diikuti tanda kurung buka tidak dianotasi ganda.
    # Tahap 3: Unmasking untuk mengembalikan protected spans ke kondisi semula.
    def annotate(self, text: str, protected_spans: list[str] | None = None) -> str:
        if not text:
            return text

        protected = protected_spans or []
        masks: dict[str, str] = {}

        # 1. Mask protected spans (misal nama hidangan utuh)
        # Urutkan span terpanjang dulu agar tidak ada konflik
        sorted_protected = sorted(set(protected), key=len, reverse=True)
        masked_text = text
        for idx, span in enumerate(sorted_protected):
            if span and span in masked_text:
                mask_key = f"__PROTECTED_SPAN_{idx}__"
                masks[mask_key] = span
                masked_text = masked_text.replace(span, mask_key)

        # 2. Anotasi setiap istilah glosarium
        for item in self.items:
            istilah = item["istilah"].strip()
            makna = item["makna"].strip()
            if not istilah or not makna:
                continue

            # Buat pola regex yang fleksibel terhadap aksen dan case-insensitive
            # Contoh: "entrees" cocok dengan "Entrées"
            escaped_term = re.escape(istilah)
            # Ganti spasi/strip dengan fleksibel
            flexible_term = escaped_term.replace(r"\ ", r"[\s_]+").replace(r"\-", r"[\s\-_]+")

            # Boundary: tidak boleh bagian dari kata lain, dan tidak boleh sudah diikuti tanda kurung buka
            pattern = re.compile(
                rf"(?<!\w)({flexible_term})(?!\w)(?!\s*\()",
                re.IGNORECASE,
            )

            def repl(m: re.Match) -> str:
                matched_original_text = m.group(1)
                return f"{matched_original_text} ({makna})"

            masked_text = pattern.sub(repl, masked_text)

        # 3. Kembalikan protected spans
        for mask_key, original_span in masks.items():
            masked_text = masked_text.replace(mask_key, original_span)

        return masked_text
