"""
Unit test untuk modul keputusan (app/engine/decision.py).
Memverifikasi kepatuhan terhadap PRD R3 dan R10.
"""

from __future__ import annotations

from pathlib import Path

from app.engine.decision import decide
from app.engine.params import EngineParams
from app.engine.scoring import rank_intents
from app.engine.snapshot import NluSnapshot


def get_snapshot() -> NluSnapshot:
    seed_dir = Path(__file__).resolve().parent.parent.parent / "seed"
    return NluSnapshot.from_seed_dir(seed_dir)


def test_prd_r3_acceptance_criteria() -> None:
    snapshot = get_snapshot()
    params = EngineParams()

    # Given pesan "cuaca hari ini bagaimana?" When diproses Then intent = fallback
    norm_oos = snapshot.normalizer.normalize("cuaca hari ini bagaimana?")
    rankings_oos = rank_intents(norm_oos.score_tokens, snapshot, params)
    dec_oos = decide(rankings_oos, snapshot, params, norm_oos.score_tokens)
    assert dec_oos.intent == "fallback"
    assert dec_oos.alasan == "di_bawah_tau"

    # Given pesan "halo" When diproses Then intent = sapaan dengan skor >= tau
    norm_halo = snapshot.normalizer.normalize("halo")
    rankings_halo = rank_intents(norm_halo.score_tokens, snapshot, params)
    dec_halo = decide(rankings_halo, snapshot, params, norm_halo.score_tokens)
    assert dec_halo.intent == "sapaan"
    assert rankings_halo[0].skor >= params.tau


def test_priority_rule_social_vs_info() -> None:
    snapshot = get_snapshot()
    params = EngineParams()

    # "halo mau reservasi tempat" -> sapaan + info reservasi
    # Sosial harus kalah dari info yang lolos tau
    norm = snapshot.normalizer.normalize("halo mau reservasi tempat")
    rankings = rank_intents(norm.score_tokens, snapshot, params)
    dec = decide(rankings, snapshot, params, norm.score_tokens)
    assert dec.intent == "reservasi"


def test_fallback_guess_rho() -> None:
    snapshot = get_snapshot()
    params = EngineParams(tau=0.45, rho=0.15)

    # Kalimat out-of-scope yang sama sekali tidak berhubungan -> tebakan None
    norm_random = snapshot.normalizer.normalize("xyz abc 12345")
    rankings_random = rank_intents(norm_random.score_tokens, snapshot, params)
    dec_random = decide(rankings_random, snapshot, params, norm_random.score_tokens)
    assert dec_random.intent == "fallback"
    assert dec_random.tebakan is None
