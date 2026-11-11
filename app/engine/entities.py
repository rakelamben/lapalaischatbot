"""
Ekstraksi entitas harga dan diet sesuai PRD R4 dan System Design Bagian 6.5.
Ekstraksi berbasis regex dan leksikon (bukan kemiripan teks).
"""

from __future__ import annotations

from app.engine.normalize import NormalizedText
from app.engine.params import EngineParams
from app.engine.snapshot import NluSnapshot
from app.engine.types import Entities, PriceEntity


# --- Ekstraksi Entitas Harga dan Diet ---
# Mengekstrak informasi spesifik yang digunakan untuk memfilter subset data:
# 1. Harga: Menentukan nilai angka dan operator perbandingan (<=, >, atau both).
#    Jika kata arah muncul tanpa angka (misal "menu murah"), threshold default Rp1.200.000 digunakan otomatis.
# 2. Diet: Menemukan label diet resmi (vegetarian, halal, non_seafood) yang cocok dengan token pesan.
def extract_entities(
    norm: NormalizedText,
    snapshot: NluSnapshot,
    params: EngineParams,
) -> Entities:
    # 1. Ekstraksi Entitas Harga (Nilai + Operator Arah)
    number = norm.extracted_number
    tokens_set = set(norm.clean_tokens)

    has_le = bool(tokens_set & params.direction_le)
    has_gt = bool(tokens_set & params.direction_gt)

    harga_entity: PriceEntity | None = None

    if number is not None:
        if has_le and not has_gt:
            harga_entity = PriceEntity(nilai=number, op="le")
        elif has_gt and not has_le:
            harga_entity = PriceEntity(nilai=number, op="gt")
        else:
            harga_entity = PriceEntity(nilai=number, op="both")
    elif has_le or has_gt:
        # Arah tanpa angka eksplisit -> gunakan threshold default Rp1.200.000
        default_val = params.price_default_threshold
        if has_le and not has_gt:
            harga_entity = PriceEntity(nilai=default_val, op="le")
        elif has_gt and not has_le:
            harga_entity = PriceEntity(nilai=default_val, op="gt")
        else:
            harga_entity = PriceEntity(nilai=default_val, op="both")

    # 2. Ekstraksi Entitas Diet (Pencocokan Kode Diet Resmi)
    found_diets: list[str] = []
    for dcode in snapshot.diet_codes:
        if dcode in tokens_set:
            found_diets.append(dcode)

    return Entities(harga=harga_entity, diet=tuple(found_diets))
