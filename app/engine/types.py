"""
Tipe data tak-berubah (dataclass) untuk NLU Engine LaPalaisChatBot.
Engine ini murni Python tanpa dependensi ke Flask atau SQLite.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any


# --- Komponen Skor Kemiripan ---
# Menyimpan 3 dimensi penilaian kemiripan teks:
# - Jaccard: rasio irisan kata terhadap gabungan kata.
# - Fuzzy: rasio token pola yang cocok secara approximate dengan difflib SequenceMatcher.
# - Cakupan: proporsi kecocokan token dengan memperhitungkan bobot kata pembeda (bobot 3 vs 1).
@dataclass(frozen=True)
class Components:
    jaccard: float
    fuzzy: float
    cakupan: float

    @property
    def total(self) -> float:
        return 0.4 * self.jaccard + 0.3 * self.fuzzy + 0.3 * self.cakupan


# --- Struktur Pola & Intent ---
# Pattern menyimpan pola alami yang sudah dipra-proses menjadi set token dan bobot masing-masing kata.
@dataclass(frozen=True)
class Pattern:
    raw: str
    tokens: frozenset[str]
    weights: dict[str, int] = field(default_factory=dict)


# IntentData menyimpan definisi lengkap satu intent: kode, nama, jenis ('info', 'sosial', 'fallback'),
# frasa kanonik untuk tombol saran, daftar objek Pattern, serta daftar variasi template kalimatnya.
@dataclass(frozen=True)
class IntentData:
    id: int
    kode: str
    nama: str
    jenis: str  # 'info', 'sosial', 'fallback'
    frasa_kanonik: str | None
    patterns: list[Pattern] = field(default_factory=list)
    templates: list[tuple[int, str]] = field(default_factory=list)  # (template_id, text)


# --- Struktur Entitas (Harga & Diet) ---
# PriceEntity menyimpan nilai integer Rupiah dan operator arah ('le' = <=, 'gt' = >, 'both' = dua kelompok).
@dataclass(frozen=True)
class PriceEntity:
    nilai: int
    op: str  # 'le', 'gt', 'both'


# Entities menampung seluruh entitas yang berhasil diekstrak dari pesan melalui regex dan leksikon.
@dataclass(frozen=True)
class Entities:
    harga: PriceEntity | None = None
    diet: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        res: dict[str, Any] = {}
        if self.harga:
            res["harga"] = {"op": self.harga.op, "nilai": self.harga.nilai}
        if self.diet:
            res["diet"] = list(self.diet)
        return res


# --- Peringkat Skor & Keputusan Sistem ---
# Ranking merekam skor total dan breakdown 3 komponen skor untuk satu intent tertentu.
@dataclass(frozen=True)
class Ranking:
    intent: str
    skor: float
    jaccard: float
    fuzzy: float
    cakupan: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "skor": round(self.skor, 4),
            "jaccard": round(self.jaccard, 4),
            "fuzzy": round(self.fuzzy, 4),
            "cakupan": round(self.cakupan, 4),
        }


# Decision menyimpan hasil keputusan akhir mesin NLU (nama intent terpilih, alasan pengambilan keputusan,
# dan rekomendasi tebakan jika skor teratas jatuh di antara ambang rho dan tau).
@dataclass(frozen=True)
class Decision:
    intent: str
    alasan: str
    tebakan: Ranking | None = None

    def to_dict(self) -> dict[str, Any]:
        res = {"intent": self.intent, "alasan": self.alasan}
        if self.tebakan:
            res["tebakan"] = self.tebakan.to_dict()
        return res


# --- Hasil Analisis NLU Lengkap ---
# Analysis merangkum seluruh jejak pemrosesan NLU dari pesan mentah, token, entitas,
# daftar peringkat 10 intent, hingga keputusan akhir dan catatan latensi eksekusi (ms).
@dataclass
class Analysis:
    raw_message: str
    clean_tokens: list[str]
    score_tokens: frozenset[str]
    entities: Entities
    ranking: list[Ranking]
    decision: Decision
    latency_ms: float = 0.0

    def to_debug_dict(self, params: Any = None) -> dict[str, Any]:
        return {
            "tokens": self.clean_tokens,
            "entities": self.entities.to_dict(),
            "ranking": [r.to_dict() for r in self.ranking],
            "decision": {
                "intent": self.decision.intent,
                "alasan": self.decision.alasan,
                "tau": params.tau if params else 0.45,
                "delta": params.delta if params else 0.10,
                "rho": params.rho if params else 0.15,
                "tebakan": self.decision.tebakan.to_dict() if self.decision.tebakan else None,
            },
            "latency_ms": self.latency_ms,
        }


# --- Objek Balasan Akhir ---
# Reply adalah paket respon final yang siap dikirim ke klien: teks jawaban terformat,
# ID template yang digunakan (untuk mencegah repetisi berturut-turut), dan tombol saran kanonik jika ada.
@dataclass(frozen=True)
class Reply:
    text: str
    template_id: int | None
    suggestions: list[dict[str, str]] = field(default_factory=list)
    analysis: Analysis | None = None
    content: list[dict[str, Any]] | str | None = None  # Data terstruktur dari handler atau teks fallback.
