"""
Mesin skor NLU sesuai PRD R2 dan System Design Bagian 6.3.
Formula:
  Skor pola = w_j * Jaccard + w_f * Fuzzy + w_c * Cakupan Berbobot
  Skor intent = MAX(Skor pola untuk pola-pola pada intent tersebut)
"""

from __future__ import annotations

from difflib import SequenceMatcher

from app.engine.params import EngineParams
from app.engine.snapshot import NluSnapshot
from app.engine.types import Components, IntentData, Pattern, Ranking


# --- Pencocokan Token Approximate (Fuzzy Matching) ---
# Memeriksa apakah suatu kata pada pola memiliki padanan dalam pesan tamu:
# 1. Kecocokan eksak langsung lolos (ratio = 1.0).
# 2. Token pendek (panjang <= 3 huruf) diwajibkan eksak agar kata pendek tidak salah cocok (misal 'jus' vs 'bus').
# 3. Token lainnya dievaluasi dengan SequenceMatcher: quick_ratio dipakai sebagai saringan cepat sebelum menghitung ratio penuh >= 0.8.
def token_matches(pat_tok: str, msg_tokens: frozenset[str], params: EngineParams) -> bool:
    if pat_tok in msg_tokens:
        return True

    if len(pat_tok) <= params.fuzzy_exact_max_len:
        return False

    for m_tok in msg_tokens:
        if len(m_tok) <= params.fuzzy_exact_max_len:
            continue
        matcher = SequenceMatcher(None, pat_tok, m_tok)
        if matcher.quick_ratio() < params.fuzzy_match_min:
            continue
        if matcher.ratio() >= params.fuzzy_match_min:
            return True

    return False


# --- Penilaian Skor Satu Pola ---
# Menghitung 3 metrik matematis sesuai PRD R2:
# 1. Jaccard: |irisan| / |gabungan| kata (setelah stopword dibuang).
# 2. Fuzzy: rasio jumlah token pola yang berhasil dicocokkan terhadap total token pola.
# 3. Cakupan Berbobot: bobot token pola yang cocok dibagi total bobot token pola (kata pembeda bobot 3, kata umum bobot 1).
def score_pattern(msg_tokens: frozenset[str], pattern: Pattern, params: EngineParams) -> Components:
    if not pattern.tokens or not msg_tokens:
        return Components(0.0, 0.0, 0.0)

    # 1. Jaccard: irisan / gabungan
    inter = pattern.tokens & msg_tokens  # Token yang muncul pada pola dan pesan.
    union = pattern.tokens | msg_tokens  # Semua token unik dari pola maupun pesan.
    jaccard = len(inter) / len(union) if union else 0.0

    # 2. Fuzzy pada level token
    hits = {t for t in pattern.tokens if token_matches(t, msg_tokens, params)}  # Token pola yang cocok eksak atau fuzzy.
    fuzzy = len(hits) / len(pattern.tokens) if pattern.tokens else 0.0

    # 3. Cakupan Berbobot
    total_weight = sum(pattern.weights.values())  # Bobot seluruh token pola sebagai penyebut cakupan.
    hit_weight = sum(pattern.weights.get(t, params.token_weight_default) for t in hits)  # Bobot token pola yang cocok.
    cakupan = hit_weight / total_weight if total_weight > 0 else 0.0

    return Components(jaccard=jaccard, fuzzy=fuzzy, cakupan=cakupan)


# --- Pembobotan Komponen Pola ---
# Mengalikan masing-masing komponen dengan bobotnya (default: 0.4 Jaccard + 0.3 Fuzzy + 0.3 Cakupan).
def score_single_pattern_total(msg_tokens: frozenset[str], pattern: Pattern, params: EngineParams) -> tuple[float, Components]:
    comp = score_pattern(msg_tokens, pattern, params)
    total_score = params.w_j * comp.jaccard + params.w_f * comp.fuzzy + params.w_c * comp.cakupan
    return total_score, comp


# --- Penilaian Skor Intent (Maksimum per Pola) ---
# Skor suatu intent diambil dari nilai MAKSIMUM skor pola-pola di dalamnya.
# Pendekatan ini mencegah dilusi skor yang sering terjadi jika semua pola digabung menjadi satu bag-of-words besar.
def score_intent(msg_tokens: frozenset[str], intent: IntentData, params: EngineParams) -> Ranking:
    if not intent.patterns:
        return Ranking(intent=intent.kode, skor=0.0, jaccard=0.0, fuzzy=0.0, cakupan=0.0)

    best_score = -1.0  # Skor pola tertinggi yang ditemukan untuk intent ini.
    best_comp = Components(0.0, 0.0, 0.0)  # Komponen skor yang menyertai pola terbaik.

    for pat in intent.patterns:
        score, comp = score_single_pattern_total(msg_tokens, pat, params)
        if score > best_score:
            best_score = score
            best_comp = comp

    return Ranking(
        intent=intent.kode,
        skor=max(0.0, best_score),
        jaccard=best_comp.jaccard,
        fuzzy=best_comp.fuzzy,
        cakupan=best_comp.cakupan,
    )


# --- Pemeringkatan Seluruh Intent ---
# Menilai seluruh 10 intent informasi dan sosial (intent fallback dikecualikan karena merupakan keputusan, bukan kandidat).
# Hasil dikembalikan dalam urutan menurun (skor tertinggi di indeks 0).
def rank_intents(msg_tokens: frozenset[str], snapshot: NluSnapshot, params: EngineParams) -> list[Ranking]:
    rankings: list[Ranking] = []
    for kode, intent in snapshot.intents.items():
        if kode == "fallback" or intent.jenis == "fallback":
            continue
        rankings.append(score_intent(msg_tokens, intent, params))

    rankings.sort(key=lambda r: r.skor, reverse=True)
    return rankings
