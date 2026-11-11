"""
Unit test untuk modul scoring (app/engine/scoring.py).
Memverifikasi kepatuhan terhadap PRD R2.
"""

from __future__ import annotations

from pathlib import Path

from app.engine.params import EngineParams
from app.engine.scoring import rank_intents, score_intent
from app.engine.snapshot import NluSnapshot


def get_snapshot() -> NluSnapshot:
    seed_dir = Path(__file__).resolve().parent.parent.parent / "seed"
    return NluSnapshot.from_seed_dir(seed_dir)


def test_scoring_determinism_and_bounds() -> None:
    snapshot = get_snapshot()
    params = EngineParams()

    norm1 = snapshot.normalizer.normalize("halo selamat malam")
    rankings1 = rank_intents(norm1.score_tokens, snapshot, params)
    rankings2 = rank_intents(norm1.score_tokens, snapshot, params)

    # Deterministik
    assert [r.skor for r in rankings1] == [r.skor for r in rankings2]

    # Rentang skor 0..1
    for r in rankings1:
        assert 0.0 <= r.skor <= 1.0
        assert 0.0 <= r.jaccard <= 1.0
        assert 0.0 <= r.fuzzy <= 1.0
        assert 0.0 <= r.cakupan <= 1.0


def test_prd_r2_acceptance_criteria() -> None:
    snapshot = get_snapshot()
    params = EngineParams()

    # Given pesan "resrvasi meja" When dihitung Then intent reservasi mendapat skor tertinggi walau ada typo
    norm_typo = snapshot.normalizer.normalize("resrvasi meja")
    rankings_typo = rank_intents(norm_typo.score_tokens, snapshot, params)
    top_typo = rankings_typo[0]
    assert top_typo.intent == "reservasi", f"Top intent harus 'reservasi', didapat: {top_typo.intent}"

    # Given pesan "menu vegetarian" When dihitung Then intent diet mengalahkan à la carte dan Carte Blanche
    # meski ketiganya memuat kata "menu"
    norm_veg = snapshot.normalizer.normalize("menu vegetarian")
    rankings_veg = rank_intents(norm_veg.score_tokens, snapshot, params)
    top_veg = rankings_veg[0]
    assert top_veg.intent == "diet", f"Top intent harus 'diet', didapat: {top_veg.intent}"

    skor_map = {r.intent: r.skor for r in rankings_veg}
    assert skor_map["diet"] > skor_map["a_la_carte"]
    assert skor_map["diet"] > skor_map["carte_blanche"]
