"""
Pemuatan dan validasi parameter engine dari config/engine.json.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


# --- Definisi Parameter Engine ---
# Menampung seluruh hiperparameter NLU yang dapat dituning:
# - w_j, w_f, w_c: bobot gabungan komponen skor (Jaccard, Fuzzy, Cakupan).
# - tau: ambang batas skor minimum agar intent diterima (di bawah tau -> fallback).
# - delta: margin pembeda antara peringkat 1 dan peringkat 2.
# - rho: ambang batas untuk menampilkan tebakan "Mungkin maksud Anda...".
# - fuzzy_match_min & fuzzy_exact_max_len: batas toleransi kecocokan typo.
# - direction_le & direction_gt: kata kunci penentu arah filter harga (<= atau >).
@dataclass(frozen=True)
class EngineParams:
    w_j: float = 0.4
    w_f: float = 0.3
    w_c: float = 0.3
    tau: float = 0.45
    delta: float = 0.10
    rho: float = 0.15
    fuzzy_match_min: float = 0.8
    fuzzy_exact_max_len: int = 3
    token_weight_default: int = 2
    price_default_threshold: int = 1200000
    direction_le: frozenset[str] = field(
        default_factory=lambda: frozenset(["bawah", "kurang", "murah", "maksimal", "sampai", "maks"])
    )
    direction_gt: frozenset[str] = field(
        default_factory=lambda: frozenset(["atas", "lebih", "mahal", "minimal", "min"])
    )
    max_message_length: int = 500

    # --- Factory Method dari Dictionary / File JSON ---
    # Membaca struktur file config/engine.json dan mengonversinya menjadi objek EngineParams.
    @classmethod
    def from_dict(cls, d: dict) -> EngineParams:
        weights = d.get("weights", {})
        return cls(
            w_j=float(weights.get("jaccard", 0.4)),
            w_f=float(weights.get("fuzzy", 0.3)),
            w_c=float(weights.get("cakupan", 0.3)),
            tau=float(d.get("tau", 0.45)),
            delta=float(d.get("delta", 0.10)),
            rho=float(d.get("rho", 0.15)),
            fuzzy_match_min=float(d.get("fuzzy_match_min", 0.8)),
            fuzzy_exact_max_len=int(d.get("fuzzy_exact_max_len", 3)),
            token_weight_default=int(d.get("token_weight_default", 2)),
            price_default_threshold=int(d.get("price_default_threshold", 1200000)),
            direction_le=frozenset(d.get("direction_le", ["bawah", "kurang", "murah", "maksimal", "sampai", "maks"])),
            direction_gt=frozenset(d.get("direction_gt", ["atas", "lebih", "mahal", "minimal", "min"])),
            max_message_length=int(d.get("max_message_length", 500)),
        )

    @classmethod
    def from_file(cls, path: Path | str) -> EngineParams:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
