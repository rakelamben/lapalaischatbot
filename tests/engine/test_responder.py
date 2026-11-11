"""
Unit test untuk generator respons (app/engine/responder.py).
Memverifikasi kepatuhan terhadap PRD R6, R7, R10, dan R11.
"""

from __future__ import annotations

from pathlib import Path

from app.engine.handlers.base import HandlerResult
from app.engine.params import EngineParams
from app.engine.responder import Responder
from app.engine.snapshot import NluSnapshot
from app.engine.types import Analysis, Decision, Entities, PriceEntity


def get_snapshot() -> NluSnapshot:
    seed_dir = Path(__file__).resolve().parent.parent.parent / "seed"
    return NluSnapshot.from_seed_dir(seed_dir)


def test_prd_r6_no_repeat_previous_template() -> None:
    snapshot = get_snapshot()
    responder = Responder(snapshot)

    # Dapatkan template intent reservasi
    res_intent = snapshot.intents["reservasi"]
    templates = res_intent.templates
    assert len(templates) == 3

    first_id = templates[0][0]

    # Pilih 100 kali berturut-turut dengan prev_template_id = first_id
    # Tidak boleh ada yang memilih first_id
    for _ in range(100):
        chosen_id, _ = responder.select_template(templates, prev_template_id=first_id)
        assert chosen_id != first_id
        assert chosen_id in (templates[1][0], templates[2][0])


def test_prd_r7_diet_disclaimer_always_present() -> None:
    snapshot = get_snapshot()
    responder = Responder(snapshot)

    analysis = Analysis(
        raw_message="menu vegetarian",
        clean_tokens=["menu", "vegetarian"],
        score_tokens=frozenset(["menu", "vegetarian"]),
        entities=Entities(diet=("vegetarian",)),
        ranking=[],
        decision=Decision("diet", "ambang"),
    )

    handler_result = HandlerResult(content="• Velouté — sup krim — Rp285.000")
    reply = responder.generate_reply(analysis, handler_result)

    disclaimer = snapshot.fixed_text["diet_disclaimer"]
    assert disclaimer in reply.text


def test_prd_r11_glossary_annotation() -> None:
    snapshot = get_snapshot()
    responder = Responder(snapshot)

    analysis = Analysis(
        raw_message="menu a la carte",
        clean_tokens=["menu", "a_la_carte"],
        score_tokens=frozenset(["menu", "a_la_carte"]),
        entities=Entities(),
        ranking=[],
        decision=Decision("a_la_carte", "ambang"),
    )

    # Konten memuat istilah Prancis kategori 'Les Entrées' dan teknik 'sous-vide'
    handler_result = HandlerResult(
        content="\n[Les Entrées]\n• Hidangan bebek sous-vide lezat.",
        protected_spans=[],
    )
    reply = responder.generate_reply(analysis, handler_result)

    # Pastikan 'Les Entrées' dan 'sous-vide' diikuti maknanya dalam kurung
    assert "Les Entrées (hidangan pembuka)" in reply.text or "les entrees (hidangan pembuka)" in reply.text.lower()
    assert "sous-vide (memasak dalam kantong vakum dengan air bersuhu rendah yang stabil)" in reply.text


def test_protected_spans_not_double_annotated() -> None:
    snapshot = get_snapshot()
    responder = Responder(snapshot)

    analysis = Analysis(
        raw_message="teknik masak",
        clean_tokens=["teknik"],
        score_tokens=frozenset(["teknik"]),
        entities=Entities(),
        ranking=[],
        decision=Decision("teknik", "ambang"),
    )

    # Nama hidangan atau baris teknik dilindungi
    istilah = "confit"
    makna = "memasak perlahan dalam lemak hingga empuk"
    handler_result = HandlerResult(
        content=f"• {istilah}: {makna}",
        protected_spans=[istilah, makna],
    )
    reply = responder.generate_reply(analysis, handler_result)

    # Istilah yang dilindungi tidak boleh menjadi 'confit (memasak...): makna (memasak...)'
    assert reply.text.count(makna) == 1
