"""
Golden Acceptance Tests untuk LaPalaisChatBot.
Memverifikasi seluruh kriteria penerimaan PRD v0.3 (R1 sampai R11).
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from app.data.repository import Repository
from app.engine import analyze, process_message
from app.engine.params import EngineParams
from app.engine.snapshot import NluSnapshot


def test_prd_acceptance_r1_preprocessing(temp_db: sqlite3.Connection) -> None:
    snapshot = NluSnapshot.from_db(temp_db)
    params = EngineParams()

    # R1.1: Given pesan "Ada menu Entrées?" When diproses Then token mengandung "entrees" dan tidak mengandung "ada"
    a1 = analyze("Ada menu Entrées?", snapshot, params)
    assert "entrees" in a1.clean_tokens
    assert "ada" not in a1.score_tokens

    # R1.2: Given pesan "di bawah 1,2 juta" When diproses Then angka terbaca 1200000
    a2 = analyze("di bawah 1,2 juta", snapshot, params)
    assert a2.entities.harga is not None
    assert a2.entities.harga.nilai == 1200000

    # R1.3: Given pesan "Prix Fixe" atau "prix fixe" When diproses Then keduanya menjadi token yang sama
    a3a = analyze("Prix Fixe", snapshot, params)
    a3b = analyze("prix fixe", snapshot, params)
    assert "prix_fixe" in a3a.clean_tokens
    assert "prix_fixe" in a3b.clean_tokens


def test_prd_acceptance_r2_scoring_engine(temp_db: sqlite3.Connection) -> None:
    snapshot = NluSnapshot.from_db(temp_db)
    params = EngineParams()

    # R2.1: Given pesan "resrvasi meja" When dihitung Then intent reservasi mendapat skor tertinggi walau ada typo
    a1 = analyze("resrvasi meja", snapshot, params)
    assert a1.ranking[0].intent == "reservasi"

    # R2.2: Given pesan "menu vegetarian" When dihitung Then intent diet mengalahkan à la carte dan Carte Blanche
    a2 = analyze("menu vegetarian", snapshot, params)
    scores = {r.intent: r.skor for r in a2.ranking}
    assert scores["diet"] > scores["a_la_carte"]
    assert scores["diet"] > scores["carte_blanche"]

    # R2.3: Skor selalu di rentang 0-1 dan deterministik
    a3 = analyze("menu vegetarian", snapshot, params)
    assert [r.skor for r in a2.ranking] == [r.skor for r in a3.ranking]
    for r in a2.ranking:
        assert 0.0 <= r.skor <= 1.0


def test_prd_acceptance_r3_decision_rules(temp_db: sqlite3.Connection) -> None:
    snapshot = NluSnapshot.from_db(temp_db)
    params = EngineParams()

    # R3.1: Given pesan "cuaca hari ini bagaimana?" When diproses Then intent = fallback
    a1 = analyze("cuaca hari ini bagaimana?", snapshot, params)
    assert a1.decision.intent == "fallback"

    # R3.2: Given pesan "halo" When diproses Then intent = sapaan dengan skor >= tau
    a2 = analyze("halo", snapshot, params)
    assert a2.decision.intent == "sapaan"
    assert a2.ranking[0].skor >= params.tau

    # R3.3: Given "halo mau reservasi tempat" (selisih tipis) Then aturan prioritas: reservasi menang atas sapaan
    a3 = analyze("halo mau reservasi tempat", snapshot, params)
    assert a3.decision.intent == "reservasi"


def test_prd_acceptance_r4_entity_filtering(temp_db: sqlite3.Connection) -> None:
    snapshot = NluSnapshot.from_db(temp_db)
    params = EngineParams()
    repo = Repository(temp_db)

    # R4.1: Given pesan "menu di bawah 1,2 juta" Then hanya menu <= 1.200.000 dan respons menulis "sampai dengan Rp1.200.000"
    reply1 = process_message("menu di bawah 1,2 juta", snapshot, params, repo)
    assert "Sampai dengan Rp1.200.000" in reply1.text
    assert "Filet de Boeuf Rossini" in reply1.text  # Tepat 1.200.000 masuk batas
    assert "Homard Thermidor" not in reply1.text  # 1.650.000 tidak boleh masuk

    # R4.2: Given pesan "menu di atas 1.200.000" Then hanya menu > 1.200.000
    reply2 = process_message("menu di atas 1.200.000", snapshot, params, repo)
    assert "Di atas Rp1.200.000" in reply2.text
    assert "Homard Thermidor" in reply2.text
    assert "Filet de Boeuf Rossini" not in reply2.text

    # R4.3: Given pesan "menu vegetarian di bawah 1,2 juta" Then hasil = irisan label vegetarian dan rentang harga
    reply3 = process_message("menu vegetarian di bawah 1,2 juta", snapshot, params, repo)
    assert "Velouté de Champignons" in reply3.text
    assert "Boeuf Bourguignon" not in reply3.text  # Bukan vegetarian


def test_prd_acceptance_r5_data_consistency_across_variations(temp_db: sqlite3.Connection) -> None:
    snapshot = NluSnapshot.from_db(temp_db)
    params = EngineParams()
    repo = Repository(temp_db)

    # Memastikan 100% variasi dalam satu intent merender daftar data yang identik
    intent_code = "reservasi"
    templates = snapshot.intents[intent_code].templates

    replies = []
    for tmpl_id, _ in templates:
        reply = process_message("info reservasi", snapshot, params, repo, prev_template_id=tmpl_id, rng_seed=42)
        replies.append(reply)

    expected_labels = [item["label"] for item in repo.get_reservation_info()]
    for reply in replies:
        assert isinstance(reply.content, list)
        assert [item["label"] for item in reply.content] == expected_labels


def test_handler_replies_include_structured_content(temp_db: sqlite3.Connection) -> None:
    snapshot = NluSnapshot.from_db(temp_db)
    params = EngineParams()
    repo = Repository(temp_db)
    cases = [
        ("tampilkan menu a la carte", "a_la_carte", "kategori"),
        ("paket prix fixe", "prix_fixe", "hidangan"),
        ("rekomendasi pairing wine", "pairing", "minuman"),
        ("apa itu teknik sous vide", "teknik", "istilah"),
        ("menu di bawah 1,2 juta", "harga", "harga"),
    ]

    for message, expected_intent, expected_key in cases:
        reply = process_message(message, snapshot, params, repo)

        assert reply.analysis is not None
        assert reply.analysis.decision.intent == expected_intent
        assert isinstance(reply.content, list)
        assert reply.content
        assert expected_key in reply.content[0]


def test_prd_acceptance_r6_no_repeating_consecutive_template(temp_db: sqlite3.Connection) -> None:
    snapshot = NluSnapshot.from_db(temp_db)
    params = EngineParams()
    repo = Repository(temp_db)

    # Panggilan ke-1
    reply1 = process_message("halo", snapshot, params, repo, prev_template_id=None, rng_seed=10)
    assert reply1.template_id is not None

    # Panggilan ke-2 dengan prev_template_id dari panggilan ke-1
    for seed in range(50):
        reply2 = process_message("halo", snapshot, params, repo, prev_template_id=reply1.template_id, rng_seed=seed)
        assert reply2.template_id != reply1.template_id, "Template tidak boleh berulang dua kali berturut-turut"


def test_prd_acceptance_r7_diet_disclaimer(temp_db: sqlite3.Connection) -> None:
    snapshot = NluSnapshot.from_db(temp_db)
    params = EngineParams()
    repo = Repository(temp_db)

    reply = process_message("menu vegetarian", snapshot, params, repo)
    disclaimer = snapshot.fixed_text["diet_disclaimer"]
    assert disclaimer in reply.text


def test_prd_acceptance_r9_latency_benchmark(temp_db: sqlite3.Connection) -> None:
    snapshot = NluSnapshot.from_db(temp_db)
    params = EngineParams()
    repo = Repository(temp_db)

    # Server target < 100 ms
    t0 = time.perf_counter()
    reply = process_message("menu vegetarian di bawah 1,2 juta", snapshot, params, repo)
    duration_ms = (time.perf_counter() - t0) * 1000.0

    assert duration_ms < 100.0, f"Latensi pemrosesan engine {duration_ms:.2f}ms melebihi 100ms"
    assert reply.analysis is not None
    assert reply.analysis.latency_ms < 100.0


def test_prd_acceptance_r10_helpful_fallback(temp_db: sqlite3.Connection) -> None:
    snapshot = NluSnapshot.from_db(temp_db)
    params = EngineParams()
    repo = Repository(temp_db)

    # 1. Fallback dengan tebakan karena ada kemiripan parsial ("tempat duduk di luar ada gak")
    # Bila skor < tau (0.45) tetapi >= rho (0.15)
    reply_guess = process_message("tempat duduk di luar ada gak", snapshot, params, repo)
    assert reply_guess.analysis.decision.intent == "fallback"
    assert reply_guess.analysis.decision.tebakan is not None
    assert reply_guess.analysis.decision.tebakan.intent == "reservasi"
    assert len(reply_guess.suggestions) >= 1
    assert any("reservasi" in s["frasa"].lower() for s in reply_guess.suggestions)

    # 2. Dua fallback berturut-turut memiliki pembuka template berbeda
    r_fb1 = process_message("jadwal pertandingan bola", snapshot, params, repo, prev_template_id=None, rng_seed=1)
    r_fb2 = process_message("jadwal pertandingan bola", snapshot, params, repo, prev_template_id=r_fb1.template_id, rng_seed=2)
    assert r_fb1.template_id != r_fb2.template_id


def test_prd_acceptance_r11_glossary_meaning_in_parentheses(temp_db: sqlite3.Connection) -> None:
    snapshot = NluSnapshot.from_db(temp_db)
    params = EngineParams()
    repo = Repository(temp_db)

    reply = process_message("tampilkan menu a la carte", snapshot, params, repo)

    # Memastikan kategori Prancis selalu diikuti artinya dalam tanda kurung
    assert "Les Entrées (hidangan pembuka)" in reply.text or "les entrees (hidangan pembuka)" in reply.text.lower()
    assert "Les Plats (hidangan utama)" in reply.text or "les plats (hidangan utama)" in reply.text.lower()
    assert "Les Fromages (hidangan keju)" in reply.text or "les fromages (hidangan keju)" in reply.text.lower()
    assert "Les Desserts (hidangan penutup)" in reply.text or "les desserts (hidangan penutup)" in reply.text.lower()
