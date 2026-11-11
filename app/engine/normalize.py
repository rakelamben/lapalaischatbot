"""
Normalisasi teks NLU sesuai PRD R1 dan System Design Bagian 6.2.
Fitur:
  - Lowercase dan pembersihan aksen (NFKD).
  - Ekstraksi dan normalisasi angka (1.200.000, 1,2 juta, 500rb -> 1200000).
  - Angka dikeluarkan dari token scoring agar tidak mendilusi Jaccard.
  - Penggantian frasa multi-kata dan sinonim (longest-match first).
  - Penghapusan stopword domain-aware untuk scoring tokens.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


# --- Pembersihan Karakter Aksen ---
# Mengubah karakter beraksen Prancis (é, è, ê, ô, ç, dll.) menjadi huruf latin polos tanpa aksen
# menggunakan normalisasi Unicode NFKD agar tidak terjadi kegagalan pencocokan string.
def remove_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# --- Deteksi dan Ekstraksi Angka Nominal ---
# Mendeteksi ekspresi angka dalam berbagai format Indonesia:
# 1. Desimal + juta/jt ("1,2 juta", "1.2jt" -> 1200000)
# 2. Integer + juta/jt ("1 juta", "2 jt" -> 1000000)
# 3. Ribuan/rb/k ("500rb", "500 ribu", "500k" -> 500000)
# 4. Format titik ribuan ("1.200.000", "500.000" -> 1200000)
# 5. Angka integer polos ("1200000" -> 1200000)
# Angka yang ditemukan kemudian dihapus dari teks kalimat agar token angka tidak mendilusi Jaccard similarity.
def extract_and_remove_number(text: str) -> tuple[str, int | None]:
    found_number: int | None = None

    # Pola 1: desimal + juta / jt (contoh: 1,2 juta, 1.2 juta, 1,2jt, 1.2jt)
    pattern_juta_dec = re.compile(r"\b(\d+)[,\.](\d+)\s*(?:juta|jt)\b", re.IGNORECASE)
    match = pattern_juta_dec.search(text)
    if match:
        whole = int(match.group(1))
        dec_str = match.group(2)
        # 1,2 juta -> 1.2 * 10^6 = 1200000
        val = int((whole + float(f"0.{dec_str}")) * 1_000_000)
        found_number = val
        text = pattern_juta_dec.sub(" ", text)

    # Pola 2: bilangan bulat + juta / jt (contoh: 1 juta, 2 jt)
    if found_number is None:
        pattern_juta_int = re.compile(r"\b(\d+)\s*(?:juta|jt)\b", re.IGNORECASE)
        match = pattern_juta_int.search(text)
        if match:
            found_number = int(match.group(1)) * 1_000_000
            text = pattern_juta_int.sub(" ", text)

    # Pola 3: desimal/bulat + ribu / rb / k (contoh: 500rb, 500 ribu, 500k)
    if found_number is None:
        pattern_ribu = re.compile(r"\b(\d+)\s*(?:ribu|rb|k)\b", re.IGNORECASE)
        match = pattern_ribu.search(text)
        if match:
            found_number = int(match.group(1)) * 1_000
            text = pattern_ribu.sub(" ", text)

    # Pola 4: angka dengan pemisah ribuan titik (contoh: 1.200.000, 500.000)
    if found_number is None:
        pattern_dot = re.compile(r"\b(\d{1,3}(?:\.\d{3})+)\b")
        match = pattern_dot.search(text)
        if match:
            num_str = match.group(1).replace(".", "")
            found_number = int(num_str)
            text = pattern_dot.sub(" ", text)

    # Pola 5: angka polos (contoh: 1200000, 500000)
    if found_number is None:
        pattern_plain = re.compile(r"\b(\d{4,9})\b")
        match = pattern_plain.search(text)
        if match:
            found_number = int(match.group(1))
            text = pattern_plain.sub(" ", text)

    return text, found_number


@dataclass(frozen=True)
class NormalizedText:
    raw: str
    clean_text: str
    clean_tokens: list[str]  # Semua token setelah penggantian frasa, sebelum stopword dibuang
    score_tokens: frozenset[str]  # Token tanpa stopword untuk Jaccard & scoring
    extracted_number: int | None


# --- Normalizer Teks Utama ---
# Kelas utama untuk pipeline normalisasi teks sesuai PRD R1:
# - Mengompilasi kamus sinonim dan frasa glosarium multi-kata secara terurut (longest-match first).
# - Menghasilkan token lengkap (clean_tokens) untuk ekstraksi entitas dan token tersaring (score_tokens) untuk scoring.
class TextNormalizer:
    def __init__(
        self,
        stopwords: set[str] | frozenset[str],
        synonyms: dict[str, str],
        multiword_phrases: list[str],
    ) -> None:
        self.stopwords = frozenset(stopwords)

        # Buat daftar mapping penggantian terurut longest-match-first
        # Termasuk varian sinonim dan frasa multi-kata glosarium
        replacements: dict[str, str] = {}

        # 1. Glosarium multi-kata (misal "prix fixe" -> "prix_fixe")
        for phrase in multiword_phrases:
            phrase_clean = remove_accents(phrase).lower().strip()
            if " " in phrase_clean:
                token_clean = phrase_clean.replace(" ", "_").replace("-", "_")
                replacements[phrase_clean] = token_clean

        # 2. Kamus sinonim
        for variant, canonical in synonyms.items():
            var_clean = remove_accents(variant).lower().strip()
            can_clean = remove_accents(canonical).lower().strip().replace(" ", "_")
            replacements[var_clean] = can_clean

        # Urutkan berdasarkan panjang frasa secara menurun (longest-match-first)
        self.sorted_replacements = sorted(
            replacements.items(),
            key=lambda item: (len(item[0]), len(item[0].split())),
            reverse=True,
        )

    # --- Pipeline Eksekusi Normalisasi ---
    # Tahap 1: Case folding & pembersihan aksen.
    # Tahap 2: Ekstraksi angka nominal.
    # Tahap 3: Pembersihan tanda baca menjadi spasi.
    # Tahap 4: Substitusi frasa multi-kata & sinonim dengan regex word boundary.
    # Tahap 5: Tokenisasi dan pembuangan stopword untuk set scoring.
    def normalize(self, text: str) -> NormalizedText:
        raw = text

        # 1. Lowercase dan hapus aksen
        cleaned = remove_accents(text).lower()

        # 2. Ekstraksi angka dan hapus dari teks
        cleaned, extracted_number = extract_and_remove_number(cleaned)

        # 3. Ganti tanda baca selain underscore dan strip dengan spasi
        # Tanda kutip, tanya, koma, seru, dll.
        cleaned = re.sub(r"[^\w\s\-_]", " ", cleaned)

        # 4. Longest-match multi-word phrase and synonym substitution
        # Gunakan regex word boundary untuk mencocokkan frasa utuh
        for pattern_str, replacement in self.sorted_replacements:
            # Escape regex dan buat boundary
            escaped = re.escape(pattern_str)
            # Boundary: \b di awal dan akhir jika alfanumerik
            boundary_pattern = rf"(?<!\w){escaped}(?!\w)"
            cleaned = re.sub(boundary_pattern, replacement, cleaned)

        # Ubah strip di tengah kata seperti "sous-vide" menjadi underscore jika ada
        cleaned = cleaned.replace("-", "_")

        # 5. Normalisasi spasi dan tokenisasi
        tokens = [t.strip() for t in cleaned.split() if t.strip()]

        # Filter stopword untuk score_tokens
        score_tokens = frozenset(t for t in tokens if t not in self.stopwords)

        return NormalizedText(
            raw=raw,
            clean_text=" ".join(tokens),
            clean_tokens=tokens,
            score_tokens=score_tokens,
            extracted_number=extracted_number,
        )
